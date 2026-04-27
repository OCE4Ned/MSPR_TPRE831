"""
Projet MECHA – Benchmark IA / BI / Données – Industrie 4.0
Génération des graphiques d'annexe pour le rapport de benchmark

Sorties (dossier outputs/) :
  01_architecture_poc.png
  02_matrice_hierarchisation.png
  03_pipeline_alertes.png
  04_roc_curves.png
  05_maintenance_distributions.png
  06_production_distributions.png
  07_qualite_distributions.png
  08_energie_distributions.png
  09_benchmark_heatmap.png
"""

import os
import warnings

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import auc, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils import resample

warnings.filterwarnings("ignore")

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN_DIR = os.path.join(BASE_DIR, "data", "clean")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "#F8F9FA",
        "axes.grid": True,
        "grid.alpha": 0.35,
        "grid.linestyle": "--",
    }
)

C = {
    "blue": "#1B4F72",
    "light_blue": "#2E86C1",
    "sky": "#85C1E9",
    "red": "#C0392B",
    "orange": "#E67E22",
    "green": "#1E8449",
    "purple": "#7D3C98",
    "gray": "#95A5A6",
    "dark": "#2C3E50",
    "teal": "#148F77",
}


def save(name: str):
    path = os.path.join(OUTPUT_DIR, name)
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    print(f"  OK  {name}")


# ============================================================
# CHARGEMENT DES DONNÉES
# ============================================================

print("Chargement des données propres...")
scada = pd.read_csv(os.path.join(CLEAN_DIR, "scada_capteurs_propre.csv"))
gmao = pd.read_csv(os.path.join(CLEAN_DIR, "gmao_propre.csv"))
mes = pd.read_csv(os.path.join(CLEAN_DIR, "mes_propre.csv"))
energie = pd.read_csv(os.path.join(CLEAN_DIR, "energie_propre.csv"))
erp = pd.read_csv(os.path.join(CLEAN_DIR, "erp_propre.csv"))

# ============================================================
# PRÉPARATION DATASET MAINTENANCE (ML)
# ============================================================

# Fusion positionnelle GMAO + SCADA (même séquence temporelle, 300 obs)
maint = pd.concat(
    [
        gmao.reset_index(drop=True),
        scada.drop(columns=["timestamp", "machine_id"]).reset_index(drop=True),
    ],
    axis=1,
)

# Heures de fonctionnement cumulatives par machine (proxy depuis SCADA)
scada_op = scada.copy()
scada_op["Operational_Hours"] = (
    scada_op.groupby("machine_id")["cycle_time_sec"].cumsum() / 3600
)
op_map = scada_op.groupby("machine_id")["Operational_Hours"].max()
maint["Operational_Hours"] = maint["machine_id"].map(op_map)

# Durée de vie restante estimée (proxy métier)
maint["Remaining_Useful_Life_days"] = np.clip(
    500 - maint["Failure_History_Count"] * 15 - maint["Last_Maintenance_Days_Ago"] * 0.5,
    0,
    500,
)

# Cible binaire : maintenance corrective = panne réelle (GMAO)
# "corrective" -> intervention suite à une panne, "preventive" -> planifiée
# maintenance_type est absent de MAINT_FEATURES -> pas de leakage
# Note: "none" était remplacé par NaN puis comblé par ffill dans l'ETL,
# failure_type ne contient donc plus de valeur "none" — maintenance_type est plus fiable.
maint["failure_target"] = (maint["maintenance_type"] == "corrective").astype(int)

# Rééquilibrage des classes
n_pos = maint["failure_target"].sum()
n_neg = len(maint) - n_pos
n_bal = min(n_pos, n_neg)

df_pos = resample(maint[maint["failure_target"] == 1], n_samples=n_bal, random_state=42)
df_neg = resample(maint[maint["failure_target"] == 0], n_samples=n_bal, random_state=42)
maint_bal = pd.concat([df_pos, df_neg]).reset_index(drop=True)

print(f"Dataset maintenance équilibré : {len(maint_bal)} lignes ({n_bal} par classe)")

