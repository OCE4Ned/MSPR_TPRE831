import joblib
import mlflow.pyfunc
import numpy as np
import pandas as pd


class ClassifierWrapper(mlflow.pyfunc.PythonModel):
    """sklearn / XGBoost / LightGBM classifier binaire.
    Sortie : DataFrame avec colonne 'risk_score' (proba classe positive)."""

    def load_context(self, context):
        self.model = joblib.load(context.artifacts["model"])

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        proba = self.model.predict_proba(model_input)[:, 1]
        return pd.DataFrame({"risk_score": proba})


class RegressorWrapper(mlflow.pyfunc.PythonModel):
    """sklearn / XGBoost regressor.
    Sortie : DataFrame avec colonne 'predicted_rul_days'."""

    def load_context(self, context):
        self.model = joblib.load(context.artifacts["model"])

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        pred = self.model.predict(model_input)
        # Clamp côté wrapper : un RUL négatif n'a pas de sens physique
        pred = np.clip(pred, a_min=0.0, a_max=None)
        return pd.DataFrame({"predicted_rul_days": pred})


class AnomalyWrapper(mlflow.pyfunc.PythonModel):
    """sklearn IsolationForest.
    Convention : 'anomaly_score' positif et croissant = plus anomal."""

    def load_context(self, context):
        self.model = joblib.load(context.artifacts["model"])

    def predict(self, context, model_input: pd.DataFrame) -> pd.DataFrame:
        # IsolationForest.score_samples renvoie plus c'est BAS, plus c'est anomal.
        # On inverse pour avoir une convention intuitive.
        scores = -self.model.score_samples(model_input)
        is_anomaly = self.model.predict(model_input) == -1
        return pd.DataFrame({
            "anomaly_score": scores,
            "is_anomaly": is_anomaly,
        })


class SequenceRegressorWrapper(mlflow.pyfunc.PythonModel):
    """Keras / TensorFlow LSTM. Entrée : ndarray (N, T, F).
    Sortie : DataFrame avec 'predicted_rul_days'."""

    def load_context(self, context):
        import tensorflow as tf  # import paresseux
        self.model = tf.keras.models.load_model(context.artifacts["model"])

    def predict(self, context, model_input) -> pd.DataFrame:
        arr = np.asarray(model_input)
        pred = self.model.predict(arr, verbose=0).ravel()
        pred = np.clip(pred, a_min=0.0, a_max=None)
        return pd.DataFrame({"predicted_rul_days": pred})