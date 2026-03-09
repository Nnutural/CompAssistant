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

export async function createAgentTask(
  request: AgentTaskCreateRequest,
): Promise<AgentTaskStatusResponse> {
  const response = await agentApi.post<AgentTaskStatusResponse>('/agent/tasks', request)
  return response.data
}

export async function getAgentTaskStatus(runId: string): Promise<AgentTaskStatusResponse> {
  const response = await agentApi.get<AgentTaskStatusResponse>(`/agent/tasks/${runId}`)
  return response.data
}

export async function getAgentTaskEvents(runId: string): Promise<AgentTaskEventsResponse> {
  const response = await agentApi.get<AgentTaskEventsResponse>(`/agent/tasks/${runId}/events`)
  return response.data
}

export async function getAgentTaskArtifacts(runId: string): Promise<AgentTaskArtifactsResponse> {
  const response = await agentApi.get<AgentTaskArtifactsResponse>(`/agent/tasks/${runId}/artifacts`)
  return response.data
}

export async function listAgentTasks(params?: {
  status?: string
  task_type?: string
  limit?: number
  offset?: number
}): Promise<AgentTaskHistoryResponse> {
  const response = await agentApi.get<AgentTaskHistoryResponse>('/agent/tasks', { params })
  return response.data
}

export async function retryAgentTask(runId: string): Promise<AgentTaskRetryResponse> {
  const response = await agentApi.post<AgentTaskRetryResponse>(`/agent/tasks/${runId}/retry`)
  return response.data
}

export async function cancelAgentTask(
  runId: string,
  request: AgentTaskCancelRequest,
): Promise<AgentTaskControlResponse> {
  const response = await agentApi.post<AgentTaskControlResponse>(`/agent/tasks/${runId}/cancel`, request)
  return response.data
}

export async function reviewAgentTask(
  runId: string,
  request: AgentTaskReviewRequest,
): Promise<AgentTaskControlResponse> {
  const response = await agentApi.post<AgentTaskControlResponse>(`/agent/tasks/${runId}/review`, request)
  return response.data
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
