# ML - Maintenance predictive MECHA

Entrainement et suivi (MLflow) des modeles de maintenance predictive a partir
des donnees capteurs (`silver.sensor_events`, extraites dans
`data/ml/sensor_events.csv`).

## Targets

| Probleme | Colonne | Description |
|---|---|---|
| Classification | `failure_within_7_days` | Panne dans les 7 jours (0/1). ~3.5 % de positifs -> **desequilibre**. |
| Regression | `remaining_useful_life_days` | Temps restant avant defaillance (RUL, en jours). |

## Modeles prevus

| Modele | Targets | Role |
|---|---|---|
| Baseline regression (Ridge/Linear) | RUL | Reference simple. |
| XGBoost | classif + reg | Meilleur rapport perf/effort (tabulaire), gere le desequilibre. |
| MLP | classif + reg | Reseau dense, comparaison DL. |
| LSTM | classif + reg | Exploite la sequence temporelle par machine. |
| Autoencoder | (non supervise) | Detection d'anomalies via erreur de reconstruction. |

## Points de vigilance

1. **Fuite de donnees** : `predicted_failure_probability` et `sensor_anomaly_score`
   sont des sorties de modele -> exclues des features par defaut
   (`config.LEAKY_FEATURES`).
2. **Desequilibre** : utiliser `scale_pos_weight` / `class_weight`, evaluer en
   PR-AUC / F1 (pas l'accuracy).
3. **Split temporel** : `data.temporal_split` decoupe par ordre chronologique
   (jamais aleatoire) pour eviter la fuite temporelle.

## Installation

```bash
pip install -r ml/requirements.txt
```

> Reseau d'entreprise (proxy TLS) : si `pip` echoue sur la verification SSL,
> ajouter :
> `--trusted-host pypi.org --trusted-host files.pythonhosted.org`

## Configuration MLflow

Copier `ml/.env.example` en `ml/.env` (deja ignore par git) et renseigner les
identifiants. Le client gere l'auth basic ; la verification TLS est desactivee
(`MLFLOW_TRACKING_INSECURE_TLS=true`) car le certificat serveur a une chaine CA
non conforme.

## Verification de l'environnement

Depuis la racine du projet :

```bash
python -m ml.check_setup
```

Cela charge le dataset, affiche le split temporel et logge un run `smoke-test`
dans l'experiment `mecha-maintenance-predictive` sur MLflow.

## Regenerer l'extract de donnees

```bash
docker exec mspr-postgres psql -U mspr -d industrial_dw -c "\copy ( \
  SELECT event_ts, machine_id, cycle_time_sec, temperature_c, vibration_mms, \
         sound_db, oil_level_pct, coolant_level_pct, hydraulic_pressure_bar, \
         coolant_flow_l_min, heat_index, power_consumption_kw, operational_hours, \
         error_codes_last_30_days, sensor_anomaly_score, predicted_failure_probability, \
         ai_override_events, quality_status, remaining_useful_life_days, failure_within_7_days \
  FROM silver.sensor_events ORDER BY machine_id, event_ts \
) TO STDOUT WITH CSV HEADER" > data/ml/sensor_events.csv
```
