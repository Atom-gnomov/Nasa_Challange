import requests
import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

# === CONFIG ===
LAT = 50.45
LON = 30.52
DAYS_BACK = 365
MAX_WORKERS = 10
REQUEST_TIMEOUT = 15  # seconds

# === Helpers ===
def get_past_dates(days_back=DAYS_BACK):
    today = datetime.date.today()
    for i in range(days_back):
        d = today - datetime.timedelta(days=i)
        yield d.strftime("%Y%m%d"), d

# Centralized request wrapper (small helper for future retries if needed)
def http_get(url, params=None):
    try:
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return None, r.json()
    except Exception as e:
        return str(e), None

# === POWER daily (NASA POWER) ===
def fetch_power_daily(date_tuple):
    date_str, date_obj = date_tuple
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
    )
    params = {
        "parameters": "T2M,WS10M,PRECTOTCORR",
        "community": "RE",
        "longitude": LON,
        "latitude": LAT,
        "start": date_str,
        "end": date_str,
        "format": "JSON",
        "accept": "nearest"
    }
    err, data = http_get(url, params)
    if err:
        return f"POWER request error {date_str}: {err}", None

    try:
        props = data["properties"]["parameter"]
        t2m = props["T2M"].get(date_str, -999.0)
        ws = props["WS10M"].get(date_str, -999.0)
        precip = props["PRECTOTCORR"].get(date_str, -999.0)

        if any(v == -999.0 for v in [t2m, ws, precip]):
            miss = [name for v, name in zip([t2m, ws, precip], ["T2M","WS10M","PRECTOTCORR"]) if v == -999.0]
            return f"POWER missing for {date_str}: {miss}", None

        rec = {
            "date": date_obj,
            "avg_temp_C": round(float(t2m), 2),
            "wind_speed_m_s": round(float(ws), 2),
            "precip_mm": round(float(precip), 3)
        }
        return None, rec
    except Exception as e:
        return f"POWER parse error {date_str}: {e}", None

# === Open-Meteo Archive for shortwave_radiation and cloudcover ===
def fetch_open_meteo_archive_vars(date_obj):
    date_iso = date_obj.strftime("%Y-%m-%d")
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": date_iso,
        "end_date": date_iso,
        "hourly": "shortwave_radiation,cloudcover",
        "timezone": "auto"
    }
    err, data = http_get(url, params)
    if err:
        return f"Open-Meteo archive error {date_iso}: {err}", None

    hourly = data.get("hourly", {})
    rad_list = hourly.get("shortwave_radiation", [])
    cloud_list = hourly.get("cloudcover", [])

    out = {}
    if rad_list:
        out["solar_radiation_W_m2"] = round(sum(rad_list)/len(rad_list), 2)
    else:
        # debug snippet
        keys = list(hourly.keys())
        print(f"[DEBUG] No shortwave_radiation for {date_iso}; hourly keys: {keys}")
        out["solar_radiation_W_m2"] = None

    if cloud_list:
        out["cloud_cover_%"] = round(sum(cloud_list)/len(cloud_list), 2)
    else:
        keys = list(hourly.keys())
        print(f"[DEBUG] No cloudcover for {date_iso}; hourly keys: {keys}")
        out["cloud_cover_%"] = None

    return None, out

# === Open-Meteo Air Quality (hourly pm2_5) ===
def fetch_open_meteo_aq(date_obj):
    date_iso = date_obj.strftime("%Y-%m-%d")
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": date_iso,
        "end_date": date_iso,
        "hourly": "pm2_5",
        "timezone": "auto"
    }
    err, data = http_get(url, params)
    if err:
        return f"Open-Meteo AQ error {date_iso}: {err}", None

    hourly = data.get("hourly", {})
    pm25_list = hourly.get("pm2_5", [])
    if pm25_list:
        # filter out nulls
        vals = [v for v in pm25_list if v is not None]
        if vals:
            return None, round(sum(vals)/len(vals), 2)
        else:
            print(f"[DEBUG] pm2_5 present but all null for {date_iso}; length={len(pm25_list)}")
            return f"No valid pm2_5 values for {date_iso}", None
    else:
        # helpful debug: show what's in response
        info_keys = list(hourly.keys())
        print(f"[DEBUG] No pm2_5 for {date_iso}; hourly keys: {info_keys}")
        # also show a short snippet of top-level keys to help debugging
        top_keys = list(data.keys())
        print(f"[DEBUG] Open-Meteo AQ response top keys: {top_keys}")
        return f"No pm2_5 data returned for {date_iso}", None

# === Fetch everything for a single date (worker) ===
def fetch_day_all(date_tuple):
    date_str, date_obj = date_tuple
    errors = []

    p_err, p_rec = fetch_power_daily(date_tuple)
    if p_err:
        return p_err, None

    # archive vars (rad + cloud)
    arc_err, arc_rec = fetch_open_meteo_archive_vars(date_obj)
    if arc_err:
        errors.append(arc_err)
        # still proceed, set None values
        arc_rec = {"solar_radiation_W_m2": None, "cloud_cover_%": None}
    # AQ
    aq_err, aq_val = fetch_open_meteo_aq(date_obj)
    if aq_err:
        errors.append(aq_err)
        aq_val = None

    # merge
    p_rec.update(arc_rec)
    p_rec["air_quality_pm2_5"] = aq_val

    return (errors if errors else None), p_rec

# === Run multi-threaded over dates_list ===
dates_list = list(get_past_dates())
records = []
errors = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
    futures = {exe.submit(fetch_day_all, d): d for d in dates_list}
    for fut in as_completed(futures):
        err, rec = fut.result()
        if rec:
            records.append(rec)
        if err:
            if isinstance(err, list):
                errors.extend(err)
            else:
                errors.append(err)

# === Save CSV ===
if records:
    df = pd.DataFrame(records).sort_values("date")
    df.to_csv("full_year_weather_data_corrected.csv", index=False)
    print("✅ Saved to full_year_weather_data_corrected.csv")
else:
    print("❌ No records fetched")

# === Print summary of errors (if any) ===
if errors:
    print("\n⚠️ Some warnings/errors encountered (showing unique messages):")
    for msg in sorted(set(errors)):
        print(" -", msg)
