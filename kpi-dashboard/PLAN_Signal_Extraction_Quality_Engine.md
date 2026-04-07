# Signal Extraction Quality Engine — Architecture Design

## The Problem

Pipeline 1 extracts structured signals from unstructured data (Slack, email, transcript). Today it uses Claude + Qdrant context and achieves 88% recall. That's not production-grade. A wrong extraction (tagging `champion_change` when it's `feature_request`) causes wrong playbook, wrong alert, wrong CSM action. The extraction quality IS the product.

## Why "Better Prompts" Won't Get Us to 97%

| Approach | Ceiling | Why It Plateaus |
|----------|---------|-----------------|
| Better prompt templates | ~90% | Prompts are generic. "Evaluating options" means `competitor_mention` at Customer A but `feature_request` at Customer B. One prompt can't know both. |
| Bigger LLM (Opus) | ~92% | More reasoning power helps ambiguous cases but costs 10x more per signal. Doesn't learn from corrections. |
| Qdrant context (shipped) | ~93% | Retrieves similar past signals but only from the same customer's history. New customers have empty Qdrant = cold start. |
| **Per-customer calibrated extraction** | **97%+** | Learns each customer's vocabulary, corrects from CSM feedback, builds customer-specific few-shot examples over time. **This is the moat.** |

## Architecture

```
                    ┌─────────────────────────────────┐
                    │     Signal Extraction Engine     │
                    │         (Pipeline 1)             │
                    └─────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────┐   ┌──────────────┐  ┌───────────┐
            │ Layer 1   │   │ Layer 2      │  │ Layer 3   │
            │ PRE-PROC  │   │ EXTRACTION   │  │ CALIBRATE │
            │           │   │              │  │           │
            │ Clean     │   │ Claude LLM   │  │ Per-cust  │
            │ Normalize │   │ + Qdrant     │  │ feedback  │
            │ Route     │   │ context      │  │ loop      │
            └──────────┘   └──────────────┘  └───────────┘
                 │               │                 │
                 ▼               ▼                 ▼
            Raw text →     Structured signal →  Calibrated signal
            clean text     {intent, sentiment}  {verified, scored}
                                                      │
                                              ┌───────┴────────┐
                                              ▼                ▼
                                      confidence ≥ 0.8    confidence < 0.8
                                      AUTO-ACCEPT         REVIEW QUEUE
                                         │                    │
                                         ▼                    ▼
                                   QualitativeSignal    CSM reviews
                                   (ready for            corrects
                                    Pipeline 2)          → feeds back
```

---

## Layer 1: Pre-Processing (source-specific text cleanup)

**Status: NOT BUILT (Sprint 3 of Signal Engine plan)**

**Purpose:** Transform raw input into clean normalized text before LLM sees it.

| Source | Pre-Processing | Why It Matters |
|--------|---------------|----------------|
| **Slack** | Strip `<@U123>` mentions → resolve to names, remove bot messages, unwrap thread replies, strip emoji reactions | Claude gets "Sarah mentioned evaluating AWS" instead of "<@U8XK2P> mentioned evaluating <http://aws.amazon.com\|AWS>" |
| **Email** | Extract body only (strip headers, signatures, disclaimers, reply chain), detect forwarded-vs-original | Claude gets the actual message, not 5 layers of "On Mon, Jan 5, John wrote:" |
| **Transcript** | Split by speaker turns, attribute statements to named participants, extract action items | Claude can say "CTO said X" instead of guessing who said what in a wall of text |
| **All** | Language detection, PII redaction (optional), whitespace normalization, truncation to optimal window | Cleaner input = fewer parse errors, fewer hallucinated intents |

**Impact on accuracy: +3-5%** (88% → 91-93%)

---

## Layer 2: Extraction (LLM + Qdrant — already built)

**Status: SHIPPED**

**What it does today:**
1. Qdrant semantic search finds 5 similar past signals for this account
2. Claude extracts: intent_signals, sentiment_score, urgency_score, stakeholder_roles
3. Collision detection checks for duplicates in context graph

**What it outputs:**
```json
{
  "intent_signals": ["champion_change", "competitor_mention"],
  "sentiment_score": -0.7,
  "urgency_score": 0.85,
  "stakeholder_roles": [{"name": "Sarah", "role": "CTO"}],
  "confidence": {"intent_signals": 0.82, "sentiment_score": 0.91},
  "is_duplicate": false
}
```

**Current accuracy: 88% recall, 50% precision**

---

