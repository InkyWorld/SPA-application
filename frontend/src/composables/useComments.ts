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

  async function load() {
    loading.value = true
    try {
      const { data } = await fetchComments(page.value, sort.value)
      items.value = data.results
      total.value = data.count
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
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${location.host}/ws/comments/`)
    ws.onmessage = () => void load()
    return () => ws.close()
  }

  return { items, total, page, sort, loading, load, setSort, setPage, connectLive }
}
