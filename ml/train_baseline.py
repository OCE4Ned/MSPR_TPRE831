"""Baselines simples (references de comparaison) avec suivi MLflow.

  - Classification : LogisticRegression (class_weight='balanced')
  - Regression     : Ridge

Sert a chiffrer la valeur ajoutee reelle des modeles plus complexes
(XGBoost / MLP / LSTM), comme demande par le cahier des charges.

    python -m ml.train_baseline --task both
"""

from __future__ import annotations

import argparse

import numpy as np
from mlflow.models import infer_signature
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, mean_absolute_error, r2_score, recall_score
from sklearn.pipeline import Pipeline

from ml import config, data, evaluate
from ml.mlflow_setup import init_mlflow


def train_clf(mlflow, splits):
    train, val, test = splits
    Xtr, ytr, (num, cat) = data.build_xy(train, "clf")
    Xva, yva, _ = data.build_xy(val, "clf")
    Xte, yte, _ = data.build_xy(test, "clf")

    pre = data.make_preprocessor(num, cat)
    Xtr_p, Xva_p, Xte_p = pre.fit_transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    params = dict(class_weight="balanced", max_iter=1000, C=1.0,
                  random_state=config.RANDOM_STATE, n_jobs=-1)

    with mlflow.start_run(run_name="baseline-logreg-clf"):
        mlflow.set_tags({"model": "logreg", "task": "classification",
                         "target": config.TARGET_CLF})
        model = LogisticRegression(**params)
        model.fit(Xtr_p, ytr)

        mlflow.log_params(params)
        mlflow.log_param("n_features", Xtr_p.shape[1])

        for name, Xs, ys in [("train", Xtr_p, ytr), ("val", Xva_p, yva), ("test", Xte_p, yte)]:
            proba = model.predict_proba(Xs)[:, 1]
            for k, v in evaluate.clf_metrics(ys, proba).items():
                mlflow.log_metric(f"{name}_{k}", v)

        thr = evaluate.best_threshold(yva, model.predict_proba(Xva_p)[:, 1])
        proba_te = model.predict_proba(Xte_p)[:, 1]
        mlflow.log_metric("test_threshold", thr)
        for k, v in evaluate.clf_metrics(yte, proba_te, thr).items():
            mlflow.log_metric(f"test_tuned_{k}", v)

        evaluate.log_clf_plots(mlflow, yte, proba_te, thr)
        evaluate.log_importance(mlflow, evaluate.feature_names(pre),
                                np.abs(model.coef_).ravel(), "Coefficients |w| (LogReg)")

        pipe = Pipeline([("pre", pre), ("model", model)])
        sig = infer_signature(Xtr.head(50), pipe.predict(Xtr.head(50)))
        evaluate.log_model_safe(mlflow, pipe, Xtr, sig, "baseline-logreg-clf")
        evaluate.log_dataset_lineage(mlflow, train, config.TARGET_CLF)

        print(f"[clf] LogReg test PR-AUC={average_precision_score(yte, proba_te):.3f} "
              f"recall@{thr:.2f}={recall_score(yte, (proba_te>=thr).astype(int)):.3f}")


def train_reg(mlflow, splits):
    train, val, test = splits
    Xtr, ytr, (num, cat) = data.build_xy(train, "reg")
    Xva, yva, _ = data.build_xy(val, "reg")
    Xte, yte, _ = data.build_xy(test, "reg")

    pre = data.make_preprocessor(num, cat)
    Xtr_p, Xva_p, Xte_p = pre.fit_transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    params = dict(alpha=1.0, random_state=config.RANDOM_STATE)

    with mlflow.start_run(run_name="baseline-ridge-reg"):
        mlflow.set_tags({"model": "ridge", "task": "regression",
                         "target": config.TARGET_REG})
        model = Ridge(**params)
        model.fit(Xtr_p, ytr)

        mlflow.log_params(params)
        mlflow.log_param("n_features", Xtr_p.shape[1])

        for name, Xs, ys in [("train", Xtr_p, ytr), ("val", Xva_p, yva), ("test", Xte_p, yte)]:
            pred = model.predict(Xs)
            for k, v in evaluate.reg_metrics(ys, pred).items():
                mlflow.log_metric(f"{name}_{k}", v)

        pred_te = model.predict(Xte_p)
        evaluate.log_reg_plots(mlflow, yte, pred_te)
        evaluate.log_importance(mlflow, evaluate.feature_names(pre),
                                np.abs(model.coef_).ravel(), "Coefficients |w| (Ridge)")

        pipe = Pipeline([("pre", pre), ("model", model)])
        sig = infer_signature(Xtr.head(50), pipe.predict(Xtr.head(50)))
        evaluate.log_model_safe(mlflow, pipe, Xtr, sig, "baseline-ridge-reg")
        evaluate.log_dataset_lineage(mlflow, train, config.TARGET_REG)

        print(f"[reg] Ridge test MAE={mean_absolute_error(yte, pred_te):.2f} j  "
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
