"""Source ingestion provenance and reusable food product identities."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import Select
from sqlalchemy.types import Uuid

from backend.app.models.base import Base


class ImportBatch(Base):
    """One source-ingestion envelope, such as a form submission or CSV run."""

    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "source_format IN ('structured_form', 'csv', 'external_integration')",
            name="ck_import_batches_source_format",
        ),
        CheckConstraint(
            "status IN ('received', 'completed', 'rejected')",
            name="ck_import_batches_status",
        ),
        CheckConstraint(
            "length(btrim(source_system)) > 0",
            name="ck_import_batches_source_system_nonempty",
        ),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_import_batches_idempotency_key_nonempty",
        ),
        CheckConstraint(
            "completed_at IS NULL OR completed_at >= received_at",
            name="ck_import_batches_completion_time",
        ),
        CheckConstraint(
            "status <> 'rejected' OR rejection_reason IS NOT NULL",
            name="ck_import_batches_rejection_reason",
        ),
        UniqueConstraint(
            "source_system",
            "idempotency_key",
            name="uq_import_batches_source_idempotency",
        ),
        UniqueConstraint(
            "id",
            "source_system",
            name="uq_import_batches_id_source_system",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal identifier for this ingestion envelope.",
    )
    source_system: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Namespace of the producer, such as the platform form or a future adapter.",
    )
    source_format: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="Controlled input boundary: structured_form, csv, or external_integration.",
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Producer key reused on retry so the same batch is not imported twice.",
    )
    external_batch_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Optional source-provided batch identifier; not the internal primary key.",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="received",
        server_default="received",
        comment="Ingest result: received, completed, or rejected.",
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the platform received this source envelope.",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When processing completed; NULL while the batch is not completed.",
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Reason required when the batch is rejected; not a failure lifecycle model.",
    )

    source_records: Mapped[list["SourceRecord"]] = relationship(
        back_populates="import_batch",
        passive_deletes=True,
    )


class SourceRecord(Base):
    """One externally identified source record with provenance and ingest result."""

    __tablename__ = "source_records"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(source_system)) > 0",
            name="ck_source_records_source_system_nonempty",
        ),
        CheckConstraint(
            "length(btrim(source_record_type)) > 0",
            name="ck_source_records_type_nonempty",
        ),
        CheckConstraint(
            "length(btrim(external_record_id)) > 0",
            name="ck_source_records_external_id_nonempty",
        ),
        CheckConstraint(
            "ingest_status IN ('received', 'accepted', 'rejected')",
            name="ck_source_records_ingest_status",
        ),
        CheckConstraint(
            "ingest_status <> 'rejected' OR ingest_message IS NOT NULL",
            name="ck_source_records_rejection_message",
        ),
        ForeignKeyConstraint(
            ["import_batch_id", "source_system"],
            ["import_batches.id", "import_batches.source_system"],
            ondelete="RESTRICT",
            name="fk_source_records_batch_source_system",
        ),
        UniqueConstraint(
            "source_system",
            "source_record_type",
            "external_record_id",
            name="uq_source_records_external_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal source-record identity; never the external record key.",
    )
    import_batch_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        comment="Ingestion envelope that supplied this record.",
    )
    source_system: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Source namespace; must match the linked import batch.",
    )
    source_record_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Producer-defined record kind, such as donation_listing or product.",
    )
    external_record_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Stable source identity used for idempotent re-imports.",
    )
    observed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the source observed the record; NULL means the source did not provide it.",
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When FoodFlow recorded this source record.",
    )
    raw_reference: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Pointer to the source row/submission/object used for provenance.",
    )
    raw_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Optional source snapshot; must not contain secrets or unbounded unrelated data.",
    )
    ingest_status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="received",
        server_default="received",
        comment="Record ingest result: received, accepted, or rejected.",
    )
    ingest_message: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Validation result or rejection message when supplied.",
    )

    import_batch: Mapped[ImportBatch] = relationship(back_populates="source_records")
    food_products: Mapped[list["FoodProduct"]] = relationship(
        back_populates="source_record",
        passive_deletes=True,
    )


class FoodProduct(Base):
    """Reusable product identity; an optional reference for future donation snapshots."""

    __tablename__ = "food_products"
    __table_args__ = (
        CheckConstraint(
            "gtin ~ '^[0-9]{8}$' OR gtin ~ '^[0-9]{12}$' "
            "OR gtin ~ '^[0-9]{13}$' OR gtin ~ '^[0-9]{14}$'",
            name="ck_food_products_gtin_format",
        ),
        UniqueConstraint("gtin", name="uq_food_products_gtin"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Internal reusable product identity; GTIN is not the primary key.",
    )
    gtin: Mapped[str] = mapped_column(
        String(14),
        nullable=False,
        comment="Canonical digits-only GTIN-8/12/13/14; barcode mapping remains optional per item.",
    )
    product_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Current reusable product name; future item snapshots copy facts separately.",
    )
    brand: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Optional reusable brand identity.",
    )
    variant: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Optional size/flavour/variant description.",
    )
    source_record_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_records.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Optional provenance record used to establish this product identity.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When this reusable product identity was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        comment="When the current reusable product fields were last changed.",
    )

    source_record: Mapped[SourceRecord | None] = relationship(
        back_populates="food_products",
    )


def source_record_identity_statement(
    *,
    source_system: str,
    source_record_type: str,
    external_record_id: str,
) -> Select[tuple[SourceRecord]]:
    """Find the canonical source record used to make an import idempotent."""

    return select(SourceRecord).where(
        SourceRecord.source_system == source_system,
        SourceRecord.source_record_type == source_record_type,
        SourceRecord.external_record_id == external_record_id,
    )
