"""Autoencoder (Keras) - detection d'anomalies NON SUPERVISEE.

Principe : on entraine l'AE a reconstruire uniquement le comportement NORMAL
(failure_within_7_days == 0). Une erreur de reconstruction elevee = comportement
atypique = anomalie. Les labels ne servent QU'A l'evaluation (ROC/PR-AUC du
score d'anomalie vs failure_within_7_days), pas a l'entrainement.

    python -m ml.train_autoencoder
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml import config, data, evaluate
from ml.mlflow_setup import init_mlflow

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
import tensorflow as tf  # noqa: E402
from tensorflow import keras  # noqa: E402

FEATURES = config.NUMERIC_FEATURES


def build_ae(n_features: int) -> keras.Model:
    tf.keras.utils.set_random_seed(config.RANDOM_STATE)
    model = keras.Sequential([
        keras.layers.Input(shape=(n_features,)),
        keras.layers.Dense(16, activation="relu"),
        keras.layers.Dense(4, activation="relu", name="bottleneck"),
        keras.layers.Dense(16, activation="relu"),
        keras.layers.Dense(n_features, activation="linear"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    return model


def recon_error(model, X) -> np.ndarray:
    rec = model.predict(X, verbose=0)
    return np.mean((X - rec) ** 2, axis=1)


def log_error_hist(mlflow, scores, labels):
    fig, ax = plt.subplots(figsize=(7, 4))
    smax = np.quantile(scores, 0.99)
    ax.hist(scores[labels == 0], bins=80, range=(0, smax), alpha=0.6, density=True, label="normal")
    ax.hist(scores[labels == 1], bins=80, range=(0, smax), alpha=0.6, density=True, label="panne <=7j")
    ax.set_xlabel("erreur de reconstruction"); ax.set_ylabel("densite")
    ax.set_title("Distribution de l'erreur AE (test)"); ax.legend()
    fig.tight_layout(); mlflow.log_figure(fig, "reconstruction_error_hist.png"); plt.close(fig)


def main():
    mlflow = init_mlflow()
    df = data.load_dataset()
    train, val, test = data.temporal_split(df)
    print(f"Donnees: train={len(train):,} val={len(val):,} test={len(test):,}")

    ytr = train[config.TARGET_CLF].astype(int).values
    yva = val[config.TARGET_CLF].astype(int).values
    yte = test[config.TARGET_CLF].astype(int).values

    # Preprocessing ajuste sur le comportement NORMAL du train uniquement.
    pre = Pipeline([("impute", SimpleImputer(strategy="median")),
                    ("scale", StandardScaler())]).fit(train.loc[ytr == 0, FEATURES])
    Xtr = pre.transform(train[FEATURES]); Xva = pre.transform(val[FEATURES])
    Xte = pre.transform(test[FEATURES])
    Xtr_norm, Xva_norm = Xtr[ytr == 0], Xva[yva == 0]

    params = dict(arch="16-4-16", optimizer="adam", lr=1e-3, batch_size=512,
                  epochs_max=120, patience=10, n_features=Xtr.shape[1],
                  train_mode="normal_only")

    with mlflow.start_run(run_name="autoencoder"):
        mlflow.set_tags({"model": "autoencoder", "task": "anomaly_detection",
                         "target": config.TARGET_CLF, "framework": "tensorflow",
                         "supervision": "unsupervised"})
        model = build_ae(Xtr.shape[1])
        es = keras.callbacks.EarlyStopping(monitor="val_loss", patience=10,
                                           restore_best_weights=True)
        model.fit(Xtr_norm, Xtr_norm, validation_data=(Xva_norm, Xva_norm),
                  epochs=120, batch_size=512, callbacks=[es], verbose=0)

        mlflow.log_params(params)
        mlflow.log_param("epochs_run", len(model.history.history["loss"]))
        mlflow.log_param("n_train_normal", len(Xtr_norm))

        score_tr = recon_error(model, Xtr_norm)
        score_va = recon_error(model, Xva)
        score_te = recon_error(model, Xte)

        # Seuil "operationnel" = 95e percentile des erreurs normales du train.
        thr_p95 = float(np.quantile(score_tr, 0.95))
        # Seuil alternatif : best-F1 calibre sur la validation (semi-supervise).
        thr_f1 = evaluate.best_threshold(yva, score_va)

        # ROC/PR-AUC du score d'anomalie vs le vrai label (evaluation seulement)
        base = evaluate.clf_metrics(yte, score_te, thr_p95)
        mlflow.log_metric("test_pr_auc", base["pr_auc"])
        mlflow.log_metric("test_roc_auc", base["roc_auc"])
        mlflow.log_metric("test_threshold_p95", thr_p95)
        for k in ("precision", "recall", "f1", "accuracy"):
            mlflow.log_metric(f"test_p95_{k}", base[k])
        tuned = evaluate.clf_metrics(yte, score_te, thr_f1)
        mlflow.log_metric("test_threshold_f1", thr_f1)
        for k in ("precision", "recall", "f1"):
            mlflow.log_metric(f"test_tuned_{k}", tuned[k])

        evaluate.log_clf_plots(mlflow, yte, score_te, thr_f1)
        log_error_hist(mlflow, score_te, yte)
        evaluate.log_keras_artifacts(mlflow, model, pre, "autoencoder")
        evaluate.log_dataset_lineage(mlflow, train, config.TARGET_CLF)

        print(f"[anomaly] AE test ROC-AUC={base['roc_auc']:.3f} PR-AUC={base['pr_auc']:.3f} "
              f"| p95: recall={base['recall']:.3f} precision={base['precision']:.3f}")


if __name__ == "__main__":
    main()
