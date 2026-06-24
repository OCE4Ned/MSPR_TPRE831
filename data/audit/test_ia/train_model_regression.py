import json
import os

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================
# CONFIGURATION
# ============================================================

DATA_PATH = "data/clean/scada_capteurs_propre.csv"
RAW_DATA_PATH = "data/raw/scada_capteurs_sale.csv"
ARTIFACT_DIR = "artifacts"
TARGET = "Remaining_Useful_Life_days"
MAX_RUL_DAYS = 365

os.makedirs(ARTIFACT_DIR, exist_ok=True)


# ============================================================
# CHARGEMENT DES DONNEES
# ============================================================

if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(
        f"Fichier introuvable : {DATA_PATH}. "
        "Lance d'abord : python etl_data.py"
    )

df = pd.read_csv(DATA_PATH)

if TARGET not in df.columns:
    raise ValueError(f"La colonne cible '{TARGET}' est absente du dataset.")

features = [
    "cycle_time_sec",
    "Temperature_C",
    "Vibration_mms",
    "Sound_dB",
    "Oil_Level_pct",
    "Coolant_Level_pct",
    "Hydraulic_Pressure_bar",
    "Coolant_Flow_L_min",
    "Heat_Index",
    "Power_Consumption_kW",
    "Operational_Hours",
    "Error_Codes_Last_30_Days",
    "sensor_anomaly_score",
]

features = [col for col in features if col in df.columns]

if not features:
    raise ValueError("Aucune variable explicative disponible pour entrainer les modeles.")

df = df.dropna(subset=features + [TARGET]).copy()

X = df[features]
y = df[TARGET].astype(float)


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
)


# ============================================================
# MODELES A COMPARER
# ============================================================

models = {
    "LinearRegression": Pipeline([
        ("scaler", StandardScaler()),
        ("model", LinearRegression()),
    ]),
    "RandomForestRegressor": RandomForestRegressor(
        n_estimators=300,
        random_state=42,
        min_samples_leaf=3,
    ),
    "GradientBoostingRegressor": GradientBoostingRegressor(
        random_state=42,
    ),
}

results = []
best_model = None
best_model_name = None
best_mae = float("inf")


# ============================================================
# ENTRAINEMENT ET EVALUATION
# ============================================================

for model_name, model in models.items():
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "model": model_name,
        "mae_days": mean_absolute_error(y_test, y_pred),
        "rmse_days": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "r2_score": r2_score(y_test, y_pred),
    }

    results.append(metrics)

    print(f"\n=== {model_name} ===")
    print(metrics)

    if metrics["mae_days"] < best_mae:
        best_mae = metrics["mae_days"]
        best_model = model
        best_model_name = model_name


# ============================================================
# PREDICTIONS METIER
# ============================================================

df["predicted_rul_days"] = np.clip(best_model.predict(X), 0, MAX_RUL_DAYS).round(1)

# Taux de degradation estime : 0% = machine saine, 100% = maintenance urgente.
df["predicted_degradation_rate_pct"] = (
    (1 - (df["predicted_rul_days"] / MAX_RUL_DAYS)) * 100
).clip(0, 100).round(1)

timestamps = pd.to_datetime(df["timestamp"], errors="coerce")

# Les CSV propres historiques peuvent contenir un timestamp mal reconverti.
# Pour calculer une vraie date, on reprend le timestamp brut quand il existe.
if timestamps.dt.year.median() < 2000 and os.path.exists(RAW_DATA_PATH):
    raw_df = pd.read_csv(RAW_DATA_PATH, usecols=["timestamp"])
    raw_timestamps = pd.to_datetime(raw_df.loc[df.index, "timestamp"], errors="coerce")
    timestamps = raw_timestamps.fillna(timestamps)

df["measurement_timestamp"] = timestamps
df["recommended_maintenance_date"] = (
    df["measurement_timestamp"]
    + pd.to_timedelta(np.ceil(df["predicted_rul_days"]), unit="D")
)

df["maintenance_priority"] = pd.cut(
    df["predicted_rul_days"],
    bins=[-1, 7, 30, 90, MAX_RUL_DAYS],
    labels=["urgent", "high", "medium", "low"],
)

prediction_columns = [
    "measurement_timestamp",
    "machine_id",
    "predicted_rul_days",
    "predicted_degradation_rate_pct",
    "recommended_maintenance_date",
    "maintenance_priority",
] + features

predictions_df = df[prediction_columns].sort_values(
    by=["predicted_rul_days", "machine_id"],
    ascending=[True, True],
)


# ============================================================
# SAUVEGARDE DES RESULTATS
# ============================================================

results_df = pd.DataFrame(results).sort_values(by="mae_days", ascending=True)

results_csv_path = os.path.join(ARTIFACT_DIR, "regression_model_comparison.csv")
metadata_path = os.path.join(ARTIFACT_DIR, "regression_model_comparison.json")
best_model_path = os.path.join(ARTIFACT_DIR, "best_rul_regressor.pkl")
predictions_path = os.path.join(ARTIFACT_DIR, "maintenance_predictions.csv")

results_df.to_csv(results_csv_path, index=False)
joblib.dump(best_model, best_model_path)
predictions_df.to_csv(predictions_path, index=False)

metadata = {
    "target": TARGET,
    "target_meaning": "Nombre de jours restants avant maintenance ou panne estimee",
    "features_used": features,
    "best_model": best_model_name,
    "selection_metric": "mae_days",
    "best_mae_days": best_mae,
    "degradation_rate_formula": "predicted_degradation_rate_pct = (1 - predicted_rul_days / 365) * 100",
    "maintenance_date_formula": "recommended_maintenance_date = measurement_timestamp + predicted_rul_days",
    "results": results,
}

with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4, ensure_ascii=False)

print("\n=== COMPARAISON FINALE DES MODELES DE REGRESSION ===")
print(results_df)

print("\nMeilleur modele retenu :", best_model_name)
print("Erreur moyenne absolue du meilleur modele :", round(best_mae, 2), "jours")
print("\nFichiers generes :")
print("-", results_csv_path)
print("-", metadata_path)
print("-", best_model_path)
print("-", predictions_path)

print("\n=== EXEMPLES DE PREDICTIONS MAINTENANCE ===")
print(predictions_df.head(10))
