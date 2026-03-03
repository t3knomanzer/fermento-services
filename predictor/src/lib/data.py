"""
data.py — Data loading and feature engineering.
"""

import numpy as np
import pandas as pd

from config import SHORT_WIN, MEDIUM_WIN, LONG_WIN


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

STATIC_DEFAULTS = {
    "starter_ratio": 1.0,
    "water_ratio": 1.0,
    "flour_ratio": 1.0,
}


def load_run(filepath: str) -> pd.DataFrame:
    """
    Load a single fermentation run from CSV.

    Required columns:
        timestamp   - ISO8601 or epoch seconds
        temperature - °C
        humidity    - %RH
        distance    - mm (sensor to starter surface; smaller = higher rise)
        co2         - ppm
        stage       - integer label 0-3 (required for training, omit for inference)

    Optional static columns (constant per run, repeated on every row):
        starter_ratio - parts of starter (e.g. 1 in a 1:5:5 feed)
        water_ratio   - parts of water   (e.g. 5 in a 1:5:5 feed)
        flour_ratio   - parts of flour   (e.g. 5 in a 1:5:5 feed)

    Missing optional columns are filled with defaults so older CSVs stay compatible.
    """
    df = pd.read_csv(filepath, parse_dates=["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Smooth out sensor noise with small rolling medians.
    df["co2"] = df["co2"].rolling(window=3, center=True, min_periods=1).median()
    df["humidity"] = (
        df["humidity"].rolling(window=3, center=True, min_periods=1).median()
    )
    df["distance"] = (
        df["distance"].rolling(window=5, center=True, min_periods=1).median()
    )

    df["elapsed_min"] = (
        df["timestamp"] - df["timestamp"].iloc[0]
    ).dt.total_seconds() / 60

    for col, default in STATIC_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default

    return df


def load_all_runs(data_dir: str) -> pd.DataFrame:
    """
    Load all CSV runs from a directory and concatenate them.
    Adds a 'run_id' column (filename stem) used for group-aware splitting.
    """
    from pathlib import Path

    frames = []
    for path in sorted(Path(data_dir).glob("*.csv")):
        df = load_run(str(path))
        if df.isna().any().any():
            print(f"Warning: Missing values found in {path}")

        df["run_id"] = path.stem
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    return pd.concat(frames, ignore_index=True)


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------


def _rolling(series: pd.Series, window: int, func: str) -> pd.Series:
    return getattr(series.rolling(window, min_periods=1), func)()


def _time_since_new_max(rise_mm: pd.Series, elapsed_min: pd.Series) -> pd.Series:
    """
    Minutes elapsed since rise_mm last set a new cumulative maximum.

    - Zero during active Exponential rise (max updates every sample).
    - Counts up through the Peak plateau (max frozen at the true peak).
    - Resets to zero if rise resumes (handles double-peak edge cases).

    This gives the model a plateau-duration signal that is independent of
    absolute run time, making it temperature-agnostic unlike elapsed_min.
    A 34°C run may reach Decline at tsnm=80min; a 26°C run at tsnm=160min —
    but both show the same rising tsnm pattern leading into Decline.
    """
    cur_max = rise_mm.iloc[0]
    cur_time = elapsed_min.iloc[0]
    result = np.zeros(len(rise_mm))
    for i in range(len(rise_mm)):
        if rise_mm.iloc[i] >= cur_max:
            cur_max = rise_mm.iloc[i]
            cur_time = elapsed_min.iloc[i]
        result[i] = elapsed_min.iloc[i] - cur_time
    return pd.Series(result, index=rise_mm.index)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build features from raw sensor columns.
    Must be called per-run (not across runs) to avoid cross-run leakage
    in cumulative features like pct_of_max_rise.
    """
    f = pd.DataFrame(index=df.index)

    # --- Raw sensor values ---
    f["temperature"] = df["temperature"]
    f["humidity"] = df["humidity"]
    f["distance"] = df["distance"]
    f["co2"] = df["co2"]

    # --- Static recipe parameters ---
    f["starter_ratio"] = df["starter_ratio"]
    f["water_ratio"] = df["water_ratio"]
    f["flour_ratio"] = df["flour_ratio"]

    # --- Time ---
    f["elapsed_min"] = (
        df["timestamp"] - df["timestamp"].iloc[0]
    ).dt.total_seconds() / 60

    # --- Rise: invert distance so higher = more risen ---
    rise = df["distance"].iloc[0] - df["distance"]
    f["rise_mm"] = rise

    # --- Slope of rise and CO2 ---
    for win, tag in [(SHORT_WIN, "short"), (MEDIUM_WIN, "med"), (LONG_WIN, "long")]:
        f[f"rise_slope_{tag}"] = rise.diff(win) / win
        f[f"co2_slope_{tag}"] = df["co2"].diff(win) / win

    # --- Rolling statistics — medium window ---
    f["rise_mean_med"] = _rolling(rise, MEDIUM_WIN, "mean")
    f["rise_std_med"] = _rolling(rise, MEDIUM_WIN, "std")
    f["co2_mean_med"] = _rolling(df["co2"], MEDIUM_WIN, "mean")
    f["co2_std_med"] = _rolling(df["co2"], MEDIUM_WIN, "std")
    f["temp_mean_med"] = _rolling(df["temperature"], MEDIUM_WIN, "mean")
    f["humidity_slope_med"] = df["humidity"].diff(MEDIUM_WIN) / MEDIUM_WIN

    # --- Acceleration of rise (second derivative) ---
    f["rise_accel"] = f["rise_slope_short"].diff(SHORT_WIN) / SHORT_WIN

    # --- Position relative to run maximum (rise) ---
    f["pct_of_max_rise"] = rise / (rise.cummax().replace(0, np.nan))
    f["drop_from_peak_mm"] = rise.cummax() - rise

    # --- Position relative to run maximum (CO2) ---
    # CO2 peaks near the true fermentation peak then falls through Decline.
    # These mirror pct_of_max_rise / drop_from_peak_mm for the gas signal.
    co2_cummax = df["co2"].cummax().replace(0, np.nan)
    f["co2_pct_of_max"] = df["co2"] / co2_cummax
    f["co2_drop_from_peak"] = co2_cummax - df["co2"]

    # --- CO2 per unit of rise ---
    f["co2_per_rise"] = df["co2"] / (rise + 1)

    # --- Plateau duration proxy ---
    # Minutes since rise_mm last set a new maximum.  Zero during active rise,
    # counts up through the plateau, giving the model a stage-relative clock
    # that is independent of absolute run time (unlike elapsed_min which encodes
    # temperature-dependent timing and causes early Decline calls on slow runs).
    f["time_since_new_max"] = _time_since_new_max(rise, df["elapsed_min"])

    f = f.fillna(0).replace([np.inf, -np.inf], np.nan).fillna(0)
    return f


def build_feature_matrix(raw_df: pd.DataFrame):
    """
    Apply feature engineering per run, returning (X, y, groups) arrays
    suitable for group-aware sklearn splitting.
    Expects 'run_id' and 'stage' columns in raw_df.
    """
    X_parts, y_parts, groups_parts = [], [], []

    for run_id, group in raw_df.groupby("run_id"):
        feat = engineer_features(group.reset_index(drop=True))
        X_parts.append(feat)
        y_parts.append(group["stage"].values)
        groups_parts.append(np.full(len(group), run_id))

    X = pd.concat(X_parts, ignore_index=True)
    y = np.concatenate(y_parts)
    groups = np.concatenate(groups_parts)
    return X, y, groups
