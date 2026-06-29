"""Chargement du dataset, split temporel et preprocessing reutilisables.

Toutes les fonctions reposent sur l'extract `data/ml/sensor_events.csv`
(genere depuis silver.sensor_events).
"""

from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml import config


def load_dataset(path=config.DATA_CSV) -> pd.DataFrame:
    """Charge le CSV, parse l'horodatage et trie chronologiquement."""
    df = pd.read_csv(path, parse_dates=[config.TIME_COL])
    df = df.sort_values(config.TIME_COL).reset_index(drop=True)
    return df


def feature_columns(include_leaky: bool = False, include_machine_id: bool = True):
    """Retourne (features_numeriques, features_categorielles)."""
    numeric = list(config.NUMERIC_FEATURES)
    if include_leaky:
        numeric += list(config.LEAKY_FEATURES)
    categorical = [
        c for c in config.CATEGORICAL_FEATURES
        if include_machine_id or c != "machine_id"
    ]
    return numeric, categorical


def temporal_split(df: pd.DataFrame,
                   train_frac: float = config.TRAIN_FRAC,
                   val_frac: float = config.VAL_FRAC):
    """Decoupe train/val/test par ordre chronologique (pas aleatoire).

    Entraine sur le passe, valide/teste sur le futur -> evite la fuite temporelle.
    """
    df = df.sort_values(config.TIME_COL).reset_index(drop=True)
    n = len(df)
    i_train = int(n * train_frac)
    i_val = int(n * (train_frac + val_frac))
    return (
        df.iloc[:i_train].copy(),
        df.iloc[i_train:i_val].copy(),
        df.iloc[i_val:].copy(),
    )


def make_preprocessor(numeric, categorical) -> ColumnTransformer:
    """Pipeline sklearn : imputation + standardisation (num) / one-hot (cat)."""
    numeric_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    return ColumnTransformer([
        ("num", numeric_pipe, numeric),
        ("cat", categorical_pipe, categorical),
    ])


def build_xy(df: pd.DataFrame, task: str,
             include_leaky: bool = False, include_machine_id: bool = True):
    """Construit (X, y, (numeric, categorical)) pour 'clf' ou 'reg'.

    Pour la regression, les lignes sans cible (RUL nul) sont retirees.
    """
    if task not in {"clf", "reg"}:
        raise ValueError("task doit etre 'clf' ou 'reg'")

    numeric, categorical = feature_columns(include_leaky, include_machine_id)

    if task == "reg":
        df = df[df[config.TARGET_REG].notna()].copy()
        y = df[config.TARGET_REG].astype(float)
    else:
        y = df[config.TARGET_CLF].astype(int)

    X = df[numeric + categorical].copy()
    return X, y, (numeric, categorical)
