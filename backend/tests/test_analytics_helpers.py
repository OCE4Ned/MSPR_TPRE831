"""Tests unitaires des fonctions pures du routeur analytics."""

from datetime import datetime

import pytest

from app.routers import analytics
from app.services import ia_client


# --- _status_from_trs -------------------------------------------------------

@pytest.mark.parametrize(
    "trs, expected",
    [(95, "good"), (85, "good"), (84.9, "warn"), (70, "warn"), (69, "crit"), (0, "crit"), (None, "crit")],
)
def test_status_from_trs(trs, expected):
    assert analytics._status_from_trs(trs) == expected


# --- _status_from_reach -----------------------------------------------------

@pytest.mark.parametrize(
    "reach, expected",
    [(100, "good"), (90, "good"), (89, "warn"), (80, "warn"), (79, "crit"), (None, "crit")],
)
def test_status_from_reach(reach, expected):
    assert analytics._status_from_reach(reach) == expected


# --- _fmt_day / _fmt_date ---------------------------------------------------

def test_fmt_day_valid():
    assert analytics._fmt_day(20260329) == "29/03"


def test_fmt_date_valid():
    assert analytics._fmt_date(20260329) == "29/03/2026"


@pytest.mark.parametrize("fn", [analytics._fmt_day, analytics._fmt_date])
def test_fmt_none_returns_empty(fn):
    assert fn(None) == ""


def test_fmt_unexpected_length_passthrough():
    # Longueur != 8 -> on renvoie la chaine telle quelle.
    assert analytics._fmt_day(123) == "123"


# --- _round -----------------------------------------------------------------

def test_round_none():
    assert analytics._round(None) is None


def test_round_default_one_digit():
    assert analytics._round(19.6789) == 19.7


def test_round_custom_digits():
    assert analytics._round(2.71828, 2) == 2.72


# --- _model_label -----------------------------------------------------------

def test_model_label_with_version():
    resp = [{"model_name": "mecha-rul-regressor", "model_version": "1"}]
    assert analytics._model_label(resp) == "mecha-rul-regressor v1"


def test_model_label_without_version():
    assert analytics._model_label([{"model_name": "clf"}]) == "clf"


def test_model_label_skips_entries_without_model():
    resp = [{"machine_id": "M1"}, {"model_name": "clf", "model_version": "2"}]
    assert analytics._model_label(resp) == "clf v2"


def test_model_label_empty():
    assert analytics._model_label([]) == "—"


# --- _machine_feature -------------------------------------------------------

def _full_sensor_row(machine_id="QLT_FR_001", event_ts=datetime(2026, 3, 29, 12, 0, 0)):
    row = {"machine_id": machine_id, "event_ts": event_ts}
    for field in ia_client.SENSOR_FIELDS:
        row[field] = 5  # valeur numerique neutre
    row["quality_status"] = "valid_sensor_event"
    return row


def test_machine_feature_structure_and_casts():
    row = _full_sensor_row()
    feat = analytics._machine_feature("FR01", row)

    assert feat["machine_id"] == "QLT_FR_001"
    assert feat["site"] == "FR01"
    assert feat["timestamp"] == "2026-03-29T12:00:00"
    sensors = feat["sensors"]
    # Entiers
    assert isinstance(sensors["error_codes_last_30_days"], int)
    assert isinstance(sensors["ai_override_events"], int)
    # Texte
    assert sensors["quality_status"] == "valid_sensor_event"
    # Numerique -> float
    assert isinstance(sensors["temperature_c"], float)


def test_machine_feature_handles_nulls():
    row = _full_sensor_row()
    row["temperature_c"] = None
    row["error_codes_last_30_days"] = None
    row["quality_status"] = None
    feat = analytics._machine_feature("FR01", row)
    assert feat["sensors"]["temperature_c"] == 0.0
    assert feat["sensors"]["error_codes_last_30_days"] == 0
    assert feat["sensors"]["quality_status"] == "valid_sensor_event"


def test_machine_feature_default_timestamp_when_missing():
    row = _full_sensor_row(event_ts=None)
    feat = analytics._machine_feature("FR01", row)
    assert feat["timestamp"] == "2026-01-01T00:00:00"


