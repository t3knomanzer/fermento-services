"""
train.py — Model training and hyperparameter tuning.

Supported backends:
    gbt   - sklearn GradientBoostingClassifier (default, no extra deps)
    lgbm  - LightGBM (pip install lightgbm)
    rf    - sklearn RandomForestClassifier
    xgb   - XGBoost (pip install xgboost)
    cnn   - 1D Convolutional Neural Network (pip install tensorflow)

Usage:
    python main.py train    <data_dir> [--backend gbt|lgbm|rf|xgb|cnn]
    python main.py tune     <data_dir> [--backend gbt|lgbm|rf|xgb|cnn|all]
    python main.py validate <data_dir> [--backend gbt|lgbm|rf|xgb]
"""

import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import LeaveOneGroupOut, cross_val_score, ParameterGrid
from sklearn.metrics import classification_report, confusion_matrix

from config import STAGE_NAMES, MODEL_PATH
from lib.data import load_all_runs, build_feature_matrix


# ---------------------------------------------------------------------------
# Backend registry
# ---------------------------------------------------------------------------


def _get_lgbm():
    try:
        from lightgbm import LGBMClassifier

        return LGBMClassifier
    except ImportError:
        raise ImportError("LightGBM is not installed. Run: pip install lightgbm")


def _get_xgb():
    try:
        from xgboost import XGBClassifier

        return XGBClassifier
    except ImportError:
        raise ImportError("XGBoost is not installed. Run: pip install xgboost")


BACKENDS = {
    "gbt": {
        "label": "Gradient Boosting (sklearn)",
        "factory": lambda p: GradientBoostingClassifier(**p, random_state=42),
        "defaults": dict(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
        ),
        "param_grid": {
            "n_estimators": [100, 200, 400],
            "max_depth": [3, 4, 5],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.7, 0.8, 1.0],
        },
    },
    "lgbm": {
        "label": "LightGBM",
        "factory": lambda p: _get_lgbm()(**p, random_state=42, verbose=-1),
        "defaults": dict(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.7,
            num_leaves=15,
        ),
        "param_grid": {
            "n_estimators": [100, 200, 400],
            "max_depth": [3, 4, 6],
            "learning_rate": [0.01, 0.05, 0.1],
            "num_leaves": [15, 31, 63],
            "subsample": [0.7, 0.8, 1.0],
        },
    },
    "rf": {
        "label": "Random Forest",
        "factory": lambda p: RandomForestClassifier(**p, random_state=42, n_jobs=-1),
        "defaults": dict(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=2,
        ),
        "param_grid": {
            "n_estimators": [100, 200, 400],
            "max_depth": [None, 10, 20],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2"],
        },
    },
    "xgb": {
        "label": "XGBoost",
        "factory": lambda p: _get_xgb()(
            **p, random_state=42, n_jobs=-1, eval_metric="mlogloss", verbosity=0
        ),
        "defaults": dict(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
        ),
        "param_grid": {
            "n_estimators": [100, 200, 400],
            "max_depth": [3, 4, 6],
            "learning_rate": [0.01, 0.05, 0.1],
            "subsample": [0.7, 0.8, 1.0],
            "colsample_bytree": [0.7, 0.8, 1.0],
        },
    },
}

# Tree-based backends that don't need feature scaling
_NO_SCALER = {"lgbm", "rf", "xgb"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_pipeline(backend: str, params: dict) -> Pipeline:
    cfg = BACKENDS[backend]
    if backend in _NO_SCALER:
        return Pipeline([("clf", cfg["factory"](params))])
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", cfg["factory"](params)),
        ]
    )


def _load_data(data_dir: str):
    print(f"Loading runs from: {data_dir}")
    raw_df = load_all_runs(data_dir)
    n_runs = raw_df["run_id"].nunique()
    print(f"  {n_runs} runs, {len(raw_df):,} samples")
    X, y, groups = build_feature_matrix(raw_df)
    return raw_df, X, y, groups


