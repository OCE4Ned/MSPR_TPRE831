import pandas as pd
import numpy as np
import os

np.random.seed(42)

RAW_DIR = "data/raw"
CLEAN_DIR = "data/clean"

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(CLEAN_DIR, exist_ok=True)

n = 300

timestamps = pd.date_range(
    start="2026-01-01 06:00:00",
    periods=n,
    freq="5min"
)

plant_ids = ["FR01", "FR02"]
lines = ["L01", "L02", "L03"]
machines = ["M01", "M02", "M03", "M04"]
products = ["P001", "P002", "P003"]
batches = ["BATCH001", "BATCH002", "BATCH003"]
work_orders = ["WO1001", "WO1002", "WO1003"]


# ============================================================
# FONCTIONS D'ERREURS
# ============================================================

def add_missing_values(df, percent=0.05):
    df_dirty = df.copy()

    bool_cols = df_dirty.select_dtypes(include=["bool"]).columns
    df_dirty[bool_cols] = df_dirty[bool_cols].astype("object")

    total_cells = df_dirty.size
    n_missing = int(total_cells * percent)

    for _ in range(n_missing):
        row = np.random.randint(0, df_dirty.shape[0])
        col = np.random.choice(df_dirty.columns)
        df_dirty.loc[row, col] = np.nan

    return df_dirty


def add_outliers(df, columns, percent=0.02):
    df_dirty = df.copy()
    n_rows = int(len(df_dirty) * percent)

    for col in columns:
        if col in df_dirty.columns:
            df_dirty[col] = pd.to_numeric(df_dirty[col], errors="coerce")
            rows = np.random.choice(df_dirty.index, n_rows, replace=False)
            mean_value = df_dirty[col].mean()

            if pd.notna(mean_value):
                df_dirty.loc[rows, col] = mean_value * np.random.randint(5, 10)

    return df_dirty


# ============================================================
# NETTOYAGE AVEC LOGIQUE MÉTIER
# ============================================================

