import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.routes.research_runtime import get_research_runtime_service
from app.schemas.agent_tasks import (
    AgentTaskArtifactsResponse,
    AgentTaskCreateRequest,
    AgentTaskEventsResponse,
    AgentTaskStatusResponse,
)
from app.services.research_runtime_service import ResearchRuntimeService

router = APIRouter(prefix="/agent/tasks")
logger = logging.getLogger("uvicorn.error")


@router.post("", response_model=AgentTaskStatusResponse, status_code=status.HTTP_201_CREATED)
def create_agent_task(
    request: AgentTaskCreateRequest,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info(
        "[agent-tasks] create task request task_type=%s task_id=%s session_id=%s",
        request.task_type,
        request.task_id,
        request.session_id,
    )
    return service.create_agent_task(request)


@router.get("/{run_id}", response_model=AgentTaskStatusResponse)
def read_agent_task(
    run_id: str,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[agent-tasks] read task status run_id=%s", run_id)
    status_payload = service.get_task_status(run_id)
    if status_payload is None:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return status_payload


@router.get("/{run_id}/events", response_model=AgentTaskEventsResponse)
def read_agent_task_events(
    run_id: str,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[agent-tasks] read task events run_id=%s", run_id)
    events_payload = service.get_task_events(run_id)
    if events_payload is None:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return events_payload


@router.get("/{run_id}/artifacts", response_model=AgentTaskArtifactsResponse)
def read_agent_task_artifacts(
    run_id: str,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[agent-tasks] read task artifacts run_id=%s", run_id)
    artifacts_payload = service.get_task_artifacts(run_id)
    if artifacts_payload is None:
        raise HTTPException(status_code=404, detail="Agent task not found")
    return artifacts_payload