def _print_transition_table(run_id, run_df, model):
    """Run the monitor on a single run using a fitted model, print transition table."""
    from lib.monitor import FermentationMonitor, SensorReading

    # Inject the in-memory model directly — avoids disk I/O per LOOCV fold
    monitor = object.__new__(FermentationMonitor)
    monitor.model_path = None
    monitor.smoothing_window = 3
    monitor.min_stage_samples = 2
    monitor.peak_timeout_min = 120
    monitor.silent = True
    monitor._model = model
    monitor._is_cnn = False
    monitor._buffer = []
    monitor._pred_buffer = []
    monitor._callbacks = []
    monitor._current_stage = 0
    monitor._stage_sample_cnt = 0
    monitor._baseline_dist = None
    monitor._peak_entered_at = None

    run_df = run_df.reset_index(drop=True)

    prev_stage, prev_true = None, None
    true_transitions, pred_transitions = {}, {}

    for _, row in run_df.iterrows():
        reading = SensorReading(
            timestamp=row["timestamp"].to_pydatetime(),
            temperature=row["temperature"],
            humidity=row["humidity"],
            distance=row["distance"],
            co2=row["co2"],
            starter_ratio=row["starter_ratio"],
            water_ratio=row["water_ratio"],
            flour_ratio=row["flour_ratio"],
        )
        stage = monitor.update(reading)
        true_stage = int(row["stage"])

        if true_stage != prev_true:
            true_transitions[true_stage] = reading.timestamp
        prev_true = true_stage

        if stage != prev_stage:
            pred_transitions[stage] = reading.timestamp
        prev_stage = stage

    all_stages = sorted(set(true_transitions) | set(pred_transitions))
    col_w = 14
    print(f"\n    Run {run_id}:")
    print(f"      {'':20}  {'True':>{col_w}}   {'Prediction':>{col_w}}   {'Error':>10}")
    print(f"      {'-'*20}  {'-'*col_w}   {'-'*col_w}   {'-'*10}")

    errors = []
    for sid in all_stages:
        name = f"Stage {STAGE_NAMES.get(sid, sid)}:"
        t_dt = true_transitions.get(sid)
        p_dt = pred_transitions.get(sid)
        t_str = t_dt.strftime("%H:%M:%S") if t_dt else "—"
        p_str = p_dt.strftime("%H:%M:%S") if p_dt else "—"
        if t_dt and p_dt:
            err_min = (p_dt - t_dt).total_seconds() / 60
            errors.append(abs(err_min))
            err_str = f"{err_min:+.0f} min"
        else:
            err_str = "—"
        print(f"      {name:<20}  {t_str:>{col_w}}   {p_str:>{col_w}}   {err_str:>10}")

    mae = sum(errors) / len(errors) if errors else 0.0
    max_err = max(errors) if errors else 0.0
    if errors:
        print(f"\n      MAE: {mae:.1f} min  |  Max error: {max_err:.1f} min")

    # Build per-stage signed errors for analysis
    stage_errors = {}
    stage_map = {1: "exp_err", 2: "peak_err", 3: "dec_err"}
    for sid, key in stage_map.items():
        t_dt = true_transitions.get(sid)
        p_dt = pred_transitions.get(sid)
        if t_dt and p_dt:
            stage_errors[key] = (p_dt - t_dt).total_seconds() / 60
        else:
            stage_errors[key] = 0.0

    return {"mae": mae, "worst": max_err, **stage_errors}


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------


def train(data_dir: str, model_path: Path = MODEL_PATH, backend: str = "lgbm") -> None:
    """
    Train on all data and save the model.
    Prints feature importances — use validate() for honest performance evaluation.
    """
    if backend == "cnn":
        _train_cnn(data_dir, model_path)
        return

    if backend not in BACKENDS:
        raise ValueError(
            f"Unknown backend '{backend}'. Choose from: {list(BACKENDS)} or 'cnn'"
        )

    cfg = BACKENDS[backend]
    print(f"Backend: {cfg['label']}")

    raw_df, X, y, groups = _load_data(data_dir)

    print("Training on all data...")
    model = _build_pipeline(backend, cfg["defaults"])
    model.fit(X, y)

    clf = model.named_steps["clf"]
    if hasattr(clf, "feature_importances_"):
        importances = pd.Series(clf.feature_importances_, index=X.columns)
        print("\nTop 10 features:")
        print(importances.nlargest(10).to_string())

    joblib.dump(model, model_path)
    print(f"\nModel saved → {model_path}")


