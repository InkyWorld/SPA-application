<template>
  <form class="comment-form" @submit.prevent="submit">
    <div class="field-row">
      <div class="field">
        <label for="home_page">Home page</label>
        <input
          id="home_page"
          v-model="form.home_page"
          type="url"
          placeholder="https://example.com"
        />
      </div>
    </div>

    <div class="field">
      <label>Text <span class="required">*</span> <span class="hint">(select text and click a style button)</span></label>
      <BbToolbar @insert="insertTag" />
      <textarea
        ref="textRef"
        v-model="form.text"
        placeholder="Write your comment here... Allowed tags: i, strong, code, a"
        required
        rows="4"
      ></textarea>
      <div v-if="previewHtml" class="preview" v-html="previewHtml"></div>
      <div v-else-if="previewError" class="preview preview-error">{{ previewError }}</div>
    </div>

    <div class="field">
      <label>Attachment</label>
      <div class="file-inputs">
        <div class="file-pill">
          <input
            id="attachment_input"
            type="file"
            accept=".jpg,.jpeg,.png,.gif,.txt"
            @change="onFile"
          />
          <label for="attachment_input" class="file-label">📎 Image or TXT (≤100KB)</label>
          <span v-if="attachedName" class="file-name">{{ attachedName }}</span>
        </div>
      </div>
    </div>

    <CaptchaField v-model="form.captcha_value" :image="captcha.image.value" @refresh="captcha.refresh()" />

    <div class="actions">
      <button type="submit" :disabled="sending" class="btn-primary">
        {{ sending ? 'Sending...' : 'Send' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </form>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { createComment, previewText } from '../api/comments'
import { useCaptcha } from '../composables/useCaptcha'
import BbToolbar, { type BbTag } from './BbToolbar.vue'
import CaptchaField from './CaptchaField.vue'

const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif']
const PREVIEW_DEBOUNCE_MS = 400

const props = withDefaults(defineProps<{ parentId?: number | null; compact?: boolean }>(), {
  parentId: null,
  compact: false,
})
const emit = defineEmits<{ sent: [] }>()

const form = reactive({
  home_page: '', text: '',
  captcha_value: '', attachment: null as File | null,
})
const captcha = useCaptcha()
const error = ref('')
const sending = ref(false)
const textRef = ref<HTMLTextAreaElement | null>(null)
const previewHtml = ref('')
const previewError = ref('')
let previewTimer: number | undefined

onMounted(() => void captcha.refresh())
onUnmounted(() => window.clearTimeout(previewTimer))

// Live preview without reload: debounced server-side sanitized HTML,
// so unsanitized markup (e.g. <img onerror>) never hits v-html.
watch(
  () => form.text,
  (text) => {
    window.clearTimeout(previewTimer)
    previewError.value = ''
    if (!text.trim()) {
      previewHtml.value = ''
      return
    }
    previewTimer = window.setTimeout(async () => {
      try {
        const { data } = await previewText(text)
        previewHtml.value = data.html
      } catch {
        previewHtml.value = ''
        previewError.value = 'Preview unavailable: check unclosed tags.'
      }
    }, PREVIEW_DEBOUNCE_MS)
  },
)

function insertTag(tag: BbTag) {
  const el = textRef.value
  if (!el) return
  el.focus()
  const start = el.selectionStart ?? 0
  const end = el.selectionEnd ?? 0
  const before = form.text.slice(0, start)
  const selected = form.text.slice(start, end)
  const after = form.text.slice(end)
  const replacement = `${tag.open}${selected}${tag.close}`
  form.text = `${before}${replacement}${after}`

  const newPos = start + tag.open.length + selected.length
  el.setSelectionRange(newPos, newPos)
}

function validateClient(): string | null {
  // Author comes from the JWT profile; only text and files are checked here.
  if (!form.text.trim()) return 'Text is required.'
  if (
    form.attachment?.name.toLowerCase().endsWith('.txt') &&
    form.attachment.size > 100 * 1024
  )
    return 'TXT must be <= 100 kB.'
  return null
}

async function submit() {
  error.value = ''
  const clientError = validateClient()
  if (clientError) { error.value = clientError; return }
  sending.value = true
  try {
    await createComment({
      home_page: form.home_page || undefined, text: form.text,
      parent_id: props.parentId, file: form.attachment,
      captcha_key: captcha.key.value, captcha_value: form.captcha_value,
    })
    form.home_page = ''
    form.text = ''
    form.captcha_value = ''
    form.attachment = null
    error.value = ''
    await captcha.refresh()
    emit('sent')
  } catch {
    error.value = 'Send failed. Check fields + CAPTCHA. CAPTCHA is one-time use — it was refreshed.'
    await captcha.refresh()
  } finally {
    sending.value = false
  }
}

function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0] ?? null
  form.attachment = null
  if (!file) return
  const lower = file.name.toLowerCase()
  const ok = IMAGE_EXTS.some((ext) => lower.endsWith(ext)) || lower.endsWith('.txt')
  if (!ok) {
    error.value = 'Only JPG/PNG/GIF images or TXT files are allowed.'
    input.value = ''
    return
  }
  form.attachment = file
}

const attachedName = computed(() => form.attachment?.name ?? '')
</script>

<style scoped>
.comment-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: #ffffff;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.field-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.required {
  color: #ef4444;
}

.hint {
  font-weight: 400;
  color: #9ca3af;
  font-size: 12px;
}

input[type="text"],
input[type="email"],
input[type="url"],
textarea {
  padding: 8px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

input:focus,
textarea:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

textarea {
  resize: vertical;
  min-height: 96px;
  line-height: 1.4;
}

.file-inputs {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.file-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  background: #f9fafb;
}

.file-pill input[type="file"] {
  font-size: 13px;
}

.file-label {
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  white-space: nowrap;
}

.file-name {
  font-size: 12px;
  color: #6b7280;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview {
  padding: 10px;
  border: 1px dashed #d1d5db;
  border-radius: 6px;
  background: #f9fafb;
  font-size: 14px;
  line-height: 1.5;
}

.preview :deep(a) {
  color: #2563eb;
  text-decoration: none;
}

.preview :deep(code) {
  background: #e5e7eb;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
}

.preview-error {
  color: #b45309;
  border-color: #f59e0b;
  background: #fffbeb;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  padding: 8px 18px;
  border: none;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error {
  margin: 0;
  color: #dc2626;
  font-size: 13px;
}
</style>
