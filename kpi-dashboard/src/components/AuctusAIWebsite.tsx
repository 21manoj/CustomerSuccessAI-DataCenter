import { useState, useEffect } from "react";
const PILLARS = [
  { id:"P1", name:"Deployment Velocity",     weight:"15%", color:"#0EA5E9", kpis:["Time-to-First-Workload","Installation Completion Rate","Configuration Accuracy","Deployment Cycle Time","Hardware Commissioning Time","Network Readiness Score","Deployment Team Velocity","Documentation Completeness"] },
  { id:"P2", name:"Operational Stability",   weight:"20%", color:"#10B981", kpis:["RMA Frequency Rate","MTBF (Mean Time Between Failures)","Critical Incidents (30d)","System Uptime Percentage","Thermal Management Score","Power Efficiency (PUE)","Mean Time To Repair (MTTR)","Preventive Maintenance Compliance"] },
  { id:"P3", name:"AI Workload Performance", weight:"25%", color:"#8B5CF6", kpis:["GPU Utilization Rate","Training Job Completion Rate","Inference Latency (P95)","Model Training Time","GPU Memory Efficiency","Distributed Training Efficiency","Workload Diversity Score","Batch Processing Throughput"] },
  { id:"P4", name:"Channel & Partner Health",weight:"15%", color:"#F59E0B", kpis:["Partner Engagement Score","VAR Performance Rating","Joint QBR Frequency","Channel Conflict Score","Co-selling Opportunities","Partner NPS"] },
  { id:"P5", name:"Expansion Readiness",     weight:"25%", color:"#EF4444", kpis:["Capacity Utilization Rate","Capacity Utilization Trajectory","Workload Growth Velocity","Compute Hour Consumption Trend","Budget Availability Signals","New Use Case Adoption","Expansion Probability (90d)","Technical Champion Engagement"] },
];
const FEATURES = [
  { icon:"\u{1F9E0}", title:"Context Graph Intelligence",  desc:"Signal \u2192 Decision \u2192 Outcome causal chains across every account. 8 story arcs map real revenue narratives \u2014 from silent churn to expansion champion.",  tag:"Revenue Intel",     tagColor:"#EF4444" },
  { icon:"\u{1F916}", title:"20+ MCP Tools via Claude",    desc:"Fully integrated with Claude. Account health, revenue at risk, causal chains, ROI stories, CSM actions \u2014 all queryable through natural language.",           tag:"AI Integration",   tagColor:"#6366F1" },
  { icon:"\u{1F4B0}", title:"Power-of-1 Revenue Model",    desc:"Calculate the revenue impact of a 1% improvement in any business metric \u2014 NRR, GRR, expansion rate, TTFV. Connects operational KPIs to dollar outcomes.",    tag:"Revenue Intel",    tagColor:"#EF4444" },
  { icon:"\u{1F4C8}", title:"ROI Engine & Portfolio Story", desc:"Historical proof of value delivered + forward projections + bridging narrative. Per-account and portfolio-level ROI stories with trajectory assessment.",          tag:"Revenue Intel",    tagColor:"#10B981" },
  { icon:"\u{1F50D}", title:"Signal Analyst Agent",         desc:"AI agent combining 38 KPIs from PostgreSQL with qualitative signals from Qdrant into natural-language health recommendations with early-warning flags.",          tag:"Agentic AI",       tagColor:"#8B5CF6" },
  { icon:"\u{1F3AF}", title:"Playbook Orchestration",       desc:"5 trigger-based playbooks with severity routing. VoC Sprint, Activation Blitz, SLA Stabilizer, Renewal Safeguard, Expansion Timing \u2014 each with named CSM owner.", tag:"Automation",   tagColor:"#F59E0B" },
  { icon:"\u2699\uFE0F", title:"Wizard A / B / C Pipeline",  desc:"Journey Generator, Pattern Analyzer, and Weight Optimizer run on onboarding and monthly recalibration. Weights converge to your actual outcomes.",               tag:"ML Pipeline",      tagColor:"#0EA5E9" },
  { icon:"\u{1F3E2}", title:"Multi-Tenant Architecture",    desc:"UUID-based fully isolated customer environments. Independent Qdrant collections and PostgreSQL schemas. Zero cross-tenant data exposure.",                       tag:"Enterprise",       tagColor:"#0369A1" },
];
const VERTICALS = [
  { label:"AI Chip Cos",        icon:"\u{1F9EC}", color:"#0EA5E9" },
  { label:"Server OEMs",        icon:"\u{1F5A5}\uFE0F", color:"#10B981" },
  { label:"Data Centers",       icon:"\u{1F3ED}", color:"#8B5CF6" },
  { label:"Cloud Infra",        icon:"\u2601\uFE0F", color:"#F59E0B" },
  { label:"AI Infrastructure",  icon:"\u26A1",     color:"#EF4444" },
  { label:"Colocation",         icon:"\u{1F310}", color:"#EC4899" },
];
function HealthBar({ score, color }: { score: number; color?: string }) {
  const auto = score >= 70 ? "#10B981" : score >= 50 ? "#F59E0B" : "#EF4444";
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8 }}>
      <div style={{ flex:1, height:5, background:"#1E293B", borderRadius:999 }}>
        <div style={{ width:`${score}%`, height:"100%", background:color||auto, borderRadius:999 }} />
      </div>
      <span style={{ fontSize:11, fontWeight:700, color:color||auto, minWidth:24 }}>{score}</span>
    </div>
  );
}
const CARPET = [
  { label:"REVENUE INTELLIGENCE",   color:"#DC2626", rim:"#FCA5A5", rx:260, ry:52, thickness:14, zOff:-10 },
  { label:"CONTEXT GRAPH",          color:"#991B1B", rim:"#F87171", rx:320, ry:64, thickness:11, zOff:-36 },
  { label:"MCP INTEGRATION LAYER",  color:"#7F1D1D", rim:"#FCA5A5", rx:390, ry:78, thickness: 8, zOff:-62 },
];
function HexPrism() {
  const [angle, setAngle] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setAngle(a => (a + 0.3) % 360), 30);
    return () => clearInterval(id);
  }, []);
  const FW = 170, FH = 190, APO = 147;
  return (
    <div style={{ width:"100%", display:"flex", justifyContent:"center", padding:"50px 0 60px", position:"relative" }}>
      <div style={{ position:"absolute", inset:0, display:"flex", justifyContent:"center", alignItems:"center", pointerEvents:"none" }}>
        <div style={{ width:800, height:800, borderRadius:"50%", background:"radial-gradient(circle,rgba(14,165,233,0.06) 0%,transparent 65%)" }} />
      </div>
      <div style={{ width:700, height:680, flexShrink:0, position:"relative", zIndex:2 }}>
        <div style={{ perspective:1100, perspectiveOrigin:"50% 32%", width:"100%", height:"100%" }}>
          <div style={{ width:"100%", height:"100%", position:"relative", transformStyle:"preserve-3d", transform:"rotateX(-20deg)" }}>
            {[...CARPET].reverse().map((disc) => {
              const W = disc.rx * 2, H = disc.ry * 2;
              const a = disc.rx * 0.87, b = disc.ry * 0.80;
              const cx = disc.rx, cy = disc.ry;
              const arcPath = `M ${cx - a},${cy} A ${a},${b} 0 1,1 ${cx + a},${cy} A ${a},${b} 0 1,1 ${cx - a},${cy}`;
              const perim = Math.PI * (3*(a+b) - Math.sqrt((3*a+b)*(a+3*b)));
              const spread = perim * 0.55;
              const chars = disc.label.length;
              const ls = Math.max(4, Math.round((spread - chars * 9) / chars));
              const uid = `arc${disc.rx}`;
              return (
                <div key={disc.label} style={{
                  position:"absolute",
                  left:"50%", top:"64%",
                  width: W, height: H,
                  marginLeft: -disc.rx,
                  marginTop: -disc.ry,
                  transformStyle:"preserve-3d",
                  transform:`translateZ(${disc.zOff}px)`,
                  pointerEvents:"none",
                }}>
                  <div style={{ position:"absolute", inset:0, borderRadius:"50%", background:`radial-gradient(ellipse at 40% 35%, ${disc.color}60 0%, ${disc.color}20 50%, transparent 72%)`, border:`1.5px solid ${disc.rim}70`, boxShadow:`0 0 48px ${disc.color}55, inset 0 0 28px ${disc.color}28` }} />
                  <div style={{ position:"absolute", inset:-4, borderRadius:"50%", border:`1px solid ${disc.rim}28`, boxShadow:`0 0 20px ${disc.color}44` }} />
                  <div style={{ position:"absolute", left:"4%", right:"4%", bottom:-disc.thickness, height:disc.thickness, borderRadius:"0 0 50% 50% / 0 0 100% 100%", background:`linear-gradient(180deg,${disc.color}99,${disc.color}11)`, filter:"blur(1px)" }} />
                  <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ position:"absolute", inset:0, overflow:"visible" }}>
                    <defs>
                      <path id={uid} d={arcPath} />
                      <filter id={`glow${disc.rx}`}>
                        <feGaussianBlur stdDeviation="2" result="blur" />
                        <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
                      </filter>
                    </defs>
                    <text filter={`url(#glow${disc.rx})`}>
                      <textPath
                        href={`#${uid}`}
                        startOffset="25%"
                        textAnchor="middle"
                        fill={disc.rim}
                        fontSize={11}
                        fontWeight="800"
                        fontFamily="DM Sans, system-ui"
                        letterSpacing={ls}
                      >
                        {disc.label}
                      </textPath>
                    </text>
                  </svg>
                </div>
              );
            })}
            <div style={{
              position:"absolute",
              left:"50%", top:"6%",
              width:FW, height:FH,
              marginLeft:-FW/2,
              transformStyle:"preserve-3d",
              transform:`rotateY(${angle}deg)`,
            }}>
              <div style={{ position:"absolute", width:FW, height:FW, left:0, top:`-${FW/2-10}px`, transformStyle:"preserve-3d", transform:"rotateX(90deg)", background:"conic-gradient(from 0deg,#0EA5E940,#10B98140,#8B5CF640,#F59E0B40,#EF444440,#EC489940,#0EA5E940)", clipPath:"polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)", filter:"blur(1px)" }} />
              <div style={{ position:"absolute", width:FW, height:FW, left:0, bottom:`-${FW/2-10}px`, transformStyle:"preserve-3d", transform:"rotateX(-90deg)", background:"conic-gradient(from 0deg,#0EA5E920,#10B98120,#8B5CF620,#F59E0B20,#EF444420,#EC489920,#0EA5E920)", clipPath:"polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)", filter:"blur(2px)" }} />
              {VERTICALS.map((v, i) => (
                <div key={v.label} style={{ position:"absolute", width:FW, height:FH, left:0, top:0, backfaceVisibility:"hidden", transform:`rotateY(${i*60}deg) translateZ(${APO}px)`, background:`linear-gradient(160deg,${v.color}18 0%,${v.color}08 100%)`, border:`1px solid ${v.color}55`, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", gap:10, borderRadius:4, boxShadow:`inset 0 0 30px ${v.color}15,0 0 40px ${v.color}20` }}>
                  <div style={{ fontSize:34 }}>{v.icon}</div>
                  <div style={{ fontSize:13, fontWeight:700, color:"#E2E8F0", textAlign:"center", lineHeight:1.3, padding:"0 12px" }}>{v.label}</div>
                  <div style={{ width:32, height:2, borderRadius:999, background:v.color, opacity:0.7 }} />
                  <div style={{ fontSize:10, color:v.color, fontWeight:600, letterSpacing:"0.08em", textTransform:"uppercase" }}>Segment</div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div style={{ position:"absolute", bottom:0, left:0, right:0, textAlign:"center" }}>
          <div style={{ fontSize:11, fontWeight:700, color:"#EF4444", letterSpacing:"0.1em", textTransform:"uppercase", marginBottom:4 }}>Customer Intelligence Engine</div>
          <div style={{ fontSize:13, color:"#475569" }}>One platform. Every segment. Signal-driven revenue intelligence.</div>
        </div>
      </div>
    </div>
  );
}
function SectionImg({ src, alt, height }: { src: string; alt: string; height?: number }) {
  return (
    <div style={{ borderRadius:18, overflow:"hidden", border:"1px solid rgba(255,255,255,0.07)", boxShadow:"0 24px 80px rgba(0,0,0,0.5)" }}>
      <img src={src} alt={alt} style={{ width:"100%", height:height||260, objectFit:"cover", display:"block", filter:"brightness(0.82) saturate(1.15)" }} />
    </div>
  );
}
export default function AuctusAIWebsite() {
  const [activePillar, setActivePillar] = useState(0);
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior:"smooth" });
  return (
    <div style={{ fontFamily:"'DM Sans',system-ui,sans-serif", background:"#060B18", color:"#E2E8F0", overflowX:"hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,500;9..40,700;9..40,800&family=Sora:wght@700;800&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;}
        html{scroll-behavior:smooth;}
        ::selection{background:#0EA5E9;color:#fff;}
        .gt{background:linear-gradient(135deg,#0EA5E9 0%,#818CF8 60%,#EC4899 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
        .glass{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:18px;transition:all .3s;}
        .glass:hover{background:rgba(255,255,255,0.055);border-color:rgba(14,165,233,0.3);transform:translateY(-4px);box-shadow:0 20px 60px rgba(0,0,0,0.4);}
        .pill{display:inline-flex;align-items:center;gap:6px;padding:4px 12px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;}
        .btnp{background:linear-gradient(135deg,#0EA5E9,#6366F1);color:#fff;border:none;cursor:pointer;font-weight:700;border-radius:10px;transition:all .25s;font-family:inherit;}
        .btnp:hover{transform:translateY(-2px);box-shadow:0 8px 32px rgba(14,165,233,0.4);}
        .btng{background:transparent;border:1.5px solid rgba(255,255,255,0.15);color:#E2E8F0;cursor:pointer;font-weight:600;border-radius:10px;transition:all .25s;font-family:inherit;}
        .btng:hover{border-color:#0EA5E9;color:#0EA5E9;}
        .nl{color:#94A3B8;font-size:14px;font-weight:500;cursor:pointer;transition:color .2s;text-decoration:none;background:none;border:none;padding:0;}
        .nl:hover{color:#0EA5E9;}
        .gdbg{background-image:linear-gradient(rgba(14,165,233,0.03) 1px,transparent 1px),linear-gradient(90deg,rgba(14,165,233,0.03) 1px,transparent 1px);background-size:60px 60px;}
        .divider{height:1px;background:linear-gradient(90deg,transparent,rgba(14,165,233,0.25),transparent);max-width:700px;margin:0 auto;}
        .pt{padding:6px 16px;border-radius:10px;cursor:pointer;font-size:13px;font-weight:600;transition:all .2s;white-space:nowrap;border:1.5px solid rgba(255,255,255,0.06);background:transparent;color:#64748B;font-family:inherit;}
        .pt:hover{color:#94A3B8;}
        .ptact{color:#fff !important;}
        @keyframes fadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
        @keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-10px)}}
        .fu{animation:fadeUp .7s ease forwards;}
        .fl{animation:float 4s ease-in-out infinite;}
      `}</style>
      {/* NAV */}
      <nav style={{ position:"fixed",top:0,left:0,right:0,zIndex:100,padding:"0 24px",height:60,display:"flex",alignItems:"center",justifyContent:"space-between",background:"rgba(6,11,24,0.92)",backdropFilter:"blur(20px)",borderBottom:"1px solid rgba(255,255,255,0.05)" }}>
        <div style={{ display:"flex",alignItems:"center",gap:10 }}>
          <div style={{ width:34,height:34,borderRadius:9,background:"linear-gradient(135deg,#0EA5E9,#6366F1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18 }}>{"\u26A1"}</div>
          <div>
            <div style={{ fontFamily:"Sora,sans-serif",fontWeight:800,fontSize:17,letterSpacing:"-0.02em",color:"#F1F5F9" }}>AuctusAI</div>
            <div style={{ fontSize:9,color:"#475569",letterSpacing:".1em",textTransform:"uppercase",marginTop:-2 }}>Customer Intelligence Platform</div>
          </div>
        </div>
        <div style={{ display:"flex",alignItems:"center",gap:28 }}>
          {["Platform","Segments","Context Graph","Revenue Intel","MCP Tools"].map((l,i)=>(
            <button key={l} className="nl" onClick={()=>scrollTo(["platform","verticals","context-graph","rev-intel","mcp-tools"][i])}>{l}</button>
          ))}
        </div>
        <div style={{ display:"flex",gap:10 }}>
          <button className="btng" style={{ padding:"8px 18px",fontSize:13 }}>Sign In</button>
          <button className="btnp" style={{ padding:"9px 22px",fontSize:13 }} onClick={()=>scrollTo("contact")}>Request Demo</button>
        </div>
      </nav>
      {/* HERO */}
      <section id="verticals" style={{ paddingTop:60,position:"relative",overflow:"hidden" }} className="gdbg">
        <div style={{ position:"absolute",top:"10%",left:"50%",transform:"translateX(-50%)",width:800,height:800,borderRadius:"50%",background:"radial-gradient(circle,rgba(14,165,233,0.08) 0%,transparent 65%)",pointerEvents:"none" }} />
        <div style={{ maxWidth:1100,margin:"0 auto",padding:"60px 24px 0",textAlign:"center" }}>
          <div className="pill fu" style={{ background:"rgba(14,165,233,0.1)",color:"#38BDF8",border:"1px solid rgba(14,165,233,0.2)",marginBottom:20 }}>
            <span style={{ width:6,height:6,borderRadius:"50%",background:"#38BDF8",display:"inline-block" }} />
            Customer Intelligence &middot; Revenue Intelligence &middot; AI-Native
          </div>
          <h1 className="fu" style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(36px,4.5vw,62px)",fontWeight:800,lineHeight:1.08,letterSpacing:"-0.03em",marginBottom:20 }}>
            Know Which Accounts Will Expand.<br /><span className="gt">Before They Tell You.</span>
          </h1>
          <p className="fu" style={{ fontSize:18,color:"#64748B",maxWidth:620,margin:"0 auto 16px",lineHeight:1.7 }}>
            CS Pulse transforms deployment signals, channel health, and capacity trajectories into revenue intelligence &mdash; surfacing expansion-ready accounts and silent churn risks across your installed base.
          </p>
          <p className="fu" style={{ fontSize:14,color:"#475569",maxWidth:500,margin:"0 auto 0" }}>
            Purpose-built for AI chip companies, server OEMs, and data centers. 38 KPIs. 5 pillars. 20+ Claude MCP tools.
          </p>
        </div>
        <HexPrism />
      </section>
      {/* STATS BAR */}
      <div style={{ background:"rgba(255,255,255,0.02)",borderTop:"1px solid rgba(255,255,255,0.05)",borderBottom:"1px solid rgba(255,255,255,0.05)",padding:"28px 24px" }}>
        <div style={{ maxWidth:1100,margin:"0 auto",display:"flex",justifyContent:"space-around",flexWrap:"wrap",gap:24 }}>
          {[["38","KPIs Across 5 Pillars"],["5","Trigger-Based Playbooks"],["20+","Claude MCP Tools"],["8","Revenue Story Arcs"],["0.92","Expansion Correlation"]].map(([v,l])=>(
            <div key={l} style={{ textAlign:"center" }}>
              <div style={{ fontFamily:"Sora,sans-serif",fontSize:26,fontWeight:800,color:"#F1F5F9",whiteSpace:"pre-line",lineHeight:1.2 }}>{v}</div>
              <div style={{ fontSize:12,color:"#475569",marginTop:4 }}>{l}</div>
            </div>
          ))}
        </div>
      </div>
      {/* PLATFORM FEATURES */}
      <section id="platform" style={{ padding:"90px 24px" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center",marginBottom:60 }}>
            <div>
              <div className="pill" style={{ background:"rgba(14,165,233,0.1)",color:"#38BDF8",border:"1px solid rgba(14,165,233,0.2)",marginBottom:16 }}>Platform Capabilities</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:16 }}>Full-Stack<br /><span className="gt">Revenue Intelligence</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75 }}>From context graph causal chains to Power-of-1 revenue modeling and Claude MCP integration &mdash; CS Pulse covers the entire post-sale intelligence lifecycle with explainable, auditable AI.</p>
            </div>
            <SectionImg src="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&q=80" alt="Enterprise data center" height={260} />
          </div>
          <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(280px,1fr))",gap:18 }}>
            {FEATURES.map(f=>(
              <div key={f.title} className="glass" style={{ padding:"26px" }}>
                <div style={{ display:"flex",alignItems:"flex-start",justifyContent:"space-between",marginBottom:14 }}>
                  <div style={{ fontSize:32 }}>{f.icon}</div>
                  <div className="pill" style={{ background:`${f.tagColor}18`,color:f.tagColor,border:`1px solid ${f.tagColor}33` }}>{f.tag}</div>
                </div>
                <h3 style={{ fontSize:16,fontWeight:700,color:"#F1F5F9",marginBottom:8,fontFamily:"Sora,sans-serif" }}>{f.title}</h3>
                <p style={{ fontSize:13,color:"#64748B",lineHeight:1.7 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* CONTEXT GRAPH */}
      <section id="context-graph" style={{ padding:"90px 24px",background:"rgba(255,255,255,0.01)" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center",marginBottom:50 }}>
            <div>
              <div className="pill" style={{ background:"rgba(239,68,68,0.1)",color:"#FCA5A5",border:"1px solid rgba(239,68,68,0.2)",marginBottom:16 }}>Context Graph</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:16 }}>Signal &rarr; Decision &rarr;<br /><span className="gt">Revenue Outcome</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75,marginBottom:20 }}>Every account has a causal chain. GPU utilization drops &rarr; deployment team investigates &rarr; workload migration prevents $2.4M churn. CS Pulse maps these chains automatically from your operational signals.</p>
              <div style={{ display:"flex",flexDirection:"column",gap:10 }}>
                {[
                  ["Signal","GPU utilization drops below 60% for 14 days","#EF4444"],
                  ["Decision","CSM triggers SLA Stabilizer playbook + QBR","#F59E0B"],
                  ["Outcome","Workload restored, expansion pipeline reopened","#10B981"],
                ].map(([stage,desc,color])=>(
                  <div key={stage} style={{ display:"flex",gap:12,padding:"12px 16px",background:"rgba(255,255,255,0.03)",borderRadius:11,border:`1px solid ${color}33`,borderLeft:`3px solid ${color}` }}>
                    <div style={{ fontSize:11,fontWeight:800,color,minWidth:60,textTransform:"uppercase",letterSpacing:".06em" }}>{stage}</div>
                    <div style={{ fontSize:13,color:"#94A3B8" }}>{desc}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display:"flex",flexDirection:"column",gap:16 }}>
              <SectionImg src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=800&q=80" alt="Analytics visualization" height={200} />
              <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:12 }}>
                {[
                  ["8","Story Arcs","From silent churn to expansion champion"],
                  ["15+","CSV Types","Stakeholders, decisions, outcomes, signals"],
                  ["2-hop","Traversal","Upstream causes & downstream effects"],
                  ["$","Revenue at Risk","Per-account and portfolio-level"],
                ].map(([val,label,desc])=>(
                  <div key={label} style={{ background:"rgba(255,255,255,0.03)",borderRadius:11,padding:"14px",border:"1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ fontSize:20,fontWeight:800,color:"#F1F5F9",fontFamily:"Sora,sans-serif" }}>{val}</div>
                    <div style={{ fontSize:12,fontWeight:700,color:"#94A3B8",marginTop:2 }}>{label}</div>
                    <div style={{ fontSize:11,color:"#475569",marginTop:4 }}>{desc}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* 5-PILLAR */}
      <section id="pillars" style={{ padding:"90px 24px" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center",marginBottom:50 }}>
            <div>
              <div className="pill" style={{ background:"rgba(99,102,241,0.1)",color:"#818CF8",border:"1px solid rgba(99,102,241,0.2)",marginBottom:16 }}>38 KPIs &middot; 5 Pillars</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:16 }}>Built for<br /><span className="gt">AI Infrastructure</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75 }}>Each pillar has configurable L1/L2 weights. Wizard C recalibrates them monthly from your actual churn and expansion outcomes. GPU utilization (0.88 expansion correlation) and capacity trajectory (0.92) are real signals, not vanity metrics.</p>
            </div>
            <SectionImg src="https://images.unsplash.com/photo-1639322537228-f710d846310a?w=800&q=80" alt="AI infrastructure" height={240} />
          </div>
          <div style={{ display:"flex",gap:8,justifyContent:"center",marginBottom:28,flexWrap:"wrap" }}>
            {PILLARS.map((p,i)=>(
              <button key={p.id} className={`pt${activePillar===i?" ptact":""}`}
                style={ activePillar===i ? {background:p.color,border:`1.5px solid ${p.color}`} : {} }
                onClick={()=>setActivePillar(i)}>
                {p.id} &middot; {p.name}
              </button>
            ))}
          </div>
          <div style={{ background:"rgba(255,255,255,0.03)",border:`1px solid ${PILLARS[activePillar].color}33`,borderRadius:18,padding:"32px",display:"grid",gridTemplateColumns:"1fr 1fr",gap:32 }}>
            <div>
              <div style={{ display:"flex",alignItems:"center",gap:14,marginBottom:18 }}>
                <div style={{ width:48,height:48,borderRadius:12,background:PILLARS[activePillar].color+"22",display:"flex",alignItems:"center",justifyContent:"center",fontSize:18,fontWeight:800,color:PILLARS[activePillar].color }}>{PILLARS[activePillar].id}</div>
                <div>
                  <div style={{ fontSize:19,fontWeight:700,color:"#F1F5F9",fontFamily:"Sora,sans-serif" }}>{PILLARS[activePillar].name}</div>
                  <div style={{ fontSize:12,color:"#64748B" }}>Weight: <span style={{ color:PILLARS[activePillar].color,fontWeight:700 }}>{PILLARS[activePillar].weight}</span> &middot; {PILLARS[activePillar].kpis.length} KPIs &middot; Recalibrates monthly</div>
                </div>
              </div>
              <div style={{ fontSize:13,color:"#475569",padding:"12px 14px",background:"rgba(255,255,255,0.03)",borderRadius:10,border:"1px solid rgba(255,255,255,0.06)" }}>
                {"\u{1F4A1}"} Weights are starting points. After 90 days of data, Wizard C learns the optimal weight for your portfolio from actual expansion and churn outcomes.
              </div>
            </div>
            <div style={{ display:"flex",flexDirection:"column",gap:6,maxHeight:320,overflowY:"auto" }}>
              {PILLARS[activePillar].kpis.map((kpi,ki)=>(
                <div key={kpi} style={{ display:"flex",alignItems:"center",gap:12,padding:"10px 15px",background:"rgba(255,255,255,0.03)",borderRadius:11,border:"1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ width:26,height:26,borderRadius:7,background:PILLARS[activePillar].color+"22",display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:800,color:PILLARS[activePillar].color,flexShrink:0 }}>K{ki+1}</div>
                  <span style={{ fontSize:13,color:"#CBD5E1",fontWeight:500 }}>{kpi}</span>
                  <div style={{ marginLeft:"auto",height:3,width:48,background:"#1E293B",borderRadius:999,flexShrink:0 }}>
                    <div style={{ height:"100%",width:`${45+ki*7}%`,background:PILLARS[activePillar].color,borderRadius:999 }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ marginTop:18,padding:"16px 20px",background:"rgba(255,255,255,0.02)",borderRadius:12,border:"1px solid rgba(255,255,255,0.05)" }}>
            <div style={{ fontSize:10,color:"#475569",fontWeight:700,letterSpacing:".08em",textTransform:"uppercase",marginBottom:10 }}>Portfolio Health Score Composition</div>
            <div style={{ display:"flex",height:26,borderRadius:8,overflow:"hidden",gap:2 }}>
              {PILLARS.map(p=>(
                <div key={p.id} style={{ flex:parseInt(p.weight),background:p.color,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:700,color:"rgba(255,255,255,0.9)",whiteSpace:"nowrap",overflow:"hidden" }}>{p.id} {p.weight}</div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* MCP TOOLS */}
      <section id="mcp-tools" style={{ padding:"90px 24px",background:"rgba(255,255,255,0.01)" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center",marginBottom:50 }}>
            <div>
              <div className="pill" style={{ background:"rgba(99,102,241,0.1)",color:"#818CF8",border:"1px solid rgba(99,102,241,0.2)",marginBottom:16 }}>Claude Integration</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:16 }}>Ask Claude About<br /><span className="gt">Your Accounts</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75 }}>20+ MCP tools let you query account health, revenue at risk, causal chains, ROI projections, and CSM actions through natural language. Claude becomes your revenue intelligence analyst.</p>
            </div>
            <SectionImg src="https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&q=80" alt="AI assistant" height={240} />
          </div>
          <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))",gap:14 }}>
            {[
              ["Account Health","get_account_health","Pillar breakdown, KPI scores, health classification","#10B981"],
              ["Revenue at Risk","get_revenue_at_risk","Protected, at-risk, expansion, lost revenue breakdown","#EF4444"],
              ["Causal Chains","get_causal_chain","Signal \u2192 Decision \u2192 Outcome traversal","#8B5CF6"],
              ["CSM Daily Actions","get_csm_daily_actions","Top-10 prioritized actions with dollar impact","#F59E0B"],
              ["ROI Story","get_outcome_roi_story","Historical proof + forward projection narrative","#0EA5E9"],
              ["Power-of-1","calculate_power_of_1","Revenue impact of 1% metric improvement","#EC4899"],
              ["Portfolio ROI","get_portfolio_roi_summary","Complete portfolio ROI with trajectory assessment","#10B981"],
              ["Playbook Recs","get_playbook_recommendations","Health-based playbook recommendations","#6366F1"],
            ].map(([title,tool,desc,color])=>(
              <div key={tool} className="glass" style={{ padding:"20px" }}>
                <div style={{ fontSize:14,fontWeight:700,color:"#F1F5F9",marginBottom:4 }}>{title}</div>
                <div style={{ fontSize:11,fontFamily:"monospace",color:color,marginBottom:8,opacity:0.8 }}>{tool}</div>
                <div style={{ fontSize:12,color:"#64748B",lineHeight:1.6 }}>{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* PIPELINE */}
      <section id="pipeline" style={{ padding:"90px 24px" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center",marginBottom:60 }}>
            <div>
              <div className="pill" style={{ background:"rgba(16,185,129,0.1)",color:"#34D399",border:"1px solid rgba(16,185,129,0.2)",marginBottom:16 }}>End-to-End Pipeline</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:16 }}>Raw Data to<br /><span className="gt">Revenue Intelligence</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75 }}>Six automated steps. Ingest via CSV or Claude MCP connectors. Human-validated at every milestone. Context graphs, journey timelines, and revenue stories generated automatically.</p>
            </div>
            <SectionImg src="https://images.unsplash.com/photo-1639322537228-f710d846310a?w=800&q=80" alt="AI data pipeline" height={240} />
          </div>
          <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(270px,1fr))",gap:18 }}>
            {[
              {n:"01",t:"Ingest & Provision",d:"Upload 15 CSV types or connect via Claude MCP. API validates schema, loads PostgreSQL, builds Qdrant embeddings, ingests context graph \u2014 one automated step.",c:"#0EA5E9"},
              {n:"02",t:"Context Graph Build",d:"9 CSV types map Signal \u2192 Decision \u2192 Outcome chains per account. Stakeholders, engagement events, decisions, and revenue outcomes connected causally.",c:"#EF4444"},
              {n:"03",t:"Wizard A \u2014 Journey Generator",d:"Transforms raw data into 12-month account journey timelines with health arcs, milestones, and phase transitions. Context for all downstream intelligence.",c:"#8B5CF6"},
              {n:"04",t:"Wizard B \u2014 Pattern Analyzer",d:"Detects expansion, churn, and recovery trajectories. Maps to 8 story arcs. Auto-generates early warning rules and success factors per account.",c:"#F59E0B"},
              {n:"05",t:"Wizard C \u2014 Weight Optimizer",d:"Learns which KPIs and pillars predict outcomes in your data. L1/L2 weights recalibrate monthly. GPU utilization at 0.88, capacity trajectory at 0.92 correlation.",c:"#10B981"},
              {n:"06",t:"Revenue Intelligence",d:"Power-of-1 modeling, ROI stories per account, portfolio revenue at risk, and CSM daily actions with dollar impact. Monthly cadence with full explainability.",c:"#6366F1"},
            ].map(s=>(
              <div key={s.n} className="glass" style={{ padding:"24px" }}>
                <div style={{ width:40,height:40,borderRadius:11,background:s.c+"22",border:`1.5px solid ${s.c}55`,display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"Sora,sans-serif",fontSize:13,fontWeight:800,color:s.c,marginBottom:14 }}>{s.n}</div>
                <h3 style={{ fontSize:15,fontWeight:700,color:"#F1F5F9",marginBottom:8,fontFamily:"Sora,sans-serif" }}>{s.t}</h3>
                <p style={{ fontSize:13,color:"#64748B",lineHeight:1.65 }}>{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* REVENUE INTELLIGENCE */}
      <section id="rev-intel" style={{ padding:"90px 24px",background:"rgba(255,255,255,0.01)" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1.1fr 1fr",gap:60,alignItems:"center" }}>
            <div>
              <div className="pill" style={{ background:"rgba(16,185,129,0.1)",color:"#34D399",border:"1px solid rgba(16,185,129,0.2)",marginBottom:20 }}>Revenue Intelligence</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:20 }}>Every Account.<br />Every Month.<br /><span className="gt">Revenue Forward.</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75,marginBottom:28 }}>Revenue Intelligence replaces lagging vanity metrics with a compounding improvement cadence. Power-of-1 models connect each KPI to dollar outcomes. ROI stories provide historical proof and forward projections per account.</p>
              <div style={{ borderRadius:14,overflow:"hidden",border:"1px solid rgba(255,255,255,0.07)" }}>
                <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr 1fr",background:"rgba(255,255,255,0.04)",padding:"10px 16px" }}>
                  {["Period","Signal","Outcome"].map(h=>(
                    <div key={h} style={{ fontSize:10,fontWeight:700,color:"#475569",textTransform:"uppercase",letterSpacing:".06em" }}>{h}</div>
                  ))}
                </div>
                {[
                  ["Month 1","Baseline set","Ref: 72 avg health"],
                  ["Month 2","+1pt / account","73 \u2192 stabilizing"],
                  ["Month 4","Compounding","75\u201376 avg"],
                  ["Month 6","Momentum builds","78\u201379 avg"],
                  ["Month 12","~12.7% compounded","82 avg \u00b7 ARR protected"],
                ].map(([p,g,o],i)=>(
                  <div key={p} style={{ display:"grid",gridTemplateColumns:"1fr 1fr 1fr",padding:"11px 16px",background:i%2===0?"transparent":"rgba(255,255,255,0.02)",borderTop:"1px solid rgba(255,255,255,0.04)" }}>
                    <div style={{ fontSize:13,fontWeight:600,color:"#CBD5E1" }}>{p}</div>
                    <div style={{ fontSize:13,color:"#10B981",fontWeight:600 }}>{g}</div>
                    <div style={{ fontSize:12,color:"#475569" }}>{o}</div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display:"flex",flexDirection:"column",gap:16 }}>
              <SectionImg src="https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=800&q=80" alt="Revenue analytics" height={210} />
              {[
                ["\u{1F4B0}","Power-of-1 Revenue Model","Calculate the revenue impact of improving any metric by 1%. NRR, GRR, expansion rate, TTFV \u2014 connected to dollar outcomes.","#EF4444"],
                ["\u{1F4CA}","ROI Stories Per Account","Historical proof of value delivered + forward projections. Portfolio-level and per-account with full explainability.","#8B5CF6"],
                ["\u{1F3AF}","Playbook Accountability","5 trigger-based playbooks: VoC Sprint, Activation Blitz, SLA Stabilizer, Renewal Safeguard, Expansion Timing.","#F59E0B"],
              ].map(([icon,title,desc,color])=>(
                <div key={title} className="glass" style={{ padding:"18px 22px",display:"flex",gap:14 }}>
                  <div style={{ fontSize:22,flexShrink:0 }}>{icon}</div>
                  <div>
                    <div style={{ fontSize:14,fontWeight:700,color:"#F1F5F9",marginBottom:5 }}>{title}</div>
                    <div style={{ fontSize:13,color:"#64748B",lineHeight:1.6 }}>{desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* PLAYBOOKS */}
      <section style={{ padding:"90px 24px" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center",marginBottom:50 }}>
            <div>
              <div className="pill" style={{ background:"rgba(239,68,68,0.1)",color:"#FCA5A5",border:"1px solid rgba(239,68,68,0.2)",marginBottom:16 }}>Playbook Engine</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,42px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:16 }}>5 Playbooks.<br /><span className="gt">Right Time. Right Action.</span></h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.75 }}>Each playbook has trigger conditions, severity routing, duration targets, and named CSM ownership. From 14-day SLA recovery to 90-day renewal safeguard.</p>
            </div>
            <SectionImg src="https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80" alt="Business strategy" height={240} />
          </div>
          <div style={{ display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(300px,1fr))",gap:14 }}>
            {[
              ["30d","VoC Sprint","NPS < 10, CSAT < 3.6, churn risk \u2265 30%","Voice-of-customer deep dive \u2192 NPS recovery + feedback loop","#EF4444"],
              ["30d","Activation Blitz","Adoption < 60%, active users < 50%, feature adoption < 40%","Onboarding acceleration \u2192 product activation + TTFV improvement","#F59E0B"],
              ["14\u201321d","SLA Stabilizer",">5 SLA breaches/month, response time > 2x target","Emergency SLA recovery \u2192 MTTR reduction + escalation containment","#EF4444"],
              ["90d","Renewal Safeguard","Health < 70, renewal < 90 days, champion at risk","Proactive renewal defense \u2192 NRR/GRR protection + engagement recovery","#F59E0B"],
              ["60\u201390d","Expansion Timing","Health > 80, adoption > 85%, usage > 80% license","Expansion opportunity capture \u2192 upsell pipeline + NRR growth","#10B981"],
            ].map(([dur,title,cond,play,color])=>(
              <div key={title} className="glass" style={{ padding:"18px 22px",borderLeft:`3px solid ${color}` }}>
                <div style={{ display:"flex",alignItems:"center",gap:10,marginBottom:10 }}>
                  <div className="pill" style={{ background:`${color}18`,color:color,border:`1px solid ${color}44` }}>{dur}</div>
                  <div style={{ fontSize:14,fontWeight:700,color:"#F1F5F9" }}>{title}</div>
                </div>
                <div style={{ fontSize:11,color:"#64748B",marginBottom:7,fontStyle:"italic" }}>Trigger: {cond}</div>
                <div style={{ fontSize:12,color:"#94A3B8" }}>{"\u2192"} {play}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
      <div className="divider" />
      {/* ABOUT */}
      <section id="about" style={{ padding:"90px 24px",background:"rgba(255,255,255,0.01)" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:60,alignItems:"center" }}>
            <div>
              <div className="pill" style={{ background:"rgba(14,165,233,0.1)",color:"#38BDF8",border:"1px solid rgba(14,165,233,0.2)",marginBottom:20 }}>About AuctusAI</div>
              <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(28px,3vw,40px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:20 }}>Built by a<br /><span className="gt">Practitioner,</span><br />Not a Lab</h2>
              <p style={{ fontSize:15,color:"#64748B",lineHeight:1.8,marginBottom:24 }}>Founded by <strong style={{ color:"#CBD5E1" }}>Manoj Gupta</strong> &mdash; 25 years of enterprise technology leadership across Oracle, IBM, Accenture, and DXC. CS Pulse is built from direct experience in the gap between dashboards that look good and intelligence that actually prevents churn and drives expansion.</p>
              <div style={{ display:"flex",flexDirection:"column",gap:10 }}>
                {[
                  ["\u{1F3E2}","Oracle","VP Product Engineering \u00b7 10 yrs \u00b7 Fusion ERP, 5,000+ customers"],
                  ["\u{1F535}","IBM","Partner \u00b7 Cloud Innovation \u00b7 $140M P&L \u00b7 700-person team"],
                  ["\u{1F7E3}","Accenture","Senior Manager \u00b7 Cloud Advisory \u00b7 4 years"],
                  ["\u2699\uFE0F","DXC Technology","Senior Managing Partner \u00b7 $10M+ enterprise deals"],
                ].map(([icon,co,detail])=>(
                  <div key={co} style={{ display:"flex",gap:12,padding:"11px 14px",background:"rgba(255,255,255,0.02)",borderRadius:10,border:"1px solid rgba(255,255,255,0.05)" }}>
                    <span style={{ fontSize:18 }}>{icon}</span>
                    <div>
                      <div style={{ fontSize:13,fontWeight:700,color:"#E2E8F0" }}>{co}</div>
                      <div style={{ fontSize:11,color:"#475569" }}>{detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display:"flex",flexDirection:"column",gap:18 }}>
              <SectionImg src="https://images.unsplash.com/photo-1553877522-43269d4ea984?w=800&q=80" alt="Enterprise leadership" height={220} />
              <div style={{ background:"linear-gradient(135deg,rgba(14,165,233,0.07),rgba(99,102,241,0.07))",border:"1px solid rgba(14,165,233,0.15)",borderRadius:18,padding:"26px" }}>
                <div style={{ fontFamily:"Sora,sans-serif",fontSize:36,fontWeight:800,color:"#F1F5F9",letterSpacing:"-0.03em",marginBottom:6 }}>auctus</div>
                <div style={{ fontSize:13,color:"#64748B",fontStyle:"italic",marginBottom:14 }}>Latin: "increased &middot; augmented &middot; grown"</div>
                <div style={{ height:1,background:"rgba(255,255,255,0.06)",marginBottom:14 }} />
                <div style={{ fontSize:15,fontWeight:700,color:"#CBD5E1",lineHeight:1.5,marginBottom:8 }}>"Augmented Intelligence for Revenue Growth"</div>
                <div style={{ fontSize:12,color:"#475569" }}>Customer intelligence that turns deployment signals into revenue outcomes.</div>
              </div>
            </div>
          </div>
        </div>
      </section>
      {/* LIVE DASHBOARD PREVIEW */}
      <section style={{ padding:"60px 24px",background:"rgba(14,165,233,0.03)",borderTop:"1px solid rgba(14,165,233,0.08)" }}>
        <div style={{ maxWidth:900,margin:"0 auto" }}>
          <div style={{ textAlign:"center",marginBottom:36 }}>
            <div className="pill" style={{ background:"rgba(16,185,129,0.1)",color:"#34D399",border:"1px solid rgba(16,185,129,0.2)",marginBottom:12 }}>{"\u25CF"} LIVE PREVIEW</div>
            <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:30,fontWeight:800,letterSpacing:"-0.03em" }}>Revenue Intelligence <span className="gt">Dashboard</span></h2>
          </div>
          <div style={{ background:"rgba(255,255,255,0.03)",border:"1px solid rgba(255,255,255,0.08)",borderRadius:22,overflow:"hidden",boxShadow:"0 40px 120px rgba(0,0,0,0.5)" }}>
            <div style={{ padding:"14px 20px",borderBottom:"1px solid rgba(255,255,255,0.06)",display:"flex",alignItems:"center",justifyContent:"space-between" }}>
              <div style={{ display:"flex",gap:6 }}>{["#FF5F57","#FEBC2E","#28C840"].map(c=><div key={c} style={{ width:11,height:11,borderRadius:"50%",background:c }} />)}</div>
              <div style={{ fontSize:12,color:"#475569",fontWeight:600 }}>CS Pulse &middot; Customer Intelligence Dashboard</div>
              <div className="pill" style={{ background:"rgba(16,185,129,0.1)",color:"#34D399",border:"1px solid rgba(16,185,129,0.2)",padding:"2px 10px" }}>{"\u25CF"} LIVE</div>
            </div>
            <div style={{ padding:"18px 20px",display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:12,borderBottom:"1px solid rgba(255,255,255,0.06)" }}>
              {[["Portfolio Health","76.4","+2.1 \u2191","#10B981"],["Revenue at Risk","$1.2M","2 accounts","#EF4444"],["Expansion Ready","3 accts","P5 > 80","#818CF8"],["Power-of-1","$340K","per 1% NRR","#10B981"]].map(([lbl,val,sub,col])=>(
                <div key={lbl} style={{ background:"rgba(255,255,255,0.03)",borderRadius:11,padding:"12px 14px",border:"1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize:10,color:"#64748B",marginBottom:5,textTransform:"uppercase",letterSpacing:".07em" }}>{lbl}</div>
                  <div style={{ fontSize:22,fontWeight:800,color:"#F1F5F9",fontFamily:"Sora,sans-serif" }}>{val}</div>
                  <div style={{ fontSize:11,color:col,fontWeight:600,marginTop:2 }}>{sub}</div>
                </div>
              ))}
            </div>
            <div style={{ padding:"16px 20px" }}>
              <div style={{ fontSize:11,color:"#475569",fontWeight:700,letterSpacing:".07em",textTransform:"uppercase",marginBottom:12 }}>Account Intelligence</div>
              {[
                ["CloudScale AI Labs",88,"#10B981","Healthy","GPU util 94% \u2192 expansion ready"],
                ["Nexus Research Inst.",62,"#F59E0B","At-Risk","VAR inactive 38 days"],
                ["Vertex HPC Systems",91,"#10B981","Healthy","Capacity trajectory +12% MoM"],
                ["DataForge Inc.",42,"#EF4444","Critical","SLA Stabilizer active"],
                ["OmniCloud Solutions",74,"#10B981","Healthy","QBR scheduled \u2192 upsell pipeline"],
              ].map(([name,score,col,status,note])=>(
                <div key={name as string} style={{ display:"grid",gridTemplateColumns:"1fr 140px 90px",alignItems:"center",gap:12,padding:"9px 0",borderBottom:"1px solid rgba(255,255,255,0.04)" }}>
                  <div>
                    <div style={{ fontSize:13,fontWeight:600,color:"#E2E8F0" }}>{name}</div>
                    <div style={{ fontSize:11,color:"#475569",marginTop:1 }}>{note}</div>
                  </div>
                  <HealthBar score={score as number} color={col as string} />
                  <div className="pill" style={{ background:`${col}18`,color:col as string,border:`1px solid ${col}33`,fontSize:10 }}>{status}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
      {/* CTA */}
      <section id="contact" style={{ padding:"90px 24px",position:"relative",overflow:"hidden" }}>
        <div style={{ position:"absolute",inset:0,background:"linear-gradient(135deg,rgba(14,165,233,0.04),rgba(99,102,241,0.04))",pointerEvents:"none" }} />
        <div style={{ maxWidth:660,margin:"0 auto",textAlign:"center",position:"relative" }}>
          <div className="pill" style={{ background:"rgba(14,165,233,0.1)",color:"#38BDF8",border:"1px solid rgba(14,165,233,0.2)",marginBottom:20 }}>Get Started</div>
          <h2 style={{ fontFamily:"Sora,sans-serif",fontSize:"clamp(30px,4vw,46px)",fontWeight:800,letterSpacing:"-0.03em",marginBottom:18 }}>See Which Accounts<br /><span className="gt">Drive Revenue Growth</span></h2>
          <p style={{ fontSize:16,color:"#64748B",lineHeight:1.7,marginBottom:40 }}>Request a demo &mdash; we'll run CS Pulse against a dataset matching your segment. AI chip companies, server OEMs, and data centers. No commitment, no production data required.</p>
          <div style={{ display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:32 }}>
            {[["\u{1F52C}","Live Platform Demo","See the 5-pillar dashboard, context graph, and revenue intelligence in action with your segment's data."],["\u{1F4CA}","Revenue Intel Pilot","Bring your data. Account health scoring + expansion readiness analysis in 2 weeks."]].map(([icon,title,sub])=>(
              <div key={title} className="glass" style={{ padding:"22px",textAlign:"left" }}>
                <div style={{ fontSize:26,marginBottom:10 }}>{icon}</div>
                <div style={{ fontSize:14,fontWeight:700,color:"#F1F5F9",marginBottom:6 }}>{title}</div>
                <div style={{ fontSize:13,color:"#64748B",lineHeight:1.6 }}>{sub}</div>
              </div>
            ))}
          </div>
          <div style={{ display:"flex",gap:12,justifyContent:"center",flexWrap:"wrap" }}>
            <a href="mailto:manoj.gupta@auctusai.ai" className="btnp" style={{ padding:"15px 34px",fontSize:15,borderRadius:11,textDecoration:"none",display:"inline-block" }}>Contact Us {"\u2192"}</a>
            <a href="https://auctusai.ai" className="btng" style={{ padding:"15px 26px",fontSize:15,borderRadius:11,textDecoration:"none",display:"inline-block" }}>Visit auctusai.ai</a>
          </div>
        </div>
      </section>
      {/* FOOTER */}
      <footer style={{ borderTop:"1px solid rgba(255,255,255,0.06)",padding:"40px 24px 28px",background:"rgba(0,0,0,0.3)" }}>
        <div style={{ maxWidth:1100,margin:"0 auto" }}>
          <div style={{ display:"grid",gridTemplateColumns:"2fr 1fr 1fr 1fr",gap:36,marginBottom:36 }}>
            <div>
              <div style={{ display:"flex",alignItems:"center",gap:9,marginBottom:14 }}>
                <div style={{ width:30,height:30,borderRadius:8,background:"linear-gradient(135deg,#0EA5E9,#6366F1)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:16 }}>{"\u26A1"}</div>
                <div style={{ fontFamily:"Sora,sans-serif",fontWeight:800,fontSize:15,color:"#F1F5F9" }}>AuctusAI</div>
              </div>
              <p style={{ fontSize:12,color:"#475569",lineHeight:1.7,maxWidth:240 }}>CS Pulse &mdash; AI-native customer intelligence for data center and AI infrastructure companies.</p>
              <div style={{ marginTop:12,fontSize:11,color:"#334155" }}>manoj.gupta@auctusai.ai</div>
            </div>
            {[
              ["Revenue Intel",["Context Graph","Power-of-1 Model","ROI Engine","Revenue at Risk","Portfolio Intelligence"]],
              ["Platform",["38 KPIs / 5 Pillars","Signal Analyst","5 Playbooks","Wizard A/B/C","20+ MCP Tools"]],
              ["Company",["About","Request Demo","Contact","Privacy","Terms"]],
            ].map(([heading,links])=>(
              <div key={heading as string}>
                <div style={{ fontSize:11,fontWeight:700,color:"#475569",textTransform:"uppercase",letterSpacing:".08em",marginBottom:14 }}>{heading}</div>
                <div style={{ display:"flex",flexDirection:"column",gap:9 }}>
                  {(links as string[]).map(l=>(
                    <a key={l} href="#" style={{ fontSize:12,color:"#334155",textDecoration:"none" }}
                      onMouseEnter={e=>(e.target as HTMLElement).style.color="#0EA5E9"}
                      onMouseLeave={e=>(e.target as HTMLElement).style.color="#334155"}>
                      {l}
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div style={{ borderTop:"1px solid rgba(255,255,255,0.05)",paddingTop:20,display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:10 }}>
            <div style={{ fontSize:11,color:"#334155" }}>{"\u00A9"} 2026 AuctusAI Inc. All rights reserved.</div>
            <div style={{ fontSize:11,color:"#1E293B",fontStyle:"italic" }}>auctus &mdash; Latin for "growth through augmentation"</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