def _train_cnn(data_dir: str, model_path: Path) -> None:
    from lib.cnn import CNN_DEFAULTS, make_windows, train_cnn

    print("Backend: 1D CNN (TensorFlow)")
    raw_df = load_all_runs(data_dir)
    print(
        f"  {raw_df['run_id'].nunique()} runs, {len(raw_df):,} samples — training on all"
    )

    X, y, groups = build_feature_matrix(raw_df)
    X_win, y_win, g_win = make_windows(X.values, y, groups)
    print(f"  Windows: {len(X_win):,}  shape: {X_win.shape}")
    train_cnn(X_win, y_win, g_win, CNN_DEFAULTS, model_path, test_size=None)


# ---------------------------------------------------------------------------
# Validate (LOOCV)
# ---------------------------------------------------------------------------


def _print_transition_table_cnn(run_id, run_df, keras_model, scaler):
    """
    Same as _print_transition_table but drives FermentationMonitor with a
    CNNModel wrapper built from an in-memory Keras model + scaler, without
    touching disk.
    """
    from lib.monitor import FermentationMonitor, SensorReading
    from lib.cnn import CNNModel, WINDOW_SIZE
    import tensorflow as tf

    # Wrap the in-memory model so CNNModel.predict() works without loading from disk
    wrapper = object.__new__(CNNModel)
    wrapper._model = keras_model
    wrapper._scaler = scaler
    wrapper._window = []

    # Patch FermentationMonitor to skip disk load and inject the wrapper directly
    # Use the same smoothing params as FermentationMonitor defaults
    # so CNN and tree LOOCV results are directly comparable.
    monitor = object.__new__(FermentationMonitor)
    monitor.smoothing_window = 3
    monitor.min_stage_samples = 2
    monitor.peak_timeout_min = 120
    monitor.silent = True
    monitor._model = wrapper
    monitor._is_cnn = True
    monitor._buffer = []
    monitor._pred_buffer = []
    monitor._callbacks = []
    monitor._current_stage = 0
    monitor._stage_sample_cnt = 0
    monitor._baseline_dist = None
    monitor._peak_entered_at = None

    run_df = run_df.reset_index(drop=True)
    prev_stage, prev_true = None, None
    true_transitions, pred_transitions = {}, {}

    for _, row in run_df.iterrows():
        reading = SensorReading(
            timestamp=row["timestamp"].to_pydatetime(),
            temperature=row["temperature"],
            humidity=row["humidity"],
            distance=row["distance"],
            co2=row["co2"],
            starter_ratio=row["starter_ratio"],
            water_ratio=row["water_ratio"],
            flour_ratio=row["flour_ratio"],
        )
        stage = monitor.update(reading)
        true_stage = int(row["stage"])

        if true_stage != prev_true:
            true_transitions[true_stage] = reading.timestamp
        prev_true = true_stage

        if stage != prev_stage:
            pred_transitions[stage] = reading.timestamp
        prev_stage = stage

    all_stages = sorted(set(true_transitions) | set(pred_transitions))
    col_w = 14
    print(f"\n    Run {run_id}:")
    print(f"      {'':20}  {'True':>{col_w}}   {'Prediction':>{col_w}}   {'Error':>10}")
    print(f"      {'-'*20}  {'-'*col_w}   {'-'*col_w}   {'-'*10}")

    errors = []
    for sid in all_stages:
        name = f"Stage {STAGE_NAMES.get(sid, sid)}:"
        t_dt = true_transitions.get(sid)
        p_dt = pred_transitions.get(sid)
        t_str = t_dt.strftime("%H:%M:%S") if t_dt else "—"
        p_str = p_dt.strftime("%H:%M:%S") if p_dt else "—"
        if t_dt and p_dt:
            err_min = (p_dt - t_dt).total_seconds() / 60
            errors.append(abs(err_min))
            err_str = f"{err_min:+.0f} min"
        else:
            err_str = "—"
        print(f"      {name:<20}  {t_str:>{col_w}}   {p_str:>{col_w}}   {err_str:>10}")

    mae = sum(errors) / len(errors) if errors else 0.0
    max_err = max(errors) if errors else 0.0
    if errors:
        print(f"\n      MAE: {mae:.1f} min  |  Max error: {max_err:.1f} min")

    # Build per-stage signed errors for analysis
    stage_errors = {}
    stage_map = {1: "exp_err", 2: "peak_err", 3: "dec_err"}
    for sid, key in stage_map.items():
        t_dt = true_transitions.get(sid)
        p_dt = pred_transitions.get(sid)
        if t_dt and p_dt:
            stage_errors[key] = (p_dt - t_dt).total_seconds() / 60
        else:
            stage_errors[key] = 0.0

    return {"mae": mae, "worst": max_err, **stage_errors}


