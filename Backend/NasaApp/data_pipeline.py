# NasaApp/data_pipeline.py
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from django.conf import settings


# ---------- базовые пути/идентификаторы ----------

def _data_root() -> Path:
    """
    Корневая папка для датасетов/прогнозов.
    Берётся из settings.DATA_ROOT, иначе <BASE_DIR>/data.
    """
    base = getattr(settings, "DATA_ROOT", None)
    if base:
        return Path(base)
    return Path(settings.BASE_DIR) / "data"


def coord_token(lat: float, lon: float, precision: int = 4) -> str:
    """
    Стабильный токен координат для имён папок.
    Пример: latn50_4501_lone30_5234 (4 знака после запятой).
    """
    def q(v: float) -> str:
        sgn = "n" if v >= 0 else "s"
        v = abs(v)
        return sgn + f"{v:.{precision}f}".replace(".", "_")
    return f"lat{q(lat)}_lon{q(lon)}"


def dataset_dir(activity_slug: str, lat: float, lon: float, asof: date) -> Path:
    """
    Папка набора данных: data/<activity>/<coord_token>/asof_YYYYMMDD/
    """
    return _data_root() / activity_slug / coord_token(lat, lon) / f"asof_{asof:%Y%m%d}"


# ---------- модели метаданных ----------

@dataclass
class DatasetManifest:
    activity: str
    lat: float
    lon: float
    asof: str
    created_at: str
    source: str
    files: list[str]

    def dump(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- вычисления горизонта (N + лаг) ----------

def compute_effective_horizon(target: date, lag_days: int = 3) -> tuple[int, date]:
    """
    Источник отдаёт исторические данные до (today - lag_days).
    Возвращаем: (горизонт в днях, asof).
    """
    today = date.today()
    asof = today - timedelta(days=lag_days)
    horizon = (target - asof).days
    return horizon, asof


# ---------- обеспечение наличия датасета ----------

def ensure_dataset(activity_slug: str, lat: float, lon: float, asof: date) -> Path:
    """
    Гарантирует, что есть локальный датасет с merged.csv для данных параметров.
    Если нет — вызывает парсер NasaApp.ML.Fishing_parse_data_for_year как модуль.
    """
    ddir = dataset_dir(activity_slug, lat, lon, asof)
    ddir.mkdir(parents=True, exist_ok=True)

    manifest_path = ddir / "manifest.json"
    merged_csv = ddir / "merged.csv"

    if not merged_csv.exists():
        # Вызов твоего парсера — он должен создать merged.csv в ddir
        cmd = [
            sys.executable, "-m", "NasaApp.ML.Fishing_parse_data_for_year",
            "--lat", str(lat),
            "--lon", str(lon),
            "--asof", asof.isoformat(),
            "--out", str(ddir),
        ]
        subprocess.run(cmd, check=True)

    # обновим/создадим manifest.json
    files = sorted([p.name for p in ddir.iterdir() if p.is_file() and p.name != "manifest.json"])
    DatasetManifest(
        activity=activity_slug,
        lat=lat,
        lon=lon,
        asof=asof.isoformat(),
        created_at=datetime.utcnow().isoformat() + "Z",
        source="Fishing_parse_data_for_year",
        files=files,
    ).dump(manifest_path)

    return ddir


# ---------- запуск ARIMA и чтение одной строки прогноза ----------

def run_arima_and_read_row(
    *,
    activity_slug: str,
    lat: float,
    lon: float,
    target: date,
    lag_days: int,
    dataset_path: Path,
) -> dict:
    """
    Запускает ARIMA-скрипт (как модуль) и возвращает ОДНУ строку прогноза на дату target.
    Ожидается, что merged.csv лежит в dataset_path.
    """
    outdir = dataset_path / "forecast_out"
    outdir.mkdir(parents=True, exist_ok=True)

    # Запускаем предиктор
    cmd = [
        sys.executable, "-m", "NasaApp.ML.arima_predict_merged",
        "--activity", activity_slug,
        "--lat", str(lat),
        "--lon", str(lon),
        "--date", target.isoformat(),
        "--lag-days", str(lag_days),
        "--data-root", str(_data_root()),
        "--csv-name", "merged.csv",
        "--outdir", str(outdir),
        # --ensure-missing НЕ нужен, т.к. ensure_dataset уже отработал
    ]
    subprocess.run(cmd, check=True)

    # Находим последний сгенерированный файл прогноза
    candidates = sorted(
        outdir.glob("merged_forecast_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise RuntimeError(f"ARIMA did not produce forecast CSV in {outdir}")
    fc_path = candidates[0]

    # Читаем прогноз и возвращаем строку на нужную дату
    import pandas as pd
    df = pd.read_csv(fc_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    row = df.loc[df["date"] == target]
    if row.empty:
        # если нет точного совпадения по дате — берём последнюю строку
        row = df.tail(1)
    return row.iloc[0].to_dict()