MAINT_FEATURES = [
    "Last_Maintenance_Days_Ago",
    "Maintenance_History_Count",
    "Failure_History_Count",
    "downtime_minutes",
    "Temperature_C",
    "Vibration_mms",
    "Sound_dB",
    "Oil_Level_pct",
    "Coolant_Level_pct",
    "Hydraulic_Pressure_bar",
    "Coolant_Flow_L_min",
    "Heat_Index",
    "Power_Consumption_kW",
    "cycle_time_sec",
    "Operational_Hours",
]

X = maint_bal[MAINT_FEATURES].fillna(0)
y = maint_bal["failure_target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y
)
scaler = StandardScaler()
Xs_train = scaler.fit_transform(X_train)
Xs_test = scaler.transform(X_test)

# ============================================================
# ANNEXE 1 – ARCHITECTURE POC
# ============================================================

print("\nGénération des graphiques...")

fig, ax = plt.subplots(figsize=(15, 5))
ax.set_facecolor("white")
ax.set_xlim(0, 15)
ax.set_ylim(0, 5)
ax.axis("off")
ax.set_title(
    "Architecture PoC – Flux de données Projet MECHA",
    fontsize=13,
    fontweight="bold",
    pad=14,
)

layers = [
    (1.5, "Sources\nDonnées", ["SCADA", "MES", "ERP", "GMAO"], C["blue"]),
    (4.2, "Stockage /\nTraitement", ["InfluxDB", "Python/Pandas", "ETL Airflow"], C["purple"]),
    (7.5, "BI /\nMonitoring", ["Power BI", "Grafana", "Dashboards KPI"], C["teal"]),
    (10.8, "IA / Modèles", ["Random Forest", "Grad. Boosting", "Isolation Forest"], C["orange"]),
    (13.5, "Alertes", ["[!] Critique", "[~] Majeure", "[i] Mineure"], C["red"]),
]

for x, title, items, color in layers:
    rect = mpatches.FancyBboxPatch(
        (x - 1.3, 0.3),
        2.6,
        4.4,
        boxstyle="round,pad=0.15",
        facecolor=color,
        edgecolor="white",
        linewidth=2,
        alpha=0.92,
        zorder=2,
    )
    ax.add_patch(rect)
    ax.text(
        x,
        4.25,
        title,
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="white",
        zorder=3,
    )
    for i, item in enumerate(items):
        iy = 3.1 - i * 0.82
        sub = mpatches.FancyBboxPatch(
            (x - 1.1, iy - 0.28),
            2.2,
            0.58,
            boxstyle="round,pad=0.05",
            facecolor="white",
            edgecolor=color,
            linewidth=1,
            alpha=0.96,
            zorder=3,
        )
        ax.add_patch(sub)
        ax.text(
            x,
            iy + 0.01,
            item,
            ha="center",
            va="center",
            fontsize=7.5,
            color=color,
            fontweight="medium",
            zorder=4,
        )

for i in range(len(layers) - 1):
    x1 = layers[i][0] + 1.3
    x2 = layers[i + 1][0] - 1.3
    ax.annotate(
        "",
        xy=(x2, 2.5),
        xytext=(x1, 2.5),
        arrowprops=dict(arrowstyle="-|>", color=C["dark"], lw=2, mutation_scale=16),
    )

plt.tight_layout()
save("01_architecture_poc.png")

# ============================================================
# ANNEXE 2 – MATRICE DE HIÉRARCHISATION
# ============================================================

solutions = {
    "Random Forest": (0.20, 0.88, C["green"], 220),
    "Gradient Boosting": (0.32, 0.92, C["green"], 220),
    "Isolation Forest": (0.24, 0.74, C["green"], 190),
    "K-means": (0.22, 0.58, C["teal"], 160),
    "ARIMA / Prophet": (0.30, 0.64, C["teal"], 160),
    "Power BI": (0.14, 0.87, C["green"], 200),
    "Grafana": (0.17, 0.76, C["green"], 185),
    "Docker": (0.28, 0.68, C["teal"], 160),
    "MLflow": (0.45, 0.55, C["orange"], 145),
    "Apache Airflow": (0.56, 0.60, C["orange"], 150),
    "LSTM": (0.76, 0.58, C["red"], 160),
    "Autoencoders": (0.82, 0.48, C["red"], 145),
    "Azure ML": (0.84, 0.42, C["red"], 185),
}

