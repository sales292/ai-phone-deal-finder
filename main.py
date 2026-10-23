
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import psycopg
from fastapi import FastAPI, HTTPException
from psycopg.rows import dict_row


def get_database_url():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return url


def initialise_database():
    with psycopg.connect(get_database_url()) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                id BIGSERIAL PRIMARY KEY,
                phone_brand TEXT NOT NULL DEFAULT 'Apple',
                model TEXT NOT NULL,
                storage_gb INTEGER,
                deal_type TEXT NOT NULL
                    CHECK (deal_type IN ('sim_free', 'contract')),
                retailer TEXT NOT NULL,
                product_url TEXT NOT NULL,
                upfront_price NUMERIC(10, 2),
                monthly_price NUMERIC(10, 2),
                contract_months INTEGER,
                data_allowance_gb NUMERIC(10, 2),
                extra_fees NUMERIC(10, 2) NOT NULL DEFAULT 0,
                total_cost NUMERIC(10, 2),
                last_checked TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                active BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)
        connection.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Keep the API available even if the database is temporarily unavailable.
    try:
        initialise_database()
        app.state.database_ready = True
    except Exception as exc:
        print(f"Database initialisation failed: {exc}")
        app.state.database_ready = False

    yield


app = FastAPI(
    title="AI Phone Deal Finder",
    description="Personalised UK mobile phone deal research.",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {
        "name": "AI Phone Deal Finder",
        "status": "running",
        "version": "0.2.0",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/deals")
def get_deals():
    if not getattr(app.state, "database_ready", False):
        raise HTTPException(
            status_code=503,
            detail="Deal database is not currently available.",
        )

    try:
        with psycopg.connect(
            get_database_url(),
            row_factory=dict_row,
        ) as connection:
            rows = connection.execute("""
                SELECT *
                FROM deals
                WHERE active = TRUE
                ORDER BY updated_at DESC
            """).fetchall()

        deals = []
        for row in rows:
            item = dict(row)
            for key, value in item.items():
                if hasattr(value, "isoformat"):
                    item[key] = value.isoformat()
                elif value is not None and key in {
                    "upfront_price",
                    "monthly_price",
                    "data_allowance_gb",
                    "extra_fees",
                    "total_cost",
                }:
                    item[key] = float(value)
            deals.append(item)

        return {
            "status": "ok",
            "last_updated": (
                datetime.now(timezone.utc).isoformat()
                if deals else None
            ),
            "count": len(deals),
            "deals": deals,
            "message": (
                "Offers loaded from the database."
                if deals else
                "No offers have been added yet."
            ),
        }

    except Exception as exc:
        print(f"Could not retrieve deals: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve deals from the database.",
        ) from exc
