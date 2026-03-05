"""
main.py — CLI entrypoint for the sourdough fermentation pipeline.

Commands:
  train    <data_dir> [--backend gbt|lgbm|rf|xgb|cnn]      Train on all data, save model
  tune     <data_dir> [--backend gbt|lgbm|rf|xgb|cnn|all]  Grid search, save best model
  validate <data_dir> [--backend ...] [--output-json <path>]  LOOCV — per-run transition tables + F1
  test     <file.csv>                                        Run inference on a single labeled run
  label    <input_dir> <output_dir> [options]                  Auto-label runs and plot for validation
  analyze  <data_dir> [--loocv-json <path>] [--output <path>]  Dataset analysis dashboard

Examples:
  python main.py validate data/train --backend lgbm
  python main.py train    data/train --backend lgbm
  python main.py tune     data/train --backend all
  python main.py test     data/test/run_20.csv
  python main.py analyze  data/train --loocv-json results.json
"""

import sys
from pathlib import Path

from config import MODEL_PATH


# ---------------------------------------------------------------------------
# Argument helpers
# ---------------------------------------------------------------------------


def _pop_flag(args: list, flag: str, default: str) -> tuple:
    if flag in args:
        idx = args.index(flag)
        if idx + 1 >= len(args):
            print(f"Error: {flag} requires a value.")
            sys.exit(1)
        value = args[idx + 1]
        args = args[:idx] + args[idx + 2 :]
        return value, args
    return default, args


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_train(args):
    backend, args = _pop_flag(args, "--backend", "lgbm")
    if not args:
        print("Usage: python main.py train <data_dir> [--backend gbt|lgbm|rf|xgb|cnn]")
        sys.exit(1)
    from lib.train import train

    train(data_dir=args[0], backend=backend)


def cmd_tune(args):
    backend, args = _pop_flag(args, "--backend", "all")
    if not args:
        print(
            "Usage: python main.py tune <data_dir> [--backend gbt|lgbm|rf|xgb|cnn|all]"
        )
        sys.exit(1)
    from lib.train import tune

    tune(data_dir=args[0], backend=backend)


def cmd_validate(args):
    backend, args = _pop_flag(args, "--backend", "lgbm")
    output_json, args = _pop_flag(args, "--output-json", None)
    if not args:
        print(
            "Usage: python main.py validate <data_dir> [--backend gbt|lgbm|rf|xgb|cnn] [--output-json <path>]"
        )
        sys.exit(1)
    from lib.train import validate

    validate(data_dir=args[0], backend=backend, output_json=output_json)


