import csv
import json
from pathlib import Path

ROOT = Path(__file__).parents[3]
BRANCHES = ROOT / "data/etl/reviewed/kiwiharvest-branches.v1.json"
RECIPIENTS = ROOT / "data/etl/reviewed/recipient-candidates.v1.csv"
POLICY = ROOT / "data/etl/reviewed/kiwiharvest-food-policy.v1.json"


def test_reviewed_branches_are_exactly_two_public_reference_points() -> None:
    document = json.loads(BRANCHES.read_text(encoding="utf-8"))
    branches = document["branches"]

    assert len(branches) == 2
    assert {branch["branch_name"] for branch in branches} == {
        "Auckland & HQ — Highbrook",
        "North Shore — Rosedale",
    }
    for branch in branches:
        assert branch["coordinate_status"] == "public_approximate"
        assert branch["operational_point"] is False
        assert branch["is_entrance_or_loading_bay"] is False
        assert branch["reference_only"] is True
        assert branch["route_ready"] is False
        assert branch["relationship_evidence"] == "current-public"
        assert branch["public_address_source_urls"] == ["https://www.kiwiharvest.org.nz/contact-us"]
        assert branch["coordinate_provenance"] == "docs/research.md"
        assert branch["coordinate_method"] == "ArcGIS World Geocoding Service"
        assert branch["coordinate_source_urls"] == [
            "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer"
        ]


