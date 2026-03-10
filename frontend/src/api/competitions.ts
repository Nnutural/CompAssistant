import axios from 'axios'

export interface CompetitionOption {
  id: number
  name: string
  field?: string | null
  deadline?: string | null
  difficulty?: string | null
  level?: string | null
}

const competitionsApi = axios.create({
  baseURL: '/api',
})

export async function listCompetitions(): Promise<CompetitionOption[]> {
  const response = await competitionsApi.get<CompetitionOption[]>('/competitions')
  return response.data
}

export const competitionsApiClient = {
  listCompetitions,
}
