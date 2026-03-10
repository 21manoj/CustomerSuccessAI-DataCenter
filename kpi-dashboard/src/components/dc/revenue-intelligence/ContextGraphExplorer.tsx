import { useState } from "react";

// ===================================================================
// Interactive Context Graph Explorer
// Renders the Signal → Decision → Outcome causal chain with
// stakeholder connections. Click any node to highlight its edges.
// ===================================================================

const NODES = [
  { id: "n1987", type: "stakeholder", label: "Allison Hill", sub: "VP Engineering", x: 100, y: 50 },
  { id: "n1988", type: "stakeholder", label: "Angie Henderson", sub: "CTO", x: 400, y: 50 },
  { id: "n1990", type: "stakeholder", label: "Abigail Shaffer", sub: "CSM", x: 650, y: 50 },
  { id: "n1989", type: "stakeholder", label: "Cristian Santos", sub: "Infrastructure Dir.", x: 850, y: 50 },
  { id: "n2402", type: "signal", label: "Jun 26", sub: "QBR with CTO & VP Eng", x: 100, y: 190 },
  { id: "n2287", type: "decision", label: "Jul 11", sub: "Approve POC — LLM Fine-Tuning", x: 400, y: 190 },
  { id: "n2403", type: "signal", label: "Jul 10", sub: "VP Eng proposes POC", x: 100, y: 310 },
  { id: "n2404", type: "signal", label: "Jul 28", sub: "POC deployed successfully", x: 650, y: 310 },
  { id: "n2405", type: "signal", label: "Aug 27", sub: "GPU utilization crosses 70%", x: 100, y: 430 },
  { id: "n2406", type: "signal", label: "Sep 10", sub: "GPU hits 75% — key threshold", x: 100, y: 540 },
  { id: "n2407", type: "signal", label: "Oct 02", sub: "CSM-led capacity planning", x: 650, y: 540 },
  { id: "n2408", type: "signal", label: "Oct 20", sub: "GPU hits 85%. Training impacted", x: 100, y: 650 },
  { id: "n2288", type: "decision", label: "Oct 20", sub: "Request Capacity Expansion Budget", x: 850, y: 650 },
  { id: "n2409", type: "signal", label: "Nov 03", sub: "Critical GPU memory exhaustion", x: 100, y: 760 },
  { id: "n2410", type: "signal", label: "Nov 19", sub: "VP Eng escalates to CTO", x: 400, y: 760 },
  { id: "n2334", type: "outcome", label: "Dec 03", sub: "$2.2M protected\nDisplacement Risk Averted", x: 650, y: 760 },
  { id: "n2411", type: "signal", label: "Dec 19", sub: "CTO approves $5.2M expansion", x: 400, y: 870 },
  { id: "n2412", type: "signal", label: "Jan 02", sub: "Technical deep-dive with Infra", x: 850, y: 870 },
];

const EDGES = [
  { from: "n2402", to: "n2403", label: "LED TO" },
  { from: "n2403", to: "n2405", label: "LED TO" },
  { from: "n2287", to: "n2405", label: "LED TO" },
  { from: "n2405", to: "n2406", label: "LED TO" },
  { from: "n2406", to: "n2408", label: "LED TO" },
  { from: "n2408", to: "n2409", label: "LED TO" },
  { from: "n2409", to: "n2410", label: "LED TO" },
  { from: "n2409", to: "n2288", label: "LED TO" },
  { from: "n2409", to: "n2334", label: "INDICATES" },
  { from: "n2407", to: "n2410", label: "INDICATES" },
  { from: "n2410", to: "n2411", label: "LED TO" },
  { from: "n1987", to: "n2287", label: "INVOLVES" },
  { from: "n1987", to: "n2288", label: "INVOLVES" },
  { from: "n1988", to: "n2288", label: "INVOLVES" },
];

const STYLES: Record<string, { bg: string; border: string; text: string }> = {
  signal:      { bg: "#FFA500", border: "#cc8400", text: "#000" },
  decision:    { bg: "#4169E1", border: "#2a4db5", text: "#fff" },
  outcome:     { bg: "#2E8B57", border: "#1e6b40", text: "#fff" },
  stakeholder: { bg: "#8B5CF6", border: "#6d3fd4", text: "#fff" },
};

const NW = 160;
const NH = 54;

interface GraphNode {
  id: string;
  type: string;
  label: string;
  sub: string;
  x: number;
  y: number;
}

