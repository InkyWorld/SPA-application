<template>
  <div class="app">
    <header class="app-header">
      <h1>Comments</h1>
      <p class="subtitle">Share your thoughts</p>
      <div v-if="profile" class="userbar">
        <span>{{ profile.user_name }} ({{ profile.email }})</span>
        <button type="button" @click="auth.signOut()">Logout</button>
      </div>
    </header>

    <AuthPanel v-if="auth.ready && !profile" @done="reload" />

    <section v-if="profile" class="form-section">
      <CommentForm @sent="reload" />
    </section>

    <section class="list-section">
      <div class="toolbar">
        <label class="sort-label">Sort by:
          <select v-model="sortProxy">
            <option value="-created_at">Date ↓ (newest)</option>
            <option value="created_at">Date ↑ (oldest)</option>
            <option value="user_name">User Name ↑</option>
            <option value="-user_name">User Name ↓</option>
            <option value="email">E-mail ↑</option>
            <option value="-email">E-mail ↓</option>
          </select>
        </label>
        <span v-if="loading" class="loading">Loading...</span>
        <span v-else-if="loadError" class="load-error">{{ loadError }}</span>
      </div>

      <div v-if="items.length === 0 && !loading" class="empty">
        No comments yet. Be the first!
      </div>

      <CommentCard v-for="c in items" :key="c.id" :comment="c" @sent="reload" />

      <Pagination :page="page" :total-pages="totalPages" :total="total" @change="goPage" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import CommentCard from './components/CommentCard.vue'
import CommentForm from './components/CommentForm.vue'
import AuthPanel from './components/AuthPanel.vue'
import Pagination from './components/Pagination.vue'
import { useAuth } from './composables/useAuth'
import { useComments } from './composables/useComments'
import { PAGE_SIZE } from './api/comments'

const auth = useAuth()
const profile = computed(() => auth.profile.value)
const { items, total, page, sort, loading, error: loadError, load, setSort, setPage, connectLive } = useComments()

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const sortProxy = computed({
  get: () => sort.value,
  set: (v: string) => setSort(v),
})

let disconnect: (() => void) | null = null

function reload() {
  void load()
}

function goPage(next: number) {
  const clamped = Math.min(Math.max(1, next), totalPages.value)
  setPage(clamped)
  document.querySelector('.list-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(() => {
  void auth.restore()
  void load()
  disconnect = connectLive()
})

onUnmounted(() => disconnect?.())
</script>

<style>
* { box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: #f5f7fa;
  margin: 0;
  color: #1a1a2e;
}

.app {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 16px;
}

.app-header {
  text-align: center;
  margin-bottom: 24px;
}

.app-header h1 {
  margin: 0 0 4px;
  font-size: 28px;
  font-weight: 700;
  color: #16213e;
}

.subtitle {
  margin: 0;
  color: #6b7280;
  font-size: 14px;
}

.userbar {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
  font-size: 14px;
  color: #374151;
}

.userbar button {
  padding: 4px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
}

.form-section {
  margin-bottom: 24px;
}

.list-section {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.sort-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #374151;
}

.sort-label select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
}

.loading {
  font-size: 13px;
  color: #6b7280;
}

.load-error {
  font-size: 13px;
  color: #dc2626;
}

.empty {
  text-align: center;
  padding: 40px 16px;
  color: #9ca3af;
  font-size: 14px;
}

</style>
