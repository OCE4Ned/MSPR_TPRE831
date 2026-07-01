# Déploiement de l'infrastructure

## Prérequis

- Docker et Docker Compose installés
- Accès root ou capacité à utiliser `sudo`
- Fichier `.env` configuré

## Étapes de déploiement

### 1. Configuration initiale

Populer le fichier `.env` avec les variables d'environnement nécessaires.

### 2. Démarrer PostgreSQL

```bash
docker compose -f compose.yaml up -d postgres
```

### 3. Créer les bases de données et utilisateurs

Naviguez vers le répertoire de déploiement :

```bash
cd /srv/mecha
```

Sourcer les variables d'environnement :

```bash
set -a; source .env; set +a
```

Créer la base de données `industrial_dw` :

```bash
sudo docker compose -f compose.yaml exec -T postgres \
  psql -U mecha -d postgres -c "CREATE DATABASE industrial_dw OWNER mecha;"
```

Créer l'utilisateur `etl_writer` avec le password du `.env` :

```bash
sudo docker compose -f compose.yaml exec -T postgres \
  psql -U mecha -d postgres -c "CREATE USER etl_writer WITH PASSWORD '$ETL_WRITER_PASSWORD';"
```

### 4. Appliquer le schéma initial

```bash
# Importer le fichier d'initialisation
sudo docker compose -f compose.yaml exec -T postgres \
  psql -U mecha -d industrial_dw < init-postgres.sql
```

### 5. Démarrer les services principales

```bash
docker compose -f compose.yaml up -d
```

### 6. Démarrer le pipeline ETL

```bash
docker compose -f compose.etl.yml up -d
```