<template>
  <div class="auth">
    <div class="tabs">
      <button type="button" :class="{ active: mode === 'login' }" @click="mode = 'login'">Login</button>
      <button type="button" :class="{ active: mode === 'register' }" @click="mode = 'register'">Register</button>
    </div>
    <form @submit.prevent="submit">
      <input
        v-if="mode === 'register'"
        v-model="userName"
        placeholder="User Name*"
        pattern="[A-Za-z0-9]+"
        maxlength="50"
        required
      />
      <input v-model="email" type="email" placeholder="E-mail*" required />
      <input v-model="password" type="password" placeholder="Password*" minlength="8" required />
      <button type="submit" :disabled="busy">{{ busy ? '…' : mode === 'login' ? 'Login' : 'Register' }}</button>
    </form>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuth } from '../composables/useAuth'

const emit = defineEmits<{ done: [] }>()
const auth = useAuth()

const mode = ref<'login' | 'register'>('login')
const userName = ref('')
const email = ref('')
const password = ref('')
const busy = ref(false)
const error = ref('')

async function submit() {
  busy.value = true
  error.value = ''
  try {
    if (mode.value === 'login') {
      await auth.signIn(email.value, password.value)
    } else {
      await auth.signUp(userName.value, email.value, password.value)
    }
    emit('done')
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Auth failed.'
  } finally {
    busy.value = false
  }
}
</script>

<style scoped>
.auth {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 24px;
}
.tabs { display: flex; gap: 8px; margin-bottom: 12px; }
.tabs button {
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
}
.tabs button.active { background: #2563eb; border-color: #2563eb; color: #fff; }
form { display: flex; gap: 8px; flex-wrap: wrap; }
input {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
}
button[type='submit'] {
  padding: 8px 18px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
button:disabled { opacity: 0.6; }
.error { color: #dc2626; font-size: 13px; }
</style>
