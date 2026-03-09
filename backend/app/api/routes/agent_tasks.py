import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.routes.research_runtime import get_research_runtime_service
from app.schemas.agent_tasks import (
    AgentTaskArtifactsResponse,
    AgentTaskCancelRequest,
    AgentTaskControlResponse,
    AgentTaskCreateRequest,
    AgentTaskEventsResponse,
    AgentTaskHistoryResponse,
    AgentTaskRetryResponse,
    AgentTaskReviewRequest,
    AgentTaskStatusResponse,
)
from app.services.research_runtime_service import ResearchRuntimeService, TaskConflictError, TaskControlError

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
    try:
        return service.create_agent_task(request)
    except TaskConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=AgentTaskHistoryResponse)
def list_agent_tasks(
    status_filter: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info(
        "[agent-tasks] list tasks status=%s task_type=%s limit=%s offset=%s",
        status_filter,
        task_type,
        limit,
        offset,
    )
    return service.list_agent_tasks(
        status_filter=status_filter,
        task_type_filter=task_type,
        limit=limit,
        offset=offset,
    )


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


@router.post("/{run_id}/retry", response_model=AgentTaskRetryResponse)
def retry_agent_task(
    run_id: str,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[agent-tasks] retry task run_id=%s", run_id)
    try:
        return service.retry_agent_task(run_id)
    except TaskControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{run_id}/cancel", response_model=AgentTaskControlResponse)
def cancel_agent_task(
    run_id: str,
    request: AgentTaskCancelRequest,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[agent-tasks] cancel task run_id=%s", run_id)
    try:
        return service.cancel_agent_task(run_id, request)
    except TaskControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/{run_id}/review", response_model=AgentTaskControlResponse)
def review_agent_task(
    run_id: str,
    request: AgentTaskReviewRequest,
    service: ResearchRuntimeService = Depends(get_research_runtime_service),
):
    logger.info("[agent-tasks] review task run_id=%s decision=%s", run_id, request.decision)
    try:
        return service.review_agent_task(run_id, request)
    except TaskControlError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
