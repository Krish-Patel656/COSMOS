# COSMOS — Interactive 3D Exoplanet Explorer

COSMOS is a full-stack astronomy platform: real NASA exoplanet data, explainable habitability and Earth-similarity scores, and immersive Three.js views of stars, orbits and worlds.

It is designed to feel less like a database and more like a scientific universe. Search TRAPPIST-1, fly into the system, pick a planet, and read *why* it scored the way it did.

## What you can do

- Search stars and exoplanets, then open a 3D system with orbits and habitable-zone rings
- Inspect radius, mass, temperature, period, distance, star type and discovery metadata
- Read **Earth Similarity** and **habitability** scores with a factor-by-factor breakdown
- Filter the explorer by distance, temperature, size, star type, HZ membership and scores
- Compare worlds side by side (try Earth, TRAPPIST-1 e, Kepler-186 f)
- Tune a hypothetical planet in the simulator and watch the same engine recompute live
- Create an account to favourite worlds, build collections and save comparisons
- Switch to flat mode, reduce motion, or drop render quality from the header

Surfaces are always labelled as **artistic renderings**. No exoplanet has been imaged.

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, TypeScript, React Three Fiber, Tailwind CSS |
| Backend | FastAPI, Python 3.11+, SQLAlchemy |
| Data | NASA Exoplanet Archive TAP (`pscomppars`) + Solar System references |
| Persistence | SQLite by default; PostgreSQL and Redis optional |

## Quick start

You need **Python 3.11+** and **Node 20+**.

```bash
# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python -m app.ingest          # NASA archive, or notable systems if offline
uvicorn app.main:app --reload --port 8000

# Frontend (another terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). API docs live at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

The first ingest queries NASA (or `--curated` for an offline notable-systems set plus the Solar System). Subsequent runs reuse `backend/app/data/exoplanet_snapshot.json.gz` when present.

```bash
python -m app.ingest --curated   # offline: TRAPPIST-1, Proxima, Kepler-186, …
python -m app.ingest --refresh   # live NASA Exoplanet Archive
```

## Optional PostgreSQL and Redis

```bash
docker compose up -d
```

Then in `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://cosmos:cosmos@localhost:5432/cosmos
REDIS_URL=redis://localhost:6379/0
```

Re-run ingest after switching databases.

## Tests

```bash
cd backend && pytest
cd frontend && npm test && npm run typecheck
```

## Scoring, in one paragraph

Habitable-zone edges follow Kopparapu et al. (2013). The Earth Similarity Index follows Schulze-Makuch et al. (2011). Habitability is a weighted geometric mean of temperature, size, mass/gravity, zone position, eccentricity, insolation and host-star properties. Missing inputs are dropped, not invented; confidence reports how much of the score rested on measurements. Full notes: [docs/METHODOLOGY.md](docs/METHODOLOGY.md) and `/methodology` in the app.

## Suggested tour

1. Home → **Enter TRAPPIST-1**
2. Select planet **e** → open the dossier and read the breakdown
3. Stellar map → click Proxima Cen
4. Compare Earth / TRAPPIST-1 e / Kepler-186 f
5. Simulator → load the Venus preset
