import { apiRequest } from './http'

export type ClanMember = {
  user_id: string
  name: string
  email: string
  joined_at: string
}

export type Clan = {
  id: string
  name: string
  created_by_id: string
  created_at: string
  member_count: number
}

export type ClanDetail = {
  id: string
  name: string
  created_by_id: string
  created_at: string
  members: ClanMember[]
}

export const clansApi = {
  list: () => apiRequest<Clan[]>('/clans'),
  listMine: () => apiRequest<Clan[]>('/clans?mine=true'),
  get: (clanId: string) => apiRequest<ClanDetail>(`/clans/${encodeURIComponent(clanId)}`),
  create: (name: string) =>
    apiRequest<ClanDetail>('/clans', { method: 'POST', body: JSON.stringify({ name }) }),
  addMember: (clanId: string, email: string) =>
    apiRequest<ClanDetail>(`/clans/${encodeURIComponent(clanId)}/members`, {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),
  removeMember: (clanId: string, userId: string) =>
    apiRequest<ClanDetail>(
      `/clans/${encodeURIComponent(clanId)}/members/${encodeURIComponent(userId)}`,
      { method: 'DELETE' },
    ),
}
