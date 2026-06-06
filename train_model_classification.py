import os
import json
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
    classification_report,
)
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier


# ============================================================
# CONFIGURATION
# ============================================================

DATA_PATH = "data/clean/scada_capteurs_propre.csv"
ARTIFACT_DIR = "artifacts"
TARGET = "Failure_Within_7_Days"

os.makedirs(ARTIFACT_DIR, exist_ok=True)


# ============================================================
# CHARGEMENT DES DONNÉES
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

# On garde seulement les colonnes réellement présentes dans le CSV
features = [col for col in features if col in df.columns]

if not features:
    raise ValueError("Aucune variable explicative disponible pour entraîner les modèles.")

X = df[features]
y = df[TARGET].astype(int)

print("\n=== Répartition de la cible ===")
print(y.value_counts())
print("\n=== Proportion de la cible ===")
print(y.value_counts(normalize=True))


# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y,
)


# ============================================================
# MODÈLES À COMPARER
# ============================================================

models = {
    "LogisticRegression": Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=1000, random_state=42)),
    ]),
    "DecisionTreeClassifier": DecisionTreeClassifier(
        random_state=42,
        max_depth=5,
    ),
    "RandomForestClassifier": RandomForestClassifier(
        n_estimators=200,
        random_state=42,
        class_weight="balanced",
    ),
    "GradientBoostingClassifier": GradientBoostingClassifier(
        random_state=42,
    ),
}

results = []
best_model = None
best_model_name = None
best_f1 = -1


# ============================================================
# ENTRAÎNEMENT ET ÉVALUATION
# ============================================================

for model_name, model in models.items():
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)[:, 1]
        roc_auc = roc_auc_score(y_test, y_proba)
    else:
        y_proba = None
        roc_auc = None

    metrics = {
        "model": model_name,
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
        "roc_auc": roc_auc,
    }

    results.append(metrics)

    print(f"\n=== {model_name} ===")
    print(metrics)
    print("Matrice de confusion :")
    print(confusion_matrix(y_test, y_pred))
    print("Rapport de classification :")
    print(classification_report(y_test, y_pred, zero_division=0))

    if metrics["f1_score"] > best_f1:
        best_f1 = metrics["f1_score"]
        best_model = model
        best_model_name = model_name


# ============================================================
# SAUVEGARDE DES RÉSULTATS
# ============================================================

results_df = pd.DataFrame(results).sort_values(by="f1_score", ascending=False)
results_csv_path = os.path.join(ARTIFACT_DIR, "classification_model_comparison.csv")
results_df.to_csv(results_csv_path, index=False)

best_model_path = os.path.join(ARTIFACT_DIR, "best_failure_classifier.pkl")
joblib.dump(best_model, best_model_path)

metadata = {
    "target": TARGET,
    "features_used": features,
    "best_model": best_model_name,
    "selection_metric": "f1_score",
    "best_f1_score": best_f1,
    "results": results,
}

metadata_path = os.path.join(ARTIFACT_DIR, "classification_model_comparison.json")
with open(metadata_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4, ensure_ascii=False)

print("\n=== COMPARAISON FINALE DES MODÈLES ===")
print(results_df)

print("\nMeilleur modèle retenu :", best_model_name)
print("F1-score du meilleur modèle :", round(best_f1, 4))
print("\nFichiers générés :")
print("-", results_csv_path)
print("-", metadata_path)
print("-", best_model_path)
