import { api } from './client'
import type { CommentNode, Paged } from '../types/comment'

/** Must match COMMENTS_PAGE_SIZE on the backend. */
export const PAGE_SIZE = 25

export interface CreatePayload {
  home_page?: string
  text: string
  parent_id?: number | null
  file?: File | null
  captcha_key: string
  captcha_value: string
}

export function fetchComments(page = 1, sort = '-created_at') {
  return api.get<Paged<CommentNode>>('/comments/', { params: { page, sort } })
}

export function createComment(payload: CreatePayload) {
  const form = toFormData(payload)
  return api.post('/comments/', form)
}

export function previewText(text: string) {
  return api.post<{ html: string }>('/comments/preview/', { text })
}

export interface CaptchaChallenge {
  key: string
  image_url: string
  audio_url: string | null
}

export function fetchCaptcha() {
  // Served by django-simple-captcha (GET refresh, XHR-only on its side).
  return api.get<CaptchaChallenge>('/captcha/refresh/', {
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
  })
}

function toFormData(payload: CreatePayload): FormData {
  const form = new FormData()
  if (payload.home_page) form.append('home_page', payload.home_page)
  form.append('text', payload.text)
  if (payload.parent_id) form.append('parent_id', String(payload.parent_id))
  if (payload.file) form.append('file', payload.file)
  form.append('captcha_key', payload.captcha_key)
  form.append('captcha_value', payload.captcha_value)
  return form
}