def clean_with_business_rules(df):
    df = df.copy()

    df = df.replace(["None", "none", "NULL", "null", "nan", ""], np.nan)

    # ==========================
    # TIMESTAMP
    # ==========================
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

        ts_numeric = df["timestamp"].astype("int64")
        ts_numeric = ts_numeric.replace(-9223372036854775808, np.nan)

        ts_numeric = pd.Series(ts_numeric).interpolate(method="linear")
        df["timestamp"] = pd.to_datetime(ts_numeric)

        df["timestamp"] = df["timestamp"].ffill().bfill()

    # ==========================
    # IDENTIFIANTS INDUSTRIELS
    # ==========================
    for col in ["plant_id", "production_line_id", "machine_id"]:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    # ==========================
    # PRODUCT_ID
    # ==========================
    if "product_id" in df.columns:
        if "work_order_id" in df.columns:
            df["product_id"] = df.groupby("work_order_id")["product_id"].transform(
                lambda x: x.ffill().bfill()
            )

        if "batch_id" in df.columns:
            df["product_id"] = df.groupby("batch_id")["product_id"].transform(
                lambda x: x.ffill().bfill()
            )

        df["product_id"] = df["product_id"].ffill().bfill()

    # ==========================
    # BATCH_ID
    # ==========================
    if "batch_id" in df.columns:
        group_cols = []

        if "machine_id" in df.columns:
            group_cols.append("machine_id")

        if "work_order_id" in df.columns:
            group_cols.append("work_order_id")

        if group_cols:
            df["batch_id"] = df.groupby(group_cols)["batch_id"].transform(
                lambda x: x.ffill().bfill()
            )

        df["batch_id"] = df["batch_id"].ffill().bfill()

    # ==========================
    # WORK_ORDER_ID
    # ==========================
    if "work_order_id" in df.columns:
        if "batch_id" in df.columns:
            df["work_order_id"] = df.groupby("batch_id")["work_order_id"].transform(
                lambda x: x.ffill().bfill()
            )

        df["work_order_id"] = df["work_order_id"].ffill().bfill()

    # ==========================
    # QUANTITÉS PRODUCTION
    # ==========================
    for col in ["planned_production_qty", "actual_production_qty", "good_qty", "scrap_qty"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "planned_production_qty" in df.columns:
        df.loc[df["planned_production_qty"] <= 0, "planned_production_qty"] = np.nan
        df.loc[df["planned_production_qty"] > 3000, "planned_production_qty"] = np.nan
        df["planned_production_qty"] = df["planned_production_qty"].interpolate().ffill().bfill()

    if "actual_production_qty" in df.columns:
        df.loc[df["actual_production_qty"] <= 0, "actual_production_qty"] = np.nan
        df.loc[df["actual_production_qty"] > 2500, "actual_production_qty"] = np.nan
        df["actual_production_qty"] = df["actual_production_qty"].interpolate().ffill().bfill()

    if "good_qty" in df.columns:
        df.loc[df["good_qty"] < 0, "good_qty"] = np.nan
        df.loc[df["good_qty"] > 2500, "good_qty"] = np.nan
        df["good_qty"] = df["good_qty"].interpolate().ffill().bfill()

    if "scrap_qty" in df.columns:
        df.loc[df["scrap_qty"] < 0, "scrap_qty"] = np.nan
        df.loc[df["scrap_qty"] > 500, "scrap_qty"] = np.nan

    if all(col in df.columns for col in ["actual_production_qty", "good_qty", "scrap_qty"]):
        df["good_qty"] = df["good_qty"].fillna(
            df["actual_production_qty"] - df["scrap_qty"]
        )

        df["scrap_qty"] = df["scrap_qty"].fillna(
            df["actual_production_qty"] - df["good_qty"]
        )

        df.loc[df["scrap_qty"] < 0, "scrap_qty"] = 0
        df.loc[df["good_qty"] > df["actual_production_qty"], "good_qty"] = (
            df["actual_production_qty"] - df["scrap_qty"]
        )

        df["scrap_qty"] = df["scrap_qty"].fillna(0)

    # ==========================
    # TEMPS DE CYCLE
    # ==========================
    if "cycle_time_sec" in df.columns:
        df["cycle_time_sec"] = pd.to_numeric(df["cycle_time_sec"], errors="coerce")
        df.loc[
            (df["cycle_time_sec"] < 20) | (df["cycle_time_sec"] > 120),
            "cycle_time_sec"
        ] = np.nan

        if "machine_id" in df.columns:
            df["cycle_time_sec"] = df.groupby("machine_id")["cycle_time_sec"].transform(
                lambda x: x.interpolate().ffill().bfill()
            )
        else:
            df["cycle_time_sec"] = df["cycle_time_sec"].interpolate().ffill().bfill()

    if "target_cycle_time_sec" in df.columns:
        df["target_cycle_time_sec"] = pd.to_numeric(df["target_cycle_time_sec"], errors="coerce")
        df.loc[
            (df["target_cycle_time_sec"] < 20) | (df["target_cycle_time_sec"] > 120),
            "target_cycle_time_sec"
        ] = np.nan
        df["target_cycle_time_sec"] = df["target_cycle_time_sec"].interpolate().ffill().bfill()

    # ==========================
    # VITESSE DE PRODUCTION
    # ==========================
    if "production_speed" in df.columns:
        df["production_speed"] = pd.to_numeric(df["production_speed"], errors="coerce")

        if all(col in df.columns for col in ["actual_production_qty", "cycle_time_sec"]):
            df["production_speed"] = df["production_speed"].fillna(
                df["actual_production_qty"] / df["cycle_time_sec"]
            )

        df["production_speed"] = df["production_speed"].interpolate().ffill().bfill()

    # ==========================
    # MACHINE STATUS
    # ==========================
    if "machine_status" in df.columns:
        df["machine_status"] = df["machine_status"].ffill().bfill()

    # ==========================
    # SHIFT
    # ==========================
    if "shift" in df.columns and "timestamp" in df.columns:
        hours = df["timestamp"].dt.hour

        df["shift"] = np.select(
            [
                (hours >= 6) & (hours < 14),
                (hours >= 14) & (hours < 22),
                (hours >= 22) | (hours < 6)
            ],
            ["matin", "apres_midi", "nuit"],
            default=df["shift"]
        )

    # ==========================
    # QUALITÉ
    # ==========================
    if "dimension_measurement" in df.columns:
        df["dimension_measurement"] = pd.to_numeric(df["dimension_measurement"], errors="coerce")
        df["dimension_measurement"] = df["dimension_measurement"].interpolate().ffill().bfill()

    if "tolerance_min" in df.columns:
        df["tolerance_min"] = pd.to_numeric(df["tolerance_min"], errors="coerce")
        df["tolerance_min"] = df["tolerance_min"].interpolate().ffill().bfill()

    if "tolerance_max" in df.columns:
        df["tolerance_max"] = pd.to_numeric(df["tolerance_max"], errors="coerce")
        df["tolerance_max"] = df["tolerance_max"].interpolate().ffill().bfill()

    if all(col in df.columns for col in ["dimension_measurement", "tolerance_min", "tolerance_max"]):
        df["is_conforming"] = (
            (df["dimension_measurement"] >= df["tolerance_min"]) &
            (df["dimension_measurement"] <= df["tolerance_max"])
        )

    if "defect_type" in df.columns and "is_conforming" in df.columns:
        df.loc[df["is_conforming"] == True, "defect_type"] = "no_defect"
        df["defect_type"] = df["defect_type"].ffill().bfill()

    if "defect_category" in df.columns and "defect_type" in df.columns:
        defect_mapping = {
            "rayure": "esthetique",
            "fissure": "fonctionnel",
            "deformation": "dimensionnel",
            "no_defect": "none"
        }

        df["defect_category"] = df["defect_category"].fillna(
            df["defect_type"].map(defect_mapping)
        )
        df["defect_category"] = df["defect_category"].ffill().bfill()

    if "defect_severity" in df.columns:
        df["defect_severity"] = df["defect_severity"].ffill().bfill()

    if "scrap_flag" in df.columns and "is_conforming" in df.columns:
        df["is_conforming"] = df["is_conforming"].fillna(True).astype(bool)
        df["scrap_flag"] = df["is_conforming"].apply(lambda x: not x)

    if "rework_required" in df.columns and "defect_severity" in df.columns:
        df["rework_required"] = df["rework_required"].fillna(
            df["defect_severity"].isin(["major", "critical"])
        )

    if "quality_score" in df.columns:
        df["quality_score"] = pd.to_numeric(df["quality_score"], errors="coerce")

        if "is_conforming" in df.columns:
            df["quality_score"] = df["quality_score"].fillna(
                pd.Series(np.where(df["is_conforming"], 95, 70), index=df.index)
            )

        df["quality_score"] = df["quality_score"].interpolate().ffill().bfill()

    if "vision_defect_detected" in df.columns:
        df["vision_defect_detected"] = df["vision_defect_detected"].fillna(False)

    if "operator_validation" in df.columns:
        df["operator_validation"] = df["operator_validation"].fillna(False)

    if "inspection_id" in df.columns:
        df["inspection_id"] = df["inspection_id"].ffill().bfill()

    # ==========================
    # CAPTEURS / ÉNERGIE
    # ==========================
    sensor_limits = {
        "Temperature_C": (0, 100),
        "Vibration_mms": (0, 8),
        "Sound_dB": (40, 110),
        "Oil_Level_pct": (0, 100),
        "Coolant_Level_pct": (0, 100),
        "Hydraulic_Pressure_bar": (50, 200),
        "Coolant_Flow_L_min": (0, 80),
        "Heat_Index": (0, 120),
        "Power_Consumption_kW": (0, 120),
        "energy_consumption_kwh": (0, 150),
        "compressed_air_usage": (0, 80),
        "cooling_water_usage": (0, 60),
        "power_peak_kw": (0, 200)
    }

    for col, (min_val, max_val) in sensor_limits.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df.loc[(df[col] < min_val) | (df[col] > max_val), col] = np.nan

            if "machine_id" in df.columns:
                df[col] = df.groupby("machine_id")[col].transform(
                    lambda x: x.interpolate().ffill().bfill()
                )
            else:
                df[col] = df[col].interpolate().ffill().bfill()

    # ==========================
    # MAINTENANCE
    # ==========================
    maintenance_numeric_cols = [
        "Operational_Hours",
        "Installation_Year",
        "Last_Maintenance_Days_Ago",
        "Maintenance_History_Count",
        "Failure_History_Count",
        "Error_Codes_Last_30_Days",
        "repair_time_minutes",
        "downtime_minutes",
        "maintenance_cost",
        "Remaining_Useful_Life_days",
        "predicted_failure_probability",
        "sensor_anomaly_score",
        "AI_Override_Events"
    ]

    for col in maintenance_numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Installation_Year" in df.columns:
        df.loc[
            (df["Installation_Year"] < 1990) | (df["Installation_Year"] > 2026),
            "Installation_Year"
        ] = np.nan
        df["Installation_Year"] = df["Installation_Year"].ffill().bfill()

    if "Error_Codes_Last_30_Days" in df.columns:
        df["Error_Codes_Last_30_Days"] = df["Error_Codes_Last_30_Days"].fillna(0)

    if "repair_time_minutes" in df.columns:
        df.loc[df["repair_time_minutes"] < 0, "repair_time_minutes"] = np.nan
        df.loc[df["repair_time_minutes"] > 500, "repair_time_minutes"] = np.nan

        if "failure_type" in df.columns:
            df["repair_time_minutes"] = df.groupby("failure_type")["repair_time_minutes"].transform(
                lambda x: x.fillna(x.median())
            )

    if "downtime_minutes" in df.columns:
        df.loc[df["downtime_minutes"] < 0, "downtime_minutes"] = np.nan
        df.loc[df["downtime_minutes"] > 500, "downtime_minutes"] = np.nan

    for col in maintenance_numeric_cols:
        if col in df.columns:
            df[col] = df[col].interpolate().ffill().bfill()

    if "Failure_Within_7_Days" in df.columns and "predicted_failure_probability" in df.columns:
        df["Failure_Within_7_Days"] = df["predicted_failure_probability"] >= 0.7

    maintenance_text_cols = [
        "maintenance_event_id",
        "maintenance_type",
        "failure_type",
        "failure_code",
        "failure_severity",
        "technician_id",
        "spare_part_used"
    ]

    for col in maintenance_text_cols:
        if col in df.columns:
            df[col] = df[col].ffill().bfill()

    # ==========================
    # SÉCURITÉ FINALE
    # ==========================
    for col in df.columns:
        if df[col].isna().sum() > 0:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = df[col].interpolate().ffill().bfill()
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].ffill().bfill()
            else:
                df[col] = df[col].ffill().bfill()

    return df


