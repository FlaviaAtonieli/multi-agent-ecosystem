import { apiRequest } from './http'

export type ClanMember = {
  user_id: string
  name: string
  email: string
  joined_at: string
}

export type ClanPolicy = 'ALL_MEMBERS' | 'OWNER_ONLY'

export type ClanSettings = {
  is_open: boolean
  skills_policy: ClanPolicy
  members_policy: ClanPolicy
}

export type Clan = ClanSettings & {
  id: string
  name: string
  created_by_id: string
  created_at: string
  member_count: number
}

export type ClanDetail = ClanSettings & {
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
  create: (name: string, settings: ClanSettings) =>
    apiRequest<ClanDetail>('/clans', { method: 'POST', body: JSON.stringify({ name, ...settings }) }),
  updateSettings: (clanId: string, settings: Partial<ClanSettings & { name: string }>) =>
    apiRequest<ClanDetail>(`/clans/${encodeURIComponent(clanId)}/settings`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    }),
  join: (clanId: string) =>
    apiRequest<ClanDetail>(`/clans/${encodeURIComponent(clanId)}/join`, { method: 'POST' }),
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

/** Espelha clan_service.ensure_can_register_skills: a lista de clãs vem de
 * listMine (o usuário já é membro), então basta checar skills_policy. */
export function canRegisterSkillsIn(clan: Clan, user: { id: string } | null | undefined): boolean {
  if (!user) return false
  return clan.created_by_id === user.id || clan.skills_policy === 'ALL_MEMBERS'
}
