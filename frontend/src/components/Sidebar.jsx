import { useState, useMemo } from 'react'
import { createNote, deleteNote } from '../api'

export default function Sidebar({ notes, selectedNote, onSelectNote, onNoteCreated, onNoteDeleted }) {
  const [search, setSearch] = useState('')
  const [newName, setNewName] = useState('')
  const [showNew, setShowNew] = useState(false)
  const [creating, setCreating] = useState(false)

  // Organize notes by tag
  const grouped = useMemo(() => {
    const groups = {}
    const filtered = notes.filter((n) => {
      if (!search) return true
      const q = search.toLowerCase()
      return (
        n.title.toLowerCase().includes(q) ||
        n.tags.some((t) => t.toLowerCase().includes(q))
      )
    })
    for (const note of filtered) {
      const group = note.tags.length > 0 ? note.tags[0] : 'untagged'
      if (!groups[group]) groups[group] = []
      groups[group].push(note)
    }
    return groups
  }, [notes, search])

  const allTags = useMemo(() => {
    const tags = new Set()
    notes.forEach((n) => n.tags.forEach((t) => tags.add(t)))
    return [...tags].sort()
  }, [notes])

  const handleCreate = async () => {
    const title = newName.trim()
    if (!title) return
    setCreating(true)
    try {
      await createNote(title)
      setNewName('')
      setShowNew(false)
      onNoteCreated()
    } catch (err) {
      alert('Failed to create note: ' + err.message)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id) => {
    if (!confirm("Delete this note?")) return
    try {
      await deleteNote(id)
      onNoteDeleted(id)
    } catch (err) {
      alert('Failed to delete note: ' + err.message)
    }
  }

  return (
    <aside className="w-72 flex-shrink-0 bg-surface-800 border-r border-surface-600 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-surface-600">
        <h2 className="text-sm font-semibold text-gray-200 mb-3 flex items-center gap-2">
          <span className="text-yellow-400">📁</span> Notes Explorer
        </h2>
        {/* Search */}
        <input
          type="text"
          placeholder="Search notes or tags..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full bg-surface-700 text-gray-200 text-xs px-3 py-2 rounded-lg border border-surface-600 focus:outline-none focus:border-blue-500 placeholder-gray-500"
        />
      </div>

      {/* Note list grouped by tag */}
      <div className="flex-1 overflow-y-auto p-2">
        {Object.keys(grouped).length === 0 && (
          <p className="text-gray-500 text-xs text-center mt-8">No notes found</p>
        )}
        {Object.entries(grouped).map(([tag, tagNotes]) => (
          <div key={tag} className="mb-3">
            <div className="flex items-center gap-1.5 px-2 py-1">
              <span
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: getTagColor(tag) }}
              />
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wide">
                {tag}
              </span>
              <span className="text-xs text-gray-600 ml-auto">{tagNotes.length}</span>
            </div>
            {tagNotes.map((note) => (
              <div
                key={note.id}
                onClick={() => onSelectNote(note)}
                className={`group flex items-center gap-2 px-3 py-1.5 mx-1 rounded-lg cursor-pointer transition-colors ${
                  selectedNote?.id === note.id
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                    : 'text-gray-400 hover:bg-surface-700 hover:text-gray-200'
                }`}
              >
                <span className="text-xs truncate flex-1">{note.title}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDelete(note.id)
                  }}
                  className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 text-xs transition-opacity"
                  title="Delete note"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* New note button */}
      <div className="p-3 border-t border-surface-600">
        {showNew ? (
          <div className="flex gap-1">
            <input
              type="text"
              placeholder="Note title..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              className="flex-1 bg-surface-700 text-gray-200 text-xs px-2 py-1.5 rounded border border-surface-600 focus:outline-none focus:border-blue-500"
              autoFocus
            />
            <button
              onClick={handleCreate}
              disabled={creating}
              className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded disabled:opacity-50"
            >
              ✓
            </button>
            <button
              onClick={() => setShowNew(false)}
              className="px-2 py-1 bg-surface-600 hover:bg-surface-500 text-gray-400 text-xs rounded"
            >
              ✕
            </button>
          </div>
        ) : (
          <button
            onClick={() => setShowNew(true)}
            className="w-full py-2 text-xs text-gray-400 hover:text-gray-200 bg-surface-700 hover:bg-surface-600 rounded-lg transition-colors flex items-center justify-center gap-1"
          >
            <span>+</span> New Note
          </button>
        )}
      </div>

      {/* Tags legend */}
      <div className="p-3 border-t border-surface-600">
        <p className="text-xs text-gray-500 mb-2">Tags ({allTags.length})</p>
        <div className="flex flex-wrap gap-1">
          {allTags.map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full cursor-pointer hover:opacity-80 transition-opacity"
              style={{
                backgroundColor: getTagColor(tag) + '22',
                color: getTagColor(tag),
                border: `1px solid ${getTagColor(tag)}44`,
              }}
              onClick={() => setSearch(tag)}
            >
              {tag}
            </span>
          ))}
        </div>
      </div>
    </aside>
  )
}

// Deterministic color per tag
const TAG_COLORS = [
  '#60a5fa', '#a78bfa', '#34d399', '#f472b6', '#fbbf24',
  '#fb923c', '#94a3b8', '#38bdf8', '#a3e635', '#e879f9',
]

function getTagColor(tag) {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}