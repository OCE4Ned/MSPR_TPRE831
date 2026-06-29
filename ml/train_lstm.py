"""LSTM (Keras/TensorFlow) - classification + regression sur SEQUENCES.

Contrairement aux autres modeles (1 ligne = 1 exemple), le LSTM consomme une
fenetre glissante des L dernieres mesures d'une machine pour predire la cible
a la fin de la fenetre -> il capte la dynamique de degradation.

    python -m ml.train_lstm --task both --window 24

Split temporel PAR MACHINE (70/15/15 dans l'ordre chronologique) puis fenetrage
a l'interieur de chaque segment -> aucune fuite entre train/val/test.
"""

from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml import config, data, evaluate
from ml.mlflow_setup import init_mlflow

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf  # noqa: E402
from tensorflow import keras  # noqa: E402

FEATURES = config.NUMERIC_FEATURES
TRAIN_FRAC, VAL_FRAC = config.TRAIN_FRAC, config.VAL_FRAC


def _segment(g: pd.DataFrame):
    n = len(g)
    i1, i2 = int(n * TRAIN_FRAC), int(n * (TRAIN_FRAC + VAL_FRAC))
    return g.iloc[:i1], g.iloc[i1:i2], g.iloc[i2:]


def _windows(values: np.ndarray, labels: np.ndarray, length: int):
    if len(values) <= length:
        return None, None
    sw = np.lib.stride_tricks.sliding_window_view(values, length, axis=0)  # (n-L+1, F, L)
    Xw = np.swapaxes(sw, 1, 2).astype("float32")                            # (n-L+1, L, F)
    yw = labels[length - 1:]
    return Xw, yw


def build_sequences(df: pd.DataFrame, target: str, task: str, length: int):
    """Construit les fenetres train/val/test + le preprocessor (fit sur train)."""
    df = df.sort_values(["machine_id", config.TIME_COL])
    segments = []
    train_rows = []
    for _, g in df.groupby("machine_id", sort=False):
        tr, va, te = _segment(g)
        segments.append((tr, va, te))
        train_rows.append(tr[FEATURES])

    pre = Pipeline([("impute", SimpleImputer(strategy="median")),
                    ("scale", StandardScaler())]).fit(pd.concat(train_rows))

    packs = {"train": [[], []], "val": [[], []], "test": [[], []]}
    for tr, va, te in segments:
        for name, seg in [("train", tr), ("val", va), ("test", te)]:
            if seg.empty:
                continue
            vals = pre.transform(seg[FEATURES].values)
            Xw, yw = _windows(vals, seg[target].values, length)
            if Xw is None:
                continue
            packs[name][0].append(Xw)
            packs[name][1].append(yw)

    out = {}
    for name, (xs, ys) in packs.items():
        X = np.concatenate(xs); y = np.concatenate(ys)
        if task == "reg":                      # on retire les cibles RUL manquantes
            mask = ~np.isnan(y)
            X, y = X[mask], y[mask]
        else:
            y = y.astype("float32")
        out[name] = (X, y)
    return out, pre


