# MSPR_TPRE831

Repo git pour le Bloc 3 (TPRE831) d'evaluation de notre MSPR pour la premiere annee de master EISI IA.

## Architecture data

Le projet contient maintenant une stack Docker pour simuler la chaine industrielle suivante :

```text
Sources sales CSV -> Kafka -> Datalake brut -> Airflow ELT -> PostgreSQL bronze/silver/gold
```

Important : Airflow fait ici de l'ELT, pas de l'ETL.

- Extract : lecture des fichiers JSONL bruts du datalake.
- Load : chargement tel quel dans `bronze.raw_events` avec le payload JSONB brut.
- Transform : nettoyage et aggregation dans PostgreSQL vers `silver.sensor_events`, puis `gold.machine_health_daily`.

## Services Docker

- `postgres` : base PostgreSQL avec les schemas `bronze`, `silver`, `gold`, plus la base metadata Airflow.
- `kafka` : broker Kafka local en mode KRaft.
- `kafka-producer` : lit les CSV sales dans `data/raw` et les publie dans Kafka.
- `kafka-datalake-consumer` : consomme Kafka et ecrit les messages bruts dans `data/datalake/raw/*.jsonl`.
- `airflow-webserver` et `airflow-scheduler` : executent le DAG ELT.

## Demarrage

Docker doit etre installe et disponible dans le terminal.

```powershell
docker compose up -d --build postgres kafka airflow-init airflow-webserver airflow-scheduler
```

Interface Airflow :

```text
http://localhost:8080
login: admin
password: admin
```

Pour envoyer les donnees sales dans Kafka puis les ecrire dans le datalake :

```powershell
docker compose --profile ingestion up --build kafka-producer kafka-datalake-consumer
```

Ensuite, dans Airflow, lancer manuellement le DAG :

```text
industrial_kafka_datalake_elt
```

## Verification PostgreSQL

Exemples de requetes :

```powershell
docker compose exec postgres psql -U mspr -d industrial_dw
```

```sql
SELECT COUNT(*) FROM bronze.raw_events;
SELECT COUNT(*) FROM silver.sensor_events;
SELECT * FROM gold.machine_health_daily ORDER BY snapshot_date, machine_id;
```
