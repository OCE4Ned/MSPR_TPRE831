"""Controle de l'origine des requetes.

On ne veut ni recevoir ni renvoyer de donnees a n'importe qui : seules les
origines explicitement autorisees (liste blanche) peuvent appeler l'API.

- ALLOWED_ORIGINS sert de source unique : elle alimente a la fois le CORS
  (gere par le navigateur) et le middleware ci-dessous (controle cote serveur).
- La liste est surchargeable via la variable d'environnement ALLOWED_ORIGINS
  (origines separees par des virgules).
"""

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Origines autorisees par defaut (frontend en developpement).
_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]


def get_allowed_origins() -> list[str]:
    """Retourne la liste blanche des origines autorisees."""
    env = os.getenv("ALLOWED_ORIGINS")
    if env:
        return [origin.strip() for origin in env.split(",") if origin.strip()]
    return _DEFAULT_ORIGINS


ALLOWED_ORIGINS = get_allowed_origins()


class OriginCheckMiddleware(BaseHTTPMiddleware):
    """Rejette les requetes dont l'origine n'est pas dans la liste blanche.

    Si une requete porte un header Origin (cas d'un appel navigateur depuis
    un autre site), il doit figurer dans ALLOWED_ORIGINS, sinon -> 403.
    Les requetes sans Origin (outils en ligne de commande, appels
    serveur-a-serveur, meme origine) ne sont pas bloquees ici, le CORS
    s'occupant deja du filtrage cote navigateur.
    """

    def __init__(self, app, allowed_origins: list[str] | None = None):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ALLOWED_ORIGINS

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if origin is not None and origin not in self.allowed_origins:
            return JSONResponse(
                status_code=403,
                content={"detail": "Origine non autorisee"},
            )
        return await call_next(request)