# ============================================================
# 1. ERP
# ============================================================

erp = pd.DataFrame({
    "plant_id": np.random.choice(plant_ids, n),
    "product_id": np.random.choice(products, n),
    "work_order_id": np.random.choice(work_orders, n),
    "planned_production_qty": np.random.randint(900, 1200, n),
    "target_cycle_time_sec": np.random.randint(40, 55, n),
    "shift": np.random.choice(["matin", "apres_midi", "nuit"], n),
    "Installation_Year": np.random.randint(2012, 2022, n),
    "failure_code": np.random.choice(["F001", "F002", "F003", "F004"], n),
    "failure_severity": np.random.choice(["minor", "major", "critical"], n),
    "repair_time_minutes": np.random.randint(20, 180, n),
    "technician_id": np.random.choice(["TECH01", "TECH02", "TECH03"], n),
    "spare_part_used": np.random.choice(["bearing", "pump", "sensor", "none"], n),
    "maintenance_cost": np.random.randint(100, 3000, n),
    "energy_cost": np.random.uniform(20, 150, n).round(2)
})

erp_dirty = add_missing_values(erp, 0.05)
erp_dirty = add_outliers(
    erp_dirty,
    ["planned_production_qty", "repair_time_minutes", "maintenance_cost"],
    0.02
)

