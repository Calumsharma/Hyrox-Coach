from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import athletes, auth, exercises, recovery, stations, training, workouts
from app.db_bootstrap import ensure_schema_current
from app.seed_data import seed

app = FastAPI(title="S9 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(athletes.router)
app.include_router(stations.router)
app.include_router(training.router)
app.include_router(workouts.router)
app.include_router(exercises.router)
app.include_router(recovery.router)


@app.on_event("startup")
def on_startup():
    ensure_schema_current()
    seed.run()


@app.get("/health")
def health():
    return {"status": "ok"}
