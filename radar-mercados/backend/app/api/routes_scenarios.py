from fastapi import APIRouter

from app.services import scenario_service

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios() -> list[dict]:
    return scenario_service.get_scenarios()
