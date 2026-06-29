from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
CLEAN_DIR = BASE_DIR / "data" / "clean"
OUTPUT_DIR = BASE_DIR / "data" / "processed" / "business"


SOURCE_FILES = {
    "energie": CLEAN_DIR / "energie_propre.csv",
    "erp": CLEAN_DIR / "erp_propre.csv",
    "gmao": CLEAN_DIR / "gmao_propre.csv",
    "mes": CLEAN_DIR / "mes_propre.csv",
    "scada": CLEAN_DIR / "scada_capteurs_propre.csv",
}


def build_factories() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "factory_id": "FR01",
                "factory_name": "Usine Lyon",
                "country": "France",
                "city": "Lyon",
                "site_maturity_level": "mature",
                "equipment_level": "recent",
                "sensor_reliability": "high",
                "data_quality_level": "high",
                "maintenance_strategy": "preventive",
                "machine_availability_profile": "stable",
                "oee_profile": "stable",
                "unplanned_downtime_profile": "low",
                "quality_drift_profile": "low",
                "energy_efficiency_profile": "optimized",
                "systems_maturity": "MES/SCADA/GMAO integres",
            },
            {
                "factory_id": "ES01",
                "factory_name": "Usine Madrid",
                "country": "Espagne",
                "city": "Madrid",
                "site_maturity_level": "developing",
                "equipment_level": "heterogeneous_older",
                "sensor_reliability": "medium",
                "data_quality_level": "heterogeneous",
                "maintenance_strategy": "corrective_dominant",
                "machine_availability_profile": "variable",
                "oee_profile": "unstable",
                "unplanned_downtime_profile": "high",
                "quality_drift_profile": "high",
                "energy_efficiency_profile": "variable",
                "systems_maturity": "MES/SCADA/GMAO heterogenes",
            },
        ]
    )


def build_parts() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "product_id": "P001",
                "part_name": "Disque de frein",
                "eligible_factory_ids": "FR01|ES01",
                "product_family": "Freinage automobile",
            },
            {
                "product_id": "P002",
                "part_name": "Carter moteur",
                "eligible_factory_ids": "FR01|ES01",
                "product_family": "Moteur automobile",
            },
            {
                "product_id": "P003",
                "part_name": "Arbre de transmission",
                "eligible_factory_ids": "FR01|ES01",
                "product_family": "Transmission automobile",
            },
            {
                "product_id": "P004",
                "part_name": "Aube de turbine",
                "eligible_factory_ids": "FR01|ES01",
                "product_family": "Turbomachine aéronautique",
            },
            {
                "product_id": "P005",
                "part_name": "Support moteur aéronautique",
                "eligible_factory_ids": "FR01|ES01",
                "product_family": "Structure moteur aéronautique",
            },
            {
                "product_id": "P006",
                "part_name": "Boîtier hydraulique",
                "eligible_factory_ids": "FR01|ES01",
                "product_family": "Hydraulique aéronautique",
            },
        ]
    )


def build_production_lines() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "production_line_id": "FR_L_CARTERS",
                "production_line_name": "Ligne carters moteur",
                "factory_id": "FR01",
                "product_id": "P002",
            },
            {
                "production_line_id": "FR_L_FREINS",
                "production_line_name": "Ligne disques de frein",
                "factory_id": "FR01",
                "product_id": "P001",
            },
            {
                "production_line_id": "FR_L_ARBRES",
                "production_line_name": "Ligne arbres de transmission",
                "factory_id": "FR01",
                "product_id": "P003",
            },
            {
                "production_line_id": "FR_L_QUALITE",
                "production_line_name": "Contrôle qualité précision",
                "factory_id": "FR01",
                "product_id": "P004",
            },
            {
                "production_line_id": "ES_L_CARTERS",
                "production_line_name": "Ligne carters moteur",
                "factory_id": "ES01",
                "product_id": "P002",
            },
            {
                "production_line_id": "ES_L_FOURS",
                "production_line_name": "Traitement thermique précision",
                "factory_id": "ES01",
                "product_id": "P003",
            },
            {
                "production_line_id": "ES_L_AUBES",
                "production_line_name": "Ligne aubes turbine",
                "factory_id": "ES01",
                "product_id": "P004",
            },
            {
                "production_line_id": "ES_L_QUALITE",
                "production_line_name": "Contrôle qualité dimensionnel",
                "factory_id": "ES01",
                "product_id": "P006",
            },
        ]
    )


