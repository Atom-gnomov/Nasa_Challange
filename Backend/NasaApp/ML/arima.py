#!/usr/bin/env python3
# arima.py — minimal: pick and print ONLY the best (S)ARIMA per target using moon_phase dummies as exog
import argparse, warnings
import numpy as np
import pandas as pd
from math import inf
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings("ignore")

DATE_COL = "date"
TARGETS  = ["air_temp_C", "pressure_kPa", "wind_speed_m_s", "estimated_water_temp_C"]  # no summer_factor, no model for moon_phase

def seasonal_m(freq: str|None) -> int:
    if not freq: return 0
    f = freq.upper()
    if f.startswith("D"): return 7
    if f.startswith("H"): return 24
    if f.startswith("M"): return 12
    if f.startswith("W"): return 52
    return 0

def main():
    ap = argparse.ArgumentParser(description="Print best (S)ARIMA per column using moon_phase dummies as exog")
    ap.add_argument("--csv", required=True)
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    if DATE_COL not in df.columns:
        raise SystemExit(f"CSV must contain '{DATE_COL}'")

    # Index & frequency
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL]).sort_values(DATE_COL).set_index(DATE_COL)
    freq = pd.infer_freq(df.index)
    if freq is None: freq = "D"
    df = df.asfreq(freq)

    # Exogenous: one-hot dummies for moon_phase
    exog = None
    if "moon_phase" in df.columns:
        exog = pd.get_dummies(df["moon_phase"].astype("category"),
                              prefix="moon", drop_first=True, dummy_na=True)
        if exog.shape[1] == 0:
            exog = None
    if exog is not None:
        exog = exog.ffill().bfill()

    # Targets present
    cols = [c for c in TARGETS if c in df.columns]
    if not cols:
        raise SystemExit("No target columns found among: " + ", ".join(TARGETS))

    # Basic cleaning
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce").ffill().bfill()

    m = seasonal_m(freq)
    use_seasonal = m > 1
    print(f"# Frequency: {freq} | seasonal m={m if use_seasonal else 0} | exog_cols={0 if exog is None else exog.shape[1]}")
    print("# BEST MODELS (by AIC):")

    # Small, robust grids
    order_grid = [(p,d,q) for p in range(0,4) for d in (0,1,2) for q in range(0,4)]
    seas_grid  = [(0,0,0,0)] if not use_seasonal else [(P,D,Q,m) for P in (0,1) for D in (0,1) for Q in (0,1)]

    for col in cols:
        y = df[col].astype(float)
        best = {"aic": inf, "order": None, "sorder": None}
        for (p,d,q) in order_grid:
            for sorder in seas_grid:
                try:
                    mod = SARIMAX(
                        y,
                        exog=exog,
                        order=(p,d,q),
                        seasonal_order=sorder,
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                    )
                    res = mod.fit(disp=False)
                    aic = res.aic
                    if aic < best["aic"]:
                        best.update({"aic": aic, "order": (p,d,q), "sorder": sorder})
                except Exception:
                    continue
        if best["order"] is None:
            print(f"{col}: FAILED to fit any spec")
        else:
            print(f"{col}: order={best['order']}, seasonal_order={best['sorder']}, AIC={best['aic']:.2f}")

if __name__ == "__main__":
    main()
