"""Connexion a la base de donnees et gestion des sessions.

La base cible est PostgreSQL (lancee via Docker, voir deployments/compose.yaml).
L'URL de connexion est fournie par la variable d'environnement DATABASE_URL :

    DATABASE_URL=postgresql+psycopg://utilisateur:motdepasse@hote:5432/mecha

- en local (uvicorn) : hote = localhost ;
- dans Docker Compose : hote = nom du service (postgres).

Aucune donnee n'est creee ici : init_db() ne fait que materialiser la
structure des tables (vides) decrites par les modeles SQLModel.
"""

import os

from sqlmodel import Session, SQLModel, create_engine

# Par defaut : PostgreSQL local (le conteneur Docker expose le port 5432).
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://mecha:mecha@localhost:5432/mecha",
)

engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Cree les tables (vides) a partir des modeles si elles n'existent pas."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependance FastAPI : fournit une session de base de donnees par requete."""
    with Session(engine) as session:
        yield session
