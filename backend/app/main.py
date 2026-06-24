"""Point d'entree du backend de la solution de supervision MECHA."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.db import init_db
from app.middleware import ALLOWED_ORIGINS, OriginCheckMiddleware
from app.routers import dimensions, facts, predictions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Au demarrage : cree les tables (vides) si elles n'existent pas encore.
    init_db()
    yield


app = FastAPI(title="MECHA Supervision API", lifespan=lifespan)

# Controle d'origine cote serveur : rejette les appels d'origines inconnues.
app.add_middleware(OriginCheckMiddleware)

# CORS restreint a la liste blanche (filtrage cote navigateur).
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dimensions.router)
app.include_router(facts.router)
app.include_router(predictions.router)


@app.get("/")
def read_root():
    """Endpoint de sante / racine de l'API."""
    return {"message": "Ceci est le backend de la solution!"}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
