"""Smoke test de bout en bout : dataset -> split temporel -> connexion MLflow.

Lancer depuis la racine du projet :
    python -m ml.check_setup
"""

from __future__ import annotations

from ml import config, data


def main() -> None:
    # 1) Dataset
    df = data.load_dataset()
    print(f"[data] {len(df):,} lignes | "
          f"{df[config.TIME_COL].min()} -> {df[config.TIME_COL].max()} | "
          f"{df['machine_id'].nunique()} machines")

    # 2) Split temporel
    train, val, test = data.temporal_split(df)
    print(f"[split] train={len(train):,} | val={len(val):,} | test={len(test):,}")
    for name, part in [("train", train), ("val", val), ("test", test)]:
        taux = part[config.TARGET_CLF].mean()
        print(f"        {name:5s} {part[config.TIME_COL].min().date()} "
              f"-> {part[config.TIME_COL].max().date()} | taux panne = {taux:.3%}")

    # 3) Matrices X / y (exemple classification, sans colonnes leaky)
    X, y, (num, cat) = data.build_xy(train, task="clf")
    print(f"[xy]    classification : X={X.shape}, features num={len(num)}, cat={len(cat)}")
    Xr, yr, _ = data.build_xy(train, task="reg")
    print(f"[xy]    regression     : X={Xr.shape}, cibles RUL non nulles={len(yr):,}")

    # 4) MLflow
    from ml.mlflow_setup import init_mlflow
    mlflow = init_mlflow()
    experiments = mlflow.search_experiments()
    print(f"[mlflow] {mlflow.get_tracking_uri()} | "
          f"{len(experiments)} experiment(s) : {[e.name for e in experiments]}")
    with mlflow.start_run(run_name="smoke-test"):
        mlflow.log_param("check", "ok")
        mlflow.log_metric("rows", len(df))
    print("[mlflow] run 'smoke-test' logge avec succes.")

    print("\nOK - environnement ML pret.")


if __name__ == "__main__":
    main()
