import requests
import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIGURATION ===
LAT = 50.45
LON = 30.52
DAYS_BACK = 365
MAX_WORKERS = 10

# === Helper: generate past dates ===
def get_past_dates(days_back=DAYS_BACK):
    today = datetime.date.today()
    for i in range(days_back):
        candidate = today - datetime.timedelta(days=i)
        yield candidate.strftime("%Y%m%d"), candidate

# === Moon Phase Calculation ===
def moon_phase(date):
    diff = date - datetime.date(2001, 1, 1)
    days = diff.days
    lunations = 29.53058867
    phase_index = (days % lunations) / lunations
    if phase_index < 0.03 or phase_index > 0.97:
        return "New Moon"
    elif phase_index < 0.22:
        return "First Quarter"
    elif phase_index < 0.47:
        return "Full Moon"
    elif phase_index < 0.72:
        return "Last Quarter"
    else:
        return "Waning"

# === Coefficients for water temperature estimation ===
a0, a1, a2, a3, a4, a5 = 0.5, 0.8, -0.1, 0.01, 1.5, 4.0

# === Fetch data for a single date ===
def fetch_day_data(date_tuple):
    date_str, date_obj = date_tuple
    try:
        power_url = (
            f"https://power.larc.nasa.gov/api/temporal/daily/point?"
            f"parameters=T2M,PS,WS10M&community=RE&longitude={LON}&latitude={LAT}"
            f"&start={date_str}&end={date_str}&format=JSON"
        )
        response = requests.get(power_url, timeout=10)
        data = response.json()

        t2m = data['properties']['parameter']['T2M'][date_str]
        ps = data['properties']['parameter']['PS'][date_str]
        ws = data['properties']['parameter']['WS10M'][date_str]

        if any(v == -999.0 for v in [t2m, ps, ws]):
            return f"⚠️ Missing POWER data for {date_str}", None

        # Moon phase string
        moon_str = moon_phase(date_obj)

        # Summer factor (May–Sep)
        summer_factor = 1.0 if 5 <= date_obj.month <= 9 else 0.0

        # Estimate water temp
        water_temp = a0 + a1*t2m + a2*ws + a3*ps + a4*(0.5 if moon_str=="Full Moon" else 0.25) + a5*summer_factor

        record = {
            "date": date_obj,
            "air_temp_C": t2m,
            "pressure_kPa": ps,
            "wind_speed_m_s": ws,
            "moon_phase": moon_str,
            "summer_factor": summer_factor,
            "estimated_water_temp_C": round(water_temp, 2)
        }
        return None, record

    except Exception as e:
        return f"❌ Failed for {date_str}: {e}", None

# === Run multi-threaded ===
dates_list = list(get_past_dates())
records = []
errors = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(fetch_day_data, d): d for d in dates_list}
    for future in as_completed(futures):
        error_msg, record = future.result()
        if error_msg:
            errors.append(error_msg)
        if record:
            records.append(record)

# === Save to CSV ===
if records:
    df = pd.DataFrame(records).sort_values("date")
    df.to_csv("fishing_year_values.csv", index=False)
    print("\n✅ Yearly water temperature estimation saved to 'river_water_temp_moon_phase.csv'")

# === Print errors if any ===
if errors:
    print("\n⚠️ Errors encountered:")
    for e in errors:
        print(e)
