"""Client HTTP vers l'API IA MECHA (https://api-ia.ecluse.cloud).

Expose les predictions du modele (etat 7 jours, duree de vie restante) a
partir d'une mesure capteur (SensorReading). L'authentification se fait par
header `X-API-Key`.

Configuration via variables d'environnement :
- IA_API_BASE_URL : URL de base (defaut : https://api-ia.ecluse.cloud)
- IA_API_KEY      : cle d'API (header X-API-Key)
- IA_VERIFY_SSL   : "true"/"false" (le certificat ecluse.cloud est auto-signe
                    -> verification desactivee par defaut)
- IA_TIMEOUT      : timeout par requete en secondes (defaut : 10)
"""

import os

import httpx

IA_API_BASE_URL = os.getenv("IA_API_BASE_URL", "https://api-ia.ecluse.cloud").rstrip("/")
IA_API_KEY = os.getenv("IA_API_KEY", "mecha_api_key")
IA_VERIFY_SSL = os.getenv("IA_VERIFY_SSL", "false").lower() in {"1", "true", "yes", "oui"}
IA_TIMEOUT = float(os.getenv("IA_TIMEOUT", "10"))

# Champs attendus par le modele (SensorReading). Doivent etre presents et
# numeriques : on remplace les valeurs manquantes par 0.
SENSOR_FIELDS = [
    "cycle_time_sec",
    "temperature_c",
    "vibration_mms",
    "sound_db",
    "oil_level_pct",
    "coolant_level_pct",
    "hydraulic_pressure_bar",
    "coolant_flow_l_min",
    "heat_index",
    "power_consumption_kw",
    "operational_hours",
    "error_codes_last_30_days",
    "quality_status",
    "ai_override_events",
]


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=IA_API_BASE_URL,
        headers={"X-API-Key": IA_API_KEY},
        verify=IA_VERIFY_SSL,
        timeout=IA_TIMEOUT,
    )


def predict_state_batch(features: list[dict]) -> list[dict]:
    """Etat (normal / at_risk) + risk_score pour un lot de machines (1 appel)."""
    with _client() as client:
        resp = client.post("/api/v1/predictions/state/batch", json=features)
        resp.raise_for_status()
        return resp.json()


def predict_rul_many(features: list[dict]) -> list[dict]:
    """Duree de vie restante par machine (un appel /rul par machine).

    Renvoie la liste des reponses RulResponse (machine_id,
    remaining_useful_life_days, model_name, model_version). Une machine en
    echec apparait avec remaining_useful_life_days=None, sans interrompre
    les autres."""
    out: list[dict] = []
    with _client() as client:
        for feature in features:
            machine_id = feature["machine_id"]
            try:
                resp = client.post("/api/v1/predictions/rul", json=feature)
                resp.raise_for_status()
                out.append(resp.json())
            except httpx.HTTPError:
                out.append({"machine_id": machine_id, "remaining_useful_life_days": None})
    return out
