# MSPR_TPRE831

Repo git pour le Bloc 3 (TPRE831) d'evaluation de notre MSPR pour la premiere annee de master EISI IA.

## Architecture data

Le projet contient maintenant une stack Docker pour simuler la chaine industrielle suivante :

```text
CSV sales + CSV enrichis business -> Kafka -> Datalake brut -> Airflow ETL/ELT -> PostgreSQL bronze/silver/gold
Simulateur Python machines -> Kafka -> Datalake brut -> Airflow ETL/ELT -> PostgreSQL bronze/silver/gold
```

Important : Airflow fait ici de l'ELT, pas de l'ETL.

- Extract : lecture des fichiers JSONL bruts du datalake.
- Load : chargement tel quel dans `bronze.raw_events` avec le payload JSONB brut.
- Transform : nettoyage vers `silver.sensor_events`, aggregation vers `gold.machine_health_daily`, puis alimentation de la base Gold en etoile.

La couche Gold reprend le modele decisionnel du schema :

- Dimensions : `gold.dim_date`, `gold.dim_plant`, `gold.dim_line`, `gold.dim_shift`, `gold.dim_product`, `gold.dim_defect`, `gold.dim_machine`.
- Facts : `gold.fact_production`, `gold.fact_quality`, `gold.fact_maintenance`, `gold.fact_energy`, `gold.fact_alerts`.

## Services Docker

- `postgres` : base PostgreSQL avec les schemas `bronze`, `silver`, `gold`, plus la base metadata Airflow.
- `kafka` : broker Kafka local en mode KRaft.
- `kafka-producer` : lit les CSV sales dans `data/raw` et les CSV enrichis dans `data/processed/business`, puis les publie dans Kafka.
- `kafka-machine-simulator` : genere en continu des evenements machines SCADA, MES, energie et parfois GMAO, puis les publie dans Kafka.
- `kafka-datalake-consumer` : consomme Kafka et ecrit les messages bruts dans `data/datalake/raw/*.jsonl`.
- `airflow-webserver` et `airflow-scheduler` : executent le DAG ELT toutes les 5 minutes.

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

Pour generer des donnees machines en continu :

```powershell
docker compose --profile streaming up --build kafka-machine-simulator kafka-datalake-consumer
```

Variables utiles du simulateur :

- `SEND_INTERVAL_SECONDS` : delai entre deux generations, par defaut `2`.
- `MAX_EVENTS` : `0` pour infini, sinon nombre maximal d'evenements.

Le DAG Airflow se lance automatiquement toutes les 5 minutes. Il peut aussi etre lance manuellement :

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
SELECT COUNT(*) FROM gold.fact_production;
SELECT COUNT(*) FROM gold.fact_quality;
SELECT COUNT(*) FROM gold.fact_maintenance;
SELECT COUNT(*) FROM gold.fact_energy;
SELECT COUNT(*) FROM gold.fact_alerts;
```

Si le volume PostgreSQL existe deja avant l'ajout des nouvelles tables Gold, recréer la base :

```powershell
docker compose down -v
docker compose up -d --build postgres kafka airflow-init airflow-webserver airflow-scheduler
```
