import { useRef, useEffect, useCallback } from 'react'
import { Network } from 'vis-network/standalone'

const TAG_COLORS = [
  '#60a5fa', '#a78bfa', '#34d399', '#f472b6', '#fbbf24',
  '#fb923c', '#94a3b8', '#38bdf8', '#a3e635', '#e879f9',
]

function getTagColorHex(tag) {
  let hash = 0
  for (let i = 0; i < tag.length; i++) {
    hash = tag.charCodeAt(i) + ((hash << 5) - hash)
  }
  return TAG_COLORS[Math.abs(hash) % TAG_COLORS.length]
}

export default function GraphView({ graph, selectedNodeId, onSelectNode, aiEdges = [] }) {
  const containerRef = useRef(null)
  const networkRef = useRef(null)
  const aiEdgeIdsRef = useRef(new Set())

  useEffect(() => {
    if (!containerRef.current) return

    // Transform data for vis-network
    const nodes = graph.nodes.map((node) => {
      const color = node.group ? getTagColorHex(node.group) : '#94a3b8'
      return {
        id: node.id,
        label: node.label,
        group: node.group,
        color: {
          background: color + '22',
          border: color,
          highlight: { background: color + '44', border: color },
          hover: { background: color + '33', border: color },
        },
        font: {
          color: '#cbd5e1',
          size: 13,
          face: 'ui-sans-serif, system-ui, sans-serif',
          strokeWidth: 2,
          strokeColor: '#0f1117',
        },
        borderWidth: 2,
        shape: 'dot',
        size: 22,
        scaling: {
          min: 16,
          max: 30,
          label: { enabled: true, min: 11, max: 15 },
        },
      }
    })

    const edges = graph.edges.map((edge) => ({
      from: edge.source,
      to: edge.target,
      color: { color: '#374151', highlight: '#60a5fa', hover: '#60a5fa' },
      width: 1.5,
      smooth: { type: 'continuous', roundness: 0.5 },
      arrows: { to: { enabled: false } },
    }))

    const data = { nodes, edges }
    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -40,
          centralGravity: 0.005,
          springLength: 160,
          springConstant: 0.08,
          damping: 0.4,
          avoidOverlap: 0.5,
        },
        stabilization: {
          iterations: 200,
          updateInterval: 25,
        },
        minVelocity: 0.75,
        maxVelocity: 30,
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        navigationButtons: false,
        keyboard: true,
        zoomView: true,
        dragView: true,
      },
      layout: {
        improvedLayout: true,
      },
      edges: {
        smooth: { type: 'continuous', roundness: 0.5 },
        chosen: false,
      },
      nodes: {
        chosen: {
          node: (values) => {
            values.borderWidth = 3
          },
        },
      },
    }

    const network = new Network(containerRef.current, data, options)
    networkRef.current = network

    // Click handler
    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        onSelectNode(params.nodes[0])
      }
    })

    // Fit all nodes
    network.once('stabilizationIterationsDone', () => {
      network.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } })
    })

    // Cleanup
    return () => {
      network.destroy()
    }
  }, [graph])

  // Update AI edges separately (don't rebuild entire graph)
  useEffect(() => {
    if (!networkRef.current) return
    const network = networkRef.current

    // Remove old AI edges
    const oldIds = [...aiEdgeIdsRef.current]
    oldIds.forEach((id) => {
      try { network.body.data.edges.remove(id) } catch (e) {}
    })
    aiEdgeIdsRef.current = new Set()

    // Add new AI edges as dashed green
    aiEdges.forEach((edge, i) => {
      const edgeId = `ai_${edge.source}_${edge.target}_${i}`
      try {
        network.body.data.edges.add({
          id: edgeId,
          from: edge.source,
          to: edge.target,
          dashes: [8, 4],
          color: { color: '#22c55e66', highlight: '#22c55e', hover: '#22c55e' },
          width: 2,
          smooth: { type: 'continuous', roundness: 0.3 },
          arrows: { to: { enabled: false } },
          title: `AI suggested: ${edge.title} (${Math.round(edge.score * 100)}%)`,
        })
        aiEdgeIdsRef.current.add(edgeId)
      } catch (e) {}
    })
  }, [aiEdges])

  // Highlight selected node
  useEffect(() => {
    if (!networkRef.current) return
    const network = networkRef.current

    const allNodes = graph.nodes
    allNodes.forEach((node) => {
      const color = node.group ? getTagColorHex(node.group) : '#94a3b8'
      network.body.data.nodes.update({
        id: node.id,
        color: {
          background: color + '22',
          border: color,
        },
        borderWidth: 2,
      })
    })

    if (selectedNodeId) {
      const selNode = graph.nodes.find((n) => n.id === selectedNodeId)
      if (selNode) {
        const color = selNode.group ? getTagColorHex(selNode.group) : '#94a3b8'
        network.body.data.nodes.update({
          id: selectedNodeId,
          color: {
            background: color + '55',
            border: '#fbbf24',
          },
          borderWidth: 3,
        })
        network.focus(selectedNodeId, {
          scale: 1.2,
          animation: { duration: 400, easingFunction: 'easeInOutQuad' },
        })
      }
    }
  }, [selectedNodeId, graph.nodes])

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ minHeight: '500px' }}
    />
  )
}