def build_lstm(length: int, n_features: int, task: str) -> keras.Model:
    tf.keras.utils.set_random_seed(config.RANDOM_STATE)
    out_act, loss, metrics = (
        ("sigmoid", "binary_crossentropy", [keras.metrics.AUC(curve="PR", name="pr_auc")])
        if task == "clf"
        else ("linear", "mse", [keras.metrics.MeanAbsoluteError(name="mae")])
    )
    model = keras.Sequential([
        keras.layers.Input(shape=(length, n_features)),
        keras.layers.LSTM(48),
        keras.layers.Dropout(0.3),
        keras.layers.Dense(32, activation="relu"),
        keras.layers.Dense(1, activation=out_act),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss=loss, metrics=metrics)
    return model


def _fit(model, Xtr, ytr, Xva, yva, monitor, mode, class_weight=None):
    es = keras.callbacks.EarlyStopping(monitor=monitor, mode=mode, patience=6,
                                       restore_best_weights=True)
    model.fit(Xtr, ytr, validation_data=(Xva, yva), epochs=40, batch_size=512,
              callbacks=[es], class_weight=class_weight, verbose=0)
    return model


def run(mlflow, df, task: str, length: int):
    target = config.TARGET_CLF if task == "clf" else config.TARGET_REG
    seq, pre = build_sequences(df, target, task, length)
    (Xtr, ytr), (Xva, yva), (Xte, yte) = seq["train"], seq["val"], seq["test"]

    params = dict(window=length, lstm_units=48, dropout=0.3, optimizer="adam",
                  lr=1e-3, batch_size=512, epochs_max=40, patience=6,
                  n_features=Xtr.shape[2])

    run_name = f"lstm-{task}"
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tags({"model": "lstm", "task": "classification" if task == "clf" else "regression",
                         "target": target, "framework": "tensorflow"})
        model = build_lstm(length, Xtr.shape[2], task)

        if task == "clf":
            n = len(ytr); n_pos = int(ytr.sum()); n_neg = n - n_pos
            cw = {0: n / (2 * n_neg), 1: n / (2 * n_pos)}
            params["class_weight_pos"] = round(cw[1], 3)
            _fit(model, Xtr, ytr, Xva, yva, "val_pr_auc", "max", class_weight=cw)
        else:
            _fit(model, Xtr, ytr, Xva, yva, "val_mae", "min")

        mlflow.log_params(params)
        mlflow.log_param("n_windows_train", len(ytr))
        mlflow.log_param("epochs_run", len(model.history.history["loss"]))

        if task == "clf":
            for name, Xs, ys in [("train", Xtr, ytr), ("val", Xva, yva), ("test", Xte, yte)]:
                proba = model.predict(Xs, verbose=0).ravel()
                for k, v in evaluate.clf_metrics(ys, proba).items():
                    mlflow.log_metric(f"{name}_{k}", v)
            thr = evaluate.best_threshold(yva, model.predict(Xva, verbose=0).ravel())
            proba_te = model.predict(Xte, verbose=0).ravel()
            mlflow.log_metric("test_threshold", thr)
            for k, v in evaluate.clf_metrics(yte, proba_te, thr).items():
                mlflow.log_metric(f"test_tuned_{k}", v)
            evaluate.log_clf_plots(mlflow, yte, proba_te, thr)
            from sklearn.metrics import average_precision_score, recall_score
            print(f"[clf] LSTM test PR-AUC={average_precision_score(yte, proba_te):.3f} "
                  f"recall@{thr:.2f}={recall_score(yte, (proba_te>=thr).astype(int)):.3f}")
        else:
            for name, Xs, ys in [("train", Xtr, ytr), ("val", Xva, yva), ("test", Xte, yte)]:
                pred = model.predict(Xs, verbose=0).ravel()
                for k, v in evaluate.reg_metrics(ys, pred).items():
                    mlflow.log_metric(f"{name}_{k}", v)
            pred_te = model.predict(Xte, verbose=0).ravel()
            evaluate.log_reg_plots(mlflow, yte, pred_te)
            from sklearn.metrics import mean_absolute_error, r2_score
            print(f"[reg] LSTM test MAE={mean_absolute_error(yte, pred_te):.2f} j  "
                  f"R2={r2_score(yte, pred_te):.3f}")

        evaluate.log_keras_artifacts(mlflow, model, pre, run_name)
        evaluate.log_dataset_lineage(mlflow, df, target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["clf", "reg", "both"], default="both")
    parser.add_argument("--window", type=int, default=24, help="longueur de fenetre (timesteps)")
    args = parser.parse_args()

    mlflow = init_mlflow()
    df = data.load_dataset()
    print(f"Donnees: {len(df):,} lignes, fenetre={args.window} timesteps")

    if args.task in ("clf", "both"):
        run(mlflow, df, "clf", args.window)
    if args.task in ("reg", "both"):
        run(mlflow, df, "reg", args.window)


if __name__ == "__main__":
    main()