def _validate_cnn(data_dir: str) -> None:
    """LOOCV for the CNN backend using raw windows (no engineered features)."""
    try:
        import tensorflow as tf
        from tensorflow.keras.callbacks import EarlyStopping
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import classification_report, confusion_matrix, f1_score
    except ImportError:
        raise ImportError("TensorFlow is not installed. Run: pip install tensorflow")

    from lib.cnn import CNN_DEFAULTS, make_windows, build_cnn, WINDOW_SIZE

    print("Backend: 1D CNN (TensorFlow)")

    raw_df, X, y, groups = _load_data(data_dir)
    n_runs = raw_df["run_id"].nunique()
    unique_ids = np.unique(groups)
    print(f"  Leave-one-out CV — {n_runs} iterations\n")

    X_win, y_win, g_win = make_windows(X.values, y, groups)

    logo = LeaveOneGroupOut()
    all_y_true = []
    all_y_pred = []
    all_maes = []
    all_max_errs = []

    for i, (train_idx, test_idx) in enumerate(logo.split(X_win, y_win, g_win), 1):
        run_id = np.unique(g_win[test_idx])[0]
        print(f"  [{i:>2}/{n_runs}]  Run {run_id}  training CNN...")

        X_tr, y_tr = X_win[train_idx], y_win[train_idx]
        X_te, y_te = X_win[test_idx], y_win[test_idx]

        # Scale
        n_s, n_st, n_f = X_tr.shape
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X_tr.reshape(-1, n_f)).reshape(n_s, n_st, n_f)
        X_te_s = scaler.transform(X_te.reshape(-1, n_f)).reshape(
            X_te.shape[0], n_st, n_f
        )

        model = build_cnn(n_f, CNN_DEFAULTS)
        model.fit(
            X_tr,
            y_tr,
            validation_split=0.1,
            epochs=CNN_DEFAULTS["epochs"],
            batch_size=CNN_DEFAULTS["batch_size"],
            callbacks=[
                EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)
            ],
            verbose=0,
        )

        preds = np.argmax(model.predict(X_te_s, verbose=0), axis=1)
        acc = (preds == y_te).mean()
        print(f"             accuracy={acc:.4f}")

        all_y_pred.extend(preds.tolist())
        all_y_true.extend(y_te.tolist())

        run_df = raw_df[raw_df["run_id"] == run_id]
        result = _print_transition_table_cnn(run_id, run_df, model, scaler)
        if result["mae"]:
            all_maes.append(result["mae"])
        if result["worst"]:
            all_max_errs.append(result["worst"])

        # Free GPU memory between folds
        del model
        tf.keras.backend.clear_session()

    # --- Aggregate results ---
    print(f"\n{'='*60}")
    print(f"  LOOCV Results — {n_runs} runs, {len(all_y_true):,} samples")
    print(f"{'='*60}")
    print(
        classification_report(
            all_y_true,
            all_y_pred,
            target_names=list(STAGE_NAMES.values()),
            zero_division=0,
        )
    )
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(all_y_true, all_y_pred))
    if all_maes:
        print(
            f"\nTransition timing — mean MAE: {np.mean(all_maes):.1f} min  |  "
            f"worst run: {max(all_maes):.1f} min  |  "
            f"max error: {max(all_max_errs):.1f} min"
        )


