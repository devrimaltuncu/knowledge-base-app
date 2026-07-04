const API_BASE = import.meta.env.VITE_API_URL || 'https://knowledge-base-backend-pi14.onrender.com'

/**
 * Get the Supabase auth token from localStorage (set by @supabase/supabase-js).
 * Returns null if no session exists.
 */
function getAuthHeaders() {
  const supabaseAuth = localStorage.getItem('sb-' + getSupabaseProjectId() + '-auth-token')
  if (!supabaseAuth) return {}
  try {
    const parsed = JSON.parse(supabaseAuth)
    if (parsed.access_token) {
      return { Authorization: `Bearer ${parsed.access_token}` }
    }
  } catch {}
  return {}
}

function getSupabaseProjectId() {
  // Extract project ID from the Supabase URL
  const url = import.meta.env.VITE_SUPABASE_URL || ''
  const match = url.match(/https:\/\/([^.]+)\./)
  return match ? match[1] : 'default'
}

export async function fetchNotes() {
  const res = await fetch(`${API_BASE}/notes`, { headers: getAuthHeaders() })
  if (!res.ok) throw new Error('Failed to fetch notes')
  return res.json()
}

export async function fetchNote(id) {
  const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(id)}`, { headers: getAuthHeaders() })
  if (!res.ok) throw new Error('Failed to fetch note')
  return res.json()
}

export async function updateNote(id, content) {
  const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(id)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ content }),
  })
  if (!res.ok) throw new Error('Failed to update note')
  return res.json()
}

export async function createNote(title, content = '') {
  const res = await fetch(`${API_BASE}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ title, content }),
  })
  if (!res.ok) throw new Error('Failed to create note')
  return res.json()
}

export async function deleteNote(id) {
  const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(id)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to delete note')
  return res.json()
}

export async function fetchGraph() {
  const res = await fetch(`${API_BASE}/graph`, { headers: getAuthHeaders() })
  if (!res.ok) throw new Error('Failed to fetch graph')
  return res.json()
}

export async function fetchTags() {
  const res = await fetch(`${API_BASE}/tags`, { headers: getAuthHeaders() })
  if (!res.ok) throw new Error('Failed to fetch tags')
  return res.json()
}

export async function fetchSuggestedConnections(noteId, topK = 5) {
  const res = await fetch(`${API_BASE}/notes/${encodeURIComponent(String(noteId))}/suggested?top_k=${topK}`, {
    headers: getAuthHeaders(),
  })
  if (!res.ok) throw new Error('Failed to fetch suggested connections')
  return res.json()
}

export async function chatWithGraph(question, topK = 5) {
  const res = await fetch(`${API_BASE}/chat/graph`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify({ question, top_k: topK }),
  })
  if (!res.ok) throw new Error('Failed to chat with graph')
  return res.json()
}