interface GraphEdge {
  from: string;
  to: string;
  label: string;
}

function getCenter(node: GraphNode) {
  return { cx: node.x + NW / 2, cy: node.y + NH / 2 };
}

function NodeShape({
  node,
  dimmed,
  onClick,
}: {
  node: GraphNode;
  dimmed: boolean;
  onClick: (node: GraphNode) => void;
}) {
  const s = STYLES[node.type];
  const { x, y } = node;
  const cx = x + NW / 2;
  const cy = y + NH / 2;
  const opacity = dimmed ? 0.25 : 1;

  return (
    <g
      onClick={() => onClick(node)}
      style={{ cursor: "pointer", opacity, transition: "opacity 0.2s" }}
    >
      {node.type === "stakeholder" ? (
        <circle cx={cx} cy={cy} r={32} fill={s.bg} stroke={s.border} strokeWidth={2} />
      ) : node.type === "decision" ? (
        <polygon
          points={`${cx},${y} ${x + NW},${cy} ${cx},${y + NH} ${x},${cy}`}
          fill={s.bg}
          stroke={s.border}
          strokeWidth={2}
        />
      ) : (
        <rect
          x={x}
          y={y}
          width={NW}
          height={NH}
          rx={7}
          fill={s.bg}
          stroke={s.border}
          strokeWidth={node.type === "outcome" ? 3 : 2}
        />
      )}
      <text
        x={cx}
        y={cy - 8}
        textAnchor="middle"
        fill={s.text}
        fontSize={11}
        fontWeight={800}
        fontFamily="'Courier New', monospace"
      >
        {node.label}
      </text>
      <foreignObject x={x + 4} y={cy + 3} width={NW - 8} height={30}>
        <div
          style={{
            fontSize: 9,
            color: s.text,
            textAlign: "center",
            lineHeight: 1.3,
            fontFamily: "monospace",
            whiteSpace: "pre-wrap",
            opacity: 0.9,
          }}
        >
          {node.sub}
        </div>
      </foreignObject>
    </g>
  );
}

function EdgeLine({
  edge,
  nodes,
  dimmed,
}: {
  edge: GraphEdge;
  nodes: GraphNode[];
  dimmed: boolean;
}) {
  const fn = nodes.find((n) => n.id === edge.from);
  const tn = nodes.find((n) => n.id === edge.to);
  if (!fn || !tn) return null;

  const { cx: x1, cy: y1 } = getCenter(fn);
  const { cx: x2, cy: y2 } = getCenter(tn);
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const id = `arr-${edge.from}-${edge.to}`;
  const color = dimmed ? "#333" : "#666";
  const dash =
    edge.label === "INVOLVES" ? "5,4" : edge.label === "INDICATES" ? "3,3" : "0";

  return (
    <g style={{ opacity: dimmed ? 0.15 : 1, transition: "opacity 0.2s" }}>
      <defs>
        <marker id={id} markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill={color} />
        </marker>
      </defs>
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray={dash}
        markerEnd={`url(#${id})`}
      />
      <text x={mx} y={my - 5} textAnchor="middle" fill={color} fontSize={8} fontFamily="monospace">
        {edge.label}
      </text>
    </g>
  );
}

