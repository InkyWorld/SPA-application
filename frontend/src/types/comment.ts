export interface CommentNode {
  id: number
  parent_id: number | null
  user_name: string
  email: string
  home_page: string
  text: string // sanitized XHTML from server — render with v-html
  image_url: string | null
  image_name: string | null
  file_url: string | null
  file_name: string | null
  created_at: string
  replies: CommentNode[]
}

export interface Paged<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type SortKey = 'user_name' | 'email' | 'created_at'
