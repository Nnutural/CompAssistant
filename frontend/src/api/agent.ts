import axios from 'axios'

import type {
  AgentTaskArtifactsResponse,
  AgentTaskCancelRequest,
  AgentTaskControlResponse,
  AgentTaskCreateRequest,
  AgentTaskEventsResponse,
  AgentTaskHistoryResponse,
  AgentTaskRetryResponse,
  AgentTaskReviewRequest,
  AgentTaskStatusResponse,
} from '../types/agent'

const agentApi = axios.create({
  baseURL: '/api',
})

agentApi.interceptors.response.use(
  (response) => response,
  (error: unknown) => Promise.reject(normalizeAgentApiError(error)),
)

export async function createAgentTask(request: AgentTaskCreateRequest): Promise<AgentTaskStatusResponse> {
  return (await agentApi.post<AgentTaskStatusResponse>('/agent/tasks', request)).data
}

export async function getAgentTaskStatus(runId: string): Promise<AgentTaskStatusResponse> {
  return (await agentApi.get<AgentTaskStatusResponse>(`/agent/tasks/${runId}`)).data
}

export async function getAgentTaskEvents(runId: string): Promise<AgentTaskEventsResponse> {
  return (await agentApi.get<AgentTaskEventsResponse>(`/agent/tasks/${runId}/events`)).data
}

export async function getAgentTaskArtifacts(runId: string): Promise<AgentTaskArtifactsResponse> {
  return (await agentApi.get<AgentTaskArtifactsResponse>(`/agent/tasks/${runId}/artifacts`)).data
}

export async function listAgentTasks(params?: {
  status?: string
  task_type?: string
  limit?: number
  offset?: number
}): Promise<AgentTaskHistoryResponse> {
  return (await agentApi.get<AgentTaskHistoryResponse>('/agent/tasks', { params })).data
}

export async function retryAgentTask(runId: string): Promise<AgentTaskRetryResponse> {
  return (await agentApi.post<AgentTaskRetryResponse>(`/agent/tasks/${runId}/retry`)).data
}

export async function cancelAgentTask(
  runId: string,
  request: AgentTaskCancelRequest,
): Promise<AgentTaskControlResponse> {
  return (await agentApi.post<AgentTaskControlResponse>(`/agent/tasks/${runId}/cancel`, request)).data
}

export async function reviewAgentTask(
  runId: string,
  request: AgentTaskReviewRequest,
): Promise<AgentTaskControlResponse> {
  return (await agentApi.post<AgentTaskControlResponse>(`/agent/tasks/${runId}/review`, request)).data
}

export const agentTaskApi = {
  createTask: createAgentTask,
  getTaskStatus: getAgentTaskStatus,
  getEvents: getAgentTaskEvents,
  getArtifacts: getAgentTaskArtifacts,
  listTasks: listAgentTasks,
  retryTask: retryAgentTask,
  cancelTask: cancelAgentTask,
  reviewTask: reviewAgentTask,
}

function normalizeAgentApiError(error: unknown): Error {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error : new Error('未知请求错误。')
  }

  const detail = error.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) {
    return new Error(detail)
  }

  if (detail && typeof detail === 'object') {
    return new Error(JSON.stringify(detail))
  }

  if (typeof error.message === 'string' && error.message.trim()) {
    return new Error(error.message)
  }

  return new Error('请求失败。')
}
