"""Configuration centrale du projet ML (maintenance predictive MECHA).

Deux problemes / deux targets :
  - Classification : failure_within_7_days  (panne dans les 7 jours : 0/1)
  - Regression     : remaining_useful_life_days  (RUL, jours avant defaillance)
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_CSV = PROJECT_ROOT / "data" / "ml" / "sensor_events.csv"

# Colonnes d'identification (pas des features par defaut)
TIME_COL = "event_ts"
ID_COLS = ["event_ts", "machine_id"]

# Targets
TARGET_CLF = "failure_within_7_days"
TARGET_REG = "remaining_useful_life_days"

# Features capteurs numeriques "saines"
NUMERIC_FEATURES = [
    "cycle_time_sec",
    "temperature_c",
    "vibration_mms",
    "sound_db",
    "oil_level_pct",
    "coolant_level_pct",
    "hydraulic_pressure_bar",
    "coolant_flow_l_min",
    "heat_index",
    "power_consumption_kw",
    "operational_hours",
    "error_codes_last_30_days",
    "ai_override_events",
]

# Colonnes a fort risque de FUITE (sorties de modele, pas des mesures capteur).
# Exclues par defaut des features ; a n'utiliser que comme baseline de comparaison.
LEAKY_FEATURES = ["predicted_failure_probability", "sensor_anomaly_score"]

# Categorielles (encodage one-hot).
# machine_id rend le modele "machine-specifique" (8 machines connues) -> optionnel.
CATEGORICAL_FEATURES = ["machine_id", "quality_status"]

# Split temporel (les donnees sont des series temporelles -> pas de split aleatoire)
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# test = le reste (~0.15)

# MLflow
MLFLOW_EXPERIMENT = "mecha-maintenance-predictive"

RANDOM_STATE = 42
