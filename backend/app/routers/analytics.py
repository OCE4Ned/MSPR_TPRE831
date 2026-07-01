"""Routes d'analyse : agregats prets a afficher pour le dashboard.

Contrairement aux routes /dimensions et /facts (lignes brutes), ces routes
calculent directement les indicateurs consolides attendus par le frontend
(KPIs, TRS par ligne, machines a risque, series temporelles, alertes) a
partir du schema `gold`.
"""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db import engine
from app.services import ia_client

router = APIRouter(prefix="/analytics", tags=["analytics"])


# --- Helpers ----------------------------------------------------------------

def _status_from_trs(trs: float | None) -> str:
    """Niveau de sante a partir d'un TRS (en %)."""
    if trs is None:
        return "crit"
    if trs >= 85:
        return "good"
    if trs >= 70:
        return "warn"
    return "crit"


def _status_from_reach(reach: float | None) -> str:
    if reach is None:
        return "crit"
    if reach >= 90:
        return "good"
    if reach >= 80:
        return "warn"
    return "crit"


def _status_from_scrap(scrap: float | None) -> str:
    """Niveau de sante a partir d'un taux de rebut (en %)."""
    if scrap is None:
        return "good"
    if scrap < 3:
        return "good"
    if scrap < 5:
        return "warn"
    return "crit"


_SEVERITY_MAP = {
    "critical": "critique",
    "high": "critique",
    "major": "majeur",
    "warning": "majeur",
    "medium": "majeur",
}


def _severity(value: str | None) -> str:
    return _SEVERITY_MAP.get((value or "").lower(), "mineur")


def _status_from_rul(rul: float | None) -> str:
    """Urgence de maintenance a partir de la duree de vie restante (jours)."""
    if rul is None:
        return "good"
    if rul < 30:
        return "crit"
    if rul < 90:
        return "warn"
    return "good"


# Horizon (jours) au-dela duquel la RUL ne contribue plus au risque.
RUL_HORIZON_DAYS = 365


def _risk_score(risk_score: float | None, rul_days: float | None) -> int:
    """Score de risque gradue 0-100.

    Le classifieur etant binaire (0 ou 1), on le combine a l'urgence derivee
    de la RUL (plus la duree de vie restante est courte, plus le risque monte)
    a poids egal. Sans RUL, on retombe sur la sortie brute du classifieur.
    """
    clf = (risk_score or 0) * 100
    if rul_days is None:
        return round(clf)
    urgency = max(0.0, min(100.0, 100.0 * (1 - rul_days / RUL_HORIZON_DAYS)))
    return round(0.5 * clf + 0.5 * urgency)


def _fmt_day(date_id: int | None) -> str:
    """20260329 -> '29/03'."""
    if date_id is None:
        return ""
    s = str(date_id)
    if len(s) == 8:
        return f"{s[6:8]}/{s[4:6]}"
    return s


def _fmt_date(date_id: int | None) -> str:
    """20260329 -> '29/03/2026'."""
    if date_id is None:
        return ""
    s = str(date_id)
    if len(s) == 8:
        return f"{s[6:8]}/{s[4:6]}/{s[0:4]}"
    return s


def _round(value, ndigits: int = 1):
    return None if value is None else round(float(value), ndigits)


def _model_label(responses: list[dict]) -> str:
    """'mecha-rul-regressor v1' a partir de la 1re reponse contenant le modele."""
    for resp in responses:
        name = resp.get("model_name")
        if name:
            version = resp.get("model_version")
            return f"{name} v{version}" if version else name
    return "—"


def _machine_feature(plant_id: str, row) -> dict:
    """Transforme une ligne silver.sensor_events en entree MachineFeatures."""
    sensors: dict = {"machine_id": row["machine_id"]}
    for field in ia_client.SENSOR_FIELDS:
        value = row[field]
        if field in ("error_codes_last_30_days", "ai_override_events"):
            sensors[field] = int(value or 0)
        elif field == "quality_status":
            sensors[field] = str(value or "valid_sensor_event")
        else:
            sensors[field] = float(value) if value is not None else 0.0
    ts = row["event_ts"]
    return {
        "machine_id": row["machine_id"],
        "site": plant_id,
        "timestamp": ts.isoformat() if ts is not None else "2026-01-01T00:00:00",
        "sensors": sensors,
    }