def test_reviewed_recipients_preserve_counts_periods_unknowns_and_truth_boundary() -> None:
    with RECIPIENTS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 60
    assert len({row["organisation_name"] for row in rows}) == 60
    assert sum(bool(row["latitude"]) and bool(row["longitude"]) for row in rows) == 58
    assert {row["organisation_name"] for row in rows if row["coordinate_status"] == "unknown"} == {
        "Hapori Tautua Collective",
        "The Koha Shed - West Auckland",
    }
    assert {row["point_class"] for row in rows} <= {"A", "I", "S", "H", "U"}
    assert sum(row["relationship_evidence"] == "FY25-snapshot" for row in rows) == 51
    assert sum(row["relationship_evidence"] == "current-public" for row in rows) == 6
    assert sum(row["relationship_evidence"] == "FY25-snapshot;current-public" for row in rows) == 3
    assert {
        row["organisation_name"]
        for row in rows
        if row["relationship_evidence"] == "FY25-snapshot;current-public"
    } == {
        "Island Child Charitable Trust",
        "Kootuitui ki Papakura",
        "Māngere Budgeting Services Trust",
    }
    assert all(row["reference_only"] == "true" and row["route_ready"] == "false" for row in rows)
    assert all(row["fy25_source_url"] for row in rows if row["fy25_report_name"])
    assert all(not row["fy25_source_url"] for row in rows if not row["fy25_report_name"])
    assert sum(bool(row["current_relationship_source_urls"]) for row in rows) == 9
    assert all(
        row["current_relationship_source_urls"].startswith("https://www.kiwiharvest.org.nz/")
        for row in rows
        if row["current_relationship_source_urls"]
    )
    assert all(
        not row["current_relationship_source_urls"]
        for row in rows
        if row["fy25_report_name"] and not row["current_public_name"]
    )
    assert all(
        row["current_status_or_location_source_urls"] for row in rows if row["fy25_report_name"]
    )
    assert sum(row["coordinate_provenance"] == "docs/research.md" for row in rows) == 58
    assert sum(row["coordinate_provenance"] == "unknown" for row in rows) == 2
    assert all(
        row["coordinate_method"] == "unknown"
        for row in rows
        if row["coordinate_status"] == "unknown"
    )
    assert all(
        row["coordinate_method"] != "unknown"
        for row in rows
        if row["coordinate_status"] != "unknown"
    )

    expected_fy25_names = {
        "ATC Vision College - Papakura Campus",
        "Auckland Women\u2019s Centre - Single Mum\u2019s Group",
        "Auckland Women\u2019s Refuge",
        "Awataha Marae",
        "Baverstock Oaks School",
        "Beachhaven Food Bank",
        "Blue Light Otara",
        "Blue Light Papakura",
        "C3 Cares Albany",
        "CAB Glen Innes Foodbank",
        "Church Unlimited Auckland City Campus",
        "Everybody Eats Glen Innes",
        "Everybody Eats Onehunga",
        "Feed the Streets (Kai Avondale)",
        "Genesis Youth Trust - Glen Innes",
        "Genesis Youth Trust - Mangere",
        "Genesis Youth Trust - Manurewa",
        "Grandparents raising Grandchildren Trust NZ - Papakura Support Group",
        "Howick College",
        "Island Child Charitable Trust",
        "Kootuitui ki Papakura",
        "Mairangi Bay Community Church",
        "Mangere Budgeting Services Trust",
        "Manukau City Baptist Church",
        "Manukau Institute of Technology - SSTS",
        "Manurewa Soup Kitchen",
        "North Shore Women\u2019s Centre",
        "Onehunga Community Embracing Families and Homeless in Need",
        "Otahuhu Maori Wardens",
        "Papakura Marae",
        "Reconnect Family Services Manukau",
        "Reconnect Family Services New Lynn",
        "Ronald McDonald House Auckland",
        "Roskill South Oasis",
        "Ruapotaka Marae Incorporated Society",
        "Shine Mt Albert",
        "Shine North Shore",
        "South Auckland Family Refuge Papatoetoe",
        "St Columba Anglican Church Grey Lynn",
        "Strive Community Trust Manurewa",
        "Te Whare Aio - Manurewa Women\u2019s Refuge",
        "Te Whare Marama O Mangere Women\u2019s Refuge",
        "Te Whare O Nga Tumanako Women\u2019s Refuge",
        "The Koha Shed - West Auckland",
        "The Otara Kai Village",
        "The Salvation Army Glenfield Foodbank",
        "The Salvation Army Hibiscus Coast",
        "The Salvation Army Manukau Foodbank",
        "The Salvation Army Rosedale",
        "Vaka Tautua - Manukau",
        "Waitakere College",
        "Whanau Resource Centre o Pukekohe Charitable Trust",
        "Whangaparoa Baptist Church Foodbank",
        "Women\u2019s Refuge Tamaki Makaurau",
    }
    expected_current_names = {
        "Island Child Charitable Trust",
        "Kootuitui ki Papakura",
        "Māngere Budgeting Services Trust\uff0fTātou Social Supermarket",
        "Asylum Seekers Support Trust",
        "Good Care Community Trust",
        "Hapori Tautua Collective",
        "We o Tara\uff0fAccelerating Aotearoa",
        "Windsor Park Baptist Church",
        "Women\u2019s Refuge Auckland network",
    }
    assert {
        row["fy25_report_name"] for row in rows if row["fy25_report_name"]
    } == expected_fy25_names
    assert {
        row["current_public_name"] for row in rows if row["current_public_name"]
    } == expected_current_names
    assert all(
        "safe-house" not in row["public_point_label"].casefold()
        for row in rows
        if row["protected_or_sensitive"] == "true"
    )
    assert not {
        "capacity",
        "need",
        "receiving_window",
        "entrance",
        "onboarding",
    }.intersection(rows[0])


def test_reviewed_food_policy_contains_only_bounded_facts_and_unknown_operations() -> None:
    document = json.loads(POLICY.read_text(encoding="utf-8"))
    assert [item["category"] for item in document["accepted_categories"]] == [
        "ambient",
        "fresh",
        "frozen",
        "prepared",
    ]
    assert {item["condition"] for item in document["rejections"]} == {
        "recalled",
        "opened",
        "previously_served",
        "spoiled",
    }
    assert {item["rule"] for item in document["handling_boundaries"]} == {
        "chilled_temperature",
        "frozen_state",
        "packaging_condition",
    }
    assert {item["mark"] for item in document["date_mark_semantics"]} == {
        "best-before",
        "use-by",
        "baked-on-or-baked-for",
    }
    truth_boundary = document["truth_boundary"]
    for field in (
        "specific_site_acceptance",
        "specific_site_capability",
        "specific_site_capacity",
        "specific_site_need",
        "specific_site_receiving_window",
    ):
        assert truth_boundary[field] == "unknown"
    assert set(document["operational_values_not_materialised"]) >= {
        "current capacity",
        "current need",
        "receiving window",
    }