def validate(data_dir: str, backend: str = "lgbm", output_json: str = None) -> None:
    """
    Leave-one-out cross-validation across all runs.
    Each run is held out once while the model trains on the remaining N-1 runs.
    Prints per-run transition tables and aggregate F1 + timing MAE.
    Does not save a model — use train() after validating.

    If output_json is provided, saves per-run results to a JSON file
    for use by the analyze command.
    """
    if backend == "cnn":
        _validate_cnn(data_dir)
        return

    if backend not in BACKENDS:
        raise ValueError(
            f"Unknown backend '{backend}'. Choose from: {list(BACKENDS)} or 'cnn'"
        )

    cfg = BACKENDS[backend]
    print(f"Backend: {cfg['label']}")

    raw_df, X, y, groups = _load_data(data_dir)
    n_runs = raw_df["run_id"].nunique()
    print(f"  Leave-one-out CV — {n_runs} iterations\n")

    logo = LeaveOneGroupOut()
    all_y_true = []
    all_y_pred = []
    all_maes = []
    all_max_errs = []
    per_run_results = {}

    for i, (train_idx, test_idx) in enumerate(logo.split(X, y, groups), 1):
        m = _build_pipeline(backend, cfg["defaults"])
        m.fit(X.iloc[train_idx], y[train_idx])

        preds = m.predict(X.iloc[test_idx])
        all_y_pred.extend(preds)
        all_y_true.extend(y[test_idx])

        # Which run is held out this iteration
        run_id = np.unique(groups[test_idx])[0]
        run_df = raw_df[raw_df["run_id"] == run_id]
        acc = sum(p == t for p, t in zip(preds, y[test_idx])) / len(preds)

        print(f"  [{i:>2}/{n_runs}]  Run {run_id}  accuracy={acc:.4f}")
        result = _print_transition_table(run_id, run_df, m)
        per_run_results[str(run_id)] = result
        if result["mae"]:
            all_maes.append(result["mae"])
        if result["worst"]:
            all_max_errs.append(result["worst"])

    # --- Aggregate results ---
    print(f"\n{'='*60}")
    print(f"  LOOCV Results — {n_runs} runs, {len(all_y_true):,} samples")
    print(f"{'='*60}")
    print(
        classification_report(
            all_y_true,
            all_y_pred,
            target_names=list(STAGE_NAMES.values()),
            zero_division=0,
        )
    )
    print("Confusion matrix (rows=true, cols=pred):")
    print(confusion_matrix(all_y_true, all_y_pred))
    if all_maes:
        print(
            f"\nTransition timing — mean MAE: {np.mean(all_maes):.1f} min  |  "
            f"worst run: {max(all_maes):.1f} min  |  "
            f"max error: {max(all_max_errs):.1f} min"
        )

    if output_json:
        import json
        with open(output_json, "w") as f:
            json.dump(per_run_results, f, indent=2)
        print(f"\n✓ Per-run results saved → {output_json}")


# ---------------------------------------------------------------------------
# Tune
# ---------------------------------------------------------------------------


def _tune_backend(backend, X, y, groups, scoring):
    cfg = BACKENDS[backend]
    grid = list(ParameterGrid(cfg["param_grid"]))
    total = len(grid)
    logo = LeaveOneGroupOut()

    print(f"\n{'='*60}")
    print(f"  {cfg['label']}  —  {total} combinations, LOOCV")
    print(f"{'='*60}")

    best_score = -np.inf
    best_params = None
    results = []

    for i, params in enumerate(grid, 1):
        try:
            model = _build_pipeline(backend, params)
            scores = cross_val_score(
                model, X, y, groups=groups, cv=logo, scoring=scoring, n_jobs=-1
            )
            mean, std = scores.mean(), scores.std()
        except Exception as e:
            print(f"  [{i:>3}/{total}]  ERROR: {e}")
            continue

        results.append({"backend": backend, "params": params, "mean": mean, "std": std})
        flag = " ✓ best" if mean > best_score else ""
        print(f"  [{i:>3}/{total}]  {scoring}={mean:.4f} ±{std:.4f}  {params}{flag}")

        if mean > best_score:
            best_score = mean
            best_params = params

    print(f"\n  Best {cfg['label']}: {scoring}={best_score:.4f}  {best_params}")
    return {
        "backend": backend,
        "params": best_params,
        "score": best_score,
        "results": results,
    }


