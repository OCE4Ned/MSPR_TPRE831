"""MLP (reseau dense Keras/TensorFlow) - classification + regression.

    python -m ml.train_mlp --task both

Le MLP est entraine sur les memes features tabulaires que XGBoost/baseline ;
il sert de point de comparaison "deep learning" sur donnees non sequentielles.
"""

from __future__ import annotations

import argparse
import os

import numpy as np
from sklearn.metrics import average_precision_score, mean_absolute_error, r2_score, recall_score

from ml import config, data, evaluate
from ml.mlflow_setup import init_mlflow

# TensorFlow est bavard -> on limite les logs avant import.
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf  # noqa: E402
from tensorflow import keras  # noqa: E402


def build_mlp(n_features: int, task: str) -> keras.Model:
    tf.keras.utils.set_random_seed(config.RANDOM_STATE)
    out_units, out_act, loss, metrics = (
        (1, "sigmoid", "binary_crossentropy", [keras.metrics.AUC(curve="PR", name="pr_auc")])
        if task == "clf"
        else (1, "linear", "mse", [keras.metrics.MeanAbsoluteError(name="mae")])
    )
    model = keras.Sequential([
        keras.layers.Input(shape=(n_features,)),
        keras.layers.Dense(128, activation="relu"),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(64, activation="relu"),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(out_units, activation=out_act),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss=loss, metrics=metrics)
    return model


def _fit(model, Xtr, ytr, Xva, yva, monitor, mode, class_weight=None):
    es = keras.callbacks.EarlyStopping(monitor=monitor, mode=mode, patience=12,
                                       restore_best_weights=True)
    model.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=120, batch_size=512,
              callbacks=[es], class_weight=class_weight, verbose=0)
    return model


def train_clf(mlflow, splits):
    train, val, test = splits
    Xtr, ytr, (num, cat) = data.build_xy(train, "clf")
    Xva, yva, _ = data.build_xy(val, "clf")
    Xte, yte, _ = data.build_xy(test, "clf")

    pre = data.make_preprocessor(num, cat)
    Xtr_p, Xva_p, Xte_p = pre.fit_transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    # Poids de classe (gestion du desequilibre)
    n = len(ytr); n_pos = int(ytr.sum()); n_neg = n - n_pos
    class_weight = {0: n / (2 * n_neg), 1: n / (2 * n_pos)}

    params = dict(arch="128-64", dropout=0.3, optimizer="adam", lr=1e-3,
                  batch_size=512, epochs_max=120, patience=12,
                  class_weight_pos=round(class_weight[1], 3))

    with mlflow.start_run(run_name="mlp-clf"):
        mlflow.set_tags({"model": "mlp", "task": "classification",
                         "target": config.TARGET_CLF, "framework": "tensorflow"})
        model = build_mlp(Xtr_p.shape[1], "clf")
        _fit(model, Xtr_p, ytr.values, Xva_p, yva.values,
             monitor="val_pr_auc", mode="max", class_weight=class_weight)

        mlflow.log_params(params)
        mlflow.log_param("n_features", Xtr_p.shape[1])
        mlflow.log_param("epochs_run", len(model.history.history["loss"]))

        for name, Xs, ys in [("train", Xtr_p, ytr), ("val", Xva_p, yva), ("test", Xte_p, yte)]:
            proba = model.predict(Xs, verbose=0).ravel()
            for k, v in evaluate.clf_metrics(ys, proba).items():
                mlflow.log_metric(f"{name}_{k}", v)

        proba_va = model.predict(Xva_p, verbose=0).ravel()
        thr = evaluate.best_threshold(yva, proba_va)
        proba_te = model.predict(Xte_p, verbose=0).ravel()
        mlflow.log_metric("test_threshold", thr)
        for k, v in evaluate.clf_metrics(yte, proba_te, thr).items():
            mlflow.log_metric(f"test_tuned_{k}", v)

        evaluate.log_clf_plots(mlflow, yte, proba_te, thr)
        evaluate.log_keras_artifacts(mlflow, model, pre, "mlp-clf")
        evaluate.log_dataset_lineage(mlflow, train, config.TARGET_CLF)

        print(f"[clf] MLP test PR-AUC={average_precision_score(yte, proba_te):.3f} "
              f"recall@{thr:.2f}={recall_score(yte, (proba_te>=thr).astype(int)):.3f}")


def train_reg(mlflow, splits):
    train, val, test = splits
    Xtr, ytr, (num, cat) = data.build_xy(train, "reg")
    Xva, yva, _ = data.build_xy(val, "reg")
    Xte, yte, _ = data.build_xy(test, "reg")

    pre = data.make_preprocessor(num, cat)
    Xtr_p, Xva_p, Xte_p = pre.fit_transform(Xtr), pre.transform(Xva), pre.transform(Xte)

    params = dict(arch="128-64", dropout=0.3, optimizer="adam", lr=1e-3,
                  batch_size=512, epochs_max=120, patience=12)

    with mlflow.start_run(run_name="mlp-reg"):
        mlflow.set_tags({"model": "mlp", "task": "regression",
                         "target": config.TARGET_REG, "framework": "tensorflow"})
        model = build_mlp(Xtr_p.shape[1], "reg")
        _fit(model, Xtr_p, ytr.values, Xva_p, yva.values, monitor="val_mae", mode="min")

        mlflow.log_params(params)
        mlflow.log_param("n_features", Xtr_p.shape[1])
        mlflow.log_param("epochs_run", len(model.history.history["loss"]))

        for name, Xs, ys in [("train", Xtr_p, ytr), ("val", Xva_p, yva), ("test", Xte_p, yte)]:
            pred = model.predict(Xs, verbose=0).ravel()
            for k, v in evaluate.reg_metrics(ys, pred).items():
                mlflow.log_metric(f"{name}_{k}", v)

        pred_te = model.predict(Xte_p, verbose=0).ravel()
        evaluate.log_reg_plots(mlflow, yte, pred_te)
        evaluate.log_keras_artifacts(mlflow, model, pre, "mlp-reg")
        evaluate.log_dataset_lineage(mlflow, train, config.TARGET_REG)

        print(f"[reg] MLP test MAE={mean_absolute_error(yte, pred_te):.2f} j  "
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
