"""Entrainement XGBoost (classification + regression) avec suivi MLflow.

Lancer depuis la racine du projet :
    python -m ml.train_xgboost --task both     # defaut
    python -m ml.train_xgboost --task clf
    python -m ml.train_xgboost --task reg
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from mlflow.models import infer_signature
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
from sklearn.pipeline import Pipeline

from ml import config, data
from ml.mlflow_setup import init_mlflow


# --------------------------------------------------------------------------- #
# Helpers d'evaluation
# --------------------------------------------------------------------------- #
def clf_metrics(y_true, proba, threshold=0.5) -> dict:
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
    """Seuil maximisant le F1 (calibre sur la validation)."""
    prec, rec, thr = precision_recall_curve(y_true, proba)
    if len(thr) == 0:
        return 0.5
    f1 = 2 * prec * rec / (prec + rec + 1e-12)
    return float(thr[int(np.nanargmax(f1[: len(thr)]))])


def reg_metrics(y_true, pred) -> dict:
    rmse = float(np.sqrt(mean_squared_error(y_true, pred)))
    return {
        "mae": mean_absolute_error(y_true, pred),
        "rmse": rmse,
        "r2": r2_score(y_true, pred),
    }


def feature_names(pre) -> list[str]:
    try:
        return list(pre.get_feature_names_out())
    except Exception:
        return [f"f{i}" for i in range(pre.transform_count_)]


# --------------------------------------------------------------------------- #
# Plots (logges directement dans MLflow)
# --------------------------------------------------------------------------- #
def log_importance(mlflow, model, names, top=20):
    imp = model.feature_importances_
    order = np.argsort(imp)[::-1][:top]
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.barh([names[i] for i in order][::-1], imp[order][::-1])
    ax.set_title("Importance des features (XGBoost)")
    fig.tight_layout()
    mlflow.log_figure(fig, "feature_importance.png")
    plt.close(fig)


def log_clf_plots(mlflow, y_true, proba, threshold):
    # Courbe Precision-Recall
    prec, rec, _ = precision_recall_curve(y_true, proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(rec, prec)
    ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
    ax.set_title(f"Courbe PR (test) - AP={average_precision_score(y_true, proba):.3f}")
    fig.tight_layout(); mlflow.log_figure(fig, "pr_curve_test.png"); plt.close(fig)

    # Courbe ROC
    fpr, tpr, _ = roc_curve(y_true, proba)
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(fpr, tpr); ax.plot([0, 1], [0, 1], "--", color="grey")
    ax.set_xlabel("FPR"); ax.set_ylabel("TPR")
    ax.set_title(f"Courbe ROC (test) - AUC={roc_auc_score(y_true, proba):.3f}")
    fig.tight_layout(); mlflow.log_figure(fig, "roc_curve_test.png"); plt.close(fig)

    # Matrice de confusion (seuil calibre)
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
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.scatter(y_true, pred, s=4, alpha=0.2)
    lims = [float(min(y_true.min(), pred.min())), float(max(y_true.max(), pred.max()))]
    ax.plot(lims, lims, "--", color="red")
    ax.set_xlabel("RUL reel (jours)"); ax.set_ylabel("RUL predit (jours)")
    ax.set_title("Predit vs reel (test)")
    fig.tight_layout(); mlflow.log_figure(fig, "pred_vs_actual_test.png"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(np.asarray(y_true) - np.asarray(pred), bins=60)
    ax.set_xlabel("Residu (reel - predit)"); ax.set_title("Distribution des residus (test)")
    fig.tight_layout(); mlflow.log_figure(fig, "residuals_test.png"); plt.close(fig)


def log_dataset_lineage(mlflow, train_df, target):
    try:
        ds = mlflow.data.from_pandas(
            train_df, name="sensor_events_train", targets=target
        )
        mlflow.log_input(ds, context="training")
    except Exception as exc:  # lineage = best effort
        print("  (lineage dataset non logge:", exc, ")")


def log_model_safe(mlflow, pipe, X_example, signature, model_name):
    """Logge le pipeline (flavor sklearn). Fallback gzip si le serveur refuse
    l'artefact (limite de taille nginx 413)."""
    try:
        mlflow.sklearn.log_model(
            pipe, name=model_name, input_example=X_example.head(5),
            signature=signature, serialization_format="cloudpickle",
        )
        mlflow.set_tag("model_artifact", "mlflow_sklearn")
    except Exception as exc:
        print(f"  log_model flavor KO ({type(exc).__name__}) -> fallback gzip")
        import gzip
        import tempfile

        import joblib

        tmp = Path(tempfile.mkdtemp())
        booster_path = tmp / "booster.ubj"
        pipe.named_steps["model"].get_booster().save_model(str(booster_path))
        with open(booster_path, "rb") as fin, gzip.open(str(tmp / "booster.ubj.gz"), "wb") as fout:
            fout.write(fin.read())
        joblib.dump(pipe.named_steps["pre"], tmp / "preprocessor.joblib")
        mlflow.log_artifact(str(tmp / "booster.ubj.gz"), artifact_path="model_fallback")
        mlflow.log_artifact(str(tmp / "preprocessor.joblib"), artifact_path="model_fallback")
        mlflow.set_tag("model_artifact", "gzip_fallback")


