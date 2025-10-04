#!/usr/bin/env python3
# arima_predict_merged.py
# Forecast N days ahead with fixed SARIMA specs, moon_phase dummies as exog.
# Can work from:
#   1) --csv <path> + --horizon N
#   2) (--activity + --lat + --lon) and computed asof=(today-<lag-days>) to locate dataset under --data-root,
#      optionally fetch it if missing by calling your Fishing_parse_data_for_year.py module.
#
# OUTPUT: CSV with columns:
#   date, moon_phase, air_temp_C, pressure_kPa, wind_speed_m_s, estimated_water_temp_C
# No prediction intervals are produced.

import argparse
import warnings
from pathlib import Path
from datetime import date, datetime, timedelta
import subprocess
import sys

import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

DATE_COL = "date"
TARGETS = [
    "air_temp_C",
    "pressure_kPa",
    "wind_speed_m_s",
    "estimated_water_temp_C",
]

# Your fixed SARIMA specs
BEST_MODELS = {
    "air_temp_C":             {"order": (1, 1, 3), "seasonal_order": (0, 0, 1, 7)},
    "pressure_kPa":           {"order": (1, 1, 2), "seasonal_order": (0, 0, 1, 7)},
    "wind_speed_m_s":         {"order": (1, 1, 3), "seasonal_order": (0, 0, 1, 7)},
    "estimated_water_temp_C": {"order": (1, 1, 3), "seasonal_order": (0, 0, 1, 7)},
}

# Simple lunar-cycle approximation
SYNODIC_MONTH = 29.53058867  # days
CANON_FRAC = {
    "New Moon": 0.00,
    "First Quarter": 0.25,
    "Full Moon": 0.50,
    "Last Quarter": 0.75,
    # coarse labels if present in training
    "Waning": 0.81,
    "Waxing": 0.31,
}


# ---------------------------
# Helpers for dataset layout
# ---------------------------

def data_root(path: str | None) -> Path:
    return Path(path or "./data").resolve()

def coord_token(lat: float, lon: float, precision: int = 4) -> str:
    def q(v: float) -> str:
        sgn = "n" if v >= 0 else "s"
        v = abs(v)
        return sgn + f"{v:.{precision}f}".replace(".", "_")
    return f"lat{q(lat)}_lon{q(lon)}"

def dataset_dir(root: Path, activity: str, lat: float, lon: float, asof: date) -> Path:
    return root / activity / coord_token(lat, lon) / f"asof_{asof:%Y%m%d}"

def compute_asof_and_horizon(target: date, lag_days: int) -> tuple[date, int]:
    today_utc = date.today()
    asof = today_utc - timedelta(days=lag_days)
    horizon = (target - asof).days
    return asof, horizon

