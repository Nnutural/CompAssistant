import axios from 'axios'

import type {
  AgentTaskArtifactsResponse,
  AgentTaskCreateRequest,
  AgentTaskEventsResponse,
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

export const agentTaskApi = {
  createTask: createAgentTask,
  getTaskStatus: getAgentTaskStatus,
  getEvents: getAgentTaskEvents,
  getArtifacts: getAgentTaskArtifacts,
}