def build_machine_mapping() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "old_machine_id": "M01",
                "machine_id": "CNC_FR_001",
                "machine_name": "Centre d'usinage Mazak",
                "machine_type": "CNC",
                "factory_id": "FR01",
                "factory_name": "Usine Lyon",
                "country": "France",
                "production_line_id": "FR_L_CARTERS",
                "production_line_name": "Ligne carters moteur",
                "product_family": "Moteur automobile",
                "manufacturer": "Mazak",
                "criticality_level": "high",
                "default_product_id": "P002",
                "machine_generation": "recent",
            },
            {
                "old_machine_id": "M02",
                "machine_id": "LAS_FR_001",
                "machine_name": "Découpe laser Trumpf",
                "machine_type": "Découpe laser",
                "factory_id": "FR01",
                "factory_name": "Usine Lyon",
                "country": "France",
                "production_line_id": "FR_L_FREINS",
                "production_line_name": "Ligne disques de frein",
                "product_family": "Freinage automobile",
                "manufacturer": "Trumpf",
                "criticality_level": "medium",
                "default_product_id": "P001",
                "machine_generation": "recent",
            },
            {
                "old_machine_id": "M03",
                "machine_id": "FOU_FR_001",
                "machine_name": "Four traitement thermique",
                "machine_type": "Four industriel",
                "factory_id": "FR01",
                "factory_name": "Usine Lyon",
                "country": "France",
                "production_line_id": "FR_L_ARBRES",
                "production_line_name": "Ligne arbres de transmission",
                "product_family": "Transmission automobile",
                "manufacturer": "SECO/WARWICK",
                "criticality_level": "critical",
                "default_product_id": "P003",
                "machine_generation": "mid_life",
            },
            {
                "old_machine_id": "M04",
                "machine_id": "QLT_FR_001",
                "machine_name": "Contrôle qualité vision",
                "machine_type": "Contrôle qualité",
                "factory_id": "FR01",
                "factory_name": "Usine Lyon",
                "country": "France",
                "production_line_id": "FR_L_QUALITE",
                "production_line_name": "Contrôle qualité précision",
                "product_family": "Turbomachine aéronautique",
                "manufacturer": "Keyence",
                "criticality_level": "medium",
                "default_product_id": "P004",
                "machine_generation": "recent",
            },
            {
                "old_machine_id": "M05",
                "machine_id": "CNC_ES_001",
                "machine_name": "Centre d'usinage DMG Mori",
                "machine_type": "CNC",
                "factory_id": "ES01",
                "factory_name": "Usine Madrid",
                "country": "Espagne",
                "production_line_id": "ES_L_CARTERS",
                "production_line_name": "Ligne carters moteur",
                "product_family": "Moteur automobile",
                "manufacturer": "DMG Mori",
                "criticality_level": "critical",
                "default_product_id": "P002",
                "machine_generation": "older",
            },
            {
                "old_machine_id": "M06",
                "machine_id": "FOU_ES_001",
                "machine_name": "Four haute température",
                "machine_type": "Four industriel",
                "factory_id": "ES01",
                "factory_name": "Usine Madrid",
                "country": "Espagne",
                "production_line_id": "ES_L_FOURS",
                "production_line_name": "Traitement thermique précision",
                "product_family": "Transmission automobile",
                "manufacturer": "Ipsen",
                "criticality_level": "critical",
                "default_product_id": "P003",
                "machine_generation": "older",
            },
            {
                "old_machine_id": "M07",
                "machine_id": "ROB_ES_001",
                "machine_name": "Robot palettisation",
                "machine_type": "Robot industriel",
                "factory_id": "ES01",
                "factory_name": "Usine Madrid",
                "country": "Espagne",
                "production_line_id": "ES_L_AUBES",
                "production_line_name": "Ligne aubes turbine",
                "product_family": "Turbomachine aéronautique",
                "manufacturer": "Fanuc",
                "criticality_level": "medium",
                "default_product_id": "P004",
                "machine_generation": "older",
            },
            {
                "old_machine_id": "M08",
                "machine_id": "QLT_ES_001",
                "machine_name": "Contrôle qualité dimensionnel",
                "machine_type": "Contrôle qualité",
                "factory_id": "ES01",
                "factory_name": "Usine Madrid",
                "country": "Espagne",
                "production_line_id": "ES_L_QUALITE",
                "production_line_name": "Contrôle qualité dimensionnel",
                "product_family": "Hydraulique aéronautique",
                "manufacturer": "Zeiss",
                "criticality_level": "high",
                "default_product_id": "P006",
                "machine_generation": "mid_life",
            },
        ]
    )


def add_factory_profiles(mapping: pd.DataFrame, factories: pd.DataFrame) -> pd.DataFrame:
    profile_columns = [
        "factory_id",
        "site_maturity_level",
        "equipment_level",
        "sensor_reliability",
        "data_quality_level",
        "maintenance_strategy",
        "machine_availability_profile",
        "oee_profile",
        "unplanned_downtime_profile",
        "quality_drift_profile",
        "energy_efficiency_profile",
        "systems_maturity",
    ]
    return mapping.merge(factories[profile_columns], on="factory_id", how="left")


def read_sources() -> dict[str, pd.DataFrame]:
    missing_files = [str(path) for path in SOURCE_FILES.values() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"Fichiers source introuvables: {', '.join(missing_files)}")

    return {name: pd.read_csv(path) for name, path in SOURCE_FILES.items()}


def assert_all_machines_mapped(df: pd.DataFrame, mapping: pd.DataFrame, dataset_name: str) -> None:
    if "machine_id" not in df.columns:
        return

    source_ids = set(df["machine_id"].dropna().astype(str).unique())
    mapped_ids = set(mapping["old_machine_id"])
    missing = sorted(source_ids - mapped_ids)
    if missing:
        raise ValueError(f"{dataset_name}: machines absentes du mapping: {missing}")


