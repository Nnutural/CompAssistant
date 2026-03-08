from fastapi import APIRouter, Depends, HTTPException

from app.schemas.research_runtime import AgentResult, AgentTaskEnvelope, ResearchLedger
from app.services.research_runtime_service import ResearchRuntimeService

router = APIRouter(prefix="/research-runtime")


def get_research_runtime_service() -> ResearchRuntimeService:
    return ResearchRuntimeService()


@router.post("/run", response_model=AgentResult)
def run_research_runtime(
    task: AgentTaskEnvelope,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    return service.run_task(task)


@router.get("/ledger/{ledger_id}", response_model=ResearchLedger)
def read_research_ledger(
    ledger_id: str,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    ledger = service.get_ledger(ledger_id)
    if ledger is None:
        raise HTTPException(status_code=404, detail="Research ledger not found")
    return ledger