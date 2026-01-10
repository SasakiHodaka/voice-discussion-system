import React, { useState, useRef, useEffect } from 'react';

type TopicNode = {
  id: string;
  label: string;
  x?: number;
  y?: number;
};

type TopicMapData = {
  nodes: TopicNode[];
  edges?: { from: string; to: string }[];
};

const WIDTH = 400;
const HEIGHT = 300;
const NODE_RADIUS = 28;

const TopicMapEditor: React.FC<{ mapData?: TopicMapData }> = ({ mapData }) => {
  const [positions, setPositions] = useState<{ [id: string]: { x: number; y: number } }>({});

  // mapData.nodesが変化したら初期配置を再計算
  useEffect(() => {
    if (!mapData || !mapData.nodes || mapData.nodes.length === 0) {
      setPositions({});
      return;
    }
    // nodesの内容が変化したら必ず新しいpositionsを生成
    const n = mapData.nodes.length;
    const centerX = WIDTH / 2;
    const centerY = HEIGHT / 2;
    const radius = Math.min(WIDTH, HEIGHT) / 2 - NODE_RADIUS - 10;
    const pos: { [id: string]: { x: number; y: number } } = {};
    mapData.nodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / n;
      pos[node.id] = {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      };
    });
    setPositions({ ...pos });
  }, [mapData && mapData.nodes ? mapData.nodes.map(n => n.id + n.label).join(',') : '']);

  const draggingNode = useRef<string | null>(null);

  const handleMouseDown = (id: string, e: React.MouseEvent) => {
    draggingNode.current = id;
  };
  const handleMouseUp = () => {
    draggingNode.current = null;
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!draggingNode.current) return;
    const rect = (e.target as SVGElement).closest('svg')?.getBoundingClientRect();
    if (!rect) return;
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setPositions(prev => ({ ...prev, [draggingNode.current!]: { x, y } }));
  };

  if (!mapData || !mapData.nodes || mapData.nodes.length === 0) {
    return <div className="text-gray-400 text-center">トピックマップはありません</div>;
  }

  return (
    <div>
      <svg
        width={WIDTH}
        height={HEIGHT}
        style={{ border: '1px solid #ddd', background: '#fafafa' }}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
      >
        {/* エッジ描画 */}
        {mapData.edges && mapData.edges.map((edge, idx) => {
          const from = positions[edge.from];
          const to = positions[edge.to];
          if (!from || !to) return null;
          return (
            <line
              key={idx}
              x1={from.x}
              y1={from.y}
              x2={to.x}
              y2={to.y}
              stroke="#888"
              strokeWidth={2}
            />
          );
        })}
        {/* ノード描画 */}
        {mapData.nodes.map(node => {
          const pos = positions[node.id];
          if (!pos) return null;
          return (
            <g key={node.id}>
              <circle
                cx={pos.x}
                cy={pos.y}
                r={NODE_RADIUS}
                fill="#4f8ef7"
                stroke="#333"
                strokeWidth={2}
                onMouseDown={e => handleMouseDown(node.id, e)}
                style={{ cursor: 'grab' }}
              />
              <text
                x={pos.x}
                y={pos.y + 5}
                textAnchor="middle"
                fontSize={14}
                fill="#fff"
                pointerEvents="none"
              >{node.label}</text>
            </g>
          );
        })}
      </svg>
      <div className="mt-2 text-xs text-gray-500">ノードはドラッグで移動できます</div>
    </div>
  );
};

export default TopicMapEditor;
