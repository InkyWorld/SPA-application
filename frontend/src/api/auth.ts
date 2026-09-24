import { api, clearTokens, readTokens, writeTokens } from './client'

export interface AuthProfile {
  id: number
  user_name: string
  email: string
}

export interface AuthPayload {
  user_name: string
  email: string
  password: string
}

export function register(payload: AuthPayload) {
  return api.post<AuthProfile>('/register/', payload)
}

export function login(email: string, password: string) {
  return api.post<{ access: string; refresh: string }>('/token/', { email, password })
}

export function fetchMe() {
  return api.get<AuthProfile>('/me/')
}

export function saveSession(access: string, refresh: string): void {
  writeTokens(access, refresh)
}

export function dropSession(): void {
  clearTokens()
}

export function hasSession(): boolean {
  return readTokens().access !== null
}
