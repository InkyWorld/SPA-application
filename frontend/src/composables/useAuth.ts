import { ref } from 'vue'
import { dropSession, fetchMe, hasSession, login, register, saveSession } from '../api/auth'

export interface AuthProfile {
  id: number
  user_name: string
  email: string
}

// Module-level state: every useAuth() caller shares one session.
const profile = ref<AuthProfile | null>(null)
const ready = ref(false)
const error = ref('')

/** Auth session: tokens in localStorage, profile in memory (shared). */
export function useAuth() {
  async function restore() {
    error.value = ''
    if (!hasSession()) {
      ready.value = true
      return
    }
    try {
      const { data } = await fetchMe()
      profile.value = data
    } catch {
      dropSession()
      profile.value = null
    } finally {
      ready.value = true
    }
  }

  async function signUp(user_name: string, email: string, password: string) {
    error.value = ''
    await register({ user_name, email, password })
    await signIn(email, password)
  }

  async function signIn(email: string, password: string) {
    error.value = ''
    try {
      const { data } = await login(email, password)
      saveSession(data.access, data.refresh)
      const me = await fetchMe()
      profile.value = me.data
    } catch {
      error.value = 'Invalid email or password.'
      throw new Error(error.value)
    }
  }

  function signOut() {
    dropSession()
    profile.value = null
  }

  return { profile, ready, error, restore, signUp, signIn, signOut }
}