fig, ax = plt.subplots(figsize=(12, 8))
ax.axhspan(0.5, 1.0, xmin=0, xmax=0.5, alpha=0.07, color=C["green"])
ax.axhspan(0.5, 1.0, xmin=0.5, xmax=1.0, alpha=0.05, color=C["orange"])
ax.axhspan(0.0, 0.5, xmin=0, xmax=0.5, alpha=0.05, color=C["teal"])
ax.axhspan(0.0, 0.5, xmin=0.5, xmax=1.0, alpha=0.07, color=C["red"])
ax.axhline(y=0.5, color=C["gray"], linestyle="--", lw=1.2)
ax.axvline(x=0.5, color=C["gray"], linestyle="--", lw=1.2)

quad_labels = [
    (0.25, 0.975, "PRIORITÉ POC", C["green"]),
    (0.75, 0.975, "À PLANIFIER", C["orange"]),
    (0.25, 0.025, "UTILE / SECONDAIRE", C["teal"]),
    (0.75, 0.025, "NON PRIORITAIRE", C["red"]),
]
for tx, ty, label, col in quad_labels:
    ax.text(
        tx,
        ty,
        label,
        ha="center",
        va="center" if ty > 0.5 else "center",
        fontsize=8.5,
        fontweight="bold",
        color=col,
        transform=ax.transAxes,
        alpha=0.7,
    )

for name, (x, y, color, sz) in solutions.items():
    ax.scatter(x, y, s=sz, color=color, alpha=0.85, edgecolors="white", linewidth=1.5, zorder=4)
    ax.annotate(
        name,
        (x, y),
        xytext=(x + 0.02, y + 0.025),
        fontsize=8,
        fontweight="medium",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.85),
    )

ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_xlabel("Complexité / Risque PoC  →", fontsize=11)
ax.set_ylabel("Valeur / Priorité PoC  →", fontsize=11)
ax.set_title(
    "Matrice de hiérarchisation – Solutions IA / BI / Données\nProjet MECHA – PoC Industrie 4.0",
    fontsize=12,
    fontweight="bold",
)

legend_items = [
    mpatches.Patch(color=C["green"], label="Prioritaire PoC"),
    mpatches.Patch(color=C["teal"], label="Utile / Secondaire"),
    mpatches.Patch(color=C["orange"], label="Moyen terme"),
    mpatches.Patch(color=C["red"], label="Non prioritaire PoC"),
]
ax.legend(handles=legend_items, loc="lower right", fontsize=9)
plt.tight_layout()
save("02_matrice_hierarchisation.png")

# ============================================================
# ANNEXE 3 – PIPELINE DÉCISIONNEL DES ALERTES
# ============================================================

fig, ax = plt.subplots(figsize=(12, 6))
ax.set_facecolor("white")
fig.patch.set_facecolor("white")
ax.set_xlim(0, 12)
ax.set_ylim(0, 6)
ax.axis("off")
ax.set_title(
    "Pipeline décisionnel des alertes – Projet MECHA",
    fontsize=13,
    fontweight="bold",
    pad=14,
)

nodes = [
    (1.2, 3.0, "Données capteurs\nSCADA / IoT", C["blue"], "white"),
    (3.2, 4.6, "Règles seuils\nERP / MES", C["teal"], "white"),
    (3.2, 1.4, "Détection anomalies\nIsolation Forest", C["purple"], "white"),
    (6.2, 3.0, "Scoring risque\nGradient Boosting", C["orange"], "white"),
    (9.5, 4.5, "ALERTE\nCRITIQUE", C["red"], "white"),
    (9.5, 3.0, "ALERTE\nMAJEURE", C["orange"], "white"),
    (9.5, 1.5, "ALERTE\nMINEURE", C["green"], "white"),
]

bw, bh = 1.7, 0.78
for x, y, label, fc, tc in nodes:
    r = mpatches.FancyBboxPatch(
        (x - bw / 2, y - bh / 2),
        bw,
        bh,
        boxstyle="round,pad=0.1",
        facecolor=fc,
        edgecolor="white",
        linewidth=1.5,
        zorder=3,
    )
    ax.add_patch(r)
    ax.text(x, y, label, ha="center", va="center", fontsize=8.5, fontweight="bold", color=tc, zorder=4)

