#!/usr/bin/env python3
# arima_predict_merged.py
# Forecast N days ahead with fixed SARIMA specs, moon_phase dummies as exog.
# OUTPUT: single CSV with columns:
#   date, moon_phase, air_temp_C, pressure_kPa, wind_speed_m_s, estimated_water_temp_C
# No prediction intervals are produced.

import argparse
import warnings
from pathlib import Path
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

# Your best models (fixed)
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

def main():
    ap = argparse.ArgumentParser(description="Merged SARIMA forecasts without intervals; includes moon_phase label")
    ap.add_argument("--csv", required=True, help="CSV with date, targets, moon_phase, summer_factor")
    ap.add_argument("--horizon", type=int, required=True, help="Days to forecast")
    ap.add_argument("--outdir", default="forecast_out", help="Output directory")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.csv)
    if DATE_COL not in df.columns:
        raise SystemExit(f"CSV must contain '{DATE_COL}'")

    # Index & frequency
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
    future_idx = pd.date_range(start=df.index[-1] + step, periods=args.horizon, freq=freq)
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

        fc = res.get_forecast(steps=args.horizon, exog=exog_future.values)
        merged[target] = fc.predicted_mean.values.astype(float)

    # Final CSV
    merged.reset_index(inplace=True)
    merged.rename(columns={"index": "date"}, inplace=True)
    # column order
    cols_out = ["date", "moon_phase"] + [c for c in TARGETS if c in merged.columns]
    merged = merged[cols_out]

    out_path = outdir / f"merged_forecast_{args.horizon}.csv"
    merged.to_csv(out_path, index=False)

    print(f"Saved merged forecast to: {out_path}")
    print(merged.head(5).to_string(index=False))

if __name__ == "__main__":
    main()