def enrich_machine_dataset(df: pd.DataFrame, mapping: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    assert_all_machines_mapped(df, mapping, dataset_name)

    enriched = df.copy()
    enriched["old_machine_id"] = enriched["machine_id"]
    source_columns_to_preserve = [
        "factory_id",
        "factory_name",
        "country",
        "production_line_id",
        "production_line_name",
        "product_family",
        "manufacturer",
        "criticality_level",
        "machine_generation",
        "site_maturity_level",
        "equipment_level",
        "sensor_reliability",
        "data_quality_level",
        "maintenance_strategy",
        "machine_availability_profile",
        "oee_profile",
        "unplanned_downtime_profile",
        "quality_drift_profile",
        "energy_efficiency_profile",
        "systems_maturity",
    ]
    rename_source_columns = {
        col: f"old_{col}"
        for col in source_columns_to_preserve
        if col in enriched.columns and f"old_{col}" not in enriched.columns
    }
    enriched = enriched.rename(columns=rename_source_columns)

    business_columns = [
        "old_machine_id",
        "machine_id",
        "machine_name",
        "machine_type",
        "factory_id",
        "factory_name",
        "country",
        "production_line_id",
        "production_line_name",
        "product_family",
        "manufacturer",
        "criticality_level",
        "machine_generation",
        "site_maturity_level",
        "equipment_level",
        "sensor_reliability",
        "data_quality_level",
        "maintenance_strategy",
        "machine_availability_profile",
        "oee_profile",
        "unplanned_downtime_profile",
        "quality_drift_profile",
        "energy_efficiency_profile",
        "systems_maturity",
        "default_product_id",
    ]

    enriched = enriched.merge(
        mapping[business_columns],
        on="old_machine_id",
        how="left",
    )
    enriched = enriched.drop(columns=["machine_id_x"]).rename(columns={"machine_id_y": "machine_id"})
    return enriched


def enrich_mes(df: pd.DataFrame, mapping: pd.DataFrame, parts: pd.DataFrame) -> pd.DataFrame:
    source = df.copy()
    source["old_plant_id"] = source["plant_id"]
    source["old_product_id"] = source["product_id"]

    enriched = enrich_machine_dataset(source, mapping, "mes")
    enriched["plant_id"] = enriched["factory_id"]
    enriched["product_id"] = enriched["default_product_id"]

    part_columns = ["product_id", "part_name"]
    enriched = enriched.merge(parts[part_columns], on="product_id", how="left")
    return enriched.drop(columns=["default_product_id"])


def enrich_erp(df: pd.DataFrame, factories: pd.DataFrame, parts: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()

    # L'ancien jeu de données utilisait FR02 comme deuxième usine. La couche métier
    # le rattache explicitement à ES01 pour limiter le PoC à Lyon et Madrid.
    enriched["plant_id"] = enriched["plant_id"].replace({"FR02": "ES01"})

    enriched = enriched.merge(
        factories,
        left_on="plant_id",
        right_on="factory_id",
        how="left",
    )
    enriched = enriched.drop(columns=["factory_id"])
    enriched = enriched.merge(
        parts[["product_id", "part_name", "product_family"]],
        on="product_id",
        how="left",
    )
    return enriched


def write_reference_files(
    factories: pd.DataFrame,
    production_lines: pd.DataFrame,
    parts: pd.DataFrame,
    mapping: pd.DataFrame,
) -> None:
    mapping_public = mapping.drop(columns=["default_product_id"])

    factories.to_csv(OUTPUT_DIR / "factories.csv", index=False)
    production_lines.to_csv(OUTPUT_DIR / "production_lines.csv", index=False)
    parts.to_csv(OUTPUT_DIR / "parts.csv", index=False)
    mapping_public.to_csv(OUTPUT_DIR / "machine_mapping.csv", index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    factories = build_factories()
    parts = build_parts()
    production_lines = build_production_lines()
    mapping = add_factory_profiles(build_machine_mapping(), factories)

    sources = read_sources()

    write_reference_files(factories, production_lines, parts, mapping)

    enrich_machine_dataset(sources["energie"], mapping, "energie").drop(
        columns=["default_product_id"]
    ).to_csv(OUTPUT_DIR / "energie_business.csv", index=False)

    enrich_erp(sources["erp"], factories, parts).to_csv(
        OUTPUT_DIR / "erp_business.csv", index=False
    )

    enrich_machine_dataset(sources["gmao"], mapping, "gmao").drop(
        columns=["default_product_id"]
    ).to_csv(OUTPUT_DIR / "gmao_business.csv", index=False)

    enrich_mes(sources["mes"], mapping, parts).to_csv(
        OUTPUT_DIR / "mes_business.csv", index=False
    )

    enrich_machine_dataset(sources["scada"], mapping, "scada").drop(
        columns=["default_product_id"]
    ).to_csv(OUTPUT_DIR / "scada_capteurs_business.csv", index=False)

    print(f"Fichiers métier générés dans: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
