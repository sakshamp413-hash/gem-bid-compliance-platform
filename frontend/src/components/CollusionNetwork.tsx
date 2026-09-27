/**
 * CollusionNetwork — Interactive SVG Force-Directed Graph Visualizer
 * for the Procurement Integrity Graph (F05).
 *
 * Zero-dependency, pure React + SVG physics layout:
 * - Repulsion (Coulomb) + Link Springs (Hooke) + Centering
 * - Draggable nodes with real-time physics settling
 * - Exact vs Fuzzy matching edge styling
 * - Cluster color palette with glowing borders for collusion rings
 */
import React, { useEffect, useRef, useState, useCallback } from "react";

export interface GraphNode {
  id: string;
  label: string;
  submission_id: number;
  group: number; // 0=clean, 1..N=cluster
  suspicious: boolean;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  value: number; // confidence 0-1
  attributes: Array<{
    attribute: string;
    value: string;
    match: string;
    confidence: number;
  }>;
  match_type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
  metadata: {
    tender_id: number;
    node_count: number;
    link_count: number;
    cluster_count: number;
    risk_level: string;
    source: string;
  };
}

const CLUSTER_COLOURS = [
  "#6366f1", // indigo (clean)
  "#ef4444", // red    (cluster 1)
  "#f97316", // orange (cluster 2)
  "#eab308", // yellow (cluster 3)
  "#a855f7", // purple (cluster 4)
  "#ec4899", // pink   (cluster 5+)
];

function clusterColor(group: number): string {
  return CLUSTER_COLOURS[Math.min(group, CLUSTER_COLOURS.length - 1)] ?? "#6366f1";
}

interface Props {
  data: GraphData;
  width?: number;
  height?: number;
}

