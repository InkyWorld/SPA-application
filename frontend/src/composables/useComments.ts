import { ref } from 'vue'
import { fetchComments } from '../api/comments'
import type { CommentNode } from '../types/comment'

/** List state: page + sort + WS live refresh. One concern per function. */
export function useComments() {
  const items = ref<CommentNode[]>([])
  const total = ref(0)
  const page = ref(1)
  const sort = ref('-created_at')
  const loading = ref(false)
  const error = ref('')

  async function load() {
    loading.value = true
    error.value = ''
    try {
      const { data } = await fetchComments(page.value, sort.value)
      items.value = data.results
      total.value = data.count
    } catch {
      error.value = 'Could not load comments.'
    } finally {
      loading.value = false
    }
  }

  function setSort(next: string) {
    sort.value = next
    page.value = 1
    void load()
  }

  function setPage(next: number) {
    page.value = next
    void load()
  }

  function connectLive() {
    let ws: WebSocket | null = null
    let attempts = 0
    let timer: number | undefined
    let closed = false

    function connect() {
      if (closed) return
      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
      ws = new WebSocket(`${protocol}//${location.host}/ws/comments/`)
      ws.onopen = () => {
        attempts = 0
      }
      ws.onmessage = () => void load()
      ws.onclose = () => {
        if (closed) return
        attempts += 1
        timer = window.setTimeout(connect, Math.min(1000 * 2 ** attempts, 30000))
      }
    }

    connect()
    return () => {
      closed = true
      window.clearTimeout(timer)
      ws?.close()
    }
  }

  return { items, total, page, sort, loading, error, load, setSort, setPage, connectLive }
}
