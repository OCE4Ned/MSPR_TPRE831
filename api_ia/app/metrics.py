from prometheus_client import Gauge, Counter, Histogram

models_loaded = Gauge("ia_models_loaded", "Nombre de modèles chargés")
api_ready = Gauge("ia_api_ready", "1 si l'API est prête, 0 sinon")

predictions_total = Counter(
    "ia_predictions_total",
    "Nombre total de prédictions",
    ["model", "status"],
)
prediction_latency = Histogram(
    "ia_prediction_duration_seconds",
    "Durée d'inférence",
    ["model"],
)