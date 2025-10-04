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


# === Fire Risk Level Mapping ===
def fire_risk_category(value):
    if value < 20:
        return "Very Low"
    elif value < 40:
        return "Low"
    elif value < 60:
        return "Moderate"
    elif value < 80:
        return "High"
    else:
        return "Extreme"


# === Fetch data for a single date ===
def fetch_day_data(date_tuple):
    date_str, date_obj = date_tuple
    try:
        # Fetch daily weather data
        power_url = (
            f"https://power.larc.nasa.gov/api/temporal/daily/point?"
            f"parameters=T2M_MAX,T2M_MIN,WS10M,RH2M,PRECTOTCORR"
            f"&community=RE&longitude={LON}&latitude={LAT}"
            f"&start={date_str}&end={date_str}&format=JSON"
        )

        response = requests.get(power_url, timeout=10)
        data = response.json()
        params = data['properties']['parameter']

        # Extract values
        t2m_max = params['T2M_MAX'][date_str]
        t2m_min = params['T2M_MIN'][date_str]
        ws = params['WS10M'][date_str]
        humidity = params['RH2M'][date_str]
        precip = params['PRECTOTCORR'][date_str]

        # Skip if any invalid
        if any(v == -999.0 for v in [t2m_max, t2m_min, ws, humidity, precip]):
            return f"⚠️ Missing POWER data for {date_str}", None

        # === Fire Risk Formula ===
        # Scaled and adjusted to give 0–100 realistic range
        risk_raw = (
            0.6 * (t2m_max - 10)
            + 0.5 * ws
            - 0.4 * precip
            - 0.3 * (humidity - 30)
            + 0.2 * (t2m_max - t2m_min)
        )
        fire_risk = max(0, min(100, risk_raw * 10))

        # Categorical risk level
        risk_level = fire_risk_category(fire_risk)

        record = {
            "date": date_obj,
            "max_temp_C": round(t2m_max, 2),
            "night_temp_C": round(t2m_min, 2),
            "wind_speed_m_s": round(ws, 2),
            "humidity_%": round(humidity, 2),
            "precip_mm": round(precip, 2),
            "fire_risk_index": round(fire_risk, 2),
            "fire_risk_level": risk_level
        }

        return None, record

    except Exception as e:
        return f"❌ Failed for {date_str}: {e}", None


# === Run multi-threaded fetching ===
dates_list = list(get_past_dates())
records = []
errors = []

print(f"⏳ Fetching {len(dates_list)} days of POWER data for LAT={LAT}, LON={LON}...")

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
    df.to_csv("forest_camping_year_values.csv", index=False)
    print("\n✅ Yearly fire risk dataset saved to 'forest_camping_year_values.csv'")

# === Print errors if any ===
if errors:
    print("\n⚠️ Errors encountered:")
    for e in errors:
        print(e)
