# NasaApp/ML/main_fishing.py
from __future__ import annotations

import sys
from pathlib import Path
from datetime import date, datetime
from typing import Optional, Dict, Any

import pandas as pd

# Важно: файлы лежат рядом в NasaApp/ML
import Fishing_parse_data_for_year 
import arima_predict_fishing
import fishing_LLM_analyzer
import coordinate_tool


def run(
    lat: float,
    lon: float,
    *,
    target_date: Optional[date] = None,
    horizon: Optional[int] = 12,
    results_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Главный раннер для рыбалки:
      1) тянет год истории (если нужно) через Fishing_parse_data_for_year
      2) ARIMA-прогноз на horizon дней (или до target_date)
      3) Gemini-анализ по каждому дню прогноза
      4) сохраняет результирующий CSV и возвращает его путь + JSON-данные
    """
    # 0) Определяем горизонт
    if horizon is None:
        if not target_date:
            raise ValueError("Provide target_date or horizon")
        today = date.today()
        horizon = max(1, (target_date - today).days)

    # 1) История: всегда дергаем твой парсер (демо-логика ок)
    #    Он сохранит fishing_year_values_{LAT}_{LON}.csv в текущей папке
    
    flag, coord = coordinate_tool.find_existing(lat,lon)
    LAT = coord[0]
    LON = coord[1]
    print(flag, coord[0],coord[1])
    if flag == False:
        Fishing_parse_data_for_year.main(LAT, LON)

    # 2) ARIMA — твоя версия ожидает CLI-аргументы через sys.argv и возвращает DataFrame
    csv_name = f"fishing_year_values_{LAT}_{LON}.csv"
    sys.argv = [
        "arima_predict_fishing.py",
        "--csv", csv_name,
        "--horizon", str(horizon),
        "--outdir", "forecast_out",
    ]
    future_df: pd.DataFrame = arima_predict_fishing.main()

    # 3) LLM-анализ по каждому дню прогноза
    final_results = pd.DataFrame()
    for _, row in future_df.iterrows():
        res = fishing_LLM_analyzer.evaluate_fishing_with_gemini(
            air_temp_par=row["air_temp_C"],
            pressure_kpa_par=row["pressure_kPa"],
            wind_speed_par=row["wind_speed_m_s"],
            moon_phase_par=row["moon_phase"],
            water_temp_par=row["estimated_water_temp_C"],
        )

        # дата + входные параметры в каждую строку
        res.insert(0, "date", pd.to_datetime(row["date"]).date())
        res["air_temp_C"] = float(row["air_temp_C"])
        res["pressure_kPa"] = float(row["pressure_kPa"])
        res["wind_speed_m_s"] = float(row["wind_speed_m_s"])
        res["moon_phase"] = row["moon_phase"]
        res["water_temp_C"] = float(row["estimated_water_temp_C"])

        final_results = pd.concat([final_results, res], ignore_index=True)

    # 4) Сохранение CSV
    out_dir = Path(results_dir or "results_folder")
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    suffix = f"_to_{target_date.isoformat()}" if target_date else f"_{horizon}d"
    out_path = out_dir / f"fishing_evaluation_results_{lat}_{lon}{suffix}_{stamp}.csv"
    final_results.to_csv(out_path, index=False, encoding="utf-8")

    return {"csv_path": str(out_path), "rows": final_results.to_dict(orient="records")}

run(80,30)