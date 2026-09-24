<template>
  <div class="toolbar" role="toolbar" aria-label="Text formatting">
    <button
      v-for="tag in tags"
      :key="tag.label"
      type="button"
      class="tag-btn"
      :title="tag.title"
      @click="$emit('insert', tag)"
    >
      {{ tag.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
export interface BbTag {
  label: string
  open: string
  close: string
  title: string
}

const tags: BbTag[] = [
  { label: '[i]', open: '<i>', close: '</i>', title: 'Italic' },
  { label: '[strong]', open: '<strong>', close: '</strong>', title: 'Bold' },
  { label: '[code]', open: '<code>', close: '</code>', title: 'Code' },
  { label: '[a]', open: '<a href="" title="">', close: '</a>', title: 'Link' },
]

defineEmits<{ insert: [tag: BbTag] }>()
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 6px;
  padding: 6px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 8px;
}

.tag-btn {
  min-width: 32px;
  height: 28px;
  padding: 0 8px;
  border: 1px solid transparent;
  border-radius: 4px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.tag-btn:hover {
  background: #e0e7ff;
  border-color: #c7d2fe;
  color: #2563eb;
}

.tag-btn:active {
  transform: translateY(1px);
}
</style>
