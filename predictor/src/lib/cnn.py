"""
cnn.py — 1D CNN backend for fermentation stage classification.

Requires: pip install tensorflow

The CNN operates on raw sliding windows of sensor sequences rather than
hand-engineered features. Each sample is a window of WINDOW_SIZE timesteps
across all sensor channels, giving the model the full temporal shape to learn from.

Saved as two files:
    <model_path>.keras  - the Keras model weights and architecture
    <model_path>.scaler - the fitted StandardScaler (joblib)
"""

import numpy as np
import joblib
from pathlib import Path

from config import STAGE_NAMES

# ---------------------------------------------------------------------------
# CNN config
# ---------------------------------------------------------------------------

WINDOW_SIZE = 30    # timesteps per sample (~30 min at 1 sample/min)
N_CLASSES   = len(STAGE_NAMES)

CNN_DEFAULTS = dict(
    filters_1    = 64,
    filters_2    = 128,
    kernel_size  = 5,
    dropout      = 0.3,
    dense_units  = 64,
    learning_rate= 0.001,
    epochs       = 50,
    batch_size   = 32,
)

CNN_PARAM_GRID = {
    "filters_1":     [32, 64],
    "filters_2":     [64, 128],
    "kernel_size":   [3, 5],
    "dropout":       [0.2, 0.3],
    "dense_units":   [32, 64],
    "learning_rate": [0.001, 0.0005],
    "epochs":        [50],
    "batch_size":    [32],
}


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def make_windows(X: np.ndarray, y: np.ndarray, groups: np.ndarray):
    """
    Slide a window over each run independently to build 3D arrays.
    Windows never cross run boundaries.

    Returns:
        X_win:  (n_windows, WINDOW_SIZE, n_features)
        y_win:  (n_windows,)  label = label of the last timestep in window
        g_win:  (n_windows,)  group = run_id of the window
    """
    X_wins, y_wins, g_wins = [], [], []
    unique_groups = np.unique(groups)

    for gid in unique_groups:
        mask  = groups == gid
        X_run = X[mask]
        y_run = y[mask]

        for i in range(WINDOW_SIZE, len(X_run) + 1):
            X_wins.append(X_run[i - WINDOW_SIZE:i])
            y_wins.append(y_run[i - 1])          # label of the last step
            g_wins.append(gid)

    return (
        np.array(X_wins, dtype=np.float32),
        np.array(y_wins, dtype=np.int32),
        np.array(g_wins),
    )


# ---------------------------------------------------------------------------
# Model architecture
# ---------------------------------------------------------------------------

def build_cnn(n_features: int, params: dict):
    """Build and compile a 1D CNN Keras model."""
    try:
        from tensorflow import keras
        from tensorflow.keras import layers
    except ImportError:
        raise ImportError("TensorFlow is not installed. Run: pip install tensorflow")

    model = keras.Sequential([
        layers.Input(shape=(WINDOW_SIZE, n_features)),

        layers.Conv1D(params["filters_1"], params["kernel_size"],
                      activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.MaxPooling1D(pool_size=2),
        layers.Dropout(params["dropout"]),

        layers.Conv1D(params["filters_2"], params["kernel_size"],
                      activation="relu", padding="same"),
        layers.BatchNormalization(),
        layers.GlobalAveragePooling1D(),
        layers.Dropout(params["dropout"]),

        layers.Dense(params["dense_units"], activation="relu"),
        layers.Dense(N_CLASSES, activation="softmax"),
    ])

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=params["learning_rate"]),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ---------------------------------------------------------------------------
# Train / evaluate
# ---------------------------------------------------------------------------

def train_cnn(
    X:          np.ndarray,
    y:          np.ndarray,
    groups:     np.ndarray,
    params:     dict,
    model_path: Path,
    test_size:  float = 0.25,
    seed:       int   = 42,
    verbose:    int   = 1,
) -> dict:
    """
    Train the CNN, evaluate on a held-out group split, save model + scaler.

    Returns dict with test accuracy and f1_macro.
    """
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.metrics import classification_report, f1_score
    try:
        from tensorflow.keras.callbacks import EarlyStopping
    except ImportError:
        raise ImportError("TensorFlow is not installed. Run: pip install tensorflow")

    # Group-aware split — skip when test_size is None (train on all data)
    if test_size:
        splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=seed)
        train_idx, test_idx = next(splitter.split(X, y, groups))
        X_train, y_train = X[train_idx], y[train_idx]
        X_test,  y_test  = X[test_idx],  y[test_idx]
    else:
        X_train, y_train = X, y
        X_test,  y_test  = None, None

    # Scale per-feature across the time axis
    n_samples, n_steps, n_feats = X_train.shape
    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train.reshape(-1, n_feats)).reshape(n_samples, n_steps, n_feats)
    X_test  = scaler.transform(X_test.reshape(-1, n_feats)).reshape(X_test.shape[0], n_steps, n_feats)

    model = build_cnn(n_feats, params)

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)
    ]

    model.fit(
        X_train, y_train,
        validation_split = 0.15,
        epochs           = params["epochs"],
        batch_size       = params["batch_size"],
        callbacks        = callbacks,
        verbose          = verbose,
    )

    # Evaluate — only if a test set was held out
    if X_test is not None:
        y_pred = np.argmax(model.predict(X_test, verbose=0), axis=1)
        print("\n--- CNN Test Set Results ---")
        print(classification_report(y_test, y_pred, target_names=list(STAGE_NAMES.values())))
        score = f1_score(y_test, y_pred, average="macro")
    else:
        score = 0.0

    # Save
    keras_path  = Path(str(model_path) + ".keras")
    scaler_path = Path(str(model_path) + ".scaler")
    model.save(keras_path)
    joblib.dump(scaler, scaler_path)
    print(f"CNN model saved → {keras_path}")
    print(f"CNN scaler saved → {scaler_path}")

    return {"f1_macro": score, "model": model, "scaler": scaler}


