#!/usr/bin/env python3
"""Builder for config/datacenter_v1_kpi_catalog.json — GPU-rental neocloud vertical.
Emits the {"pillars":{...},"kpis":{...}} shape the generic scorer expects.
Pillar codes P1..P6 (P-format convention); semantic map in metadata.pillar_map.
"""
import json, os, collections

OUT = "/Users/manojgupta/CustomerSuccessAI-DataCenter/kpi-dashboard/backend/config/datacenter_v1_kpi_catalog.json"

# pillar_code -> (name, weight_l2, frequency-note, semantic R#)
PILLARS = collections.OrderedDict([
    ("P1", ("Revenue & Unit Economics", 0.25, "R1")),
    ("P2", ("Fleet Utilization & Goodput", 0.22, "R2")),
    ("P3", ("Reliability & SLA Delivery", 0.20, "R3")),
    ("P4", ("Power & Facility", 0.13, "R4")),
    ("P5", ("Commercial & Expansion", 0.15, "R5")),
    ("P6", ("Provisioning Velocity", 0.05, "R6")),
])

# Each KPI: code, name, unit, direction ('up'|'down'), weight_l1, target,
#   b1 = risk boundary, b2 = (up: healthy_max) / (down: critical ceiling), freq
# For 'up':   healthy [target, b2], risk [b1, target], critical [0, b1]
# For 'down': healthy [0, target],  risk [target, b1], critical [b1, b2]
K = [
 # ---- P1 Revenue & Unit Economics ----
 ("P1-KPI1","Realized $/GPU-hour","$/gpu-hr","up",0.25, 2.5, 1.8, 4.0,"daily"),
 ("P1-KPI2","Effective-utilization revenue capture","percentage","up",0.20, 85, 70, 100,"daily"),
 ("P1-KPI3","Reserved revenue coverage","percentage","up",0.15, 60, 40, 100,"weekly"),
 ("P1-KPI4","Gross margin per cluster","percentage","up",0.20, 45, 30, 80,"monthly"),
 ("P1-KPI5","Rate / discount leakage","percentage","down",0.10, 10, 20, 40,"weekly"),
 ("P1-KPI6","Revenue per available MW","$m/MW","up",0.10, 1.2, 0.8, 2.5,"monthly"),
 # ---- P2 Fleet Utilization & Goodput ----
 ("P2-KPI1","GPU Utilization (allocated)","percentage","up",0.22, 70, 50, 100,"realtime"),
 ("P2-KPI2","Effective utilization (goodput)","percentage","up",0.22, 90, 75, 100,"realtime"),
 ("P2-KPI3","Idle GPU-hour rate","percentage","down",0.15, 10, 20, 40,"realtime"),
 ("P2-KPI4","Reserved-cluster utilization","percentage","up",0.15, 60, 40, 100,"daily"),
 ("P2-KPI5","Fleet fragmentation / stranded GPUs","percentage","down",0.10, 5, 12, 30,"hourly"),
 ("P2-KPI6","Queue time-to-schedule","minutes","down",0.08, 5, 15, 60,"realtime"),
 ("P2-KPI7","GPU memory efficiency","percentage","up",0.08, 80, 65, 100,"daily"),
 # ---- P3 Reliability & SLA Delivery ----
 ("P3-KPI1","Training-job completion rate","percentage","up",0.18, 95, 85, 100,"daily"),
 ("P3-KPI2","Job interruption / preemption rate","percentage","down",0.18, 2, 5, 20,"realtime"),
 ("P3-KPI3","GPU/node failure rate","events_per_1k_gpu_hr","down",0.15, 1, 3, 10,"realtime"),
 ("P3-KPI4","Fabric error rate (IB/NVLink RDMA)","errors_per_hr","down",0.13, 1, 5, 25,"realtime"),
 ("P3-KPI5","Checkpoint-restart frequency","restarts_per_run","down",0.08, 1, 3, 10,"per_run"),
 ("P3-KPI6","SLA attainment","percentage","up",0.14, 99.5, 99.0, 100,"monthly"),
 ("P3-KPI7","MTBF","hours","up",0.08, 8760, 4380, 100000,"monthly"),
 ("P3-KPI8","Inference latency (P95)","milliseconds","down",0.06, 50, 100, 300,"realtime"),
 # ---- P4 Power & Facility ----
 ("P4-KPI1","Sellable MW / power-capacity utilization","percentage","up",0.28, 80, 60, 95,"daily"),
 ("P4-KPI2","Stranded power (provisioned-unsellable)","percentage","down",0.18, 10, 20, 45,"daily"),
 ("P4-KPI3","Power Efficiency (PUE)","ratio","down",0.15, 1.3, 1.5, 2.2,"realtime"),
 ("P4-KPI4","Cooling / DLC headroom","percentage","up",0.17, 20, 10, 60,"realtime"),
 ("P4-KPI5","Power cost per GPU-hour","$/gpu-hr","down",0.12, 0.6, 1.0, 2.5,"monthly"),
 ("P4-KPI6","Thermal management score","percentage","up",0.10, 95, 85, 100,"realtime"),
 # ---- P5 Commercial & Expansion ----
 ("P5-KPI1","Reserved commitment coverage","months","up",0.18, 6, 3, 24,"weekly"),
 ("P5-KPI2","Ramp-to-commit","percentage","up",0.18, 90, 70, 100,"weekly"),
 ("P5-KPI3","Compute-hour consumption trend","percentage_change","up",0.15, 15, 0, 200,"monthly"),
 ("P5-KPI4","Expansion probability (90d)","percentage","up",0.13, 50, 30, 100,"monthly"),
 ("P5-KPI5","Silicon-refresh readiness","score","up",0.08, 60, 40, 100,"quarterly"),
 ("P5-KPI6","Customer runway / solvency","months","up",0.13, 12, 6, 48,"monthly"),
 ("P5-KPI7","Technical champion engagement","score","up",0.07, 75, 55, 100,"monthly"),
 ("P5-KPI8","Multi-cloud diversification (share elsewhere)","percentage","down",0.08, 25, 45, 90,"quarterly"),
 # ---- P6 Provisioning Velocity ----
 ("P6-KPI1","Time-to-first-job","hours","down",0.50, 24, 72, 240,"per_onboard"),
 ("P6-KPI2","Provisioning / quota-grant time","hours","down",0.25, 4, 12, 72,"per_onboard"),
 ("P6-KPI3","Configuration accuracy","percentage","up",0.25, 95, 85, 100,"per_onboard"),
]

