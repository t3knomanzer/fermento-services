"""
labeler.py — Automatic stage labeling from distance signal.

Applies a consistent, threshold-based rule to every run in a directory,
saves labeled CSVs to an output folder, and plots the distance curve
with stage bands for visual validation.

Algorithm (applied to smoothed distance):
    Lag  → Exponential : distance drops LAG_DROP mm from start
    Exponential → Peak : smoothed rise within PEAK_NEAR mm of its max,
                         AND total rise exceeds MIN_RISE mm
    Peak → Decline     : distance rises DEC_DROP mm above smoothed max

All thresholds require CONSISTENCY consecutive samples to confirm.

Usage:
    python main.py label <input_dir> <output_dir> [options]

Options:
    --smooth     Median filter window in samples     (default: 7)
    --consistency  Consecutive samples to confirm     (default: 5)
    --lag-drop   mm drop from start → Exponential    (default: 3.0)
    --min-rise   mm min total rise before Peak fires  (default: 10.0)
    --peak-near  mm from smoothed max → Peak         (default: 2.0)
    --dec-drop   mm above smoothed max → Decline     (default: 5.0)
    --no-plot    Skip plots (useful for batch runs)
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

from config import STAGE_NAMES

# ---------------------------------------------------------------------------
# Stage colors for plots
# ---------------------------------------------------------------------------

STAGE_COLORS = {
    0: "#b0c4de",   # Lag        — steel blue
    1: "#90ee90",   # Exponential — light green
    2: "#ffd700",   # Peak        — gold
    3: "#ff8c69",   # Decline     — salmon
}


# ---------------------------------------------------------------------------
# Core labeling algorithm
# ---------------------------------------------------------------------------

def auto_label(
    distance:        pd.Series,
    smooth:          int   = 7,
    smooth_dec:      int   = 25,
    consistency:     int   = 5,
    lag_drop:        float = 3.0,
    peak_near_frac:  float = 0.10,
    dec_drop_frac:   float = 0.15,
) -> np.ndarray:
    """
    Offline labeler using global signal statistics.

    Args:
        distance:       Raw distance series (mm, smaller = higher rise).
        smooth:         Median filter window for Peak/Lag detection.
        smooth_dec:     Heavier median filter window for Decline detection.
                        Wide window averages out plateau oscillations so only
                        a genuine sustained baseline shift triggers Decline.
        consistency:    Consecutive samples required for Lag→Exp and Exp→Peak.
        lag_drop:       mm drop from start to confirm Exponential.
        peak_near_frac: Fraction of total rise — enter Peak when within this
                        distance of global min. Default 0.10 (10% of rise).
        dec_drop_frac:  Fraction of total rise above global_min that defines
                        the Peak/Decline boundary. Default 0.15 (15% of rise).

    Algorithm:
        Lag→Exp   : smoothed distance drops lag_drop mm from start
        Exp→Peak  : smoothed distance within (total_rise * peak_near_frac) of global_min
        Peak→Dec  : scan backwards on the HEAVILY smoothed signal — find the last
                    sample where it is below global_min + dec_drop_frac * total_rise.
                    Everything after that is Decline. Backwards scan ensures that
                    brief excursions above the threshold during the plateau don't
                    fire early — only a permanent baseline shift counts.
    """
    s          = distance.rolling(window=smooth,     center=True, min_periods=1).median()
    s_heavy    = distance.rolling(window=smooth_dec, center=True, min_periods=smooth_dec//2).median()
    start_dist = s.iloc[0]
    global_min = s.min()
    total_rise = start_dist - global_min
    peak_near  = total_rise * peak_near_frac
    dec_thresh = global_min + total_rise * dec_drop_frac

    # Last sample of the heavily-smoothed signal below dec_thresh —
    # Decline starts at the next sample.
    below         = s_heavy[s_heavy < dec_thresh]
    dec_start_idx = below.index[-1] + 1 if len(below) > 0 else len(s)

    stage   = np.zeros(len(s), dtype=int)
    consec  = 0
    current = 0

    for i in range(len(s)):
        d = s.iloc[i]

        if current == 0:    # Lag → Exponential
            cond = (start_dist - d) >= lag_drop
        elif current == 1:  # Exponential → Peak
            cond = (d - global_min) <= peak_near
        elif current == 2:  # Peak → Decline
            cond = (i >= dec_start_idx)
        else:
            cond = False

        if cond:
            consec += 1
            if consec >= consistency:
                current += 1
                consec   = 0
        else:
            consec = 0

        stage[i] = current

    return stage


def plot_run(df: pd.DataFrame, run_id: str, output_path: Path) -> None:
    """
    Plot distance curve with stage bands and save to output_path.
    Expects df to have: timestamp, distance, stage (auto labels), co2 columns.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})

    elapsed = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds() / 60

    # Shade stage regions
    for ax in (ax1, ax2):
        prev_stage = df["stage"].iloc[0]
        seg_start  = elapsed.iloc[0]
        for i in range(1, len(df)):
            s = df["stage"].iloc[i]
            if s != prev_stage or i == len(df) - 1:
                ax.axvspan(seg_start, elapsed.iloc[i],
                           color=STAGE_COLORS[prev_stage], alpha=0.25, linewidth=0)
                seg_start  = elapsed.iloc[i]
                prev_stage = s

    # Distance curve
    ax1.plot(elapsed, df["distance"], color="#2c3e50", linewidth=1.2, label="Distance (mm)")
    if "distance_smooth" in df.columns:
        ax1.plot(elapsed, df["distance_smooth"], color="#e74c3c", linewidth=1.5,
                 linestyle="--", label="Smoothed", alpha=0.8)

    ax1.set_ylabel("Distance (mm)")
    ax1.invert_yaxis()   # lower distance = higher rise
    ax1.set_title(f"Run {run_id} — Auto Labels")
    ax1.legend(loc="upper right", fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Stage transition markers on ax1
    prev = None
    for i, row in df.iterrows():
        s = row["stage"]
        if s != prev and s > 0:
            ax1.axvline(elapsed.iloc[df.index.get_loc(i)], color=STAGE_COLORS[s],
                        linewidth=1.5, linestyle=":")
            ax1.text(elapsed.iloc[df.index.get_loc(i)] + 1, ax1.get_ylim()[0] + 1,
                     STAGE_NAMES[s], fontsize=7, color="black")
        prev = s

    # CO2 curve
    ax2.plot(elapsed, df["co2"], color="#8e44ad", linewidth=1.0, label="CO₂ (ppm)")
    ax2.set_ylabel("CO₂ (ppm)")
    ax2.set_xlabel("Elapsed (min)")
    ax2.legend(loc="upper right", fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Legend patches
    patches = [mpatches.Patch(color=STAGE_COLORS[s], alpha=0.5, label=STAGE_NAMES[s])
               for s in STAGE_NAMES]
    fig.legend(handles=patches, loc="lower center", ncol=4, fontsize=9,
               bbox_to_anchor=(0.5, 0.01))

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def label_directory(
    input_dir:       str,
    output_dir:      str,
    smooth:          int   = 7,
    smooth_dec:      int   = 25,
    consistency:     int   = 5,
    lag_drop:        float = 3.0,
    peak_near_frac:  float = 0.10,
    dec_drop_frac:   float = 0.15,
    plot:            bool  = True,
) -> None:
    """
    Label all CSVs in input_dir, save to output_dir, and plot each run.
    """
    input_path  = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    plots_path = output_path / "plots"
    if plot:
        plots_path.mkdir(exist_ok=True)

    csv_files = sorted(input_path.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {input_dir}")
        return

    print(f"Labeling {len(csv_files)} runs → {output_dir}")
    print(f"  smooth={smooth}  smooth_dec={smooth_dec}  consistency={consistency}  "
          f"lag_drop={lag_drop}mm  peak_near={peak_near_frac*100:.0f}%  "
          f"dec_drop={dec_drop_frac*100:.0f}% of rise (backwards scan)\n")

    for path in csv_files:
        df = pd.read_csv(path, parse_dates=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        labels = auto_label(
            df["distance"],
            smooth=smooth, smooth_dec=smooth_dec,
            consistency=consistency,
            lag_drop=lag_drop,
            peak_near_frac=peak_near_frac,
            dec_drop_frac=dec_drop_frac,
        )
        df["stage"] = labels

        # Store smoothed distance for plotting
        df["distance_smooth"] = (df["distance"]
                                 .rolling(window=smooth, center=True, min_periods=1)
                                 .median())

        # Print summary
        elapsed = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds() / 60
        parts   = []
        for s, name in STAGE_NAMES.items():
            mask = df["stage"] == s
            if mask.any():
                t = elapsed[mask].iloc[0]
                parts.append(f"{name}@{t:.0f}min")
        print(f"  {path.stem:>4}: {' → '.join(parts)}")

        # Save labeled CSV (drop the smoothed helper column)
        out_csv = output_path / path.name
        df.drop(columns=["distance_smooth"]).to_csv(out_csv, index=False)

        # Plot
        if plot:
            plot_run(df, path.stem, plots_path / f"{path.stem}.png")

    print(f"\n✓ Labeled CSVs saved → {output_path}")
    if plot:
        print(f"✓ Plots saved        → {plots_path}")