def run_ia(plant_id, sensor_rows):
    """Appelle l'API IA une fois et renvoie les predictions par machine.

    Retourne (preds, clf_model, rul_model, online) avec
    preds[machine_id] = {"state", "risk_score", "rul_days"}.
    En cas d'echec (IA injoignable ou aucune mesure) : ({}, "—", "—", False).
    """
    try:
        features = [_machine_feature(plant_id, r) for r in sensor_rows]
        if not features:
            raise RuntimeError("aucune mesure capteur disponible")

        states = ia_client.predict_state_batch(features)
        ruls = ia_client.predict_rul_many(features)
        rul_map = {r["machine_id"]: r.get("remaining_useful_life_days") for r in ruls}
        preds = {
            s["machine_id"]: {
                "state": s.get("state", "normal"),
                "risk_score": s.get("risk_score") or 0,
                "rul_days": rul_map.get(s["machine_id"]),
            }
            for s in states
        }
        return preds, _model_label(states), _model_label(ruls), True
    except Exception:
        return {}, "—", "—", False


def build_ia_indicators(preds, clf_model, rul_model, online, agg, active_alerts, n_machines):
    """Carte "Indicateurs IA-ready". Repli local si l'IA est hors ligne."""
    if not online:
        return [
            {"label": "Stabilité performance", "value": f"{_round(agg['performance'])}%", "tone": "brand"},
            {"label": "Qualité moyenne", "value": f"{_round(agg['quality'])}%",
             "tone": "good" if (agg["quality"] or 0) >= 90 else "warn"},
            {"label": "Machines suivies", "value": n_machines, "tone": "neutral"},
            {"label": "Alertes actives", "value": int(active_alerts or 0),
             "tone": "crit" if (active_alerts or 0) > 100 else "warn"},
            {"label": "IA", "value": "hors ligne", "tone": "warn"},
        ]

    machines = list(preds.values())
    at_risk = [p for p in machines if p["state"] == "at_risk"]
    risk_scores = [p["risk_score"] for p in machines]
    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    rul_values = [p["rul_days"] for p in machines if p["rul_days"] is not None]
    avg_rul = sum(rul_values) / len(rul_values) if rul_values else None

    return [
        {"label": "Machines à risque (7j)", "value": f"{len(at_risk)}/{len(machines)}",
         "tone": "crit" if at_risk else "good"},
        {"label": "Risque de panne moyen", "value": f"{round(avg_risk * 100)}%",
         "tone": "crit" if avg_risk >= 0.5 else "warn" if avg_risk >= 0.25 else "good"},
        {"label": "Durée de vie restante moyenne",
         "value": f"{round(avg_rul)} j" if avg_rul is not None else "—",
         "tone": "warn" if (avg_rul is not None and avg_rul < 90) else "good"},
        {"label": "Modèle classification", "value": clf_model, "tone": "brand"},
        {"label": "Modèle RUL", "value": rul_model, "tone": "brand"},
    ]


def build_risk_machines(machine_stats, preds, online):
    """Top machines a risque. Enrichi par l'IA (etat + risk_score + RUL) si
    disponible ; sinon repli sur un score derive du nombre d'incidents."""
    items = []
    for st in machine_stats:
        mid = st["machine_id"]
        base = {
            "id": mid,
            "name": mid,
            "incidents": int(st["incidents"] or 0),
            "lastIntervention": _fmt_date(st["last_maint"]) or "—",
        }
        pred = preds.get(mid) if online else None
        if pred is not None:
            rul = pred["rul_days"]
            base.update(
                state=pred["state"],
                riskScore=_risk_score(pred["risk_score"], rul),
                rulDays=round(rul) if rul is not None else None,
            )
        else:
            base.update(state=None, riskScore=None, rulDays=None)
        items.append(base)

    if online:
        # Score gradue decroissant, puis RUL croissante en cas d'egalite.
        items.sort(key=lambda x: (
            -(x["riskScore"] or 0),
            x["rulDays"] if x["rulDays"] is not None else 10**9,
        ))
    else:
        max_inc = max((x["incidents"] for x in items), default=1) or 1
        for x in items:
            x["riskScore"] = min(98, round(30 + 68 * x["incidents"] / max_inc))
        items.sort(key=lambda x: -x["incidents"])

    return items[:6]