def cmd_test(args):
    no_plot, args = _pop_flag(list(args), "--no-plot", None)
    if not args:
        print("Usage: python main.py test <file.csv> [--no-plot]")
        sys.exit(1)

    import numpy as np
    from lib.data import load_run
    from lib.monitor import FermentationMonitor, SensorReading
    from config import STAGE_NAMES

    df = load_run(args[0])
    run_name = Path(args[0]).stem
    monitor = FermentationMonitor(
        model_path=MODEL_PATH, peak_timeout_min=120, silent=True
    )

    prev_stage = None
    prev_true = None
    true_transitions = {}
    pred_transitions = {}

    # per-sample data collected for plotting
    elapsed_mins = []
    true_stages = []
    pred_stages = []
    temperatures = []
    humidities = []
    distances = []
    co2s = []

    for _, row in df.iterrows():
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
        ts = reading.timestamp

        elapsed = (ts - df["timestamp"].iloc[0].to_pydatetime()).total_seconds() / 60
        elapsed_mins.append(elapsed)
        temperatures.append(reading.temperature)
        humidities.append(reading.humidity)
        distances.append(reading.distance)
        co2s.append(reading.co2)
        pred_stages.append(stage)

        if "stage" in row:
            true_stage = int(row["stage"])
            true_stages.append(true_stage)
            if true_stage != prev_true:
                true_transitions[true_stage] = ts
            prev_true = true_stage

        if stage != prev_stage:
            pred_transitions[stage] = ts
        prev_stage = stage

    # -------------------------------------------------------------------------
    # Console output
    # -------------------------------------------------------------------------
    all_stages = sorted(set(true_transitions) | set(pred_transitions))
    col_w = 14
    print(f"\nStage transitions:")
    print(f"  {'':20}  {'True':>{col_w}}   {'Prediction':>{col_w}}   {'Error':>10}")
    print(f"  {'-'*20}  {'-'*col_w}   {'-'*col_w}   {'-'*10}")

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
        print(f"  {name:<20}  {t_str:>{col_w}}   {p_str:>{col_w}}   {err_str:>10}")

    if errors:
        print(
            f"\n  MAE: {sum(errors)/len(errors):.1f} min  |  Max error: {max(errors):.1f} min"
        )

    if no_plot is not None:
        return

    # -------------------------------------------------------------------------
    # Plot
    # -------------------------------------------------------------------------
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import matplotlib.gridspec as gridspec
    import pandas as pd

    t = np.array(elapsed_mins)
    d = np.array(distances)
    ps = np.array(pred_stages)
    ts_arr = np.array(true_stages) if true_stages else None
    has_true = ts_arr is not None and len(ts_arr) == len(t)

    smooth7 = pd.Series(d).rolling(7, center=True, min_periods=1).median().values

    SC = {0: "#6baed6", 1: "#74c476", 2: "#fdd835", 3: "#ef6c57"}
    SL = {0: "Lag", 1: "Exponential", 2: "Peak", 3: "Decline"}
    BG = "#0f1117"
    PBG = "#181c27"
    GC = "#252a38"
    TD = "#8a8fa0"
    TX = "#c8cdd8"
    TH = "#e0e4f0"
    DIM = "#55596a"

    total_min = float(t[-1])
    t0_dt = df["timestamp"].iloc[0].to_pydatetime()

    def elapsed_of(transitions, sid):
        if sid not in transitions:
            return None
        return (transitions[sid] - t0_dt).total_seconds() / 60

    def duration_of(transitions, sid):
        start = elapsed_of(transitions, sid)
        if start is None:
            return None
        nexts = [
            elapsed_of(transitions, s)
            for s in range(sid + 1, 4)
            if elapsed_of(transitions, s) is not None
        ]
        return (min(nexts) if nexts else total_min) - start

    # ── layout: distance chart (left 70%) + stats panel (right 30%) ──────────
    fig = plt.figure(figsize=(16, 7))
    fig.patch.set_facecolor(BG)
    gs = gridspec.GridSpec(
        1,
        2,
        figure=fig,
        width_ratios=[2.6, 1],
        left=0.05,
        right=0.97,
        top=0.93,
        bottom=0.10,
        wspace=0.04,
    )

    # ── distance chart ────────────────────────────────────────────────────────
    ax = fig.add_subplot(gs[0])
    ax.set_facecolor(PBG)

    # true stage background shading
    if has_true:
        prev_s, x0 = ts_arr[0], t[0]
        for i in range(1, len(t)):
            if ts_arr[i] != prev_s or i == len(t) - 1:
                ax.axvspan(x0, t[i], color=SC[prev_s], alpha=0.18, linewidth=0)
                x0, prev_s = t[i], ts_arr[i]

    # predicted stage colour bar along the bottom edge
    d_rng = d.max() - d.min()
    bar_top = d.max() + d_rng * 0.03
    bar_bot = d.max() + d_rng * 0.09
    for i in range(len(t) - 1):
        ax.fill_between(
            t[i : i + 2], bar_top, bar_bot, color=SC[ps[i]], linewidth=0, alpha=0.92
        )

    ax.plot(t, d, color="#2e3347", linewidth=0.7, alpha=0.5)
    ax.plot(t, smooth7, color=TH, linewidth=1.7, zorder=3)
    ax.invert_yaxis()

    def draw_vlines(transitions, ls, lw):
        for sid, ts_dt in transitions.items():
            if sid == 0:
                continue
            ax.axvline(
                (ts_dt - t0_dt).total_seconds() / 60,
                color=SC[sid],
                linestyle=ls,
                linewidth=lw,
                alpha=0.9,
                zorder=4,
            )

    if has_true:
        draw_vlines(true_transitions, "-", 1.1)
    draw_vlines(pred_transitions, "--", 1.9)

    ax.set_xlabel("Elapsed (min)", fontsize=8, color=TD)
    ax.set_ylabel("Distance (mm)", fontsize=8, color=TD)
    ax.tick_params(colors=DIM, labelsize=7)
    for sp in ax.spines.values():
        sp.set_edgecolor(GC)
    ax.grid(axis="y", color=GC, linewidth=0.5, zorder=0)
    ax.grid(axis="x", color=GC, linewidth=0.3, zorder=0)

    legend_h = [mpatches.Patch(color=SC[s], alpha=0.7, label=SL[s]) for s in SL]
    if has_true:
        legend_h += [
            plt.Line2D([0], [0], color="#aaa", lw=1.1, ls="-", label="True"),
            plt.Line2D([0], [0], color="#aaa", lw=1.9, ls="--", label="Predicted"),
            mpatches.Patch(color="#888", alpha=0.18, label="True stage (bg)"),
        ]
    ax.legend(
        handles=legend_h,
        loc="lower right",
        fontsize=7,
        ncol=3,
        framealpha=0.2,
        facecolor=BG,
        edgecolor=GC,
        labelcolor=TX,
    )

    # ── stats panel ───────────────────────────────────────────────────────────
    ax_s = fig.add_subplot(gs[1])
    ax_s.set_facecolor(PBG)
    ax_s.set_xlim(0, 1)
    ax_s.set_ylim(0, 1)
    ax_s.axis("off")
    for sp in ax_s.spines.values():
        sp.set_edgecolor(GC)

    avg_temp = float(np.mean(temperatures))
    temp_range = float(np.max(temperatures) - np.min(temperatures))

    # run header
    ax_s.text(
        0.5,
        0.97,
        f"Run {run_name}",
        ha="center",
        va="top",
        fontsize=14,
        color=TH,
        fontweight="bold",
        transform=ax_s.transAxes,
    )
    ax_s.text(
        0.5,
        0.915,
        f"{avg_temp:.1f}°C avg  ±{temp_range:.1f}°C\n"
        f"{total_min:.0f} min total  ·  {len(t)} samples",
        ha="center",
        va="top",
        fontsize=8,
        color=TD,
        linespacing=1.6,
        transform=ax_s.transAxes,
    )

    # separator
    ax_s.plot([0.04, 0.96], [0.845, 0.845], color=GC, lw=0.8, transform=ax_s.transAxes)

    # columns: Stage | T start | P start | T dur | P dur | Err
    # err is right-aligned in its own column so it never overlaps P dur
    HDR_Y = 0.805
    COL_X = [0.03, 0.34, 0.50, 0.66, 0.80]  # stage | T start | P start | T dur | P dur
    ERR_X = 0.97  # error: right-aligned
    HDRS = ["Stage", "T start", "P start", "T dur", "P dur"]
    for hdr, cx in zip(HDRS, COL_X):
        ax_s.text(
            cx,
            HDR_Y,
            hdr,
            ha="left",
            va="top",
            fontsize=6.5,
            color=TD,
            fontweight="bold",
            transform=ax_s.transAxes,
        )
    ax_s.text(
        ERR_X,
        HDR_Y,
        "Err",
        ha="right",
        va="top",
        fontsize=6.5,
        color=TD,
        fontweight="bold",
        transform=ax_s.transAxes,
    )

    ax_s.plot([0.04, 0.96], [0.782, 0.782], color=GC, lw=0.5, transform=ax_s.transAxes)

    row_y = 0.755
    row_step = 0.105
    mae_vals = []

    for sid in range(4):
        t_start = elapsed_of(true_transitions, sid) if has_true else None
        p_start = elapsed_of(pred_transitions, sid)
        t_dur = duration_of(true_transitions, sid) if has_true else None
        p_dur = duration_of(pred_transitions, sid)

        err = (
            (p_start - t_start)
            if (t_start is not None and p_start is not None)
            else None
        )
        err_str = f"{err:+.0f}" if err is not None else ""
        err_color = (
            "#ef6c57"
            if err is not None and abs(err) > 15
            else "#66bb6a" if err is not None and abs(err) <= 5 else TX
        )
        if err is not None:
            mae_vals.append(abs(err))

        dot_y = row_y - 0.018
        ax_s.plot(
            COL_X[0] + 0.01,
            dot_y,
            "o",
            color=SC[sid],
            markersize=5,
            transform=ax_s.transAxes,
            zorder=3,
        )
        ax_s.text(
            COL_X[0] + 0.05,
            row_y,
            SL[sid],
            ha="left",
            va="top",
            fontsize=7.5,
            color=TX,
            transform=ax_s.transAxes,
        )

        for val, cx, col in [
            (f"{t_start:.0f}" if t_start is not None else "—", COL_X[1], TD),
            (f"{p_start:.0f}" if p_start is not None else "—", COL_X[2], TX),
            (f"{t_dur:.0f}" if t_dur is not None else "—", COL_X[3], TD),
            (f"{p_dur:.0f}" if p_dur is not None else "—", COL_X[4], TX),
        ]:
            ax_s.text(
                cx,
                row_y,
                val,
                ha="left",
                va="top",
                fontsize=7.5,
                color=col,
                transform=ax_s.transAxes,
            )

        if err_str:
            ax_s.text(
                ERR_X,
                row_y,
                err_str,
                ha="right",
                va="top",
                fontsize=7.5,
                color=err_color,
                fontweight="bold",
                transform=ax_s.transAxes,
            )

        row_y -= row_step

    # MAE footer
    ax_s.plot(
        [0.04, 0.96],
        [row_y + row_step * 0.5, row_y + row_step * 0.5],
        color=GC,
        lw=0.5,
        transform=ax_s.transAxes,
    )
    if mae_vals:
        ax_s.text(
            0.5,
            row_y + row_step * 0.3,
            f"MAE  {sum(mae_vals)/len(mae_vals):.1f} min  ·  "
            f"worst  {max(mae_vals):.1f} min",
            ha="center",
            va="top",
            fontsize=8,
            color=TX,
            transform=ax_s.transAxes,
        )

    ax_s.text(
        0.5,
        0.025,
        "minutes  ·  T = true  ·  P = predicted",
        ha="center",
        va="bottom",
        fontsize=6,
        color=DIM,
        transform=ax_s.transAxes,
    )

    out_path = Path(args[0]).with_suffix(".test.png")
    plt.savefig(out_path, dpi=140, bbox_inches="tight", facecolor=BG)
    print(f"\n  Plot saved → {out_path}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Label
# ---------------------------------------------------------------------------


def cmd_label(args):
    no_plot, args = _pop_flag(list(args), "--no-plot", None)
    smooth, args = _pop_flag(list(args), "--smooth", "7")
    smooth_dec, args = _pop_flag(list(args), "--smooth-dec", "25")
    consist, args = _pop_flag(list(args), "--consistency", "5")
    lag_drop, args = _pop_flag(list(args), "--lag-drop", "3.0")
    peak_near_frac, args = _pop_flag(list(args), "--peak-near-frac", "0.10")
    dec_drop_frac, args = _pop_flag(list(args), "--dec-drop-frac", "0.15")

    if len(args) < 2:
        print("Usage: python main.py label <input_dir> <output_dir> [options]")
        print(
            "  --smooth N              Signal filter window for Lag/Peak (default: 7)"
        )
        print(
            "  --smooth-dec N          Heavy filter window for Decline scan (default: 25)"
        )
        print("  --consistency N         Consecutive samples to confirm (default: 5)")
        print(
            "  --lag-drop N            mm drop from start → Exponential (default: 3.0)"
        )
        print(
            "  --peak-near-frac N      Fraction of total rise to enter Peak (default: 0.10)"
        )
        print(
            "  --dec-drop-frac N       Fraction of total rise for Decline threshold (default: 0.15)"
        )
        print("  --no-plot               Skip plots")
        sys.exit(1)

    from lib.labeler import label_directory

    label_directory(
        input_dir=args[0],
        output_dir=args[1],
        smooth=int(smooth),
        smooth_dec=int(smooth_dec),
        consistency=int(consist),
        lag_drop=float(lag_drop),
        peak_near_frac=float(peak_near_frac),
        dec_drop_frac=float(dec_drop_frac),
        plot=(no_plot is None),
    )


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


def cmd_analyze(args):
    loocv_json, args = _pop_flag(list(args), "--loocv-json", None)
    output, args = _pop_flag(list(args), "--output", None)

    if not args:
        print("Usage: python main.py analyze <data_dir> [--loocv-json <path>] [--output <path>]")
        sys.exit(1)

    from lib.analysis import analyze

    analyze(
        data_dir=args[0],
        loocv_json=loocv_json,
        output=output,
    )


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "train": cmd_train,
    "tune": cmd_tune,
    "validate": cmd_validate,
    "test": cmd_test,
    "label": cmd_label,
    "analyze": cmd_analyze,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