## Layer 3: Calibration Engine (THE MOAT — not built)

### 3.1 Per-Customer Signal Vocabulary

**Problem:** "Evaluating options" means different things at different companies.

**Solution:** Each customer gets a `signal_vocabulary` — a mapping of their specific phrases/patterns to intent codes, built over time from corrections.

```python
# Customer 250's learned vocabulary (stored in CustomerConfig JSON)
{
  "signal_vocabulary": {
    "strategic review": {"intent": "executive_escalation", "confidence_boost": 0.15},
    "exploring alternatives": {"intent": "competitor_mention", "confidence_boost": 0.2},
    "leadership transition": {"intent": "champion_change", "confidence_boost": 0.25},
    "capacity planning": {"intent": "expansion_interest", "confidence_boost": 0.2},
    # Negative examples (things that look like X but aren't)
    "routine review": {"intent": "NOT_competitor_mention", "confidence_penalty": 0.3},
  }
}
```

**How it's built:** Automatically from CSM corrections in the Review Queue (Layer 3.3).

**How it's used:** Before Claude call, scan raw_text for vocabulary matches. Inject as few-shot context: "For this customer, 'strategic review' historically means executive_escalation (3 confirmed instances)."

---

### 3.2 Confidence Gating

**Problem:** A wrong signal is worse than no signal. Better to say "I'm not sure" than to misclassify.

**Rules:**

| Confidence | Action | What Happens |
|-----------|--------|-------------|
| ≥ 0.8 | **AUTO-ACCEPT** | Signal stored as verified, available to Pipeline 2 |
| 0.5 – 0.8 | **REVIEW QUEUE** | Signal stored as `requires_review=True`, CSM sees it in Review Queue UI |
| < 0.5 | **HOLD** | Signal stored but NOT visible to Pipeline 2 until reviewed. Logged for quality analysis. |

**Where confidence comes from:**
- Claude's self-reported confidence per field (already in enrichment output)
- Qdrant similarity score (high similarity to known-good signals = higher confidence)
- Vocabulary match boost/penalty (from 3.1)
- Historical accuracy for this intent type at this customer (from 3.3)

**Combined confidence formula:**
```
final_confidence = (
    llm_confidence * 0.4 +
    qdrant_similarity * 0.25 +
    vocabulary_boost * 0.2 +
    historical_accuracy * 0.15
)
```

---

### 3.3 Feedback Loop (Self-Improving Accuracy)

**Problem:** No way for CSM corrections to improve future extractions.

**Flow:**

```
1. Signal extracted → confidence 0.65 → REVIEW QUEUE
2. CSM sees: "Classified as competitor_mention. Is this correct?"
3. CSM clicks: "No → champion_change"
4. System records correction:
   - Original: competitor_mention (confidence 0.65)
   - Corrected: champion_change (by CSM, timestamp)
   - Raw text snippet that caused the error
5. Correction feeds back:
   a. Update signal_vocabulary (3.1): "exploring alternatives" at
      this customer = champion_change, not competitor_mention
   b. Store corrected signal in Qdrant with CORRECTED intent
      → next time similar text arrives, Qdrant retrieves the
      correction as context → Claude avoids same mistake
   c. Track accuracy per intent per customer:
      - competitor_mention: 12/15 correct (80%)
      - champion_change: 8/8 correct (100%)
      → Lower confidence threshold for competitor_mention at
        this customer (more go to review queue)
```

**Storage:**

```python
# New model or JSON in CustomerConfig
class SignalCorrection:
    signal_id: str           # Original signal
    original_intent: str     # What LLM said
    corrected_intent: str    # What CSM said
    raw_text_snippet: str    # The text that caused the error (for few-shot)
    corrected_by: int        # User ID
    corrected_at: datetime
    customer_id: int
```

**Impact on accuracy: +5-8% over 3 months** (93% → 97%+ as corrections accumulate)

---

### 3.4 Cold Start (New Customers)

**Problem:** New customer has no Qdrant history, no vocabulary, no corrections. Accuracy drops to ~80%.

**Mitigations:**

