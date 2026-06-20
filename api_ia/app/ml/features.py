import numpy as np
import pandas as pd

from app.dto.predictions import MachineFeatures, MachineSequence, SensorReading

# Source unique. Ordre garanti par Pydantic (ordre de déclaration).
FEATURE_COLUMNS: tuple[str, ...] = tuple(SensorReading.model_fields.keys())


def features_to_dataframe(features: MachineFeatures) -> pd.DataFrame:
    return pd.DataFrame([features.sensors.model_dump()], columns=list(FEATURE_COLUMNS))


def features_batch_to_dataframe(items: list[MachineFeatures]) -> pd.DataFrame:
    return pd.DataFrame(
        [f.sensors.model_dump() for f in items],
        columns=list(FEATURE_COLUMNS),
    )


def sequence_to_array(sequence: MachineSequence) -> np.ndarray:
    rows = [[getattr(r, col) for col in FEATURE_COLUMNS] for r in sequence.readings]
    arr = np.array(rows, dtype=np.float32)
    return arr.reshape(1, arr.shape[0], arr.shape[1])