erp_dirty.to_csv(f"{RAW_DIR}/erp_sale.csv", index=False)

erp_clean = clean_with_business_rules(erp_dirty)
erp_clean.to_csv(f"{CLEAN_DIR}/erp_propre.csv", index=False)


# ============================================================
# 2. MES
# ============================================================

mes = pd.DataFrame({
    "timestamp": timestamps,
    "production_line_id": np.random.choice(lines, n),
    "machine_id": np.random.choice(machines, n),
    "batch_id": np.random.choice(batches, n),
    "work_order_id": np.random.choice(work_orders, n),
    "actual_production_qty": np.random.randint(850, 1150, n),
    "good_qty": np.random.randint(800, 1100, n),
    "machine_status": np.random.choice(["running", "stopped", "maintenance"], n, p=[0.8, 0.15, 0.05]),
    "downtime_minutes": np.random.randint(0, 60, n),
    "setup_time_minutes": np.random.randint(5, 45, n),
    "operator_id": np.random.choice(["OP01", "OP02", "OP03"], n),
    "inspection_id": [f"INS{i:04d}" for i in range(n)],
    "defect_type": np.random.choice(["rayure", "fissure", "deformation", "no_defect"], n, p=[0.05, 0.03, 0.02, 0.90]),
    "defect_category": np.random.choice(["dimensionnel", "esthetique", "fonctionnel", "none"], n),
    "defect_severity": np.random.choice(["minor", "major", "critical"], n),
    "is_conforming": np.random.choice([True, False], n, p=[0.9, 0.1]),
    "scrap_flag": np.random.choice([True, False], n, p=[0.1, 0.9]),
    "rework_required": np.random.choice([True, False], n, p=[0.15, 0.85]),
    "quality_score": np.random.randint(70, 100, n),
    "vision_defect_detected": np.random.choice([True, False], n, p=[0.12, 0.88]),
    "operator_validation": np.random.choice([True, False], n, p=[0.8, 0.2])
})

