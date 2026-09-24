import { ref } from 'vue'
import { fetchCaptcha } from '../api/comments'

export function useCaptcha() {
  const key = ref('')
  const image = ref('')

  async function refresh() {
    const { data } = await fetchCaptcha()
    key.value = data.key
    // image_url is same-origin (proxied /api/* in dev and nginx in prod).
    image.value = data.image_url
  }

  return { key, image, refresh }
}