arrows = [
    (2.05, 3.0, 2.3, 4.6),
    (2.05, 3.0, 2.3, 1.4),
    (4.05, 4.6, 5.3, 3.2),
    (4.05, 1.4, 5.3, 2.8),
    (7.05, 3.0, 8.6, 4.5),
    (7.05, 3.0, 8.6, 3.0),
    (7.05, 3.0, 8.6, 1.5),
]
for x1, y1, x2, y2 in arrows:
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="->", color=C["dark"], lw=1.6),
    )

# Score labels on arrows to alert level
for y_alert, score in [(4.5, "score ≥ 0.8"), (3.0, "0.5 ≤ score < 0.8"), (1.5, "score < 0.5")]:
    ax.text(8.0, y_alert + 0.45, score, ha="center", fontsize=7.5, color=C["dark"], style="italic")

plt.tight_layout()
save("03_pipeline_alertes.png")

# ============================================================
# ANNEXE 4 – COURBES ROC
# ============================================================

models_roc = {
    "Gradient Boosting": (GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, random_state=42), False),
    "Logistic Regression": (LogisticRegression(C=1.0, max_iter=1000, random_state=42), True),
    "Random Forest": (RandomForestClassifier(n_estimators=200, min_samples_leaf=2, random_state=42), False),
    "Decision Tree": (DecisionTreeClassifier(max_depth=6, random_state=42), False),
}
model_colors_roc = {
    "Gradient Boosting": C["blue"],
    "Logistic Regression": C["orange"],
    "Random Forest": C["green"],
    "Decision Tree": C["red"],
}

fig, ax = plt.subplots(figsize=(9, 7))

for name, (model, scaled) in models_roc.items():
    Xt, Xv, yt, yv = (Xs_train, Xs_test, y_train, y_test) if scaled else (X_train, X_test, y_train, y_test)
    model.fit(Xt, yt)
    y_score = model.predict_proba(Xv)[:, 1]
    fpr, tpr, _ = roc_curve(yv, y_score)
    roc_auc = auc(fpr, tpr)
    ax.plot(fpr, tpr, color=model_colors_roc[name], lw=2.2, label=f"{name} : AUC = {roc_auc:.3f}")

ax.plot([0, 1], [0, 1], color=C["gray"], lw=1.5, linestyle="--", label="Aléatoire (AUC = 0.500)")
ax.fill_between([0, 1], [0, 1], alpha=0.04, color=C["gray"])
ax.set_xlim([0.0, 1.0])
ax.set_ylim([0.0, 1.05])
ax.set_xlabel("Taux de Faux Positifs (FPR)", fontsize=11)
ax.set_ylabel("Taux de Vrais Positifs (TPR)", fontsize=11)
ax.set_title(
    "Courbes ROC – Prédiction de panne machine\nProjet MECHA – PoC Industrie 4.0",
    fontsize=12,
    fontweight="bold",
)
ax.legend(loc="lower right", fontsize=10)
plt.tight_layout()
save("04_roc_curves.png")

# ============================================================
# DISTRIBUTIONS MAINTENANCE
# ============================================================

fig, axes = plt.subplots(2, 3, figsize=(15, 9))
fig.suptitle(
    "Distributions – Dataset Maintenance (GMAO + SCADA)", fontsize=14, fontweight="bold", y=0.99
)

dist_maint = [
    ("failure_target", "bar", "Équilibre des classes (cible)", "Classe", C["green"]),
    ("Operational_Hours", "hist", "Heures de fonctionnement", "Heures cumulées", C["blue"]),
    ("Temperature_C", "hist", "Température machine (°C)", "°C", C["orange"]),
    ("Vibration_mms", "hist", "Vibrations (mm/s)", "mm/s", C["purple"]),
    ("Power_Consumption_kW", "hist", "Consommation électrique (kW)", "kW", C["light_blue"]),
    ("Remaining_Useful_Life_days", "hist", "Durée de vie restante (jours)", "Jours", C["teal"]),
]