mes["scrap_qty"] = mes["actual_production_qty"] - mes["good_qty"]

bad_rows = np.random.choice(mes.index, int(n * 0.03), replace=False)
mes.loc[bad_rows, "scrap_qty"] = -10

mes_dirty = add_missing_values(mes, 0.05)
mes_dirty = add_outliers(
    mes_dirty,
    ["actual_production_qty", "good_qty", "downtime_minutes"],
    0.02
)

mes_dirty.to_csv(f"{RAW_DIR}/mes_sale.csv", index=False)

mes_clean = clean_with_business_rules(mes_dirty)
mes_clean.to_csv(f"{CLEAN_DIR}/mes_propre.csv", index=False)


# ============================================================
# 3. SCADA / CAPTEURS
# ============================================================

scada = pd.DataFrame({
    "timestamp": timestamps,
    "machine_id": np.random.choice(machines, n),
    "cycle_time_sec": np.random.normal(45, 5, n).round(2),
    "Temperature_C": np.random.normal(65, 8, n).round(2),
    "Vibration_mms": np.random.normal(2.5, 0.6, n).round(2),
    "Sound_dB": np.random.normal(75, 5, n).round(2),
    "Oil_Level_pct": np.random.normal(80, 8, n).round(2),
    "Coolant_Level_pct": np.random.normal(75, 10, n).round(2),
    "Hydraulic_Pressure_bar": np.random.normal(120, 15, n).round(2),
    "Coolant_Flow_L_min": np.random.normal(30, 5, n).round(2),
    "Heat_Index": np.random.normal(70, 8, n).round(2),
    "Power_Consumption_kW": np.random.normal(45, 7, n).round(2)
})

