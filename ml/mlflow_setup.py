"""Initialisation du client MLflow (auth basic htpasswd + TLS du serveur).

L'instance https://mlflow.ecluse.cloud presente un certificat dont la chaine CA
n'est pas conforme (OpenSSL refuse la verification). On desactive donc la
verification TLS via MLFLOW_TRACKING_INSECURE_TLS. L'authentification basic
(mspr2026/mspr2026) est geree automatiquement par le client mlflow a partir des
variables MLFLOW_TRACKING_USERNAME / MLFLOW_TRACKING_PASSWORD.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

from ml import config


def init_mlflow(experiment: str = config.MLFLOW_EXPERIMENT):
    """Charge ml/.env, configure le tracking et retourne le module mlflow."""
    # MLflow ecrit des emojis (URL des runs) -> KO sur les consoles Windows cp1252.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    load_dotenv(config.PROJECT_ROOT / "ml" / ".env")

    uri = os.environ.get("MLFLOW_TRACKING_URI")
    if not uri:
        raise RuntimeError(
            "MLFLOW_TRACKING_URI manquant. Copier ml/.env.example en ml/.env."
        )

    # Certificat serveur non conforme -> verification TLS desactivee par defaut.
    os.environ.setdefault("MLFLOW_TRACKING_INSECURE_TLS", "true")

    # Importe mlflow APRES avoir pose les variables d'environnement.
    import mlflow

    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(experiment)
    return mlflow


if __name__ == "__main__":
    mlflow = init_mlflow()
    print("Tracking URI :", mlflow.get_tracking_uri())
    experiments = mlflow.search_experiments()
    print(f"Connexion OK - {len(experiments)} experiment(s) :",
          [e.name for e in experiments])
