"""
monitor.py — Stateful fermentation monitor for live inference.

Feed SensorReadings one at a time via FermentationMonitor.update().
Notifications fire on confirmed stage transitions.
"""

import json
import joblib
import warnings
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

warnings.filterwarnings(
    "ignore",
    message="X does not have valid feature names",
    category=UserWarning,
)

from config import STAGE_NAMES, LONG_WIN, MODEL_PATH
from lib.data import engineer_features


# ---------------------------------------------------------------------------
# Sensor reading
# ---------------------------------------------------------------------------


@dataclass
class SensorReading:
    timestamp: datetime
    temperature: float
    humidity: float
    distance: float
    co2: float
    starter_ratio: float = 1.0
    water_ratio: float = 1.0
    flour_ratio: float = 1.0


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------


@dataclass
class FermentationMonitor:
    """
    Stateful monitor. Call update() for each new sensor reading.

    Stage transitions are confirmed via two layers of smoothing:
      1. Majority vote over the last `smoothing_window` raw predictions.
      2. A transition must persist for `min_stage_samples` before being confirmed.

    Stages only move forward (Lag → Exponential → Peak → Decline).
    A Peak timeout fires Decline if the model gets stuck.

    Set silent=True to suppress console notifications (e.g. during batch inference).
    Transition events are always written to notifications.log regardless of silent.
    """

    model_path: Path = MODEL_PATH
    smoothing_window: int = 3
    min_stage_samples: int = 2
    peak_timeout_min: int = 120
    silent: bool = True

    _model: object = field(init=False, default=None)
    _is_cnn: bool = field(init=False, default=False)
    _buffer: list = field(init=False, default_factory=list)
    _pred_buffer: list = field(init=False, default_factory=list)
    _current_stage: int = field(init=False, default=0)
    _stage_sample_cnt: int = field(init=False, default=0)
    _baseline_dist: Optional[float] = field(init=False, default=None)
    _peak_entered_at: Optional[datetime] = field(init=False, default=None)

    def __post_init__(self):
        keras_path = Path(str(self.model_path) + ".keras")
        if keras_path.exists():
            from cnn import CNNModel

            self._model = CNNModel(self.model_path)
            self._is_cnn = True
        else:
            self._model = joblib.load(self.model_path)
            self._is_cnn = False
        if not self.silent:
            print(f"Model loaded from {self.model_path}")

    def _reading_to_row(self, reading: SensorReading) -> dict:
        elapsed = 0.0
        if self._buffer:
            elapsed = (
                reading.timestamp - self._buffer[0].timestamp
            ).total_seconds() / 60
        return {
            "timestamp": reading.timestamp,
            "elapsed_min": elapsed,
            "temperature": reading.temperature,
            "humidity": reading.humidity,
            "distance": reading.distance,
            "co2": reading.co2,
            "starter_ratio": reading.starter_ratio,
            "water_ratio": reading.water_ratio,
            "flour_ratio": reading.flour_ratio,
        }

    def _predict_current(self) -> int:
        df = pd.DataFrame([self._reading_to_row(r) for r in self._buffer])
        if self._baseline_dist is None:
            self._baseline_dist = df["distance"].iloc[0]
        feats = engineer_features(df)
        if self._is_cnn:
            self._model.update_buffer(feats.iloc[-1].values)
            return int(self._model.predict(feats.iloc[[-1]])[0])
        return int(self._model.predict(feats.iloc[[-1]])[0])

    def _smoothed_stage(self) -> Optional[int]:
        if len(self._pred_buffer) < self.smoothing_window:
            return None
        recent = self._pred_buffer[-self.smoothing_window :]
        counts = np.bincount(recent, minlength=4)
        return int(np.argmax(counts))

    def _notify(self, stage: int, reading: SensorReading) -> None:
        rise = (self._baseline_dist or reading.distance) - reading.distance
        msg = (
            f"\n{'='*50}\n"
            f"🍞 FERMENTATION UPDATE — {reading.timestamp.strftime('%H:%M:%S')}\n"
            f"   Stage: {STAGE_NAMES[stage]}\n"
            f"   Temp: {reading.temperature:.1f}°C  |  Humidity: {reading.humidity:.1f}%\n"
            f"   Rise: {rise:.1f}mm  |  CO₂: {reading.co2:.0f}ppm\n"
            f"{'='*50}"
        )
        if not self.silent:
            print(msg)

        with open("notifications.log", "a") as f:
            f.write(
                json.dumps(
                    {
                        "time": reading.timestamp.isoformat(),
                        "stage": STAGE_NAMES[stage],
                        "temp": reading.temperature,
                        "co2": reading.co2,
                    }
                )
                + "\n"
            )

    def update(self, reading: SensorReading) -> int:
        """
        Ingest one new sensor reading.
        Returns the current confirmed stage.
        Fires _notify() on confirmed stage transitions.
        """
        self._buffer.append(reading)

        if len(self._buffer) < LONG_WIN:
            return self._current_stage

        if len(self._buffer) > LONG_WIN * 4:
            self._buffer = self._buffer[-(LONG_WIN * 4) :]

        raw_pred = self._predict_current()
        self._pred_buffer.append(raw_pred)

        smoothed = self._smoothed_stage()
        if smoothed is None:
            return self._current_stage

        if smoothed < self._current_stage:
            return self._current_stage

        if self._current_stage == 2:
            if self._peak_entered_at is None:
                self._peak_entered_at = reading.timestamp
            else:
                elapsed = (
                    reading.timestamp - self._peak_entered_at
                ).total_seconds() / 60
                if elapsed >= self.peak_timeout_min:
                    self._current_stage = 3
                    self._peak_entered_at = None
                    self._notify(3, reading)
                    return self._current_stage

        if smoothed != self._current_stage:
            self._stage_sample_cnt += 1
            if self._stage_sample_cnt >= self.min_stage_samples:
                self._current_stage = smoothed
                self._stage_sample_cnt = 0
                if smoothed > 0:
                    self._notify(smoothed, reading)
        else:
            self._stage_sample_cnt = 0

        return self._current_stage
