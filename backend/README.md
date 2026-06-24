# Backend — MECHA Supervision API

API REST (FastAPI + SQLModel) de la solution de supervision industrielle MECHA.
Elle expose les données de l'entrepôt **gold** (modèle en étoile : dimensions +
faits) et un endpoint de maintenance prédictive.

> État actuel : **squelette fonctionnel**. La structure des tables, les routes et
> les requêtes sont en place, mais **il n'y a pas encore de données** (le dataset
> est en cours de production). L'objectif est que tout soit branchable directement
> dès que les données et la base PostgreSQL seront disponibles.

---

## Stack technique

- **FastAPI** — framework web / API
- **SQLModel** (Pydantic + SQLAlchemy) — modèles servant à la fois de tables BD
  et de schémas API
- **Uvicorn** — serveur ASGI
- **PostgreSQL** (via Docker) — base de données, pilote `psycopg`

---

## Structure du projet

```
backend/
├── requirements.txt          # dépendances (sqlmodel ; psycopg commenté)
├── Dockerfile
├── .gitignore
└── app/
    ├── main.py               # point d'entrée : app, middlewares, routers, init BD
    ├── db/
    │   └── session.py        # moteur, get_session(), init_db()
    ├── dto/                  # modèles SQLModel
    │   ├── dimensions.py     # DIM_* (7 tables)
    │   ├── facts.py          # FACT_* (5 tables)
    │   └── ai_pred.py        # schémas entrée/sortie de prédiction
    ├── middleware/
    │   └── origin.py         # contrôle d'origine (liste blanche)
    └── routers/
        ├── dimensions.py     # routes /dimensions/*
        ├── facts.py          # routes /facts/*
        └── predictions.py    # route /predict/failure
```

---

## Lancer le projet

### 1. Démarrer la base PostgreSQL (Docker)

Depuis la racine du dépôt :

```bash
docker compose -f deployments/compose.yaml --env-file deployments/.env.example up -d postgres
```

La base démarre vide. Identifiants par défaut (voir `deployments/.env.example`) :
base `mecha`, utilisateur `mecha`, mot de passe `mecha`, port `5432`.

### 2. Démarrer le backend

Depuis le dossier `backend/` :

```bash
# Environnement virtuel + dépendances
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

# Serveur (rechargement auto en dev)
uvicorn app.main:app --reload --port 8000
```

- API : http://localhost:8000
- Documentation interactive (Swagger) : http://localhost:8000/docs
- Documentation alternative (ReDoc) : http://localhost:8000/redoc

Au démarrage, le backend se connecte à PostgreSQL et y crée automatiquement les
tables (**vides**) si elles n'existent pas encore.

---

## Configuration

Variables d'environnement (optionnelles) :

| Variable          | Défaut                                              | Rôle                                         |
|-------------------|-----------------------------------------------------|----------------------------------------------|
| `DATABASE_URL`    | `postgresql+psycopg://mecha:mecha@localhost:5432/mecha` | Connexion à la base de données            |
| `ALLOWED_ORIGINS` | `localhost:5173,3000` (+ 127.0.0.1)                 | Origines autorisées (CORS + contrôle serveur), séparées par des virgules |

- **En dev local** (uvicorn) : l'hôte est `localhost` (valeur par défaut, rien à
  configurer).
- **En conteneur** (Docker Compose) : l'hôte est le nom du service `postgres` ;
  la valeur est fournie par `deployments/.env.example`.

---

## Endpoints

### Dimensions (référentiels) — `/dimensions/*`
`list` + `get by id` pour : `plants`, `lines`, `machines`, `products`,
`shifts`, `defects`, `dates`. Filtres : lignes par `plant_id`, machines par
`production_line_id`, dates par `year`/`month`.

### Faits (mesures) — `/facts/*`
- `GET /facts/production` — TRS, quantités, temps de cycle
- `GET /facts/quality` — conformité, défauts
- `GET /facts/maintenance` — pannes, coûts, anomalies
- `GET /facts/energy` — consommation énergétique
- `GET /facts/alerts` — alertes machines

Chaque route de faits accepte des filtres par clés étrangères
(`machine_id`, `date_id`, etc.).

### Prédiction — `/predict/*`
- `POST /predict/failure` — probabilité de panne machine *(non implémenté)*

---

## Sécurité

Le contrôle d'origine est assuré par **deux couches** s'appuyant sur la même
liste blanche (`ALLOWED_ORIGINS`) :

1. **CORS** (`CORSMiddleware`) — filtrage côté navigateur.
2. **`OriginCheckMiddleware`** — filtrage côté serveur : toute requête portant
   un header `Origin` hors liste blanche est rejetée en `403`.

---

## État d'avancement

### Fait
- [x] Structure du projet (db / dto / routers / middleware)
- [x] Modèles SQLModel de toutes les tables gold (7 dimensions + 5 faits)
- [x] Routes de lecture des dimensions et des faits (avec filtres)
- [x] Base PostgreSQL via Docker (service dans `deployments/compose.yaml`)
- [x] Création automatique des tables au démarrage
- [x] Contrôle d'origine des requêtes (CORS + middleware)

### Reste à faire
- [ ] **Alimenter la base** avec le dataset gold une fois disponible
      (pipeline d'import / ETL)
- [ ] **Implémenter `POST /predict/failure`** (intégration du modèle ML)
- [ ] Ajuster les modèles si le dataset évolue (le schéma n'est pas encore figé)
- [ ] Gestion des migrations de schéma (ex. Alembic) pour la production
- [ ] Authentification / autorisation si nécessaire
- [ ] Tests automatisés (pytest)
- [ ] Pagination sur les routes de faits (volumétrie potentiellement élevée)
```
