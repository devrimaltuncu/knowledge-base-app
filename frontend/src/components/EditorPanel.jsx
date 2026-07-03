import { useState, useEffect, useCallback } from 'react'
import { updateNote, fetchNote } from '../api'

export default function EditorPanel({ note, onNoteUpdated, onClose }) {
  const [content, setContent] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [view, setView] = useState('preview') // 'preview' | 'edit' | 'split'

  // Load content when note changes
  useEffect(() => {
    if (note) {
      setContent(note.content || '')
      setIsEditing(false)
    }
  }, [note])

  const handleSave = useCallback(async () => {
    if (!note) return
    setSaving(true)
    try {
      await updateNote(note.id, content)
      // Fetch the updated note with re-parsed content
      const refreshed = await fetchNote(note.id)
      onNoteUpdated(refreshed)
      setIsEditing(false)
    } catch (err) {
      alert('Failed to save: ' + err.message)
    } finally {
      setSaving(false)
    }
  }, [note, content, onNoteUpdated])

  const handleHotKey = useCallback(
    (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
      }
    },
    [handleSave],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleHotKey)
    return () => window.removeEventListener('keydown', handleHotKey)
  }, [handleHotKey])

  if (!note) return null

  return (
    <aside className="w-96 lg:w-[480px] flex-shrink-0 bg-surface-800 border-l border-surface-600 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-surface-600">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-gray-200 truncate flex-1">
            {note.title}
          </h3>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-lg leading-none ml-2"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Meta info */}
        <div className="flex items-center gap-2 flex-wrap mb-2">
          {note.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-surface-600 text-gray-400"
            >
              {tag}
            </span>
          ))}
          {note.date && (
            <span className="text-xs text-gray-600">{note.date}</span>
          )}
        </div>
        {note.id && (
          <span className="text-xs text-gray-600 font-mono">ID: {note.id.substring(0, 8)}...</span>
        )}

        {/* Links */}
        {note.links && note.links.length > 0 && (
          <div className="mt-2 flex items-center gap-1 flex-wrap">
            <span className="text-xs text-gray-600 mr-1">Links:</span>
            {note.links.map((link) => (
              <span
                key={link}
                className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"
              >
                {link}
              </span>
            ))}
          </div>
        )}

        {/* View mode toggles */}
        <div className="flex items-center gap-1 mt-3">
          {[
            ['preview', 'Preview'],
            ['edit', 'Edit'],
            ['split', 'Split'],
          ].map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => {
                setView(mode)
                if (mode === 'edit') setIsEditing(true)
              }}
              className={`text-xs px-3 py-1 rounded transition-colors ${
                view === mode
                  ? 'bg-blue-600 text-white'
                  : 'bg-surface-700 text-gray-400 hover:text-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
          <div className="flex-1" />
          <button
            onClick={handleSave}
            disabled={saving || !isEditing}
            className={`text-xs px-3 py-1 rounded transition-colors ${
              saving
                ? 'bg-yellow-600 text-white'
                : isEditing
                  ? 'bg-green-600 hover:bg-green-500 text-white'
                  : 'bg-surface-700 text-gray-600 cursor-not-allowed'
            }`}
            title="Ctrl+S to save"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {view === 'preview' && (
          <div className="flex-1 overflow-y-auto p-4 markdown-body">
            <PreviewContent content={content} />
          </div>
        )}

        {view === 'edit' && (
          <textarea
            value={content}
            onChange={(e) => {
              setContent(e.target.value)
              setIsEditing(true)
            }}
            className="flex-1 bg-surface-900 text-gray-200 p-4 font-mono text-sm resize-none focus:outline-none border-none"
            placeholder="Write markdown here... Use [[Wiki Links]] to connect notes."
            spellCheck={false}
          />
        )}

        {view === 'split' && (
          <div className="flex-1 flex overflow-hidden">
            <div className="w-1/2 overflow-y-auto p-4 markdown-body border-r border-surface-600">
              <PreviewContent content={content} />
            </div>
            <textarea
              value={content}
              onChange={(e) => {
                setContent(e.target.value)
                setIsEditing(true)
              }}
              className="w-1/2 bg-surface-900 text-gray-200 p-4 font-mono text-sm resize-none focus:outline-none border-none"
              placeholder="Write markdown here..."
              spellCheck={false}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-surface-600 text-xs text-gray-600 text-center">
        Ctrl+S to save · [[Wiki Links]] supported
      </div>
    </aside>
  )
}

// Simple markdown-to-html preview (wiki links highlighted)
function PreviewContent({ content }) {
  const html = renderMarkdown(content)
  return <div dangerouslySetInnerHTML={{ __html: html }} />
}

function renderMarkdown(text) {
  let html = text

  // Escape HTML entities in non-code sections
  html = html.replace(/&/g, '&').replace(/</g, '<').replace(/>/g, '>')

  // Code blocks (```...```)
  html = html.replace(
    /```(\w*)\n([\s\S]*?)```/g,
    '<pre><code class="language-$1">$2</code></pre>',
  )

  // Inline code (`...`)
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')

  // Headers
  html = html.replace(/^#### (.+)$/gm, '<h4>$1</h4>')
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')

  // Horizontal rules
  html = html.replace(/^---$/gm, '<hr>')

  // Bold and italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Wiki links [[target]] or [[target|alias]]
  html = html.replace(
    /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
    '<span class="inline-block px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 border border-blue-500/25 font-medium">🔗 $2$1</span>',
  )

  // Regular links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')

  // Images ![alt](url)
  html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" class="max-w-full rounded">')

  // Tables
  html = html.replace(/^\|(.+)\|$/gm, (match) => {
    const cells = match
      .replace(/^\||\|$/g, '')
      .split('|')
      .map((c) => c.trim())
    const isHeader =
      cells.every((c) => /^[-:]+$/.test(c)) || match.includes('---')
    if (isHeader) return ''
    const tag = match.includes('---') ? 'th' : 'td'
    return (
      '<tr>' +
      cells.map((c) => `<${tag}>${c}</${tag}>`).join('') +
      '</tr>'
    )
  })

  // Blockquotes
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')

  // Unordered lists
  html = html.replace(/^[\-\*] (.+)$/gm, '<li>$1</li>')

  // Ordered lists
  html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>')

  // Wrap consecutive <li> in <ul> or <ol>
  html = html.replace(/(<li>[\s\S]*?<\/li>)\n(?=<li>)/g, '$1')
  html = html.replace(/((?:<li>[\s\S]*?<\/li>\n?)+)/g, '<ul>$1</ul>')

  // Paragraphs: non-tag lines
  html = html.replace(/^(?!<[a-zA-Z/!])(.+)$/gm, '<p>$1</p>')

  // Clean up multiple newlines
  html = html.replace(/\n+/g, '\n')

  // Decode inside code blocks (re-encode only the code content)
  html = html.replace(
    /<code class="language-(\w*)">([\s\S]*?)<\/code>/g,
    (_, lang, code) => {
      const decoded = code
        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
      return `<code class="language-${lang}">${decoded}</code>`
    },
  )

  return html
}