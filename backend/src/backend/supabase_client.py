from __future__ import annotations

import os
from typing import Any, Optional

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


# ============================================================
# CONFIG
# ============================================================

SUPABASE_URL = (
    os.getenv(
        "SUPABASE_URL",
        "",
    ).strip()
)

SUPABASE_KEY = (
    os.getenv(
        "SUPABASE_KEY",
        "",
    ).strip()
)


# ============================================================
# CLIENT
# ============================================================

_supabase: Optional[Client] = None
_initialization_attempted = False


def supabase_available() -> bool:
    """
    Return True only when Supabase credentials are configured
    and the client can be initialized.
    """

    global _supabase
    global _initialization_attempted

    if _supabase is not None:
        return True

    if _initialization_attempted:
        return False

    _initialization_attempted = True

    if not SUPABASE_URL or not SUPABASE_KEY:

        print(
            "[SUPABASE] Credentials not configured."
        )

        print(
            "[SUPABASE] Running without database persistence."
        )

        return False

    try:

        _supabase = create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
        )

        print(
            "[SUPABASE] Client initialized."
        )

        return True

    except Exception as exc:

        print(
            "[SUPABASE] Initialization failed:"
            f" {exc}"
        )

        return False


def _client() -> Client:
    if not supabase_available() or _supabase is None:

        raise RuntimeError(
            "Supabase is not configured or unavailable."
        )

    return _supabase


# ============================================================
# ENGINE
# ============================================================

def get_engine_uuid(
    engine_id: str,
) -> Optional[str]:

    client = _client()

    response = (
        client
        .table("engines")
        .select("id")
        .eq(
            "engine_id",
            engine_id,
        )
        .limit(1)
        .execute()
    )

    if response.data:

        return response.data[0]["id"]

    response = (
        client
        .table("engines")
        .insert(
            {
                "engine_id": engine_id,
            }
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            f"Failed to create engine: {engine_id}"
        )

    return response.data[0]["id"]


# ============================================================
# MISSION
# ============================================================

def get_mission_uuid(
    mission_id: str,
    engine_uuid: str,
) -> Optional[str]:

    client = _client()

    response = (
        client
        .table("missions")
        .select("id")
        .eq(
            "mission_id",
            mission_id,
        )
        .limit(1)
        .execute()
    )

    if response.data:

        return response.data[0]["id"]

    response = (
        client
        .table("missions")
        .insert(
            {
                "mission_id": mission_id,
                "engine_id": engine_uuid,
            }
        )
        .execute()
    )

    if not response.data:

        raise RuntimeError(
            f"Failed to create mission: {mission_id}"
        )

    return response.data[0]["id"]


# ============================================================
# TELEMETRY
# ============================================================

def insert_telemetry(
    data: dict[str, Any],
) -> list[dict[str, Any]]:

    client = _client()

    response = (
        client
        .table("telemetry")
        .insert(data)
        .execute()
    )

    return response.data or []