# --- _status_from_rul -------------------------------------------------------

@pytest.mark.parametrize(
    "rul, expected",
    [(None, "good"), (200, "good"), (90, "good"), (89, "warn"), (30, "warn"), (29, "crit"), (0, "crit")],
)
def test_status_from_rul(rul, expected):
    assert analytics._status_from_rul(rul) == expected


# --- _status_from_scrap / _severity -----------------------------------------

@pytest.mark.parametrize(
    "scrap, expected",
    [(None, "good"), (0, "good"), (2.9, "good"), (3, "warn"), (4.9, "warn"), (5, "crit"), (10, "crit")],
)
def test_status_from_scrap(scrap, expected):
    assert analytics._status_from_scrap(scrap) == expected


@pytest.mark.parametrize(
    "value, expected",
    [("critical", "critique"), ("high", "critique"), ("major", "majeur"),
     ("warning", "majeur"), ("unknown", "mineur"), (None, "mineur")],
)
def test_severity(value, expected):
    assert analytics._severity(value) == expected


# --- _risk_score ------------------------------------------------------------

@pytest.mark.parametrize(
    "risk, rul, expected",
    [
        (1.0, 73, 90),     # at_risk + RUL courte : 0.5*100 + 0.5*80
        (0.0, 187, 24),    # normal + RUL moyenne : 0.5*0 + 0.5*48.77
        (1.0, None, 100),  # pas de RUL -> classifieur brut
        (0.0, None, 0),
        (0.0, 0, 50),      # RUL nulle -> urgence max (100) ponderee 0.5
        (0.0, 400, 0),     # RUL > horizon -> urgence bornee a 0
    ],
)
def test_risk_score(risk, rul, expected):
    assert analytics._risk_score(risk, rul) == expected


# --- run_ia -----------------------------------------------------------------

def _states(machines):
    return [{"machine_id": m, "state": st, "risk_score": rs,
             "model_name": "mecha-failure-7d-classifier", "model_version": "1"}
            for m, st, rs in machines]


def _ruls(items):
    return [{"machine_id": m, "remaining_useful_life_days": d,
             "model_name": "mecha-rul-regressor", "model_version": "1"} for m, d in items]


def test_run_ia_online(monkeypatch):
    rows = [_full_sensor_row(m) for m in ("CNC_FR_001", "LAS_FR_001")]
    monkeypatch.setattr(ia_client, "predict_state_batch",
                        lambda f: _states([("CNC_FR_001", "normal", 0.0), ("LAS_FR_001", "at_risk", 1.0)]))
    monkeypatch.setattr(ia_client, "predict_rul_many",
                        lambda f: _ruls([("CNC_FR_001", 241.0), ("LAS_FR_001", 73.0)]))

    preds, clf, rul, online = analytics.run_ia("FR01", rows)
    assert online is True
    assert preds["LAS_FR_001"] == {"state": "at_risk", "risk_score": 1.0, "rul_days": 73.0}
    assert clf == "mecha-failure-7d-classifier v1"
    assert rul == "mecha-rul-regressor v1"


def test_run_ia_offline_on_error(monkeypatch):
    def boom(_):
        raise RuntimeError("IA injoignable")

    monkeypatch.setattr(ia_client, "predict_state_batch", boom)
    preds, clf, rul, online = analytics.run_ia("FR01", [_full_sensor_row()])
    assert online is False and preds == {} and clf == "—"


def test_run_ia_offline_when_no_sensors():
    _, _, _, online = analytics.run_ia("FR01", [])
    assert online is False


# --- build_ia_indicators ----------------------------------------------------

def test_build_ia_indicators_online():
    preds = {
        "A": {"state": "at_risk", "risk_score": 1.0, "rul_days": 73.0},
        "B": {"state": "normal", "risk_score": 0.0, "rul_days": 200.0},
        "C": {"state": "at_risk", "risk_score": 1.0, "rul_days": None},
        "D": {"state": "normal", "risk_score": 0.0, "rul_days": 150.0},
    }
    ind = analytics.build_ia_indicators(preds, "clf v1", "rul v1", True, {}, 0, 4)
    by = {i["label"]: i["value"] for i in ind}
    assert by["Machines à risque (7j)"] == "2/4"
    assert by["Risque de panne moyen"] == "50%"
    # moyenne des RUL disponibles : (73 + 200 + 150) / 3 = 141
    assert by["Durée de vie restante moyenne"] == "141 j"
    assert by["Modèle classification"] == "clf v1"