def build_maintenance_plan(preds, online):
    """Interventions a planifier, triees par duree de vie restante croissante."""
    if not online:
        return []
    plan = []
    for mid, pred in preds.items():
        rul = pred["rul_days"]
        if rul is None:
            continue
        due = date.today() + timedelta(days=round(rul))
        plan.append({
            "id": mid,
            "machine": mid,
            "state": pred["state"],
            "rulDays": round(rul),
            "dueDate": due.strftime("%d/%m/%Y"),
            "status": _status_from_rul(rul),
        })
    plan.sort(key=lambda x: x["rulDays"])
    return plan


def build_ia_alerts(preds, online, factory_name, today_str, rul_threshold=90):
    """Alertes predictives : machine at_risk ou RUL sous le seuil."""
    if not online:
        return []
    order = {"critique": 0, "majeur": 1, "mineur": 2}
    out = []
    for mid, pred in preds.items():
        rul = pred["rul_days"]
        state = pred["state"]
        low_rul = rul is not None and rul < rul_threshold
        if state != "at_risk" and not low_rul:
            continue
        if state == "at_risk" and rul is not None and rul < 30:
            severity = "critique"
        elif state == "at_risk":
            severity = "majeur"
        else:
            severity = "mineur"
        reasons = []
        if state == "at_risk":
            reasons.append("panne probable sous 7 j")
        if rul is not None:
            reasons.append(f"durée de vie restante {round(rul)} j")
        out.append({
            "id": f"ia-{mid}",
            "title": "Risque de panne prédit (IA)",
            "severity": severity,
            "description": f"{mid} — {', '.join(reasons)}",
            "factory": factory_name,
            "date": today_str,
            "status": "active",
        })
    out.sort(key=lambda a: order.get(a["severity"], 3))
    return out


# --- /analytics/sites -------------------------------------------------------