export function CollusionNetwork({ data, width = 640, height = 400 }: Props) {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredLink, setHoveredLink] = useState<GraphLink | null>(null);
  const draggingNodeRef = useRef<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const animFrameRef = useRef<number | null>(null);

  // Initialize node positions in a circle
  useEffect(() => {
    if (!data.nodes.length) {
      setNodes([]);
      return;
    }

    const n = data.nodes.length;
    const radius = Math.min(width, height) * 0.35;
    const centerX = width / 2;
    const centerY = height / 2;

    const initialNodes: GraphNode[] = data.nodes.map((node, i) => {
      const angle = (2 * Math.PI * i) / n;
      return {
        ...node,
        x: centerX + radius * Math.cos(angle) + (Math.random() - 0.5) * 20,
        y: centerY + radius * Math.sin(angle) + (Math.random() - 0.5) * 20,
        vx: 0,
        vy: 0,
      };
    });

    setNodes(initialNodes);
  }, [data, width, height]);

  // Run lightweight physics simulation loop
  useEffect(() => {
    if (nodes.length === 0) return;

    let localNodes = [...nodes];
    const centerX = width / 2;
    const centerY = height / 2;
    const kRepel = 4000;
    const kSpring = 0.04;
    const restLength = 110;
    const damping = 0.85;

    let step = 0;
    const maxSteps = 120; // settle after 120 frames

    const tick = () => {
      // Repulsion between all node pairs
      for (let i = 0; i < localNodes.length; i++) {
        for (let j = i + 1; j < localNodes.length; j++) {
          const a = localNodes[i];
          const b = localNodes[j];
          if (!a.x || !a.y || !b.x || !b.y) continue;

          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist > 300) continue;

          let force = kRepel / (dist * dist);
          let fx = (dx / dist) * force;
          let fy = (dy / dist) * force;

          if (draggingNodeRef.current !== a.id) {
            a.vx = (a.vx ?? 0) - fx;
            a.vy = (a.vy ?? 0) - fy;
          }
          if (draggingNodeRef.current !== b.id) {
            b.vx = (b.vx ?? 0) + fx;
            b.vy = (b.vy ?? 0) + fy;
          }
        }
      }

      // Spring attraction along links
      for (const link of data.links) {
        const sourceNode = localNodes.find((n) => n.id === link.source);
        const targetNode = localNodes.find((n) => n.id === link.target);
        if (!sourceNode || !targetNode || !sourceNode.x || !sourceNode.y || !targetNode.x || !targetNode.y) {
          continue;
        }

        const dx = targetNode.x - sourceNode.x;
        const dy = targetNode.y - sourceNode.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const displacement = dist - restLength;
        const force = displacement * kSpring;

        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (draggingNodeRef.current !== sourceNode.id) {
          sourceNode.vx = (sourceNode.vx ?? 0) + fx;
          sourceNode.vy = (sourceNode.vy ?? 0) + fy;
        }
        if (draggingNodeRef.current !== targetNode.id) {
          targetNode.vx = (targetNode.vx ?? 0) - fx;
          targetNode.vy = (targetNode.vy ?? 0) - fy;
        }
      }

      // Center gravity + update position
      for (const n of localNodes) {
        if (!n.x || !n.y) continue;
        if (draggingNodeRef.current !== n.id) {
          const gx = (centerX - n.x) * 0.01;
          const gy = (centerY - n.y) * 0.01;
          n.vx = ((n.vx ?? 0) + gx) * damping;
          n.vy = ((n.vy ?? 0) + gy) * damping;

          n.x += n.vx;
          n.y += n.vy;

          // Clamping inside box
          n.x = Math.max(30, Math.min(width - 30, n.x));
          n.y = Math.max(30, Math.min(height - 30, n.y));
        }
      }

      setNodes([...localNodes]);

      step++;
      if (step < maxSteps || draggingNodeRef.current !== null) {
        animFrameRef.current = requestAnimationFrame(tick);
      }
    };

    animFrameRef.current = requestAnimationFrame(tick);

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [data.links, width, height, nodes.length === 0]);

  // Drag handlers
  const handleMouseDown = (nodeId: string) => {
    draggingNodeRef.current = nodeId;
  };

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!draggingNodeRef.current || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      setNodes((prev) =>
        prev.map((n) =>
          n.id === draggingNodeRef.current
            ? { ...n, x: mouseX, y: mouseY, vx: 0, vy: 0 }
            : n
        )
      );
    },
    []
  );

  const handleMouseUp = () => {
    draggingNodeRef.current = null;
  };

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div className="relative rounded-xl border border-slate-700 bg-slate-900 overflow-hidden shadow-xl">
      {/* Header Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-700 bg-slate-800/80">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm text-slate-100 flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
            Procurement Integrity Graph (Collusion Engine)
          </span>
          <span className="text-xs text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-700">
            {data.metadata.node_count} bidders · {data.metadata.link_count} links · {data.metadata.cluster_count} collusion clusters
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
              data.metadata.risk_level === "critical"
                ? "bg-red-950 text-red-300 border border-red-800"
                : data.metadata.risk_level === "high"
                ? "bg-amber-950 text-amber-300 border border-amber-800"
                : "bg-emerald-950 text-emerald-300 border border-emerald-800"
            }`}
          >
            {data.metadata.risk_level} RISK
          </span>
          <span className="text-slate-400 font-mono text-[11px]">{data.metadata.source}</span>
        </div>
      </div>

      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="w-full select-none cursor-grab active:cursor-grabbing"
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <defs>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Links */}
        {data.links.map((link, idx) => {
          const s = nodeMap.get(link.source);
          const t = nodeMap.get(link.target);
          if (!s || !t || !s.x || !s.y || !t.x || !t.y) return null;

          const isHovered = hoveredLink === link;
          const strokeWidth = isHovered ? 3.5 : Math.max(1.5, link.value * 2.5);
          const isFuzzy = link.match_type === "fuzzy";
          const strokeColor = isFuzzy ? "#f97316" : "#ef4444";

          const midX = (s.x + t.x) / 2;
          const midY = (s.y + t.y) / 2;
          const attrLabel = (link.attributes || []).map((a) => a.attribute).join(", ");

          return (
            <g
              key={`link-${idx}`}
              onMouseEnter={() => setHoveredLink(link)}
              onMouseLeave={() => setHoveredLink(null)}
              className="cursor-pointer"
            >
              <line
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={strokeColor}
                strokeWidth={strokeWidth}
                strokeDasharray={isFuzzy ? "5,4" : undefined}
                strokeOpacity={isHovered ? 1.0 : 0.75}
              />
              {/* Midpoint link label badge */}
              <rect
                x={midX - (attrLabel.length * 3.2 + 6)}
                y={midY - 8}
                width={attrLabel.length * 6.4 + 12}
                height={16}
                rx={4}
                fill="#0f172a"
                stroke={strokeColor}
                strokeWidth={1}
                opacity={0.9}
              />
              <text
                x={midX}
                y={midY + 3}
                fill="#f1f5f9"
                fontSize={9}
                fontFamily="monospace"
                textAnchor="middle"
                pointerEvents="none"
              >
                {attrLabel}
              </text>
            </g>
          );
        })}

        {/* Nodes */}
        {nodes.map((node) => {
          if (!node.x || !node.y) return null;
          const isSelected = selectedNode?.id === node.id;
          const color = clusterColor(node.group);
          const radius = node.suspicious ? 22 : 16;

          return (
            <g
              key={node.id}
              transform={`translate(${node.x}, ${node.y})`}
              onMouseDown={() => handleMouseDown(node.id)}
              onClick={() => setSelectedNode(node)}
              className="cursor-pointer"
            >
              {/* Suspicious Ring Halo */}
              {node.suspicious && (
                <circle
                  r={radius + 6}
                  fill="none"
                  stroke={color}
                  strokeWidth={2}
                  strokeDasharray="4,2"
                  opacity={0.6}
                  className="animate-spin"
                  style={{ transformOrigin: "0 0" }}
                />
              )}
              {/* Main Node Circle */}
              <circle
                r={radius}
                fill={color}
                stroke={isSelected ? "#ffffff" : "#1e293b"}
                strokeWidth={isSelected ? 3 : 2}
                filter={node.suspicious ? "url(#glow)" : undefined}
              />
              {/* Label */}
              <text
                dy={radius + 14}
                fill="#f8fafc"
                fontSize={11}
                fontWeight={node.suspicious ? "bold" : "normal"}
                textAnchor="middle"
                className="select-none pointer-events-none drop-shadow"
              >
                {node.label.length > 15 ? `${node.label.slice(0, 13)}…` : node.label}
              </text>
              {/* Badge text inside node */}
              <text
                dy={4}
                fill="#ffffff"
                fontSize={9}
                fontWeight="bold"
                textAnchor="middle"
                className="select-none pointer-events-none"
              >
                #{node.submission_id}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Selected Node / Link Detail Box */}
      {selectedNode && (
        <div className="p-3 bg-slate-800/90 border-t border-slate-700 text-xs flex items-center justify-between">
          <div>
            <span className="font-semibold text-slate-200">{selectedNode.label}</span>
            <span className="text-slate-400 ml-2">Submission #{selectedNode.submission_id}</span>
            <span className="ml-2 px-2 py-0.5 rounded text-[11px] font-medium" style={{ backgroundColor: clusterColor(selectedNode.group), color: '#fff' }}>
              {selectedNode.group === 0 ? "Clean (No cross-bidder links)" : `Cluster ${selectedNode.group} (Collusion Ring)`}
            </span>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-700/60"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Legend Footer */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2 border-t border-slate-700 bg-slate-800/50 text-xs text-slate-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 inline-block" />
            Independent Bidder
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block" />
            Collusion Ring (Cluster)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-5 h-0.5 bg-red-500 inline-block" />
            Exact Shared Identifier (PAN/GSTIN/Bank/Phone)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-5 h-0.5 border-t border-dashed border-orange-500 inline-block" />
            Fuzzy Match (Address / Signatory)
          </span>
        </div>
        <span className="text-[11px] text-slate-500 italic">Drag nodes to rearrange topology</span>
      </div>
    </div>
  );
}