def ranges(direction, target, b1, b2):
    if direction == "up":
        return {"healthy":{"min":target,"max":b2,"color":"green"},
                "risk":{"min":b1,"max":target,"color":"yellow"},
                "critical":{"min":0,"max":b1,"color":"red"}}
    else:  # down
        return {"healthy":{"min":0,"max":target,"color":"green"},
                "risk":{"min":target,"max":b1,"color":"yellow"},
                "critical":{"min":b1,"max":b2,"color":"red"}}

kpis = collections.OrderedDict()
pillar_counts = collections.Counter()
wl1_sums = collections.defaultdict(float)
for code,name,unit,direction,wl1,target,b1,b2,freq in K:
    pillar = code.split("-")[0]
    pillar_counts[pillar]+=1
    wl1_sums[pillar]+=wl1
    kpis[code] = {
        "name":name,"pillar":pillar,"weight_l1":wl1,"frequency":freq,"unit":unit,
        "higher_is_better": direction=="up",
        "target":{"operator":">" if direction=="up" else "<","value":target},
        "ranges":ranges(direction,target,b1,b2),
        "description":name,
    }

pillars = collections.OrderedDict()
for pc,(name,wl2,rsem) in PILLARS.items():
    pillars[pc] = {"name":name,"weight_l2":wl2,"kpi_count":pillar_counts[pc],
                   "semantic_code":rsem}

doc = collections.OrderedDict()
doc["version"]="1.0"
doc["vertical"]="datacenter_v1"
doc["description"]="GPU-rental neocloud (DataCenterV1) — rent NVIDIA GPUs hourly / reserved clusters. Health optimized for realized revenue x utilization x goodput x sellable power. See docs/GPU_NEOCLOUD_VERTICAL_SPEC.md."
doc["pillars"]=pillars
doc["kpis"]=kpis
doc["metadata"]={
    "kpi_total":len(kpis),
    "pillar_weight_sum":round(sum(p[1] for p in PILLARS.values()),4),
    "pillar_map":{pc:rsem for pc,(_,_,rsem) in PILLARS.items()},
    "source":"docs/GPU_NEOCLOUD_VERTICAL_SPEC.md",
}

# integrity checks before writing
errs=[]
ws=round(sum(p[1] for p in PILLARS.values()),4)
if ws!=1.0: errs.append(f"pillar weight_l2 sum={ws} != 1.0")
for pc,s in wl1_sums.items():
    if round(s,4)!=1.0: errs.append(f"{pc} weight_l1 sum={round(s,4)} != 1.0")
if errs:
    print("INTEGRITY ERRORS:"); [print("  -",e) for e in errs]; raise SystemExit(1)

os.makedirs(os.path.dirname(OUT),exist_ok=True)
with open(OUT,"w") as f: json.dump(doc,f,indent=2)
print(f"WROTE {OUT}")
print(f"  {len(kpis)} KPIs across {len(pillars)} pillars; weight_l2 sum={ws}")
for pc in PILLARS: print(f"  {pc} {pillars[pc]['name']:<34} w={PILLARS[pc][1]:.2f} kpis={pillar_counts[pc]} wl1_sum={round(wl1_sums[pc],3)}")