@router.get("/sites")
def list_sites():
    """Liste des sites disposant de donnees de production (pour le selecteur)."""
    sql = text(
        """
        SELECT f.plant_id,
               COALESCE(p.plant_name, f.plant_id) AS plant_name,
               p.country,
               AVG(f.trs) * 100 AS trs
        FROM gold.fact_production f
        LEFT JOIN gold.dim_plant p ON p.plant_id = f.plant_id
        GROUP BY f.plant_id, p.plant_name, p.country
        ORDER BY f.plant_id
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()
    return [
        {
            "id": r["plant_id"],
            "code": r["plant_id"],
            "name": r["plant_name"],
            "country": r["country"] or "—",
            "trs": _round(r["trs"]),
            "status": _status_from_trs(r["trs"]),
        }
        for r in rows
    ]


# --- /analytics/group -------------------------------------------------------

@router.get("/group")
def group_analytics():
    """Agregats consolides tous sites (vue Groupe)."""
    with engine.connect() as conn:
        agg = conn.execute(
            text(
                """
                SELECT AVG(trs) * 100              AS trs,
                       AVG(availability_rate) * 100 AS availability,
                       AVG(performance_rate) * 100  AS performance,
                       AVG(quality_rate) * 100      AS quality,
                       AVG(scrap_rate) * 100        AS scrap,
                       SUM(good_qty)                AS good,
                       COUNT(DISTINCT plant_id)     AS sites,
                       COUNT(DISTINCT machine_id)   AS machines
                FROM gold.fact_production
                """
            )
        ).mappings().first()

        active_alerts = conn.execute(
            text("SELECT COUNT(*) FROM gold.fact_alerts WHERE is_active")
        ).scalar()

        site_rows = conn.execute(
            text(
                """
                SELECT f.plant_id,
                       COALESCE(p.plant_name, f.plant_id) AS plant_name,
                       AVG(f.trs) * 100        AS trs,
                       AVG(f.scrap_rate) * 100 AS scrap
                FROM gold.fact_production f
                LEFT JOIN gold.dim_plant p ON p.plant_id = f.plant_id
                GROUP BY f.plant_id, p.plant_name
                ORDER BY f.plant_id
                """
            )
        ).mappings().all()

        energy_rows = conn.execute(
            text(
                """
                SELECT mp.plant_id, AVG(e.energy_consumption_kwh) AS kwh
                FROM gold.fact_energy e
                JOIN (SELECT DISTINCT machine_id, plant_id FROM gold.fact_production) mp
                  ON mp.machine_id = e.machine_id
                GROUP BY mp.plant_id
                """
            )
        ).mappings().all()

        alerts_site_rows = conn.execute(
            text(
                """
                SELECT mp.plant_id, COUNT(*) AS n
                FROM gold.fact_alerts a
                JOIN (SELECT DISTINCT machine_id, plant_id FROM gold.fact_production) mp
                  ON mp.machine_id = a.machine_id
                WHERE a.is_active
                GROUP BY mp.plant_id
                """
            )
        ).mappings().all()

        alert_rows = conn.execute(
            text(
                """
                SELECT a.bronze_event_id, a.machine_id, a.date_id, a.alert_type,
                       a.alert_severity, a.alert_reason,
                       COALESCE(p.plant_name, mp.plant_id) AS plant_name
                FROM gold.fact_alerts a
                JOIN (SELECT DISTINCT machine_id, plant_id FROM gold.fact_production) mp
                  ON mp.machine_id = a.machine_id
                LEFT JOIN gold.dim_plant p ON p.plant_id = mp.plant_id
                WHERE a.is_active
                ORDER BY a.date_id DESC
                LIMIT 8
                """
            )
        ).mappings().all()

    trs_by_site = [
        {"label": r["plant_id"], "value": _round(r["trs"]), "status": _status_from_trs(r["trs"])}
        for r in site_rows
    ]
    scrap_by_site = [
        {"label": r["plant_id"], "value": _round(r["scrap"], 2), "status": _status_from_scrap(r["scrap"])}
        for r in site_rows
    ]

    energy_map = {r["plant_id"]: r["kwh"] for r in energy_rows}
    energy_vals = [float(v) for v in energy_map.values() if v is not None]
    energy_mean = sum(energy_vals) / len(energy_vals) if energy_vals else 0
    energy_by_site = [
        {
            "label": r["plant_id"],
            "value": _round(energy_map.get(r["plant_id"]), 0),
            "status": "warn" if float(energy_map.get(r["plant_id"]) or 0) > energy_mean else "good",
        }
        for r in site_rows
    ]

    alert_counts = {r["plant_id"]: int(r["n"]) for r in alerts_site_rows}
    alerts_max = max(alert_counts.values(), default=1) or 1
    alerts_by_site = [
        {
            "label": r["plant_id"],
            "value": alert_counts.get(r["plant_id"], 0),
            "status": (
                "crit" if alert_counts.get(r["plant_id"], 0) >= 0.8 * alerts_max
                else "warn" if alert_counts.get(r["plant_id"], 0) >= 0.4 * alerts_max
                else "good"
            ),
        }
        for r in site_rows
    ]

    alerts = [
        {
            "id": str(r["bronze_event_id"]),
            "title": (r["alert_type"] or "Alerte").replace("_", " ").capitalize(),
            "severity": _severity(r["alert_severity"]),
            "description": f"{r['machine_id']} — {r['alert_reason'] or r['alert_type']}",
            "factory": r["plant_name"],
            "date": _fmt_date(r["date_id"]),
            "status": "active",
        }
        for r in alert_rows
    ]

    kpis = [
        {"label": "TRS Groupe", "value": _round(agg["trs"]), "unit": "%", "trend": "flat"},
        {"label": "Disponibilité", "value": _round(agg["availability"]), "unit": "%", "trend": "flat"},
        {"label": "Performance", "value": _round(agg["performance"]), "unit": "%", "trend": "flat"},
        {"label": "Qualité", "value": _round(agg["quality"]), "unit": "%", "trend": "flat"},
        {"label": "Taux de rebut", "value": _round(agg["scrap"], 2), "unit": "%", "trend": "flat", "trendIsGood": True},
        {"label": "Production conforme", "value": int(agg["good"] or 0), "unit": "pièces"},
        {"label": "Usines", "value": int(agg["sites"] or 0)},
        {"label": "Alertes actives", "value": int(active_alerts or 0), "trend": "flat"},
    ]
    kpis = [k for k in kpis if k["value"] is not None]

    return {
        "kpis": kpis,
        "trsBySite": trs_by_site,
        "scrapBySite": scrap_by_site,
        "energyBySite": energy_by_site,
        "alertsBySite": alerts_by_site,
        "alerts": alerts,
        "siteCount": int(agg["sites"] or 0),
    }


# --- /analytics/site/{plant_id} --------------------------------------------

@router.get("/site/{plant_id}")
def site_analytics(plant_id: str):
    """Agregats complets d'un site : KPIs, series, lignes, machines, alertes."""
    with engine.connect() as conn:
        factory = conn.execute(
            text(
                """
                SELECT f.plant_id,
                       COALESCE(p.plant_name, f.plant_id) AS plant_name,
                       p.country,
                       AVG(f.trs) * 100 AS trs
                FROM gold.fact_production f
                LEFT JOIN gold.dim_plant p ON p.plant_id = f.plant_id
                WHERE f.plant_id = :p
                GROUP BY f.plant_id, p.plant_name, p.country
                """
            ),
            {"p": plant_id},
        ).mappings().first()

        if factory is None:
            raise HTTPException(status_code=404, detail="Site introuvable ou sans donnees")

        agg = conn.execute(
            text(
                """
                SELECT AVG(trs) * 100              AS trs,
                       AVG(availability_rate) * 100 AS availability,
                       AVG(performance_rate) * 100  AS performance,
                       AVG(quality_rate) * 100      AS quality,
                       AVG(scrap_rate) * 100        AS scrap,
                       AVG(cycle_time_sec)          AS cycle_time,
                       AVG(downtime_minutes)        AS downtime,
                       SUM(good_qty)                AS good,
                       SUM(actual_production_qty)   AS actual
                FROM gold.fact_production
                WHERE plant_id = :p
                """
            ),
            {"p": plant_id},
        ).mappings().first()

        active_alerts = conn.execute(
            text(
                """
                SELECT COUNT(*) AS n
                FROM gold.fact_alerts a
                WHERE a.is_active
                  AND a.machine_id IN (
                      SELECT DISTINCT machine_id FROM gold.fact_production WHERE plant_id = :p
                  )
                """
            ),
            {"p": plant_id},
        ).scalar()

        trs_rows = conn.execute(
            text(
                """
                SELECT date_id, AVG(trs) * 100 AS v
                FROM gold.fact_production
                WHERE plant_id = :p
                GROUP BY date_id
                ORDER BY date_id DESC
                LIMIT 14
                """
            ),
            {"p": plant_id},
        ).mappings().all()

        energy_rows = conn.execute(
            text(
                """
                SELECT date_id, AVG(energy_consumption_kwh) AS v
                FROM gold.fact_energy
                WHERE machine_id IN (
                    SELECT DISTINCT machine_id FROM gold.fact_production WHERE plant_id = :p
                )
                GROUP BY date_id
                ORDER BY date_id DESC
                LIMIT 14
                """
            ),
            {"p": plant_id},
        ).mappings().all()

        line_rows = conn.execute(
            text(
                """
                SELECT production_line_id,
                       AVG(trs) * 100            AS trs,
                       SUM(good_qty)             AS good,
                       SUM(actual_production_qty) AS actual
                FROM gold.fact_production
                WHERE plant_id = :p
                GROUP BY production_line_id
                ORDER BY production_line_id
                """
            ),
            {"p": plant_id},
        ).mappings().all()

        machine_stats = conn.execute(
            text(
                """
                SELECT m.machine_id,
                       COALESCE(a.incidents, 0) AS incidents,
                       mt.last_maint
                FROM (
                    SELECT DISTINCT machine_id FROM gold.fact_production WHERE plant_id = :p
                ) m
                LEFT JOIN (
                    SELECT machine_id, COUNT(*) AS incidents
                    FROM gold.fact_alerts WHERE is_active GROUP BY machine_id
                ) a ON a.machine_id = m.machine_id
                LEFT JOIN (
                    SELECT machine_id, MAX(date_id) AS last_maint
                    FROM gold.fact_maintenance GROUP BY machine_id
                ) mt ON mt.machine_id = m.machine_id
                ORDER BY m.machine_id
                """
            ),
            {"p": plant_id},
        ).mappings().all()

        alert_rows = conn.execute(
            text(
                """
                SELECT bronze_event_id, machine_id, date_id,
                       alert_type, alert_severity, alert_reason
                FROM gold.fact_alerts
                WHERE is_active
                  AND machine_id IN (
                      SELECT DISTINCT machine_id FROM gold.fact_production WHERE plant_id = :p
                  )
                ORDER BY date_id DESC
                LIMIT 8
                """
            ),
            {"p": plant_id},
        ).mappings().all()

        # Derniere mesure capteur par machine (entree du modele IA).
        sensor_rows = conn.execute(
            text(
                """
                SELECT DISTINCT ON (machine_id)
                       machine_id, event_ts, cycle_time_sec, temperature_c,
                       vibration_mms, sound_db, oil_level_pct, coolant_level_pct,
                       hydraulic_pressure_bar, coolant_flow_l_min, heat_index,
                       power_consumption_kw, operational_hours,
                       error_codes_last_30_days, quality_status, ai_override_events
                FROM silver.sensor_events
                WHERE machine_id IN (
                    SELECT DISTINCT machine_id FROM gold.fact_production WHERE plant_id = :p
                )
                ORDER BY machine_id, event_ts DESC NULLS LAST
                """
            ),
            {"p": plant_id},
        ).mappings().all()

    # --- Mise en forme ------------------------------------------------------
    trs_series = [
        {"label": _fmt_day(r["date_id"]), "value": _round(r["v"])}
        for r in reversed(trs_rows)
    ]
    energy_series = [
        {"label": _fmt_day(r["date_id"]), "value": _round(r["v"], 0)}
        for r in reversed(energy_rows)
    ]

    lines = []
    for r in line_rows:
        good = int(r["good"] or 0)
        actual = int(r["actual"] or 0)
        reach = (good / actual * 100) if actual else None
        lines.append(
            {
                "id": r["production_line_id"],
                "name": r["production_line_id"],
                "trs": _round(r["trs"]),
                "production": good,
                "target": actual,
                "status": _status_from_reach(reach),
            }
        )

    factory_name = factory["plant_name"]

    # Predictions IA par machine (1 seul aller-retour, reutilise partout).
    preds, clf_model, rul_model, ia_online = run_ia(plant_id, sensor_rows)

    risk_machines = build_risk_machines(machine_stats, preds, ia_online)
    maintenance_plan = build_maintenance_plan(preds, ia_online)

    today_str = date.today().strftime("%d/%m/%Y")
    ia_alerts = build_ia_alerts(preds, ia_online, factory_name, today_str)

    severity_map = {
        "critical": "critique",
        "high": "critique",
        "major": "majeur",
        "warning": "majeur",
        "medium": "majeur",
    }
    db_alerts = [
        {
            "id": str(r["bronze_event_id"]),
            "title": (r["alert_type"] or "Alerte").replace("_", " ").capitalize(),
            "severity": severity_map.get((r["alert_severity"] or "").lower(), "mineur"),
            "description": f"{r['machine_id']} — {r['alert_reason'] or r['alert_type']}",
            "factory": factory_name,
            "date": _fmt_date(r["date_id"]),
            "status": "active",
        }
        for r in alert_rows
    ]
    # Alertes predictives IA en tete, puis alertes capteurs du warehouse.
    alerts = (ia_alerts + db_alerts)[:8]

    kpis = [
        {"label": "TRS", "value": _round(agg["trs"]), "unit": "%", "trend": "flat"},
        {"label": "Disponibilité", "value": _round(agg["availability"]), "unit": "%", "trend": "flat"},
        {"label": "Performance", "value": _round(agg["performance"]), "unit": "%", "trend": "flat"},
        {"label": "Qualité", "value": _round(agg["quality"]), "unit": "%", "trend": "flat"},
        {"label": "Taux de rebut", "value": _round(agg["scrap"], 2), "unit": "%", "trend": "flat", "trendIsGood": True},
        {"label": "Temps cycle moyen", "value": _round(agg["cycle_time"]), "unit": "s", "trend": "flat"},
        {"label": "Production conforme", "value": int(agg["good"] or 0), "unit": "pièces"},
        {"label": "Alertes actives", "value": int(active_alerts or 0), "trend": "flat"},
    ]
    # On n'affiche pas les KPI sans donnee (ex. temps de cycle : colonne vide).
    kpis = [k for k in kpis if k["value"] is not None]

    ia_indicators = build_ia_indicators(
        preds, clf_model, rul_model, ia_online, agg, active_alerts, len(sensor_rows)
    )

    return {
        "factory": {
            "id": factory["plant_id"],
            "code": factory["plant_id"],
            "name": factory_name,
            "country": factory["country"] or "—",
            "trs": _round(factory["trs"]),
            "status": _status_from_trs(factory["trs"]),
        },
        "kpis": kpis,
        "trsSeries": trs_series,
        "energySeries": energy_series,
        "lines": lines,
        "riskMachines": risk_machines,
        "maintenancePlan": maintenance_plan,
        "alerts": alerts,
        "iaIndicators": ia_indicators,
        "iaOnline": ia_online,
    }
