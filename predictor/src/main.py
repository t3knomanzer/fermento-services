"""
main.py — CLI entrypoint for the sourdough fermentation pipeline.

Commands:
  train    <data_dir> [--backend gbt|lgbm|rf|xgb|cnn]      Train on all data, save model
  tune     <data_dir> [--backend gbt|lgbm|rf|xgb|cnn|all]  Grid search, save best model
  validate <data_dir> [--backend gbt|lgbm|rf|xgb]          LOOCV — per-run transition tables + F1
  test     <file.csv>                                        Run inference on a single labeled run
  label    <input_dir> <output_dir> [options]                  Auto-label runs and plot for validation

Examples:
  python main.py validate data/train --backend lgbm
  python main.py train    data/train --backend lgbm
  python main.py tune     data/train --backend all
  python main.py test     data/test/run_20.csv
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
    if not args:
        print("Usage: python main.py validate <data_dir> [--backend gbt|lgbm|rf|xgb]")
        sys.exit(1)
    from lib.train import validate

    validate(data_dir=args[0], backend=backend)


def cmd_test(args):
    if not args:
        print("Usage: python main.py test <file.csv>")
        sys.exit(1)

    from lib.data import load_run
    from lib.monitor import FermentationMonitor, SensorReading
    from config import STAGE_NAMES

    df = load_run(args[0])
    monitor = FermentationMonitor(
        model_path=MODEL_PATH, peak_timeout_min=120, silent=True
    )

    prev_stage = None
    prev_true = None
    true_transitions = {}
    pred_transitions = {}

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

        if "stage" in row:
            true_stage = int(row["stage"])
            if true_stage != prev_true:
                true_transitions[true_stage] = ts
            prev_true = true_stage

        if stage != prev_stage:
            pred_transitions[stage] = ts
        prev_stage = stage

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
# Dispatch
# ---------------------------------------------------------------------------

COMMANDS = {
    "train": cmd_train,
    "tune": cmd_tune,
    "validate": cmd_validate,
    "test": cmd_test,
    "label": cmd_label,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
