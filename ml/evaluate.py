"""Helpers d'evaluation et de logging MLflow partages entre tous les modeles.

Metriques + courbes + sauvegarde modele (avec fallback gzip si le serveur
MLflow refuse l'artefact, limite nginx 413).
"""

from __future__ import annotations

import gzip
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)


# --------------------------------------------------------------------------- #
# Metriques
# --------------------------------------------------------------------------- #
def clf_metrics(y_true, proba, threshold: float = 0.5) -> dict:
    pred = (proba >= threshold).astype(int)
    return {
        "pr_auc": average_precision_score(y_true, proba),
        "roc_auc": roc_auc_score(y_true, proba),
        "f1": f1_score(y_true, pred, zero_division=0),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "accuracy": accuracy_score(y_true, pred),
    }


def best_threshold(y_true, proba) -> float:
    """Seuil maximisant le F1 (a calibrer sur la validation)."""
    prec, rec, thr = precision_recall_curve(y_true, proba)
    if len(thr) == 0:
        return 0.5
    f1 = 2 * prec * rec / (prec + rec + 1e-12)
    return float(thr[int(np.nanargmax(f1[: len(thr)]))])


def reg_metrics(y_true, pred) -> dict:
    return {
        "mae": mean_absolute_error(y_true, pred),
        "rmse": float(np.sqrt(mean_squared_error(y_true, pred))),
        "r2": r2_score(y_true, pred),
    }


def feature_names(pre) -> list[str]:
    try:
        return list(pre.get_feature_names_out())
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# Courbes (logges directement dans MLflow)
# --------------------------------------------------------------------------- #
def log_importance(mlflow, names, values, title, top: int = 20):
    values = np.asarray(values, dtype=float)
    if not len(names):
        names = [f"f{i}" for i in range(len(values))]
    order = np.argsort(values)[::-1][:top]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh([names[i] for i in order][::-1], values[order][::-1])
    ax.set_title(title)
    fig.tight_layout()
    mlflow.log_figure(fig, "feature_importance.png")
    plt.close(fig)


def log_clf_plots(mlflow, y_true, proba, threshold):
    prec, rec, _ = precision_recall_curve(y_true, proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title(f"Courbe PR (test) - AP={average_precision_score(y_true, proba):.3f}")
    fig.tight_layout(); mlflow.log_figure(fig, "pr_curve_test.png"); plt.close(fig)

    fpr, tpr, _ = roc_curve(y_true, proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr); ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR")
    ax.set_title(f"Courbe ROC (test) - AUC={roc_auc_score(y_true, proba):.3f}")
    fig.tight_layout(); mlflow.log_figure(fig, "roc_curve_test.png"); plt.close(fig)

    cm = confusion_matrix(y_true, (proba >= threshold).astype(int))
    fig, ax = plt.subplots(figsize=(4.5, 4))
    im = ax.imshow(cm, cmap="Blues")
    for (i, j), v in np.ndenumerate(cm):
        ax.text(j, i, str(v), ha="center", va="center")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xlabel("Predit"); ax.set_ylabel("Reel")
    ax.set_title(f"Matrice de confusion (seuil={threshold:.2f})")
    fig.colorbar(im); fig.tight_layout()
    mlflow.log_figure(fig, "confusion_matrix_test.png"); plt.close(fig)


def log_reg_plots(mlflow, y_true, pred):
    y_true = np.asarray(y_true); pred = np.asarray(pred)
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(y_true, pred, s=4, alpha=0.2)
    lims = [float(min(y_true.min(), pred.min())), float(max(y_true.max(), pred.max()))]
    ax.plot(lims, lims, "--", color="red")
    ax.set_xlabel("RUL reel (jours)"); ax.set_ylabel("RUL predit (jours)")
    ax.set_title("Predit vs reel (test)")
    fig.tight_layout(); mlflow.log_figure(fig, "pred_vs_actual_test.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(y_true - pred, bins=60)
    ax.set_xlabel("Residu (reel - predit)"); ax.set_title("Distribution des residus (test)")
    fig.tight_layout(); mlflow.log_figure(fig, "residuals_test.png"); plt.close(fig)


# --------------------------------------------------------------------------- #
# Lineage + sauvegarde modele
# --------------------------------------------------------------------------- #
def log_dataset_lineage(mlflow, train_df, target):
    try:
        ds = mlflow.data.from_pandas(train_df, name="sensor_events_train", targets=target)
        mlflow.log_input(ds, context="training")
    except Exception as exc:
        print("  (lineage dataset non logge:", exc, ")")


def log_model_safe(mlflow, pipe, X_example, signature, model_name):
    """Logge le pipeline sklearn ; fallback gzip(cloudpickle) si le serveur
    refuse l'artefact (413)."""
    try:
        mlflow.sklearn.log_model(
            pipe, name=model_name, input_example=X_example.head(5),
            signature=signature, serialization_format="cloudpickle",
        )
        mlflow.set_tag("model_artifact", "mlflow_sklearn")
    except Exception as exc:
        print(f"  log_model flavor KO ({type(exc).__name__}) -> fallback gzip")
        import cloudpickle
        tmp = Path(tempfile.mkdtemp())
        with gzip.open(str(tmp / f"{model_name}.pkl.gz"), "wb") as fout:
            cloudpickle.dump(pipe, fout)
        mlflow.log_artifact(str(tmp / f"{model_name}.pkl.gz"), artifact_path="model_fallback")
        mlflow.set_tag("model_artifact", "gzip_fallback")


def log_keras_artifacts(mlflow, keras_model, preprocessor, model_name):
    """Logge un modele Keras (.keras) + le preprocessor sklearn (joblib).

    On loggue des artefacts bruts (pas de flavor mlflow.tensorflow) : robuste
    face aux incompatibilites de version et largement sous la limite 413.
    L'inference = charger preprocessor.joblib puis le .keras.
    """
    import joblib

    tmp = Path(tempfile.mkdtemp())
    model_path = tmp / f"{model_name}.keras"
    keras_model.save(model_path)
    joblib.dump(preprocessor, tmp / "preprocessor.joblib")
    mlflow.log_artifact(str(model_path), artifact_path="model")
    mlflow.log_artifact(str(tmp / "preprocessor.joblib"), artifact_path="model")
    mlflow.set_tag("model_artifact", "keras+joblib")
