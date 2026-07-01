"""Connexion a la base de donnees et gestion des sessions.

La base cible est le data-warehouse PostgreSQL `industrial_dw`, alimente par
la pipeline (voir deployments/compose.etl.yml). Les tables exploitees par
l'API se trouvent dans le schema `gold` (modele en etoile).

L'URL de connexion est fournie par la variable d'environnement DATABASE_URL :

    DATABASE_URL=postgresql+psycopg://utilisateur:motdepasse@hote:5432/industrial_dw

- en local (uvicorn) : hote = localhost ;
- dans Docker Compose : hote = nom du service (postgres).

La structure des tables `gold` est creee par la pipeline (init-postgres.sql),
pas par le backend : init_db() n'est donc pas appele au demarrage.
"""

import os

from sqlmodel import Session, SQLModel, create_engine

# Charge backend/.env s'il existe (sans rendre python-dotenv obligatoire).
try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

# Par defaut : data-warehouse local (conteneur mspr-postgres, port 5432).
# Identifiants definis dans deployments/compose.etl.yml (mspr / mspr).
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://mspr:mspr@localhost:5432/industrial_dw",
)

engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Cree les tables manquantes a partir des modeles.

    Inutile en fonctionnement normal : le schema `gold` est gere par la
    pipeline. Conserve uniquement pour des tests sur une base vierge.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependance FastAPI : fournit une session de base de donnees par requete."""
    with Session(engine) as session:
        yield session
