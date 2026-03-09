import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ResearchLedger
from app.services.research_runtime_service import ResearchRuntimeService

router = APIRouter(prefix="/research-runtime")
logger = logging.getLogger("uvicorn.error")


@lru_cache(maxsize=1)
def get_research_runtime_service() -> ResearchRuntimeService:
    return ResearchRuntimeService()


@router.post("/run", response_model=AgentResult)
def run_research_runtime(
    task: AgentTaskEnvelope,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info(
        "[research-runtime] received run request task_id=%s session_id=%s task_type=%s",
        task.task_id,
        task.session_id,
        task.task_type,
    )
    return service.run_task(task)


@router.get("/ledger/{ledger_id}", response_model=ResearchLedger)
def read_research_ledger(
    ledger_id: str,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[research-runtime] received ledger read request ledger_id=%s", ledger_id)
    ledger = service.get_ledger(ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Research ledger not found")
    return ledger
