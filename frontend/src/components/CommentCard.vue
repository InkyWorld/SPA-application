<template>
  <div class="card" :style="{ marginLeft: depth * 20 + 'px' }">
    <header class="card-header">
      <div class="author">
        <strong class="name">{{ comment.user_name }}</strong>
        <span class="email">{{ comment.email }}</span>
      </div>
      <time class="date">{{ formatDate(comment.created_at) }}</time>
    </header>

    <div class="text" v-html="comment.text"></div>

    <div v-if="comment.image_url || comment.file_url" class="attachments">
      <figure v-if="comment.image_url && imgOk" class="photo">
        <img
          :src="comment.image_url"
          :alt="comment.image_name ?? 'attachment'"
          :title="comment.image_name ?? ''"
          loading="lazy"
          class="thumb"
          @click="openImage"
          @error="imgOk = false"
        />
        <figcaption :title="comment.image_name ?? ''">
          <a :href="comment.image_url" :download="comment.image_name ?? ''" class="file-link">
            ⬇ {{ comment.image_name ?? 'image' }}
          </a>
        </figcaption>
      </figure>
      <button
        v-if="comment.file_url"
        type="button"
        class="file-link file-txt"
        :title="comment.file_name ?? ''"
        @click="openTxt"
      >
        📄 {{ comment.file_name ?? 'Download TXT' }}
      </button>
    </div>

    <button v-if="auth.profile" type="button" class="reply-btn" @click="replying = !replying">
      {{ replying ? 'Cancel reply' : 'Reply' }}
    </button>

    <CommentForm
      v-if="replying && auth.profile"
      :parent-id="comment.id"
      compact
      @sent="onReplied"
    />

    <div class="replies">
      <CommentCard
        v-for="child in comment.replies"
        :key="child.id"
        :comment="child"
        :depth="depth + 1"
        @sent="$emit('sent')"
      />
    </div>

    <Teleport to="body">
      <div v-if="viewer" class="lightbox" @click="closeViewer">
        <img
          v-if="viewer.kind === 'image'"
          :src="comment.image_url ?? ''"
          :alt="comment.image_name ?? 'full size'"
          @click.stop
        />
        <div v-else class="txt-modal" @click.stop>
          <header>
            <strong>{{ comment.file_name ?? 'file.txt' }}</strong>
            <a :href="comment.file_url ?? ''" :download="comment.file_name ?? ''" class="file-link">⬇ Download</a>
          </header>
          <pre v-if="txtContent !== null">{{ txtContent }}</pre>
          <p v-else-if="txtError" class="txt-error">{{ txtError }}</p>
          <p v-else class="txt-loading">Loading…</p>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, withDefaults } from 'vue'
import type { CommentNode } from '../types/comment'
import { useAuth } from '../composables/useAuth'
import CommentForm from './CommentForm.vue'

const auth = useAuth()

const props = withDefaults(defineProps<{ comment: CommentNode; depth?: number }>(), { depth: 0 })
defineEmits<{ sent: [] }>()

const replying = ref(false)
const imgOk = ref(true)

type Viewer = { kind: 'image' } | { kind: 'text' } | null
const viewer = ref<Viewer>(null)
const txtContent = ref<string | null>(null)
const txtError = ref('')

function onReplied() {
  replying.value = false
}

function openImage() {
  viewer.value = { kind: 'image' }
}

async function openTxt() {
  viewer.value = { kind: 'text' }
  txtContent.value = null
  txtError.value = ''
  try {
    const res = await fetch(props.comment.file_url ?? '')
    if (!res.ok) throw new Error(String(res.status))
    txtContent.value = await res.text()
  } catch {
    txtError.value = 'Could not load the file.'
  }
}

function closeViewer() {
  viewer.value = null
  txtContent.value = null
  txtError.value = ''
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') closeViewer()
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 14px;
  margin: 10px 0;
  background: #fff;
  animation: fade-in 0.25s ease-out;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.author {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}

.name {
  font-size: 15px;
  color: #111827;
}

.email {
  font-size: 13px;
  color: #6b7280;
}

.date {
  font-size: 12px;
  color: #9ca3af;
  white-space: nowrap;
}

.text {
  font-size: 14px;
  line-height: 1.55;
  color: #1f2937;
  margin: 8px 0;
}

.text :deep(a) {
  color: #2563eb;
  text-decoration: none;
}

.text :deep(a:hover) {
  text-decoration: underline;
}

.text :deep(code) {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}

.attachments {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 10px 0;
}

.photo {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.photo figcaption {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-link {
  display: inline-block;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.thumb {
  max-width: 160px;
  max-height: 120px;
  border-radius: 6px;
  cursor: zoom-in;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid #e5e7eb;
}

.thumb:hover {
  transform: scale(1.03);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.15);
}

.file-link {
  font-family: inherit;
  font-size: 13px;
  color: #374151;
  text-decoration: none;
  padding: 4px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  cursor: pointer;
}

.file-link:hover {
  background: #f3f4f6;
}

button.file-link {
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.reply-btn {
  margin-top: 6px;
  padding: 5px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.reply-btn:hover {
  background: #f3f4f6;
  border-color: #9ca3af;
}

.replies {
  margin-top: 8px;
}

.lightbox {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.85);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: zoom-out;
  animation: fade-in 0.2s ease-out;
}

.lightbox img {
  max-width: 92vw;
  max-height: 92vh;
  border-radius: 10px;
  cursor: default;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.txt-modal {
  width: min(640px, 92vw);
  max-height: 84vh;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 10px;
  cursor: default;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.txt-modal header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid #e5e7eb;
  font-size: 14px;
}

.txt-modal pre {
  margin: 0;
  padding: 14px;
  overflow: auto;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.txt-loading,
.txt-error {
  padding: 20px 14px;
  font-size: 14px;
  color: #6b7280;
}

.txt-error {
  color: #dc2626;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
