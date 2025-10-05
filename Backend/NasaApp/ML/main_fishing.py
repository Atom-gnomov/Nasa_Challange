# NasaApp/ML/main_fishing.py
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Dict, Any

import pandas as pd

# ✅ Use package-relative imports so Django can import this as NasaApp.ML.main_fishing
try:
    from . import Fishing_parse_data_for_year
    from . import arima_predict_fishing
    from . import fishing_LLM_analyzer
    from . import coordinate_tool
except ImportError:
    # Fallback if someone runs this file directly as a script (not via Django)
    import Fishing_parse_data_for_year          # noqa
    import arima_predict_fishing                # noqa
    import fishing_LLM_analyzer                 # noqa
    import coordinate_tool                      # noqa


def run(
    lat: float,
    lon: float,
    *,
    target_date: Optional[date] = None,
    horizon: Optional[int] = 12,
    results_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fishing pipeline:
      1) Ensure we have a year of history for (lat, lon) (download if missing).
      2) Run ARIMA forecast for 'horizon' days (or until 'target_date').
      3) Run Gemini LLM evaluation per day.
      4) Save final CSV and return its path and rows (list of dicts).
    """
    # --- determine horizon if only target_date provided
    if horizon is None:
        if not target_date:
            raise ValueError("Provide target_date or horizon")
        today = date.today()
        horizon = max(1, (target_date - today).days)

    # --- use/remember nearest existing coordinate if within MAX_DISTANCE_KM
    flag, (LAT, LON) = coordinate_tool.find_existing(lat, lon)

    # If no close coord found, create year dataset now
    if not flag:
        Fishing_parse_data_for_year.main(LAT, LON)

    # --- ARIMA step: set argv for module's argparse, then call main()
    csv_name = f"fishing_year_values_{LAT}_{LON}.csv"
    sys.argv = [
        "arima_predict_fishing.py",
        "--csv", csv_name,
        "--horizon", str(horizon),
        "--outdir", "forecast_out",
    ]
    future_df: pd.DataFrame = arima_predict_fishing.main()

    # --- LLM step: evaluate each predicted day
    final_results = pd.DataFrame()
    for _, row in future_df.iterrows():
        res = fishing_LLM_analyzer.evaluate_fishing_with_gemini(
            air_temp_par=row["air_temp_C"],
            pressure_kpa_par=row["pressure_kPa"],
            wind_speed_par=row["wind_speed_m_s"],
            moon_phase_par=row["moon_phase"],
            water_temp_par=row["estimated_water_temp_C"],
        )

        # copy inputs & date into result row(s)
        res.insert(0, "date", pd.to_datetime(row["date"]).date())
        res["air_temp_C"] = float(row["air_temp_C"])
        res["pressure_kPa"] = float(row["pressure_kPa"])
        res["wind_speed_m_s"] = float(row["wind_speed_m_s"])
        res["moon_phase"] = row["moon_phase"]
        res["water_temp_C"] = float(row["estimated_water_temp_C"])

        final_results = pd.concat([final_results, res], ignore_index=True)

    # --- Save final CSV
    out_dir = Path(results_dir or "results_folder")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_to_{target_date.isoformat()}" if target_date else f"_{horizon}d"
    out_path = out_dir / f"fishing_evaluation_results_{lat}_{lon}{suffix}_{stamp}.csv"
    final_results.to_csv(out_path, index=False, encoding="utf-8")

    return {"csv_path": str(out_path), "rows": final_results.to_dict(orient="records")}
