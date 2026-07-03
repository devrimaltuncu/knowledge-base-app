import { useState, useRef, useEffect, useCallback } from 'react'

const BASE = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}` : '/api'

export default function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Merhaba! Bilgi tabanindaki notlariniza dayanarak sorularinizi yanitlayabilirim. Ornegin: "Notlarimdaki DevOps araclari neler?" veya "Makine ogrenmesi notlarimi ozetle" gibi sorular sorabilirsiniz.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState('')
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streaming])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  const sendMessage = useCallback(async () => {
    const question = input.trim()
    if (!question || loading) return

    setInput('')
    setLoading(true)
    setStreaming('')
    setMessages((prev) => [...prev, { role: 'user', content: question }])

    try {
      const res = await fetch(`${BASE}/chat/graph`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, top_k: 5 }),
      })
      if (!res.ok) throw new Error('Chat request failed')
      const data = await res.json()
      
      let answer = data.answer || 'Sorry, I could not generate an answer.'
      
      // Build source citation line
      if (data.sources && data.sources.length > 0) {
        const sourceNames = data.sources.map((s) => `**${s.title}**`).join(', ')
        answer += `\n\n---\n*Sources: ${sourceNames}*`
      }
      
      setMessages((prev) => [...prev, { role: 'assistant', content: answer }])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Error: ' + err.message }])
    } finally {
      setLoading(false)
    }
  }, [input, loading])

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        sendMessage()
      }
    },
    [sendMessage],
  )

  return (
    <>
      {/* Floating toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-5 right-5 z-50 w-14 h-14 rounded-full bg-gradient-to-br from-purple-600 to-blue-600 text-white shadow-lg hover:shadow-xl hover:scale-105 transition-all flex items-center justify-center text-2xl"
        title="AI Chat with Knowledge Base"
      >
        {isOpen ? '✕' : '🤖'}
      </button>

      {/* Chat panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-5 z-50 w-96 h-[520px] max-h-[calc(100vh-120px)] bg-surface-800 border border-surface-600 rounded-xl shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="p-3 border-b border-surface-600 flex items-center justify-between bg-surface-700">
            <div className="flex items-center gap-2">
              <span className="text-lg">🤖</span>
              <span className="text-sm font-semibold text-gray-200">Graph-RAG Chat</span>
              <span className="text-xs text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded-full">AI</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-gray-500 hover:text-gray-300 text-sm"
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] rounded-xl px-3 py-2 text-xs leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : 'bg-surface-700 text-gray-300 rounded-bl-sm border border-surface-600'
                  }`}
                >
                  <div className="markdown-body prose-xs" dangerouslySetInnerHTML={{ __html: renderSimpleMarkdown(msg.content) }} />
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-surface-700 text-gray-400 rounded-xl rounded-bl-sm px-3 py-2 text-xs border border-surface-600 flex items-center gap-2">
                  <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-surface-600 bg-surface-700">
            <div className="flex gap-2">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your knowledge base..."
                className="flex-1 bg-surface-600 text-gray-200 text-xs px-3 py-2 rounded-lg border border-surface-500 focus:outline-none focus:border-purple-500 resize-none placeholder-gray-500"
                rows={2}
                disabled={loading}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="px-3 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
              >
                {loading ? '...' : 'Send'}
              </button>
            </div>
            <p className="text-xs text-gray-600 mt-1 text-center">
              Powered by TF-IDF semantic search · Add DEEPSEEK_API_KEY for AI answers
            </p>
          </div>
        </div>
      )}
    </>
  )
}

function renderSimpleMarkdown(text) {
  let html = text
    .replace(/&/g, '&')
    .replace(/</g, '<')
    .replace(/>/g, '>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')
  html = html.replace(/`([^`]+)`/g, '<code class="bg-surface-600 px-1 py-0.5 rounded text-pink-400">$1</code>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="text-sm font-semibold text-purple-400 mt-2 mb-1">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="text-base font-semibold text-blue-400 mt-2 mb-1">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="text-lg font-bold text-cyan-400 mt-2 mb-1">$1</h2>')
  html = html.replace(/^---/gm, '<hr class="border-gray-600 my-2">')
  html = html.replace(/\n/g, '<br>')
  return html
}