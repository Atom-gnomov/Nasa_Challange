#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fishing_parse_data_for_year.py
Скачивает исторические почасовые данные погоды для точки (lat, lon) за период [asof - days_back + 1, asof],
агрегирует в дневные ряды и сохраняет CSV с колонками:
  date, moon_phase, air_temp_C, pressure_kPa, wind_speed_m_s, estimated_water_temp_C

Зависимости: requests, pandas, numpy
  pip install requests pandas numpy

Пример:
  python -m NasaApp.ML.Fishing_parse_data_for_year \
    --lat 50.4501 --lon 30.5234 \
    --asof 2025-10-01 \
    --out /path/to/data/fishing/latn50_4501_lone30_5234/asof_20251001 \
    --days-back 400
"""

from __future__ import annotations
from datetime import datetime, timezone
import argparse
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import requests


# --------- Луна: те же канонические фазы, что и в твоём предикторе ---------
SYNODIC_MONTH = 29.53058867  # days
CANON_FRAC = {
    "New Moon": 0.00,
    "First Quarter": 0.25,
    "Full Moon": 0.50,
    "Last Quarter": 0.75,
    # coarse labels (если встречались в обучении)
    "Waning": 0.81,
    "Waxing": 0.31,
}

def lunar_phase_fraction(ts: pd.Timestamp) -> float:
    """Возвращает фазу в [0,1) — доля синодического месяца, как в твоём коде."""
    epoch = pd.Timestamp("2000-01-06")
    days = (ts.normalize() - epoch).days + 0.5
    return float((days % SYNODIC_MONTH) / SYNODIC_MONTH)

def nearest_phase_label(frac: float) -> str:
    """Ближайшая каноническая метка луны по доле цикла."""
    best_label, best_dist = None, 1e9
    for lab, f in CANON_FRAC.items():
        d = min(abs(frac - f), 1.0 - abs(frac - f))
        if d < best_dist:
            best_dist, best_label = d, lab
    return best_label or "New Moon"


# --------- Загрузка из Open-Meteo Historical Weather API ---------
# Документация переменных (hourly): temperature_2m, surface_pressure, wind_speed_10m и др.
# Источник и названия параметров подтверждены в официальной доке.
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

def fetch_hourly(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    """
    Скачивает JSON с почасовыми рядами для периода [start, end] (UTC) и собирает DataFrame с index=datetime.
    Берём минимум, что нужно для таргетов и производных:
      - temperature_2m (°C)
      - surface_pressure (hPa)
      - wind_speed_10m (м/с, задаём unit=ms)
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(["temperature_2m", "surface_pressure", "wind_speed_10m"]),
        "wind_speed_unit": "ms",  # сразу м/с
        "timezone": "UTC",
    }

    r = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Open-Meteo error {r.status_code}: {r.text[:300]}")

    data = r.json()
    if "hourly" not in data or "time" not in data["hourly"]:
        raise RuntimeError("Malformed Open-Meteo response: no 'hourly/time'")

    h = data["hourly"]
    # Проверяем наличие нужных полей
    missing = [k for k in ["temperature_2m", "surface_pressure", "wind_speed_10m"] if k not in h]
    if missing:
        raise RuntimeError(f"Missing hourly variables in response: {missing}")

    df = pd.DataFrame(
        {
            "time": pd.to_datetime(h["time"], errors="coerce"),
            "temperature_2m": h["temperature_2m"],
            "surface_pressure_hPa": h["surface_pressure"],  # в гПа
            "wind_speed_m_s": h["wind_speed_10m"],          # уже м/с
        }
    ).dropna(subset=["time"]).set_index("time").sort_index()

    # Приводим к float и фильтруем NaN (заполним вперёд/назад, чтобы сгладить единичные пропуски)
    for c in ["temperature_2m", "surface_pressure_hPa", "wind_speed_m_s"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.ffill().bfill()

    return df


def hourly_to_daily(dfh: pd.DataFrame) -> pd.DataFrame:
    """Агрегация в дневные средние значения (UTC) + инженерные фичи."""
    dfh = dfh.copy()
    # Гарантируем, что индекс — DatetimeIndex и он называется 'date'
    dfh.index = pd.to_datetime(dfh.index)
    dfh.index.name = "date"

    # Дневные агрегаты
    daily = dfh.resample("D")
    dfd = pd.DataFrame({
        "air_temp_C": daily["temperature_2m"].mean(),
        "pressure_kPa": daily["surface_pressure_hPa"].mean() / 10.0,
        "wind_speed_m_s": daily["wind_speed_m_s"].mean(),
    })

    # Оценка температуры воды (EMA по воздуху)
    alpha = 0.12
    vals = dfd["air_temp_C"].astype(float).tolist()
    wtemp = []
    prev = float(vals[0]) if vals else 0.0
    for x in vals:
        prev = prev + alpha * (x - prev)
        wtemp.append(prev)
    dfd["estimated_water_temp_C"] = wtemp

    # Метка фазы луны на основе индекса (который уже 'date')
    phases = pd.Series(dfd.index).apply(
        lambda ts: nearest_phase_label(lunar_phase_fraction(pd.Timestamp(ts)))
    )
    dfd["moon_phase"] = phases.values

    # Приводим к нужному формату
    dfd = dfd.reset_index()              # теперь колонка точно называется 'date'
    dfd["date"] = pd.to_datetime(dfd["date"]).dt.date

    return dfd


# --------- CLI и основной конвейер ---------

def main():
    ap = argparse.ArgumentParser(description="Download & prepare daily merged CSV for fishing model")
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--asof", type=str, required=True, help="YYYY-MM-DD (последний доступный день источника)")
    ap.add_argument("--out", type=str, required=True, help="Каталог, куда положить merged.csv и READY")
    ap.add_argument("--days-back", type=int, default=400, help="Сколько дней истории тянуть до asof (по умолчанию 400)")
    args = ap.parse_args()

    asof = date.fromisoformat(args.asof)
    start = asof - timedelta(days=max(args.days_back - 1, 1))
    end = asof

    out_dir = Path(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Fetching hourly data {start}..{end} for lat={args.lat}, lon={args.lon}")
    dfh = fetch_hourly(args.lat, args.lon, start, end)

    print(f"[INFO] Aggregating to daily and computing engineered features")
    dfd = hourly_to_daily(dfh)

    # Переставим порядок колонок как требуется твоему предиктору
    cols_out = [
        "date",
        "moon_phase",
        "air_temp_C",
        "pressure_kPa",
        "wind_speed_m_s",
        "estimated_water_temp_C",
    ]
    # На всякий случай, если вдруг NaN — подзаполним
    dfd = dfd[cols_out].copy()
    dfd[["air_temp_C", "pressure_kPa", "wind_speed_m_s", "estimated_water_temp_C"]] = \
        dfd[["air_temp_C", "pressure_kPa", "wind_speed_m_s", "estimated_water_temp_C"]].astype(float).ffill().bfill()

    csv_path = out_dir / "merged.csv"
    dfd.to_csv(csv_path, index=False)
    print(f"[OK] Saved dataset to: {csv_path}")

    # Дополнительно можно сохранить небольшой manifest.json
    manifest = {
        "source": "open-meteo archive",
        "latitude": args.lat,
        "longitude": args.lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "columns": cols_out,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # Флажок готовности
    (out_dir / "READY").write_text(f"ok {datetime.now(timezone.utc).isoformat()}", encoding="utf-8")


if __name__ == "__main__":
    main()
