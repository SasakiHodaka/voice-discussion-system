import React, { useCallback, useState, useEffect } from 'react'
import { useSessionStore } from '@/lib/store'
import {
  ReactFlow,
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Background,
  Controls,
  MiniMap,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

interface IssueNode extends Node {
  data: {
    label: string
    topic: string
    summary?: string
  }
}

interface IssueEdge extends Edge {
  data?: {
    relation: string
    weight: number
  }
}

interface EditSnapshot {
  timestamp: number
  type: 'position' | 'node_data' | 'edge_add' | 'edge_delete'
  node_id?: string
  edge_id?: string
  old_value?: Record<string, any>
  new_value?: Record<string, any>
}

interface TopicMapEditorProps {
  issueMap: any
  onChange?: (updatedMap: any) => void
  onHandleEdit?: (edit: EditSnapshot) => void
  editable?: boolean
  socket?: any
}

const TopicMapEditor: React.FC<TopicMapEditorProps> = ({
  issueMap,
  onChange,
  onHandleEdit,
  editable = true,
  socket,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<IssueNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<IssueEdge>([])
  const [editSnapshots, setEditSnapshots] = useState<Record<string, EditSnapshot>>({})
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({})
  const { sessionId } = useSessionStore()

  // Convert issue_map to React Flow nodes/edges
  // Re-generate nodes/edges whenever issueMap reference changes
  useEffect(() => {
    if (!issueMap) return

    console.log('[TopicMapEditor] Updating from issueMap:', {
      nodes: issueMap.nodes?.length,
      edges: issueMap.edges?.length,
      nodeDetails: issueMap.nodes?.map((n: any) => ({
        id: n.id,
        title: n.title?.substring(0, 20),
        summary: n.summary?.substring(0, 30),
        topic: n.topic,
      })),
    })

    // Create stable positions for nodes (preserve existing positions)
    const newPositions: Record<string, { x: number; y: number }> = { ...nodePositions }
    
    const flowNodes: IssueNode[] = (issueMap.nodes || []).map((node: any, idx: number) => {
      const nodeId = node.id || `node_${idx}`
      
      // Use existing position if available, otherwise create new position
      if (!newPositions[nodeId]) {
        newPositions[nodeId] = {
          x: 100 + (idx % 5) * 200,
          y: 100 + Math.floor(idx / 5) * 180,
        }
      }

      // Priority: summary > title > label > text
      const fullText = node.summary || node.title || node.label || node.text || `Node ${idx}`
      const displayLabel = fullText.length > 50 
        ? fullText.substring(0, 50) + '...'
        : fullText

      return {
        id: nodeId,
        data: {
          label: displayLabel,
          topic: node.topic || 'general',
          summary: node.summary || node.text || '',
          fullText: fullText, // Store full text for tooltip
        },
        position: newPositions[nodeId],
        style: {
          background: getTopicColor(node.topic || 'general'),
          color: '#fff',
          padding: '12px',
          borderRadius: '8px',
          fontSize: '13px',
          fontWeight: '500',
          textAlign: 'left',
          minWidth: '150px',
          maxWidth: '250px',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        },
      }
    })

    const flowEdges: IssueEdge[] = (issueMap.edges || []).map((edge: any, idx: number) => ({
      id: edge.id || `edge_${idx}`,
      source: edge.source || '',
      target: edge.target || '',
      label: edge.relation || '',
      data: {
        relation: edge.relation || '',
        weight: edge.weight || 0.5,
      },
      style: {
        strokeWidth: (edge.weight || 0.5) * 2,
        opacity: 0.6,
      },
    }))

    console.log('[TopicMapEditor] Setting nodes:', flowNodes.length, 'edges:', flowEdges.length)
    setNodePositions(newPositions)
    setNodes(flowNodes)
    setEdges(flowEdges)
  }, [issueMap, setNodes, setEdges])

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!editable) return

      const newEdge: IssueEdge = {
        id: `edge_${Date.now()}`,
        ...connection,
        data: {
          relation: 'related',
          weight: 0.5,
        },
      }
      setEdges((eds) => addEdge(newEdge, eds))

      // Task 4: Record hand-edit snapshot
      const edit: EditSnapshot = {
        timestamp: Date.now(),
        type: 'edge_add',
        edge_id: newEdge.id,
        new_value: {
          source: connection.source,
          target: connection.target,
        },
      }
      setEditSnapshots((prev) => ({
        ...prev,
        [newEdge.id]: edit,
      }))
      onHandleEdit?.(edit)

      // Notify parent component
      onChange?.({
        nodes,
        edges: [...edges, newEdge],
      })

      // Task 5: Emit hand_edit event to backend
      if (socket && sessionId) {
        socket.emit('hand_edit', {
          session_id: sessionId,
          edit_type: 'edge_add',
          edge_id: newEdge.id,
          new_value: {
            source: connection.source,
            target: connection.target,
          },
        })
      }
    },
    [edges, nodes, setEdges, onChange, onHandleEdit, socket, sessionId, editable]
  )

  const handleNodeChange = useCallback(
    (changes: any) => {
      if (!editable) return

      // Record edit snapshots for position changes
      changes.forEach((change: any) => {
        if (change.type === 'position' && change.position) {
          // Update stored positions
          setNodePositions((prev) => ({
            ...prev,
            [change.id]: change.position,
          }))

          const edit: EditSnapshot = {
            timestamp: Date.now(),
            type: 'position',
            node_id: change.id,
            new_value: {
              position: change.position,
            },
          }
          setEditSnapshots((prev) => ({
            ...prev,
            [change.id]: edit,
          }))
          onHandleEdit?.(edit)

          // Task 5: Emit hand_edit event to backend
          if (socket && sessionId) {
            socket.emit('hand_edit', {
              session_id: sessionId,
              edit_type: 'position',
              node_id: change.id,
              new_value: {
                position: change.position,
              },
            })
          }
        }
      })

      onNodesChange(changes)
    },
    [onNodesChange, onHandleEdit, socket, sessionId, editable]
  )

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={handleNodeChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        nodesDraggable={editable}
        nodesConnectable={editable}
        elementsSelectable={editable}
        fitView
        minZoom={0.3}
        maxZoom={2}
      >
        <Background />
        <Controls />
        <MiniMap 
          nodeColor={(node) => node.style?.background as string || '#666'}
          maskColor="rgba(0, 0, 0, 0.1)"
        />
      </ReactFlow>
      {/* Status indicator */}
      <div style={{
        position: 'absolute',
        bottom: 20,
        left: 20,
        padding: '8px 12px',
        background: 'rgba(0, 0, 0, 0.6)',
        color: '#fff',
        borderRadius: '4px',
        fontSize: '12px',
        zIndex: 1000,
      }}>
        編集スナップショット: {Object.keys(editSnapshots).length}件
      </div>
    </div>
  )
}

function getTopicColor(topic: string): string {
  const colors: Record<string, string> = {
    requirement: '#3B82F6',
    design: '#8B5CF6',
    implementation: '#10B981',
    testing: '#F59E0B',
    schedule: '#EF4444',
    resource: '#EC4899',
    general: '#6B7280',
  }
  return colors[topic] || colors.general
}

export default TopicMapEditor