def _tune_cnn_backend(X, y, groups, scoring):
    from lib.cnn import CNN_PARAM_GRID, make_windows, cv_score_cnn

    grid = list(ParameterGrid(CNN_PARAM_GRID))
    total = len(grid)
    n_folds = len(np.unique(groups))

    print(f"\n{'='*60}")
    print(f"  1D CNN (TensorFlow)  —  {total} combinations, LOOCV")
    print(f"  ⚠️  CNN tuning is slow. Reduce CNN_PARAM_GRID in cnn.py to speed up.")
    print(f"{'='*60}")

    X_win, y_win, g_win = make_windows(X.values, y, groups)

    best_score = -np.inf
    best_params = None
    results = []

    for i, params in enumerate(grid, 1):
        try:
            mean, std = cv_score_cnn(X_win, y_win, g_win, params, n_folds)
        except Exception as e:
            print(f"  [{i:>3}/{total}]  ERROR: {e}")
            continue

        results.append({"backend": "cnn", "params": params, "mean": mean, "std": std})
        flag = " ✓ best" if mean > best_score else ""
        print(f"  [{i:>3}/{total}]  f1_macro={mean:.4f} ±{std:.4f}  {params}{flag}")

        if mean > best_score:
            best_score = mean
            best_params = params

    print(f"\n  Best CNN: f1_macro={best_score:.4f}  {best_params}")
    return {
        "backend": "cnn",
        "params": best_params,
        "score": best_score,
        "results": results,
    }


def tune(
    data_dir: str,
    model_path: Path = MODEL_PATH,
    backend: str = "all",
    scoring: str = "f1_macro",
) -> dict:
    """
    Grid search using leave-one-out cross-validation.
    After the search the winning model is retrained on all data and saved.
    """
    all_known = list(BACKENDS.keys()) + ["cnn"]
    backends_to_run = all_known if backend == "all" else [backend]

    for b in backends_to_run:
        if b not in all_known:
            raise ValueError(
                f"Unknown backend '{b}'. Choose from: {all_known} or 'all'"
            )

    raw_df, X, y, groups = _load_data(data_dir)

    all_results = []
    for b in backends_to_run:
        try:
            if b == "cnn":
                result = _tune_cnn_backend(X, y, groups, scoring)
            else:
                result = _tune_backend(b, X, y, groups, scoring)
            all_results.append(result)
        except ImportError as e:
            print(f"\n  Skipping {b}: {e}")

    if not all_results:
        raise RuntimeError("All backends failed or were skipped.")

    if len(all_results) > 1:
        print(f"\n{'='*60}")
        print("  COMPARISON SUMMARY")
        print(f"{'='*60}")
        for r in sorted(all_results, key=lambda r: r["score"], reverse=True):
            label = (
                BACKENDS[r["backend"]]["label"] if r["backend"] != "cnn" else "1D CNN"
            )
            print(f"  {r['score']:.4f}  {label:35s}  {r['params']}")

    winner = max(all_results, key=lambda r: r["score"])
    winner_label = (
        BACKENDS[winner["backend"]]["label"] if winner["backend"] != "cnn" else "1D CNN"
    )
    print(f"\n🏆 Winner: {winner_label} ({scoring}={winner['score']:.4f})")

    print("\nRetraining winning model on full dataset...")
    if winner["backend"] == "cnn":
        from lib.cnn import make_windows, train_cnn

        X_win, y_win, g_win = make_windows(X.values, y, groups)
        train_cnn(X_win, y_win, g_win, winner["params"], model_path, test_size=None)
    else:
        best_model = _build_pipeline(winner["backend"], winner["params"])
        best_model.fit(X, y)
        joblib.dump(best_model, model_path)
        print(f"Model saved → {model_path}")

    return winner
