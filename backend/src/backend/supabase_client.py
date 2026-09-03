from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def get_engine_uuid(engine_id: str):
    response = (
        supabase
        .table("engines")
        .select("id")
        .eq("engine_id", engine_id)
        .execute()
    )

    if response.data:
        return response.data[0]["id"]

    response = (
        supabase
        .table("engines")
        .insert({
            "engine_id": engine_id,
        })
        .execute()
    )

    return response.data[0]["id"]


def get_mission_uuid(
    mission_id: str,
    engine_uuid: str,
):
    response = (
        supabase
        .table("missions")
        .select("id")
        .eq("mission_id", mission_id)
        .execute()
    )

    if response.data:
        return response.data[0]["id"]

    response = (
        supabase
        .table("missions")
        .insert({
            "mission_id": mission_id,
            "engine_id": engine_uuid,
        })
        .execute()
    )

    return response.data[0]["id"]


def insert_telemetry(data: dict):
    response = (
        supabase
        .table("telemetry")
        .insert(data)
        .execute()
    )

    return response.data