| Strategy | How It Works |
|----------|-------------|
| **Industry templates** | Pre-built signal vocabulary per vertical (DC infra, SaaS, FinTech). "GPU utilization" means something in DC but nothing in SaaS. Load vertical defaults on customer creation. |
| **Bootstrap from CSV signals** | If customer uploads `signals.csv` with historical signals, index those in Qdrant immediately. Gives Claude examples of what this customer's signals look like. |
| **Aggressive review queue** | For first 30 days, lower AUTO-ACCEPT threshold to 0.9 (more signals go to review). CSM corrections build vocabulary fast. After 30 days, lower threshold to 0.8. |
| **Cross-customer anonymized patterns** | Aggregate corrections across all customers in same vertical (anonymized). "In DC infra, 'rack failure' = support_escalation with 95% accuracy." Pre-seed new customers with these patterns. |

---

## Accuracy Trajectory

| Month | Layer | Recall | Precision | What Changed |
|-------|-------|--------|-----------|--------------|
| 0 (today) | L2 only (Claude + Qdrant) | 88% | 50% | Baseline |
| 1 | + L1 (pre-processing) | 93% | 60% | Cleaner input, speaker attribution |
| 2 | + L3.2 (confidence gating) | 93% | 75% | Low-confidence signals go to review, not auto-accepted |
| 3 | + L3.3 (feedback loop) | 95% | 80% | CSM corrections fix recurring misclassifications |
| 6 | + L3.1 (vocabulary) + L3.4 (cross-customer) | 97% | 85% | Per-customer vocabulary mature, cross-customer patterns bootstrapped |
| 12 | Steady state | 98%+ | 90%+ | Self-improving, customer DNA embedded in extraction |

---

## What We DON'T Build (Deliberate Scope Limits)

| Temptation | Why We Skip It |
|-----------|---------------|
| **Fine-tune an LLM** | Too expensive, too slow to iterate, model drift risk. Per-customer Qdrant retrieval + vocabulary achieves the same effect without fine-tuning. |
| **Build our own NER/NLP model** | Claude is already best-in-class at extraction. Our value is the calibration layer (vocabulary + feedback), not the extraction model itself. |
| **Real-time streaming extraction** | Batch (30s poll) is fine for CS signals. No customer needs sub-second signal extraction. Over-engineering. |
| **Auto-account matching from raw text** | Keep as separate design problem (see account matching gap in Signal Engine plan). Don't conflate extraction quality with routing quality. |
| **Multi-language support** | English-first. Detect non-English and route to review queue with language flag. Don't attempt extraction in languages Claude hasn't been validated on. |

---

## Implementation Order

| Phase | What | Effort | Depends On |
|-------|------|--------|-----------|
| **Phase 1** | Pre-processing (Layer 1) | 1.5 days | Nothing — standalone |
| **Phase 2** | Confidence gating (Layer 3.2) | 0.5 days | Nothing — adjust thresholds in enrichment.py |
| **Phase 3** | Review Queue UI (already in Sprint 3) | 1 day | Confidence gating (shows gated signals) |
| **Phase 4** | Feedback loop (Layer 3.3) | 2 days | Review Queue UI (CSM correction source) |
| **Phase 5** | Signal vocabulary (Layer 3.1) | 1.5 days | Feedback loop (builds vocabulary from corrections) |
| **Phase 6** | Cold start + cross-customer (Layer 3.4) | 1 day | Vocabulary (needs the schema first) |

**Total: ~7.5 days across 6 phases**

---

## Success Metrics

| Metric | Target | How Measured |
|--------|--------|-------------|
| **Extraction recall** | ≥ 95% by month 3 | Ground truth from manifest signals vs extracted intents (automated test) |
| **Extraction precision** | ≥ 80% by month 3 | CSM correction rate in review queue (corrections / total reviewed) |
| **Auto-accept rate** | ≥ 70% by month 3 | Signals with confidence ≥ 0.8 / total signals |
| **Review queue volume** | ≤ 10 signals/day per CSM | Total signals in review / active CSMs |
| **Feedback loop coverage** | ≥ 50 corrections per customer by month 3 | SignalCorrection records per customer |
| **Cold start time** | < 30 days to 90% recall | Days from customer creation to 90% recall on new signals |

---

## Competitive Moat

Anyone can call `Claude.extract(raw_text)` and get 88% accuracy. The moat is:

1. **Per-customer vocabulary** — "strategic review" means different things at each company. Only we learn this.
2. **Correction flywheel** — every CSM correction makes the next extraction better. Compounds over months.
3. **Cross-customer patterns** — anonymized learnings from 100+ customers in the same vertical make cold start fast.
4. **Confidence gating** — we never give a CSM a wrong signal. We say "I'm not sure" and ask. Trust > automation.

This is the "own model" — not a fine-tuned LLM, but a calibration layer that makes any LLM extract at 97%+ for each specific customer.
