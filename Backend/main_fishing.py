import fishing_LLM_analyzer
import pandas as pd
from Backend import arima_predict_fishing
from pathlib import Path
import sys
import Fishing_parse_data_for_year
from test import find_existing

if __name__ == "__main__":
    lat = 55
    lon = 25
    flag, coord = find_existing(lat,lon)
    LAT = coord[0]
    LON = coord[1]
    print(flag, coord[0],coord[1])
    if flag == False:
        Fishing_parse_data_for_year.main(LAT,LON)

    sys.argv = [
        "arima_predict.py",
        "--csv", f"fishing_year_values_{LAT}_{LON}.csv",
        "--horizon", "10",
        "--outdir", "forecast_out"
    ]

    predict = arima_predict_fishing.main()
    print(predict)
    final_results = pd.DataFrame()

    for _, row in predict.iterrows():
        res = fishing_LLM_analyzer.evaluate_fishing_with_gemini(
            air_temp_par=row["air_temp_C"],
            pressure_kpa_par=row["pressure_kPa"],
            wind_speed_par=row["wind_speed_m_s"],
            moon_phase_par=row["moon_phase"],
            water_temp_par=row["estimated_water_temp_C"]
        )
        
        # Add the date column
        res.insert(0, "date", row["date"])
        
        # Add the input parameters as new columns
        res["air_temp_C"] = row["air_temp_C"]
        res["pressure_kPa"] = row["pressure_kPa"]
        res["wind_speed_m_s"] = row["wind_speed_m_s"]
        res["moon_phase"] = row["moon_phase"]
        res["water_temp_C"] = row["estimated_water_temp_C"]
        
        # Concatenate into final_results
        final_results = pd.concat([final_results, res], ignore_index=True)

        output_folder = Path("results_folder")  # replace with your desired folder name
        output_folder.mkdir(parents=True, exist_ok=True) 
        output_file = output_folder / f"fishing_evaluation_results_{LAT}_{LON}.csv"
    final_results.to_csv(output_file, index=False)




