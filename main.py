
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Phone Deal Finder",
    description="Personalised UK mobile phone deal research.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "name": "AI Phone Deal Finder",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/deals")
def get_deals():
    return {
        "status": "ok",
        "last_updated": None,
        "count": 0,
        "deals": [],
        "message": (
            "The deal database is ready for the next development stage. "
            "No live offers have been added yet."
        ),
    }
