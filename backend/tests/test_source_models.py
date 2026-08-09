from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import (
    Base,
    FoodProduct,
    ImportBatch,
    SourceRecord,
    source_record_identity_statement,
)


def test_phase_four_registers_source_and_product_tables() -> None:
    tables = set(Base.metadata.tables)

    assert {"import_batches", "source_records", "food_products"} <= tables


def test_import_batch_and_source_record_keep_provenance(
    postgres_session: Session,
) -> None:
    observed_at = datetime(2026, 8, 9, 12, 0, tzinfo=UTC)
    batch = ImportBatch(
        source_system="foodflow_form",
        source_format="structured_form",
        idempotency_key="form-submission-001",
    )
    record = SourceRecord(
        source_system="foodflow_form",
        source_record_type="donation_listing",
        external_record_id="submission-001",
        observed_at=observed_at,
        raw_reference="form://submission-001",
        raw_payload={"barcode": None, "quantity": 25, "unit": "kg"},
        ingest_status="accepted",
    )
    batch.source_records.append(record)
    postgres_session.add(batch)
    postgres_session.commit()

    stored = postgres_session.scalars(
        source_record_identity_statement(
            source_system="foodflow_form",
            source_record_type="donation_listing",
            external_record_id="submission-001",
        )
    ).one()

    assert stored.import_batch_id == batch.id
    assert stored.observed_at == observed_at
    assert stored.raw_payload == {"barcode": None, "quantity": 25, "unit": "kg"}
    assert stored.ingest_status == "accepted"


def test_import_batch_idempotency_key_is_unique_per_source_system(
    postgres_session: Session,
) -> None:
    postgres_session.add(
        ImportBatch(
            source_system="test_csv",
            source_format="csv",
            idempotency_key="fixture-run-001",
        )
    )
    postgres_session.commit()

    postgres_session.add(
        ImportBatch(
            source_system="test_csv",
            source_format="csv",
            idempotency_key="fixture-run-001",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_source_record_external_identity_is_unique_across_batches(
    postgres_session: Session,
) -> None:
    first_batch = ImportBatch(
        source_system="test_csv",
        source_format="csv",
        idempotency_key="fixture-run-001",
    )
    second_batch = ImportBatch(
        source_system="test_csv",
        source_format="csv",
        idempotency_key="fixture-run-002",
    )
    first_batch.source_records.append(
        SourceRecord(
            source_system="test_csv",
            source_record_type="product",
            external_record_id="row-001",
            raw_reference="csv://fixture.csv#row=1",
        )
    )
    second_batch.source_records.append(
        SourceRecord(
            source_system="test_csv",
            source_record_type="product",
            external_record_id="row-001",
            raw_reference="csv://fixture.csv#row=1",
        )
    )
    postgres_session.add_all([first_batch, second_batch])

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_source_record_must_match_linked_batch_source_system(
    postgres_session: Session,
) -> None:
    batch = ImportBatch(
        source_system="foodflow_form",
        source_format="structured_form",
        idempotency_key="form-submission-002",
    )
    postgres_session.add(batch)
    postgres_session.flush()
    postgres_session.add(
        SourceRecord(
            import_batch_id=batch.id,
            source_system="test_csv",
            source_record_type="donation_listing",
            external_record_id="submission-002",
            raw_reference="form://submission-002",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_no_barcode_source_record_does_not_require_product(
    postgres_session: Session,
) -> None:
    batch = ImportBatch(
        source_system="foodflow_form",
        source_format="structured_form",
        idempotency_key="form-submission-no-barcode",
    )
    batch.source_records.append(
        SourceRecord(
            source_system="foodflow_form",
            source_record_type="donation_listing",
            external_record_id="submission-no-barcode",
            raw_reference="form://submission-no-barcode",
            raw_payload={"barcode": None, "product_name": "Loose apples"},
        )
    )
    postgres_session.add(batch)
    postgres_session.commit()

    assert postgres_session.scalars(select(FoodProduct)).all() == []


def test_food_product_has_unique_valid_gtin_and_optional_provenance(
    postgres_session: Session,
) -> None:
    product = FoodProduct(
        gtin="01234567890128",
        product_name="Example yoghurt",
        brand="Example Brand",
    )
    postgres_session.add(product)
    postgres_session.commit()

    stored = postgres_session.get(FoodProduct, product.id)
    assert stored is not None
    assert stored.gtin == "01234567890128"
    assert stored.source_record_id is None

    postgres_session.add(
        FoodProduct(
            gtin="01234567890128",
            product_name="Duplicate yoghurt identity",
        )
    )
    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_food_product_rejects_non_gtin_value(postgres_session: Session) -> None:
    postgres_session.add(
        FoodProduct(
            gtin="not-a-gtin",
            product_name="Invalid product",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_rejected_batch_requires_a_reason(postgres_session: Session) -> None:
    postgres_session.add(
        ImportBatch(
            source_system="test_csv",
            source_format="csv",
            idempotency_key="rejected-run-001",
            status="rejected",
        )
    )

    with pytest.raises(IntegrityError):
        postgres_session.commit()


def test_rejected_source_record_requires_a_message(postgres_session: Session) -> None:
    batch = ImportBatch(
        source_system="test_csv",
        source_format="csv",
        idempotency_key="rejected-record-001",
    )
    batch.source_records.append(
        SourceRecord(
            source_system="test_csv",
            source_record_type="product",
            external_record_id="row-rejected-001",
            raw_reference="csv://fixture.csv#row=2",
            ingest_status="rejected",
        )
    )
    postgres_session.add(batch)

    with pytest.raises(IntegrityError):
        postgres_session.commit()
