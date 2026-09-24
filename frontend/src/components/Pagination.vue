<template>
  <nav class="pager" aria-label="Comments pages">
    <button
      type="button"
      class="pager-btn"
      :disabled="page <= 1"
      @click="$emit('change', page - 1)"
    >
      ← Prev
    </button>
    <button
      v-for="(p, i) in pages"
      :key="i"
      type="button"
      class="pager-btn"
      :class="{ active: p === page, gap: p === '…' }"
      :disabled="p === '…' || p === page"
      @click="typeof p === 'number' && $emit('change', p)"
    >
      {{ p }}
    </button>
    <button
      type="button"
      class="pager-btn"
      :disabled="page >= totalPages"
      @click="$emit('change', page + 1)"
    >
      Next →
    </button>
    <span class="page-info">Page {{ page }} / {{ totalPages }} · {{ total }} total</span>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ page: number; totalPages: number; total: number }>()
defineEmits<{ change: [page: number] }>()

type Slot = number | '…'

const pages = computed<Slot[]>(() => {
  const current = props.page
  const last = Math.max(1, props.totalPages)
  const keep = new Set([1, last, current - 2, current - 1, current, current + 1, current + 2])
  const nums = [...keep].filter((n) => n >= 1 && n <= last).sort((a, b) => a - b)
  const out: Slot[] = []
  let prev = 0
  for (const n of nums) {
    if (n - prev > 1) out.push('…')
    out.push(n)
    prev = n
  }
  return out
})
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
}

.pager-btn {
  min-width: 36px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.15s ease;
}

.pager-btn:hover:not(:disabled) {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.pager-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pager-btn.active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
  opacity: 1;
}

.pager-btn.gap {
  border: none;
  background: none;
  min-width: auto;
  padding: 8px 2px;
}

.page-info {
  width: 100%;
  text-align: center;
  font-size: 13px;
  color: #6b7280;
}
</style>