def cv_score_cnn(
    X:       np.ndarray,
    y:       np.ndarray,
    groups:  np.ndarray,
    params:  dict,
    n_folds: int = 3,
) -> tuple[float, float]:
    """
    Group k-fold CV for the CNN. Returns (mean_f1, std_f1).
    Kept to a small fold count by default — CNN training is slow.
    """
    from sklearn.model_selection import GroupKFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import f1_score
    import tensorflow as tf

    cv     = GroupKFold(n_splits=n_folds)
    scores = []

    for fold, (train_idx, test_idx) in enumerate(cv.split(X, y, groups), 1):
        print(f"    Fold {fold}/{n_folds}...")
        X_tr, y_tr = X[train_idx], y[train_idx]
        X_te, y_te = X[test_idx],  y[test_idx]

        n_s, n_st, n_f = X_tr.shape
        scaler = StandardScaler()
        X_tr   = scaler.fit_transform(X_tr.reshape(-1, n_f)).reshape(n_s, n_st, n_f)
        X_te   = scaler.transform(X_te.reshape(-1, n_f)).reshape(X_te.shape[0], n_st, n_f)

        model = build_cnn(n_f, params)
        model.fit(X_tr, y_tr,
                  epochs=params["epochs"], batch_size=params["batch_size"],
                  verbose=0)

        y_pred = np.argmax(model.predict(X_te, verbose=0), axis=1)
        scores.append(f1_score(y_te, y_pred, average="macro"))

        # Free GPU memory between folds
        del model
        tf.keras.backend.clear_session()

    return float(np.mean(scores)), float(np.std(scores))


# ---------------------------------------------------------------------------
# Inference wrapper — mirrors sklearn Pipeline.predict() interface
# ---------------------------------------------------------------------------

class CNNModel:
    """
    Wraps a saved Keras CNN + scaler to expose a sklearn-compatible
    predict() interface, so monitor.py doesn't need to know the backend.
    """

    def __init__(self, model_path: Path):
        try:
            from tensorflow import keras
        except ImportError:
            raise ImportError("TensorFlow is not installed. Run: pip install tensorflow")

        keras_path  = Path(str(model_path) + ".keras")
        scaler_path = Path(str(model_path) + ".scaler")

        if not keras_path.exists():
            raise FileNotFoundError(f"CNN model not found: {keras_path}")
        if not scaler_path.exists():
            raise FileNotFoundError(f"CNN scaler not found: {scaler_path}")

        self._model  = keras.models.load_model(keras_path)
        self._scaler = joblib.load(scaler_path)
        self._window = []    # rolling buffer of feature vectors

    def update_buffer(self, feature_row: np.ndarray) -> None:
        """Push one feature vector into the rolling window buffer."""
        self._window.append(feature_row)
        if len(self._window) > WINDOW_SIZE:
            self._window.pop(0)

    def ready(self) -> bool:
        return len(self._window) == WINDOW_SIZE

    def predict(self, X) -> np.ndarray:
        """
        Accepts either:
          - A 2D DataFrame/array (n_samples, n_features) — batch mode
          - Internally uses self._window for live single-step inference
        """
        import pandas as pd

        if isinstance(X, pd.DataFrame):
            X = X.values

        if X.ndim == 2:
            # Single sample: use the rolling window buffer
            if not self.ready():
                return np.array([0])   # still in Lag while warming up
            win     = np.array(self._window, dtype=np.float32)
            n_f     = win.shape[1]
            win_s   = self._scaler.transform(win).reshape(1, WINDOW_SIZE, n_f)
            probs   = self._model.predict(win_s, verbose=0)
            return np.argmax(probs, axis=1)

        # 3D batch input (n_windows, window_size, n_features)
        n_w, n_st, n_f = X.shape
        X_s = self._scaler.transform(X.reshape(-1, n_f)).reshape(n_w, n_st, n_f)
        return np.argmax(self._model.predict(X_s, verbose=0), axis=1)