# --------------------------------------------------------------------------- #
# Entrainements
# --------------------------------------------------------------------------- #
def train_clf(mlflow, splits):
    train, val, test = splits
    Xtr, ytr, (num, cat) = data.build_xy(train, "clf")
    Xva, yva, _ = data.build_xy(val, "clf")
    Xte, yte, _ = data.build_xy(test, "clf")

    pre = data.make_preprocessor(num, cat)
    Xtr_p, Xva_p, Xte_p = pre.fit_transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    n_pos = int(ytr.sum())
    spw = (len(ytr) - n_pos) / max(n_pos, 1)
    params = dict(
        n_estimators=800, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        reg_lambda=1.0, objective="binary:logistic", eval_metric="aucpr",
        scale_pos_weight=spw, early_stopping_rounds=50,
        tree_method="hist", random_state=config.RANDOM_STATE, n_jobs=-1,
    )

    with mlflow.start_run(run_name="xgboost-clf"):
        mlflow.set_tags({"model": "xgboost", "task": "classification",
                         "target": config.TARGET_CLF})
        model = xgb.XGBClassifier(**params)
        model.fit(Xtr_p, ytr, eval_set=[(Xva_p, yva)], verbose=False)

        mlflow.log_params(params)
        mlflow.log_params({"n_features": Xtr_p.shape[1],
                           "best_iteration": int(model.best_iteration),
                           "n_train": len(ytr), "pos_rate_train": round(ytr.mean(), 4)})

        for name, Xs, ys in [("train", Xtr_p, ytr), ("val", Xva_p, yva), ("test", Xte_p, yte)]:
            proba = model.predict_proba(Xs)[:, 1]
            for k, v in clf_metrics(ys, proba).items():
                mlflow.log_metric(f"{name}_{k}", v)

        # Seuil calibre sur la validation, applique au test
        thr = best_threshold(yva, model.predict_proba(Xva_p)[:, 1])
        proba_te = model.predict_proba(Xte_p)[:, 1]
        mlflow.log_metric("test_threshold", thr)
        for k, v in clf_metrics(yte, proba_te, thr).items():
            mlflow.log_metric(f"test_tuned_{k}", v)

        log_clf_plots(mlflow, yte, proba_te, thr)
        log_importance(mlflow, model, feature_names(pre))

        pipe = Pipeline([("pre", pre), ("model", model)])
        sig = infer_signature(Xtr.head(50), pipe.predict(Xtr.head(50)))
        log_model_safe(mlflow, pipe, Xtr, sig, model_name="xgboost-clf")
        log_dataset_lineage(mlflow, train, config.TARGET_CLF)

        print(f"[clf] test PR-AUC={average_precision_score(yte, proba_te):.3f} "
              f"recall@{thr:.2f}={recall_score(yte, (proba_te>=thr).astype(int)):.3f}")


def train_reg(mlflow, splits):
    train, val, test = splits
    Xtr, ytr, (num, cat) = data.build_xy(train, "reg")
    Xva, yva, _ = data.build_xy(val, "reg")
    Xte, yte, _ = data.build_xy(test, "reg")

    pre = data.make_preprocessor(num, cat)
    Xtr_p, Xva_p, Xte_p = pre.fit_transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    params = dict(
        n_estimators=800, max_depth=5, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
        reg_lambda=1.0, objective="reg:squarederror", eval_metric="rmse",
        early_stopping_rounds=50, tree_method="hist",
        random_state=config.RANDOM_STATE, n_jobs=-1,
    )

    with mlflow.start_run(run_name="xgboost-reg"):
        mlflow.set_tags({"model": "xgboost", "task": "regression",
                         "target": config.TARGET_REG})
        model = xgb.XGBRegressor(**params)
        model.fit(Xtr_p, ytr, eval_set=[(Xva_p, yva)], verbose=False)

        mlflow.log_params(params)
        mlflow.log_params({"n_features": Xtr_p.shape[1],
                           "best_iteration": int(model.best_iteration),
                           "n_train": len(ytr)})

        for name, Xs, ys in [("train", Xtr_p, ytr), ("val", Xva_p, yva), ("test", Xte_p, yte)]:
            pred = model.predict(Xs)
            for k, v in reg_metrics(ys, pred).items():
                mlflow.log_metric(f"{name}_{k}", v)

        pred_te = model.predict(Xte_p)
        log_reg_plots(mlflow, yte, pred_te)
        log_importance(mlflow, model, feature_names(pre))

        pipe = Pipeline([("pre", pre), ("model", model)])
        sig = infer_signature(Xtr.head(50), pipe.predict(Xtr.head(50)))
        log_model_safe(mlflow, pipe, Xtr, sig, model_name="xgboost-reg")
        log_dataset_lineage(mlflow, train, config.TARGET_REG)

        print(f"[reg] test MAE={mean_absolute_error(yte, pred_te):.2f} j  "
              f"R2={r2_score(yte, pred_te):.3f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["clf", "reg", "both"], default="both")
    args = parser.parse_args()

    mlflow = init_mlflow()
    df = data.load_dataset()
    splits = data.temporal_split(df)
    print(f"Donnees: train={len(splits[0]):,} val={len(splits[1]):,} test={len(splits[2]):,}")

    if args.task in ("clf", "both"):
        train_clf(mlflow, splits)
    if args.task in ("reg", "both"):
        train_reg(mlflow, splits)


if __name__ == "__main__":
    main()
