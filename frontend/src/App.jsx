import { useState, useEffect, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import GraphView from './components/GraphView'
import EditorPanel from './components/EditorPanel'
import ChatWidget from './components/ChatWidget'
import { useAuth, LoginForm } from './Auth'
import { fetchNotes, fetchGraph, fetchSuggestedConnections } from './api'

export default function AppWrapper() {
  const { session } = useAuth()

  // If Supabase is configured but no session, show login
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
  if (supabaseUrl && supabaseUrl !== 'https://your-project-id.supabase.co' && !session) {
    return <LoginForm />
  }

  return <AppMain session={session} />
}

function AppMain({ session }) {
  const [notes, setNotes] = useState([])
  const [graph, setGraph] = useState({ nodes: [], edges: [] })
  const [selectedNote, setSelectedNote] = useState(null)
  const [selectedNodeId, setSelectedNodeId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showEditor, setShowEditor] = useState(false)
  const [aiEdges, setAiEdges] = useState([])
  const [suggestionsLoading, setSuggestionsLoading] = useState(false)
  const { signOut } = useAuth()

  const loadData = useCallback(async () => {
    try {
      const [notesData, graphData] = await Promise.all([fetchNotes(), fetchGraph()])
      setNotes(notesData)
      setGraph(graphData)
    } catch (err) {
      console.error('Failed to load data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (!selectedNote) { setAiEdges([]); return }
    let cancelled = false
    setSuggestionsLoading(true)
    setAiEdges([])
    fetchSuggestedConnections(selectedNote.id, 5)
      .then((data) => {
        if (cancelled) return
        const edges = []
        const sourceNode = graph.nodes.find((n) => n.noteId === selectedNote.id)
        const sourceIdx = sourceNode ? sourceNode.id : null
        if (sourceIdx && data.suggestions) {
          data.suggestions.forEach((s) => {
            const targetNode = graph.nodes.find((n) => n.noteId === s.id)
            if (targetNode && targetNode.id !== sourceIdx) {
              edges.push({ source: sourceIdx, target: targetNode.id, score: s.score, title: s.title })
            }
          })
        }
        if (!cancelled) setAiEdges(edges)
      })
      .catch(console.error)
      .finally(() => { if (!cancelled) setSuggestionsLoading(false) })
    return () => { cancelled = true }
  }, [selectedNote, graph.nodes])

  const handleSelectNote = useCallback((note) => {
    setSelectedNote(note)
    setShowEditor(true)
    const node = graph.nodes.find((n) => n.noteId === note.id)
    setSelectedNodeId(node ? node.id : null)
  }, [graph.nodes])

  const handleSelectNode = useCallback((nodeId) => {
    const node = graph.nodes.find((n) => n.id === nodeId)
    if (node) {
      const note = notes.find((n) => n.id === node.noteId)
      if (note) { setSelectedNote(note); setSelectedNodeId(nodeId); setShowEditor(true) }
    }
  }, [graph.nodes, notes])

  const handleNoteUpdated = useCallback((updatedNote) => {
    setNotes((prev) => prev.map((n) => (n.id === updatedNote.id ? updatedNote : n)))
  }, [])

  const handleNoteCreated = useCallback(() => { loadData() }, [loadData])

  const handleNoteDeleted = useCallback((id) => {
    setNotes((prev) => prev.filter((n) => n.id !== id))
    if (selectedNote?.id === id) { setSelectedNote(null); setSelectedNodeId(null); setShowEditor(false); setAiEdges([]) }
    loadData()
  }, [selectedNote, loadData])

  const handleCloseEditor = useCallback(() => { setShowEditor(false); setSelectedNodeId(null); setAiEdges([]) }, [])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-surface-900">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading Knowledge Base...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex bg-surface-900">
      <Sidebar notes={notes} selectedNote={selectedNote} onSelectNote={handleSelectNote}
        onNoteCreated={handleNoteCreated} onNoteDeleted={handleNoteDeleted} />
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-12 flex items-center justify-between px-4 bg-surface-800 border-b border-surface-600 flex-shrink-0">
          <h1 className="text-sm font-semibold text-gray-200">
            <span className="text-blue-400">✦</span> Knowledge Graph
          </h1>
          <div className="flex items-center gap-3">
            {suggestionsLoading && <span className="text-xs text-purple-400 animate-pulse">AI analyzing...</span>}
            <span className="text-xs text-gray-500">
              {graph.nodes.length} notes · {graph.edges.length} connections
              {aiEdges.length > 0 && <span className="text-purple-400 ml-1">+{aiEdges.length} AI</span>}
            </span>
            {session && (
              <button onClick={signOut} className="text-xs text-gray-500 hover:text-gray-300">Logout</button>
            )}
          </div>
        </header>
        <div className="flex-1 graph-container relative">
          <GraphView graph={graph} selectedNodeId={selectedNodeId} onSelectNode={handleSelectNode} aiEdges={aiEdges} />
          {aiEdges.length > 0 && selectedNote && (
            <div className="absolute top-3 right-3 bg-surface-800/95 border border-purple-500/30 rounded-lg p-3 w-56 shadow-lg backdrop-blur-sm">
              <p className="text-xs font-semibold text-purple-400 mb-2">🤖 AI Suggested Links</p>
              {aiEdges.map((edge, i) => (
                <div key={i} className="flex items-center justify-between py-1 border-b border-surface-600 last:border-0 cursor-pointer hover:bg-surface-700/50 rounded px-1"
                  onClick={() => handleSelectNode(edge.target)}>
                  <span className="text-xs text-gray-300 truncate flex-1">{edge.title}</span>
                  <span className="text-xs text-green-400 ml-2 font-mono">{Math.round(edge.score * 100)}%</span>
                </div>
              ))}
              <p className="text-xs text-gray-600 mt-2">Dashed green lines show AI-suggested connections</p>
            </div>
          )}
        </div>
      </div>
      {showEditor && selectedNote && (
        <EditorPanel note={selectedNote} onNoteUpdated={handleNoteUpdated} onClose={handleCloseEditor} />
      )}
      <ChatWidget />
    </div>
  )
}