for idx, (col, kind, title, xlabel, color) in enumerate(dist_maint):
    ax = axes[idx // 3, idx % 3]
    data = maint_bal[col].dropna()

    if kind == "bar":
        counts = data.value_counts().sort_index()
        bars = ax.bar(
            ["Classe 0\n(Sans panne)", "Classe 1\n(Avec panne)"],
            counts.values,
            color=[C["green"], C["red"]],
            edgecolor="white",
            linewidth=1.5,
        )
        for b, v in zip(bars, counts.values):
            ax.text(
                b.get_x() + b.get_width() / 2,
                b.get_height() + 0.5,
                str(v),
                ha="center",
                va="bottom",
                fontweight="bold",
            )
        ax.set_ylim(0, max(counts.values) * 1.18)
        ax.set_ylabel("Nombre d'observations")
    else:
        ax.hist(data, bins=22, color=color, edgecolor="white", linewidth=0.4, alpha=0.88)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Fréquence")

    ax.set_title(title)

plt.tight_layout()
save("05_maintenance_distributions.png")

# ============================================================
# DISTRIBUTIONS PRODUCTION
# ============================================================

fig, axes = plt.subplots(2, 3, figsize=(15, 9))
fig.suptitle(
    "Distributions – Dataset Production (MES + SCADA)", fontsize=14, fontweight="bold", y=0.99
)

dist_prod = [
    (erp, "planned_production_qty", "Quantités planifiées (ERP)", "Quantité", C["blue"]),
    (mes, "actual_production_qty", "Quantités réalisées (MES)", "Quantité", C["light_blue"]),
    (mes, "good_qty", "Pièces conformes", "Quantité", C["green"]),
    (mes, "scrap_qty", "Rebuts", "Quantité rebut", C["red"]),
    (scada, "cycle_time_sec", "Temps de cycle (SCADA)", "Secondes", C["orange"]),
    (mes, "downtime_minutes", "Durée d'arrêt machine (MES)", "Minutes", C["purple"]),
]

for idx, (df_src, col, title, xlabel, color) in enumerate(dist_prod):
    ax = axes[idx // 3, idx % 3]
    ax.hist(df_src[col].dropna(), bins=22, color=color, edgecolor="white", linewidth=0.4, alpha=0.88)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fréquence")

plt.tight_layout()
save("06_production_distributions.png")

# ============================================================
# DISTRIBUTIONS QUALITÉ
# ============================================================

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Distributions – Dataset Qualité (MES)", fontsize=14, fontweight="bold")

# Conformité
conf_counts = mes["is_conforming"].map({True: "Conforme", False: "Non conforme"}).value_counts()
bars = axes[0].bar(
    conf_counts.index,
    conf_counts.values,
    color=[C["green"] if l == "Conforme" else C["red"] for l in conf_counts.index],
    edgecolor="white",
    linewidth=1.5,
)
for b, v in zip(bars, conf_counts.values):
    pct = v / len(mes) * 100
    axes[0].text(
        b.get_x() + b.get_width() / 2,
        b.get_height() + 0.5,
        f"{v}\n({pct:.1f}%)",
        ha="center",
        va="bottom",
        fontweight="bold",
        fontsize=9,
    )
axes[0].set_title("Conformité des pièces")
axes[0].set_ylabel("Nombre")
axes[0].set_ylim(0, max(conf_counts.values) * 1.22)

# Score qualité
axes[1].hist(
    mes["quality_score"].dropna(), bins=22, color=C["blue"], edgecolor="white", linewidth=0.4, alpha=0.88
)
axes[1].set_title("Score de qualité global")
axes[1].set_xlabel("Score (0 – 100)")
axes[1].set_ylabel("Fréquence")

# Types de défauts
defect_counts = mes["defect_type"].value_counts()
colors_def = [C["green"] if d == "no_defect" else C["red"] for d in defect_counts.index]
axes[2].barh(defect_counts.index, defect_counts.values, color=colors_def, edgecolor="white", linewidth=0.8)
axes[2].set_title("Distribution des types de défauts")
axes[2].set_xlabel("Nombre d'occurrences")

plt.tight_layout()
save("07_qualite_distributions.png")

# ============================================================
# DISTRIBUTIONS ÉNERGIE
# ============================================================

fig, axes = plt.subplots(2, 2, figsize=(12, 9))
fig.suptitle("Distributions – Dataset Énergie", fontsize=14, fontweight="bold", y=0.99)

dist_energ = [
    ("energy_consumption_kwh", "Consommation énergétique (kWh)", "kWh", C["blue"]),
    ("compressed_air_usage", "Usage d'air comprimé", "m³/h", C["orange"]),
    ("cooling_water_usage", "Eau de refroidissement", "L/min", C["light_blue"]),
    ("power_peak_kw", "Puissance de pointe (kW)", "kW", C["red"]),
]

for idx, (col, title, xlabel, color) in enumerate(dist_energ):
    ax = axes[idx // 2, idx % 2]
    ax.hist(energie[col].dropna(), bins=22, color=color, edgecolor="white", linewidth=0.4, alpha=0.88)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fréquence")

plt.tight_layout()
save("08_energie_distributions.png")

# ============================================================
# HEATMAP BENCHMARK – COMPARAISON DES SOLUTIONS
# ============================================================

tools = [
    "Random Forest",
    "Gradient Boosting",
    "Isolation Forest",
    "K-means",
    "ARIMA / Prophet",
    "LSTM",
    "Power BI",
    "Grafana",
    "MLflow",
    "Docker",
    "Azure ML",
]

criteria = [
    "Vitesse\nPoC",
    "Performance\nML",
    "Explicabilité\nmétier",
    "Coût\n(5=gratuit)",
    "Scalabilité",
]

# Scores 1-5 (estimés pour le contexte MECHA)
scores = np.array(
    [
        # Vitesse, Perf, Explic, Coût, Scal
        [4, 4, 4, 5, 3],   # Random Forest
        [3, 5, 3, 5, 3],   # Gradient Boosting
        [4, 3, 3, 5, 3],   # Isolation Forest
        [5, 2, 3, 5, 3],   # K-means
        [4, 3, 4, 5, 2],   # ARIMA/Prophet
        [2, 5, 2, 5, 4],   # LSTM
        [5, 3, 5, 3, 3],   # Power BI
        [4, 3, 4, 5, 3],   # Grafana
        [3, 3, 4, 5, 3],   # MLflow
        [4, 3, 4, 5, 4],   # Docker
        [3, 5, 3, 1, 5],   # Azure ML
    ]
)

poc_priority = [True, True, True, True, True, False, True, True, False, True, False]

fig, ax = plt.subplots(figsize=(10, 9))
cmap = plt.get_cmap("RdYlGn")
im = ax.imshow(scores, cmap=cmap, vmin=1, vmax=5, aspect="auto")

ax.set_xticks(range(len(criteria)))
ax.set_xticklabels(criteria, fontsize=9)
ax.set_yticks(range(len(tools)))
ax.set_yticklabels(
    [f"{'★ ' if poc_priority[i] else '  '}{t}" for i, t in enumerate(tools)],
    fontsize=9,
)

for i in range(len(tools)):
    for j in range(len(criteria)):
        v = scores[i, j]
        text_color = "white" if v <= 2 else "black"
        ax.text(j, i, str(v), ha="center", va="center", fontsize=11, fontweight="bold", color=text_color)

cbar = plt.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
cbar.set_label("Score (1 = faible  /  5 = excellent)", fontsize=9)
cbar.set_ticks([1, 2, 3, 4, 5])

ax.set_title(
    "Benchmark des solutions IA / BI / Données – Projet MECHA\n★ = Prioritaire PoC",
    fontsize=12,
    fontweight="bold",
    pad=12,
)

plt.tight_layout()
save("09_benchmark_heatmap.png")

# ============================================================
# RÉSUMÉ
# ============================================================

print(f"\nTous les graphiques ont été générés dans : {OUTPUT_DIR}")
print(f"Fichiers créés :\n")
for f in sorted(os.listdir(OUTPUT_DIR)):
    size_kb = os.path.getsize(os.path.join(OUTPUT_DIR, f)) // 1024
    print(f"  {f}  ({size_kb} Ko)")