def test_build_ia_indicators_offline():
    ind = analytics.build_ia_indicators({}, "—", "—", False, {"performance": 23.0, "quality": 97.0}, 4764, 4)
    assert "IA" in [i["label"] for i in ind]


# --- build_risk_machines ----------------------------------------------------

def _stats(items):
    return [{"machine_id": m, "incidents": i, "last_maint": lm} for m, i, lm in items]


def test_build_risk_machines_online_sorted():
    stats = _stats([("CNC", 37, 20260328), ("LAS", 294, 20260329),
                    ("QLT", 4372, 20260329), ("FOU", 61, 20260328)])
    preds = {
        "CNC": {"state": "normal", "risk_score": 0.0, "rul_days": 241.0},
        "FOU": {"state": "normal", "risk_score": 0.0, "rul_days": 187.0},
        "LAS": {"state": "at_risk", "risk_score": 1.0, "rul_days": 73.0},
        "QLT": {"state": "at_risk", "risk_score": 1.0, "rul_days": 80.0},
    }
    out = analytics.build_risk_machines(stats, preds, True)
    # Score gradue : LAS (at_risk, RUL 73) devant QLT (at_risk, RUL 80)
    assert [m["id"] for m in out[:2]] == ["LAS", "QLT"]
    assert out[0]["state"] == "at_risk"
    assert out[0]["riskScore"] == 90  # 0.5*100 + 0.5*80
    assert out[0]["rulDays"] == 73
    # Les scores sont bien decroissants
    scores = [m["riskScore"] for m in out]
    assert scores == sorted(scores, reverse=True)


def test_build_risk_machines_offline_heuristic():
    stats = _stats([("CNC", 37, None), ("QLT", 4372, None)])
    out = analytics.build_risk_machines(stats, {}, False)
    assert out[0]["id"] == "QLT"  # plus d'incidents en tete
    assert out[0]["state"] is None
    assert isinstance(out[0]["riskScore"], int)


# --- build_maintenance_plan -------------------------------------------------

def test_build_maintenance_plan_sorted_by_rul():
    preds = {
        "A": {"state": "normal", "risk_score": 0.0, "rul_days": 200.0},
        "B": {"state": "at_risk", "risk_score": 1.0, "rul_days": 30.0},
        "C": {"state": "normal", "risk_score": 0.0, "rul_days": None},
    }
    plan = analytics.build_maintenance_plan(preds, True)
    assert [p["machine"] for p in plan] == ["B", "A"]  # C exclu (RUL None)
    assert plan[0]["rulDays"] == 30
    assert "dueDate" in plan[0]


def test_build_maintenance_plan_offline_empty():
    preds = {"A": {"state": "normal", "risk_score": 0, "rul_days": 10}}
    assert analytics.build_maintenance_plan(preds, False) == []


# --- build_ia_alerts --------------------------------------------------------

def test_build_ia_alerts_severity_and_order():
    preds = {
        "A": {"state": "at_risk", "risk_score": 1.0, "rul_days": 20.0},   # critique
        "B": {"state": "at_risk", "risk_score": 1.0, "rul_days": 100.0},  # majeur
        "C": {"state": "normal", "risk_score": 0.0, "rul_days": 45.0},    # mineur (rul<90)
        "D": {"state": "normal", "risk_score": 0.0, "rul_days": 200.0},   # aucun
    }
    alerts = analytics.build_ia_alerts(preds, True, "Usine Lyon", "01/07/2026")
    sev = {a["id"]: a["severity"] for a in alerts}
    assert sev == {"ia-A": "critique", "ia-B": "majeur", "ia-C": "mineur"}
    assert alerts[0]["severity"] == "critique"  # trie par gravite


def test_build_ia_alerts_offline_empty():
    preds = {"A": {"state": "at_risk", "risk_score": 1, "rul_days": 10}}
    assert analytics.build_ia_alerts(preds, False, "L", "d") == []