scada_dirty = add_missing_values(scada, 0.05)
scada_dirty = add_outliers(
    scada_dirty,
    ["cycle_time_sec", "Temperature_C", "Vibration_mms", "Power_Consumption_kW"],
    0.02
)

scada_dirty.to_csv(f"{RAW_DIR}/scada_capteurs_sale.csv", index=False)

scada_clean = clean_with_business_rules(scada_dirty)
scada_clean.to_csv(f"{CLEAN_DIR}/scada_capteurs_propre.csv", index=False)


# ============================================================
# 4. GMAO
# ============================================================

gmao = pd.DataFrame({
    "maintenance_event_id": [f"MEV{i:04d}" for i in range(n)],
    "timestamp": timestamps,
    "machine_id": np.random.choice(machines, n),
    "Last_Maintenance_Days_Ago": np.random.randint(1, 120, n),
    "Maintenance_History_Count": np.random.randint(0, 30, n),
    "Failure_History_Count": np.random.randint(0, 15, n),
    "maintenance_type": np.random.choice(["preventive", "corrective"], n, p=[0.7, 0.3]),
    "failure_type": np.random.choice(["mechanical", "electrical", "hydraulic", "none"], n),
    "downtime_minutes": np.random.randint(0, 240, n)
})

gmao_dirty = add_missing_values(gmao, 0.05)
gmao_dirty = add_outliers(
    gmao_dirty,
    ["downtime_minutes", "Failure_History_Count"],
    0.02
)

gmao_dirty.to_csv(f"{RAW_DIR}/gmao_sale.csv", index=False)

gmao_clean = clean_with_business_rules(gmao_dirty)
gmao_clean.to_csv(f"{CLEAN_DIR}/gmao_propre.csv", index=False)


# ============================================================
# 5. ÉNERGIE
# ============================================================

energie = pd.DataFrame({
    "timestamp": timestamps,
    "machine_id": np.random.choice(machines, n),
    "energy_consumption_kwh": np.random.normal(35, 6, n).round(2),
    "compressed_air_usage": np.random.normal(20, 4, n).round(2),
    "cooling_water_usage": np.random.normal(15, 3, n).round(2),
    "power_peak_kw": np.random.normal(60, 8, n).round(2)
})

energie_dirty = add_missing_values(energie, 0.05)
energie_dirty = add_outliers(
    energie_dirty,
    [
        "energy_consumption_kwh",
        "compressed_air_usage",
        "cooling_water_usage",
        "power_peak_kw"
    ],
    0.02
)

energie_dirty.to_csv(f"{RAW_DIR}/energie_sale.csv", index=False)

energie_clean = clean_with_business_rules(energie_dirty)
energie_clean.to_csv(f"{CLEAN_DIR}/energie_propre.csv", index=False)


# ============================================================
# CONTRÔLE QUALITÉ FINAL
# ============================================================

print("\nCSV sales générés dans :", RAW_DIR)
print("CSV propres générés dans :", CLEAN_DIR)

print("\nContrôle des valeurs manquantes dans les fichiers propres :")

for file in os.listdir(CLEAN_DIR):
    if file.endswith(".csv"):
        path = os.path.join(CLEAN_DIR, file)
        df_check = pd.read_csv(path)

        missing_count = df_check.isna().sum().sum()

        print(f"\n{file}")
        print("Valeurs manquantes restantes :", missing_count)

        if missing_count > 0:
            print(df_check.isna().sum()[df_check.isna().sum() > 0])