export default function ContextGraphExplorer() {
  const [selected, setSelected] = useState<string | null>(null);

  const connectedEdges = selected
    ? EDGES.filter((e) => e.from === selected || e.to === selected)
    : [];
  const connectedIds = new Set(connectedEdges.flatMap((e) => [e.from, e.to]));
  const activeNode = NODES.find((n) => n.id === selected);

  const isNodeDimmed = (id: string) => !!selected && !connectedIds.has(id);
  const isEdgeDimmed = (e: GraphEdge) => !!selected && !connectedEdges.includes(e);

  return (
    <div
      style={{
        display: "flex",
        height: "100vh",
        background: "#0d1117",
        color: "#e6edf3",
        fontFamily: "monospace",
      }}
    >
      {/* Graph */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {/* Header */}
        <div
          style={{
            padding: "14px 24px 10px",
            borderBottom: "1px solid #21262d",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontSize: 10, color: "#8b949e", letterSpacing: 2, textTransform: "uppercase" }}>
              Account #300001 — Kacme Production
            </div>
            <div style={{ fontSize: 18, fontWeight: 800 }}>Context Graph Explorer</div>
          </div>
          <div style={{ display: "flex", gap: 14 }}>
            {Object.entries(STYLES).map(([type, s]) => (
              <span
                key={type}
                style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10, color: "#8b949e" }}
              >
                <span
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: type === "stakeholder" ? "50%" : 2,
                    background: s.bg,
                    display: "inline-block",
                  }}
                />
                {type.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
        <svg
          width={1060}
          height={970}
          onClick={(e) => {
            if ((e.target as SVGElement).tagName === "svg") setSelected(null);
          }}
        >
          {EDGES.map((e, i) => (
            <EdgeLine key={i} edge={e} nodes={NODES} dimmed={isEdgeDimmed(e)} />
          ))}
          {NODES.map((n) => (
            <NodeShape
              key={n.id}
              node={n}
              dimmed={isNodeDimmed(n.id)}
              onClick={(node) => setSelected((prev) => (prev === node.id ? null : node.id))}
            />
          ))}
        </svg>
      </div>

      {/* Side Panel */}
      <div
        style={{
          width: 250,
          borderLeft: "1px solid #21262d",
          padding: 20,
          background: "#0d1117",
          overflowY: "auto",
        }}
      >
        {activeNode ? (
          <>
            <div
              style={{
                fontSize: 9,
                color: "#8b949e",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 6,
              }}
            >
              {activeNode.type}
            </div>
            <div
              style={{
                fontSize: 15,
                fontWeight: 800,
                color: STYLES[activeNode.type].bg,
                marginBottom: 4,
              }}
            >
              {activeNode.label}
            </div>
            <div
              style={{
                fontSize: 12,
                color: "#c9d1d9",
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
                marginBottom: 18,
              }}
            >
              {activeNode.sub}
            </div>
            <div
              style={{
                fontSize: 9,
                color: "#8b949e",
                textTransform: "uppercase",
                letterSpacing: 2,
                marginBottom: 10,
              }}
            >
              Connections ({connectedEdges.length})
            </div>
            {connectedEdges.map((e, i) => {
              const otherId = e.from === selected ? e.to : e.from;
              const other = NODES.find((n) => n.id === otherId);
              const dir = e.from === selected ? "\u2192" : "\u2190";
              return other ? (
                <div
                  key={i}
                  style={{
                    marginBottom: 10,
                    padding: "8px 10px",
                    background: "#161b22",
                    borderRadius: 6,
                    borderLeft: `3px solid ${STYLES[other.type].bg}`,
                    cursor: "pointer",
                  }}
                  onClick={() => setSelected(otherId)}
                >
                  <div style={{ fontSize: 9, color: "#8b949e", marginBottom: 3 }}>
                    {dir} {e.label}
                  </div>
                  <div style={{ fontSize: 11, fontWeight: 700 }}>{other.label}</div>
                  <div style={{ fontSize: 10, color: "#8b949e" }}>{other.sub}</div>
                </div>
              ) : null;
            })}
            <button
              onClick={() => setSelected(null)}
              style={{
                marginTop: 10,
                width: "100%",
                background: "transparent",
                border: "1px solid #30363d",
                color: "#8b949e",
                padding: "6px 0",
                borderRadius: 6,
                cursor: "pointer",
                fontSize: 11,
              }}
            >
              Clear Selection
            </button>
          </>
        ) : (
          <div style={{ fontSize: 12, color: "#8b949e", lineHeight: 1.7 }}>
            <div style={{ fontWeight: 800, color: "#e6edf3", marginBottom: 8, fontSize: 13 }}>
              Explore the graph
            </div>
            Click any node to highlight its connections.
            <div style={{ marginTop: 20, display: "flex", flexDirection: "column", gap: 10 }}>
              <div
                style={{
                  padding: "12px",
                  background: "#161b22",
                  borderRadius: 8,
                  borderLeft: "3px solid #2E8B57",
                }}
              >
                <div style={{ color: "#2E8B57", fontWeight: 800, fontSize: 13 }}>$2.2M Protected</div>
                <div style={{ fontSize: 10, marginTop: 3 }}>Competitive displacement risk averted</div>
              </div>
              <div
                style={{
                  padding: "12px",
                  background: "#161b22",
                  borderRadius: 8,
                  borderLeft: "3px solid #4169E1",
                }}
              >
                <div style={{ color: "#4169E1", fontWeight: 800, fontSize: 13 }}>$5.2M Approved</div>
                <div style={{ fontSize: 10, marginTop: 3 }}>CTO-approved capacity expansion</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
