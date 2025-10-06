# Nasa_Challange — Fishing Forecast (Django + Next.js)

A full‑stack app that predicts day‑by‑day fishing conditions for a chosen geo‑point and date window.  
**Backend:** Django REST API with an ARIMA‑based pipeline + short LLM summaries.  
**Frontend:** Next.js (TypeScript, Tailwind, shadcn/ui) dashboard.

---

## Features

- 🌍 Choose a location (auto‑geolocate or manual) and an activity (fishing).
- 🔭 Backend fetches historical weather, builds ARIMA forecasts, and adds a compact summary per day.
- 🧾 CSVs auto‑saved for each run (reproducible results).
- ⚡ Simple API: `POST /api/predict/fishing` returns normalized daily rows (temperature, wind, pressure, moon, water temp estimate, rating + tips).
- 🖥️ Clean dashboard UI with per‑day cards and rating.

---

## Tech Stack

- **Backend:** Python, Django, Django REST Framework, django-filter, NumPy, pandas, statsmodels (ARIMA)
- **ML Code:** `Backend/NasaApp/ML/*` (data fetch, coordinate cache, ARIMA, analyzer)
- **Frontend:** Next.js 14, React 18, TypeScript, Tailwind, shadcn/ui, lucide-react
- **Storage:** SQLite by default (in‑repo `Backend/db.sqlite3`)

---

## Project Structure

```
Nasa_Challange/
├─ Backend/
│  ├─ manage.py
│  ├─ db.sqlite3
│  ├─ .env                           # do not commit
│  ├─ NasaSite/
│  │  ├─ settings.py                 # CORS/CSRF config, INSTALLED_APPS
│  │  └─ urls.py                     # /api/ mounted here
│  └─ NasaApp/
│     ├─ models.py                   # Activity, WeatherParam, ActivityParam
│     ├─ views.py                    # ViewSets + FishingPredictView
│     ├─ urls.py                     # /api/predict/fishing, routers
│     └─ ML/
│        ├─ main_fishing.py          # end‑to‑end pipeline, saves CSV
│        ├─ arima.py, arima_predict_fishing.py
│        ├─ Fishing_parse_data_for_year.py
│        ├─ coordinate_tool.py, fishing_LLM_analyzer.py
│        ├─ saved_coords.json
│        └─ results_folder/          # output CSVs
└─ Frontend/
   ├─ package.json                    # dev script (port 9002)
   └─ src/app/page.tsx                # uses NEXT_PUBLIC_API_BASE
```

---

## Quick Start (Local Dev)

### 1) Backend (Django API)

**Prereqs:** Python 3.11+ recommended.

```bash
cd Backend
python -m venv .venv
# Windows PowerShell:
. .venv/Scripts/Activate.ps1
# Cmd:
# .venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r ../requirements.txt
```

Create **Backend/.env** with one line (keep this file private):

```
GEMINI_API_KEY=
```

Run DB migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

**CORS/CSRF for local FE:** add your UI origins (port **9002** by default) in `Backend/NasaSite/settings.py`:

```python
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:9002",
    "http://localhost:9002",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:9002",
    "http://localhost:9002",
]
```

Restart the Django server after changes.

### 2) Frontend (Next.js)

**Prereqs:** Node 20+ and npm.

```bash
cd Frontend
npm install
```

Create **Frontend/.env.local** so the UI knows where the API lives:

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

Start the dev server (port **9002**):

```bash
npm run dev
```

Open the app: <http://127.0.0.1:9002>

---

## API

### Health (debug)

```
GET /api/ping/
```

Returns a simple JSON if the server is up.

### Fishing Forecast

```
POST /api/predict/fishing
Content-Type: application/json
```

**Body (any of these key variants are accepted):**
```json
{
  "lat": 50.4501,
  "lon": 30.5234,
  "date": "2025-10-20"
}
```
- `lat` can be `latitude`
- `lon` can be `lng` or `longitude`
- `date` optional; if omitted, a default horizon is used

**Successful response (shape):**
```json
{
  "ok": true,
  "used": { "lat": 50.4501, "lon": 30.5234, "horizon": 7, "target_date": "2025-10-20" },
  "csv_path": "Backend/NasaApp/ML/results_folder/fishing_evaluation_results_50.4501_30.5234_to_2025-10-20_20251005T083150Z.csv",
  "rows": [
    {
      "date": "2025-10-15",
      "air_temp_C": 13.6,
      "pressure_kPa": 101.4,
      "wind_speed_m_s": 4.8,
      "moon_phase": "Waxing Gibbous",
      "water_temp_C": 12.1,
      "rating": "good",
      "recommendations": "Best bite around dawn; moderate wind from NW…"
    }
  ]
}
```

**Error response example:**
```json
{
  "ok": false,
  "error": "ValueError",
  "message": "Bad coordinates",
  "trace": ["..."]
}
```

**cURL examples:**

- **Kyiv, with target date**
```bash
curl -s http://127.0.0.1:8000/api/predict/fishing   -H "Content-Type: application/json"   -d '{"lat":50.4501,"lon":30.5234,"date":"2025-10-20"}'
```

- **Kyiv, default horizon (no date)**
```bash
curl -s http://127.0.0.1:8000/api/predict/fishing   -H "Content-Type: application/json"   -d '{"latitude":50.4501,"longitude":30.5234}'
```

---

## Docker (optional)

If you have a `docker-compose.yml` for the backend (Django + Postgres), ensure the app listens on `0.0.0.0:8080` (compose port mapping `8080:8080`) and the frontend points to it:

```
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8080
```

Then start:
```bash
docker compose up --build
```

---

## ML Pipeline (High‑Level)

1. **Data load/cache:** `Fishing_parse_data_for_year.py` pulls historical series for the given coordinates; caches in `saved_coords.json` and `*_year_values_*.csv`.
2. **Forecast:** `arima_predict_fishing.py` / `arima.py` fit ARIMA for core weather variables; horizon is derived from requested date (API may extend horizon if the upstream provider exposes only data ≥3 days old).
3. **Post‑processing:** `main_fishing.py` merges day‑wise features, estimates water temperature, joins moon phase, and saves a combined CSV in `results_folder/`.
4. **Summaries:** `fishing_LLM_analyzer.py` can generate a concise recommendation + rating for each day (if the key is configured).

Outputs are persisted under:
- `Backend/NasaApp/ML/results_folder/*.csv`

---

## Troubleshooting

- **CORS in browser:** add `http://localhost:9002` and `http://127.0.0.1:9002` to both `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS`, then restart Django.
- **`fetch failed` from UI:** check `NEXT_PUBLIC_API_BASE` and that Django is up at `http://127.0.0.1:8000` (or your Docker port).
- **No rows in response:** the API will return a clear error; check the JSON `message` and server logs.

---

## Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-change`
3. Commit: `git commit -m "Describe change"`
4. Push: `git push origin feature/my-change`
5. Open a PR

---