def call_parser_if_needed(parser_module: str, lat: float, lon: float, asof: date, out_dir: Path, enable: bool) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        return  # looks present
    out_dir.mkdir(parents=True, exist_ok=True)
    if not enable:
        raise SystemExit(
            f"Dataset not found at {out_dir}. "
            f"Re-run with --ensure-missing to auto-fetch via {parser_module}."
        )
    cmd = [
        sys.executable, "-m", parser_module,
        "--lat", str(lat),
        "--lon", str(lon),
        "--asof", asof.isoformat(),
        "--out", str(out_dir),
    ]
    print(f"[INFO] Fetching dataset via: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


# ---------------------------
# Time-series helpers
# ---------------------------

def infer_freq_or_daily(idx: pd.DatetimeIndex) -> str:
    f = pd.infer_freq(idx)
    return f if f is not None else "D"

def lunar_phase_fraction(d: pd.Timestamp) -> float:
    epoch = pd.Timestamp("2000-01-06")
    days = (d.normalize() - epoch).days + 0.5
    return float((days % SYNODIC_MONTH) / SYNODIC_MONTH)

def nearest_label_from_training(frac: float, allowed_labels: list[str]) -> str:
    candidates = {k: v for k, v in CANON_FRAC.items() if k in allowed_labels}
    if not candidates:
        return "New Moon"
    best_label, best_dist = None, 1e9
    for lab, f in candidates.items():
        d = min(abs(frac - f), 1.0 - abs(frac - f))
        if d < best_dist:
            best_dist, best_label = d, lab
    return best_label

def build_future_exog(train_moon_ser: pd.Series, future_index: pd.DatetimeIndex) -> tuple[pd.DataFrame, pd.Series]:
    allowed = list(train_moon_ser.astype("category").cat.categories)
    future_labels = [
        nearest_label_from_training(lunar_phase_fraction(pd.Timestamp(dt)), allowed)
        for dt in future_index
    ]
    future_moon = pd.Series(future_labels, index=future_index, name="moon_phase")
    fut = pd.get_dummies(
        future_moon.astype("category"),
        prefix="moon",
        drop_first=True,
        dummy_na=True
    ).astype("float64")
    return fut, future_moon


# ---------------------------
# Main
# ---------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Merged SARIMA forecasts (no intervals) with moon_phase dummies. "
                    "Supports direct CSV or dataset auto-resolution by activity/coords/asof."
    )

    # Old-style usage (direct CSV)
    ap.add_argument("--csv", help="Path to CSV with columns: date, targets, moon_phase, ...")
    ap.add_argument("--horizon", type=int, help="Days to forecast (used if --csv is provided or if you don't set --date)")

    # New-style usage (dataset discovery + N+lag)
    ap.add_argument("--activity", help="Activity slug (e.g., fishing)")
    ap.add_argument("--lat", type=float, help="Latitude")
    ap.add_argument("--lon", type=float, help="Longitude")
    ap.add_argument("--date", help="Target forecast date YYYY-MM-DD (horizon = (date - (today-lag)))")
    ap.add_argument("--lag-days", type=int, default=3, help="Source data lag in days (default: 3)")
    ap.add_argument("--data-root", default="./data", help="Root directory for datasets (default: ./data)")
    ap.add_argument("--csv-name", default="merged.csv", help="CSV file name inside dataset dir (default: merged.csv)")
    ap.add_argument("--ensure-missing", action="store_true",
                    help="If dataset dir is missing/empty, auto-fetch via parser module")
    ap.add_argument("--parser-module", default="NasaApp.ML.Fishing_parse_data_for_year",
                    help="Module to call when --ensure-missing is set (default: NasaApp.ML.Fishing_parse_data_for_year)")

    # Output
    ap.add_argument("--outdir", default=None, help="Output directory (default: dataset_dir/forecast_out or ./forecast_out)")
    args = ap.parse_args()

    # Resolve input CSV path
    csv_path: Path | None = None
    out_dir: Path

    # Case A: user gave direct CSV
    if args.csv:
        csv_path = Path(args.csv).resolve()
        if not csv_path.exists():
            raise SystemExit(f"--csv not found: {csv_path}")
        # Horizon either provided explicitly, or computed from --date + lag (if given)
        if args.horizon is not None:
            horizon = int(args.horizon)
            asof_for_name = None
            target_date = None
        else:
            if not args.date:
                raise SystemExit("With --csv you must provide --horizon or --date.")
            target_date = date.fromisoformat(args.date)
            asof_for_name, horizon = compute_asof_and_horizon(target_date, args.lag_days)
            if horizon <= 0:
                raise SystemExit(f"Target too close: with lag={args.lag_days}, asof={asof_for_name}. "
                                 f"Pick a later --date.")
        out_dir = Path(args.outdir).resolve() if args.outdir else Path("./forecast_out").resolve()

    # Case B: dataset discovery by activity/coords/asof
    else:
        required = ["activity", "lat", "lon"]
        missing = [k for k in required if getattr(args, k) is None]
        if missing:
            raise SystemExit(f"Missing required args for dataset mode: {missing}. "
                             f"Either provide --csv or all of {required}.")
        if args.date is None and args.horizon is None:
            raise SystemExit("Provide --date to compute N+lag or explicit --horizon.")

        # Determine asof/horizon
        if args.date:
            target_date = date.fromisoformat(args.date)
            asof_for_name, horizon = compute_asof_and_horizon(target_date, args.lag_days)
            if horizon <= 0:
                raise SystemExit(f"Target too close: with lag={args.lag_days}, asof={asof_for_name}. "
                                 f"Pick a later --date.")
        else:
            # no date -> explicit horizon
            target_date = None
            asof_for_name = date.today() - timedelta(days=args.lag_days)
            horizon = int(args.horizon)

        root = data_root(args.data_root)
        ddir = dataset_dir(root, args.activity, float(args.lat), float(args.lon), asof_for_name)
        call_parser_if_needed(args.parser_module, float(args.lat), float(args.lon), asof_for_name, ddir, args.ensure_missing)

        # CSV inside dataset dir
        csv_path = (ddir / args.csv_name).resolve()
        if not csv_path.exists():
            raise SystemExit(f"Dataset CSV not found: {csv_path}. "
                             f"Pass correct --csv-name or generate the expected file in that folder.")
        out_dir = Path(args.outdir).resolve() if args.outdir else (ddir / "forecast_out")

    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Load data ----
    df = pd.read_csv(csv_path)
    if DATE_COL not in df.columns:
        raise SystemExit(f"CSV must contain '{DATE_COL}'")

    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL]).sort_values(DATE_COL).set_index(DATE_COL)

    freq = infer_freq_or_daily(df.index)
    df = df.asfreq(freq)

    # Ensure numeric targets
    present_targets = [c for c in TARGETS if c in df.columns]
    if not present_targets:
        raise SystemExit(f"No expected target columns present: {TARGETS}")
    df[present_targets] = df[present_targets].apply(pd.to_numeric, errors="coerce").ffill().bfill()

    # Exogenous dummies from moon_phase
    if "moon_phase" not in df.columns:
        raise SystemExit("CSV must contain 'moon_phase' for exogenous dummies.")
    moon_ser = df["moon_phase"].copy()
    exog_train = pd.get_dummies(
        moon_ser.astype("category"),
        prefix="moon",
        drop_first=True,
        dummy_na=True
    ).astype("float64")
    exog_train = exog_train.reindex(df.index)

    # Future index & exog (align columns)
    step = pd.tseries.frequencies.to_offset(freq)
    future_idx = pd.date_range(start=df.index[-1] + step, periods=horizon, freq=freq)
    exog_future, future_moon = build_future_exog(moon_ser, future_idx)
    exog_future = exog_future.reindex(columns=exog_train.columns, fill_value=0.0).astype("float64")

    # Fit each model and collect forecasts
    merged = pd.DataFrame(index=future_idx)
    merged["moon_phase"] = future_moon.values  # label column

    for target in present_targets:
        spec = BEST_MODELS[target]
        y = df[target].astype(float)

        res = SARIMAX(
            y,
            exog=exog_train.values,
            order=tuple(spec["order"]),
            seasonal_order=tuple(spec["seasonal_order"]),
            enforce_stationarity=False,
            enforce_invertibility=False,
        ).fit(disp=False)

        fc = res.get_forecast(steps=horizon, exog=exog_future.values)
        merged[target] = fc.predicted_mean.values.astype(float)

    # Final CSV
    merged.reset_index(inplace=True)
    merged.rename(columns={"index": "date"}, inplace=True)

    cols_out = ["date", "moon_phase"] + [c for c in TARGETS if c in merged.columns]
    merged = merged[cols_out]

    # Build output name
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    target_suffix = f"_to_{target_date.isoformat()}" if 'target_date' in locals() and target_date else ""
    if args.csv:
        out_name = f"merged_forecast_{horizon}{target_suffix}_from_csv_{stamp}.csv"
    else:
        safe_act = (args.activity or 'activity').replace("/", "_")
        ctok = coord_token(float(args.lat), float(args.lon))
        asof_str = (asof_for_name.isoformat() if 'asof_for_name' in locals() and asof_for_name else "unknown")
        out_name = f"merged_forecast_{horizon}{target_suffix}_{safe_act}_{ctok}_asof_{asof_str}_{stamp}.csv"

    out_path = out_dir / out_name
    merged.to_csv(out_path, index=False)

    print(f"[OK] Saved merged forecast to: {out_path}")
    print(merged.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
