import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

const ACCESS_KEY = 'comments.access'
const REFRESH_KEY = 'comments.refresh'

export function readTokens(): { access: string | null; refresh: string | null } {
  return {
    access: localStorage.getItem(ACCESS_KEY),
    refresh: localStorage.getItem(REFRESH_KEY),
  }
}

export function writeTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

let refreshing: Promise<string | null> | null = null

async function refreshAccess(): Promise<string | null> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const { refresh } = readTokens()
        if (!refresh) return null
        const { data } = await axios.post<{ access: string }>('/api/token/refresh/', { refresh })
        writeTokens(data.access, refresh)
        return data.access
      } catch {
        clearTokens()
        return null
      } finally {
        refreshing = null
      }
    })()
  }
  return refreshing
}

api.interceptors.request.use((config) => {
  const { access } = readTokens()
  if (access) config.headers.set('Authorization', `Bearer ${access}`)
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true
      const access = await refreshAccess()
      if (access) {
        original.headers.set('Authorization', `Bearer ${access}`)
        return api(original)
      }
    }
    return Promise.reject(error)
  },
)
