#!/usr/bin/env python3
"""
Signal Engine 360 Fidelity Test — Round-Trip Validation.

Takes each CSV-generated signal and creates realistic unstructured text
(email/slack/transcript) that the signal engine should classify back to
the same intent. Validates the enrichment pipeline is coherent.

Round-trip: CSV signal → raw text → signal engine → enrichment → intent match?

Usage:
    from generators.signal_360_generator import Signal360Generator

    gen = Signal360Generator(customer_id=340, base_url=URL, api_key=KEY, seed=42)
    scorecard = gen.run()
    print(scorecard)
"""

import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Signal type → expected engine intent mapping
# ═══════════════════════════════════════════════════════════════════════

SIGNAL_TO_INTENT: Dict[str, str] = {
    'champion_departure':       'champion_change',
    'champion_advocacy':        'expansion_interest',
    'stakeholder_escalation':   'executive_escalation',
    'critical_incident':        'product_frustration',
    'kpi_decline':              'product_frustration',
    'competitor_mention':       'competitor_mention',
    'budget_pressure':          'pricing_concern',
    'expansion_signal':         'expansion_interest',
    'deployment_delay':         'deployment_blocker',
    'usage_decline':            'renewal_risk',
    'engagement_gap':           'renewal_risk',
    'contract_dispute':         'pricing_concern',
    'executive_engagement':     'executive_escalation',
    'champion_reengagement':    'expansion_interest',
    'advocacy':                 'expansion_interest',
    'escalation_increase':      'executive_escalation',
    'support_escalation':       'product_frustration',
    'feature_adoption_increase': 'expansion_interest',
    'usage_spike':              'expansion_interest',
    'positive_engagement':      'expansion_interest',
    'expansion_discussion':     'expansion_interest',
    'csm_intervention':         'renewal_risk',
    'kpi_recovery':             'expansion_interest',
    'health_improvement':       'expansion_interest',
    'churn_averted':            'renewal_risk',
    'seasonal_pattern':         None,  # No matching intent
    'routine_review':           None,  # No matching intent
}

# Signal type → preferred channel(s)
SIGNAL_TO_CHANNEL: Dict[str, List[str]] = {
    'champion_departure':       ['slack', 'email'],
    'stakeholder_escalation':   ['email'],
    'critical_incident':        ['slack'],
    'kpi_decline':              ['slack'],
    'competitor_mention':       ['slack', 'email'],
    'budget_pressure':          ['email'],
    'expansion_signal':         ['transcript'],
    'deployment_delay':         ['email'],
    'usage_decline':            ['slack'],
    'engagement_gap':           ['slack'],
    'contract_dispute':         ['email'],
    'executive_engagement':     ['transcript'],
    'champion_reengagement':    ['transcript'],
    'advocacy':                 ['transcript'],
    'escalation_increase':      ['slack'],
    'support_escalation':       ['slack'],
    'expansion_discussion':     ['transcript'],
    'positive_engagement':      ['transcript'],
    'csm_intervention':         ['email'],
    'kpi_recovery':             ['slack'],
    'health_improvement':       ['slack'],
    'churn_averted':            ['email'],
    'champion_advocacy':        ['transcript'],
    'feature_adoption_increase': ['slack'],
    'usage_spike':              ['slack'],
    'seasonal_pattern':         ['email'],
    'routine_review':           ['email'],
}


# ═══════════════════════════════════════════════════════════════════════
# Raw text templates per signal type × channel
# Each list has 2-3 variants; generator picks randomly.
# Templates use: {account}, {stakeholder}, {title}, {content}, {csm}, {date}
# ═══════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    'champion_departure': {
        'slack': [
            "Heads up team — {stakeholder} at {account} just gave notice. Last day is end of month. No successor named yet. Our QBR in 2 weeks is now in limbo.",
            "Bad news from {account}: {stakeholder} ({title}) resigned. Moving to a competitor. We need to identify the new decision maker ASAP before renewal conversations start.",
            "Alert: Key contact {stakeholder} at {account} is leaving the company. They were our primary champion — this puts the renewal at risk.",
        ],
        'email': [
            "Subject: {account} — Champion departure\n\nHi team,\n\n{stakeholder} ({title}) at {account} has resigned effective end of month. They were our primary champion and drove the original purchase decision. We need an urgent stakeholder mapping session to identify their replacement and rebuild the relationship before renewal.\n\nPlease block time this week.\n\n{csm}",
            "Subject: Urgent — {account} key stakeholder change\n\nTeam,\n\nJust learned that {stakeholder} at {account} is leaving. This is our main executive sponsor. I recommend we schedule an intro meeting with their successor within the next 2 weeks.\n\n{csm}",
        ],
    },
    'critical_incident': {
        'slack': [
            "P1 at {account} — {content}. {stakeholder} is escalating to their VP. Need RCA by EOD Friday.",
            "INCIDENT: {account} reporting major outage. {content}. Customer impact is significant — multiple teams affected. War room starting in 30 min.",
            "Production incident at {account}: {content}. SLA clock is ticking — we have 4 hours before breach.",
        ],
    },
    'kpi_decline': {
        'slack': [
            "Metrics alert for {account}: {content}. Health score dropped below threshold. Need to investigate root cause.",
            "KPI warning — {account} showing concerning trends. {content}. Recommend scheduling a review with {stakeholder}.",
        ],
    },
    'competitor_mention': {
        'slack': [
            "Heard from {stakeholder} at {account} that they're looking at competitor pricing. {content}. We should prepare a competitive defense deck.",
            "Competitive alert: {account} mentioned evaluating alternatives during last call. {content}.",
        ],
        'email': [
            "Subject: {account} — Competitive threat\n\nHi team,\n\n{stakeholder} at {account} mentioned they're evaluating competing solutions. {content}.\n\nI recommend we prepare a value defense presentation with TCO comparison before their next internal review.\n\n{csm}",
        ],
    },
    'budget_pressure': {
        'email': [
            "Subject: {account} — Budget concerns raised\n\nTeam,\n\nDuring our last check-in, {stakeholder} ({title}) at {account} raised concerns about budget. {content}.\n\nWe may need to prepare a cost optimization proposal or flexible payment terms for the renewal discussion.\n\n{csm}",
            "Subject: {account} renewal risk — budget freeze\n\n{stakeholder} at {account} informed us of an internal budget freeze. {content}. Recommend we schedule a value realization session to justify the investment.\n\n{csm}",
        ],
    },
    'expansion_signal': {
        'transcript': [
            "[00:12:30] {stakeholder}: We've been really happy with the results so far. Our team is looking at expanding capacity for the Q4 pipeline.\n[00:12:45] {csm}: That's great to hear. What kind of scale are you thinking?\n[00:13:00] {stakeholder}: Probably doubling our current footprint. {content}.\n[00:13:15] {csm}: I'll put together a capacity proposal this week.",
            "[00:08:15] {stakeholder}: The utilization numbers look strong. {content}. We want to bring on two more teams.\n[00:08:30] {csm}: Excellent. I can have an expansion proposal ready by next week.\n[00:08:45] {stakeholder}: Let's do it. I'll need it for the budget meeting on the 15th.",
        ],
    },
    'deployment_delay': {
        'email': [
            "Subject: {account} — Deployment blocker\n\nHi team,\n\n{account} is experiencing a deployment delay. {content}.\n\n{stakeholder} has asked for a technical resource to help unblock the integration. Can we assign someone from the SE team this week?\n\n{csm}",
            "Subject: [BLOCKED] {account} deployment stalled\n\nTeam,\n\nThe deployment at {account} has hit a technical blocker. {content}. This is delaying their go-live by at least 2 weeks and {stakeholder} is getting frustrated.\n\nNeed engineering support ASAP.\n\n{csm}",
        ],
    },
    'usage_decline': {
        'slack': [
            "Usage alert: {account} API call volume dropped significantly over the past month. {content}. This could be early churn signal — worth a check-in with {stakeholder}.",
            "Declining usage at {account}: {content}. No recent support tickets or complaints — might be silent disengagement. Scheduling a proactive outreach.",
        ],
    },
    'engagement_gap': {
        'slack': [
            "{stakeholder} at {account} hasn't responded to the last 2 meeting invites. {content}. Going to try reaching out via their manager.",
            "Engagement dropping at {account}: {content}. Last QBR was 3 months ago. Need to re-establish cadence.",
        ],
    },
    'contract_dispute': {
        'email': [
            "Subject: {account} — SLA credit request\n\nTeam,\n\n{account}'s legal team has formally requested SLA credits. {content}.\n\nWe need to review the incident log and prepare a response. This could impact renewal negotiations.\n\n{csm}",
        ],
    },
    'executive_engagement': {
        'transcript': [
            "[00:05:00] {csm}: Thank you for joining today's executive review.\n[00:05:15] {stakeholder}: Happy to be here. I wanted to personally review the progress since last quarter.\n[00:05:30] {csm}: Absolutely. {content}.\n[00:06:00] {stakeholder}: This is exactly what I needed to see. Let's discuss the roadmap for next quarter.",
        ],
    },
    'champion_reengagement': {
        'transcript': [
            "[00:03:00] {csm}: Great to have you back in the cadence, {stakeholder}.\n[00:03:15] {stakeholder}: Thanks. I know I've been quiet lately. {content}. I'm ready to re-engage on the roadmap.\n[00:03:30] {csm}: Perfect. Let's schedule the quarterly planning session.",
        ],
    },
    'advocacy': {
        'transcript': [
            "[00:20:00] {stakeholder}: We'd be happy to be a reference customer. The results speak for themselves.\n[00:20:15] {csm}: That's wonderful. {content}. Would you be open to a case study or conference presentation?\n[00:20:30] {stakeholder}: Both. Let's set it up.",
        ],
    },
    'escalation_increase': {
        'slack': [
            "Escalation spike at {account}: {content}. Deployment team is frustrated. {stakeholder} wants a call with our VP Engineering.",
            "Multiple P1 tickets from {account} this week. {content}. Need to escalate internally before this becomes a churn risk.",
        ],
    },
    'support_escalation': {
        'slack': [
            "Support escalation from {account}: {content}. Ticket has been open for 5 days with no resolution. {stakeholder} is asking for management involvement.",
        ],
    },
    'expansion_discussion': {
        'transcript': [
            "[00:15:00] {stakeholder}: We've been talking internally about expanding to the enterprise tier. {content}.\n[00:15:15] {csm}: That's exciting. What's driving the decision?\n[00:15:30] {stakeholder}: The ROI from the current deployment is clear. Our CFO wants to see a proposal by end of month.",
        ],
    },
    'positive_engagement': {
        'transcript': [
            "[00:10:00] {stakeholder}: I want to acknowledge the improvement. {content}. The team is much happier.\n[00:10:15] {csm}: Glad to hear that. We've been focused on getting Phase 1 value delivered.\n[00:10:30] {stakeholder}: It shows. Let's start planning Phase 2.",
        ],
    },
    'csm_intervention': {
        'email': [
            "Subject: {account} — New CSM assignment\n\nHi {stakeholder},\n\nI'm your new Customer Success Manager for {account}. {content}.\n\nI'd love to schedule a 30-minute intro call this week to learn about your priorities and how I can best support your team.\n\nBest,\n{csm}",
        ],
    },
    'kpi_recovery': {
        'slack': [
            "Good news from {account}: {content}. Metrics are trending back up after the playbook intervention. Keep monitoring.",
            "Recovery signal at {account}: {content}. The turnaround is working — health score climbing.",
        ],
    },
    'health_improvement': {
        'slack': [
            "Health update: {account} trending upward. {content}. Great result from the team's intervention.",
        ],
    },
    'churn_averted': {
        'email': [
            "Subject: {account} — Retention success\n\nTeam,\n\nGood news: {account} has committed to renewal. {content}.\n\nThis was a close one — the retention playbook and executive engagement made the difference. Documenting this as a win for the QBR.\n\n{csm}",
        ],
    },
    'feature_adoption_increase': {
        'slack': [
            "Adoption milestone at {account}: {content}. This is the fastest onboarding in the portfolio this quarter.",
        ],
    },
    'usage_spike': {
        'slack': [
            "Usage spike detected at {account}: {content}. This could be organic growth or a seasonal pattern — worth investigating.",
        ],
    },
}

# Fallback template for signal types without specific templates
FALLBACK_TEMPLATES = {
    'slack': [
        "Update on {account}: {content}. Flagging for team awareness.",
        "Signal from {account}: {content}. {stakeholder} mentioned this during our last interaction.",
    ],
    'email': [
        "Subject: {account} — Update\n\nTeam,\n\n{content}.\n\nPlease review and advise on next steps.\n\n{csm}",
    ],
    'transcript': [
        "[00:10:00] {csm}: Let's discuss the latest from {account}.\n[00:10:15] {stakeholder}: {content}.\n[00:10:30] {csm}: Understood. I'll follow up with a plan.",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# Generator
# ═══════════════════════════════════════════════════════════════════════

class Signal360Generator:
    """Round-trip fidelity test for signal engine."""

    def __init__(self, customer_id: int, base_url: str, api_key: str,
                 seed: int = 42, max_signals: int = 30,
                 enrichment_wait_s: int = 60):
        self.customer_id = customer_id
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.rng = random.Random(seed)
        self.max_signals = max_signals
        self.enrichment_wait_s = enrichment_wait_s
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        })

    def run(self, verbose: bool = False) -> dict:
        """Execute the full 360 test. Returns scorecard dict."""
        print(f"\n{'='*60}")
        print(f"  Signal 360 Fidelity Test — Customer {self.customer_id}")
        print(f"{'='*60}")

        # Step 1: Fetch existing CSV signals
        csv_signals = self._fetch_csv_signals()
        if not csv_signals:
            print("  No CSV signals found — skipping 360 test")
            return {'status': 'skipped', 'reason': 'no_csv_signals'}

        # Step 2: Filter to signal types we can generate raw text for
        eligible = [s for s in csv_signals if s['signal_type'] in SIGNAL_TO_INTENT]
        if not eligible:
            print(f"  No eligible signals (have {len(csv_signals)} but none with known type)")
            return {'status': 'skipped', 'reason': 'no_eligible_types'}

        # Cap and shuffle
        self.rng.shuffle(eligible)
        eligible = eligible[:self.max_signals]

        # Step 3: Generate raw text and submit
        submitted = []
        by_channel = {'slack': 0, 'email': 0, 'transcript': 0}
        for sig in eligible:
            result = self._generate_and_submit(sig, verbose)
            if result:
                submitted.append(result)
                by_channel[result['channel']] = by_channel.get(result['channel'], 0) + 1

        print(f"  Submitted: {len(submitted)} signals "
              f"({by_channel.get('slack',0)} slack, "
              f"{by_channel.get('email',0)} email, "
              f"{by_channel.get('transcript',0)} transcript)")

        if not submitted:
            return {'status': 'completed', 'submitted': 0}

        # Step 4: Wait for enrichment
        print(f"  Waiting {self.enrichment_wait_s}s for enrichment worker...")
        time.sleep(self.enrichment_wait_s)

        # Step 5: Fetch enriched signals and score
        scorecard = self._score_results(submitted, verbose)

        # Step 6: Print scorecard
        self._print_scorecard(scorecard)

        return scorecard

    def _fetch_csv_signals(self) -> List[dict]:
        """Fetch CSV-uploaded signals via API."""
        try:
            # Use the MCP search_signals or direct DB query via API
            resp = self.session.get(
                f"{self.base_url}/api/dc2s/{self.customer_id}/signals",
                params={'source': 'csv_import', 'limit': 200},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else data.get('signals', [])
        except Exception:
            pass

        # Fallback: use qualitative signals endpoint
        try:
            resp = self.session.get(
                f"{self.base_url}/api/dc2s/{self.customer_id}/qualitative-signals",
                params={'limit': 200},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                signals = data if isinstance(data, list) else data.get('signals', [])
                # Filter to CSV-only (no source_type = engine channels)
                return [s for s in signals
                        if s.get('source_type') not in ('slack', 'email', 'transcript', 'manual')]
        except Exception:
            pass

        # Last resort: fetch accounts and use MCP
        try:
            resp = self.session.get(
                f"{self.base_url}/api/v1/accounts",
                headers={'X-Customer-ID': str(self.customer_id)},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                accounts = data if isinstance(data, list) else data.get('accounts', [])
                all_signals = []
                for acct in accounts[:10]:
                    aid = acct.get('account_id')
                    sr = self.session.get(
                        f"{self.base_url}/api/context-graph/{aid}/nodes",
                        params={'node_type': 'SIGNAL', 'limit': 50},
                        headers={'X-Customer-ID': str(self.customer_id)},
                        timeout=10,
                    )
                    if sr.status_code == 200:
                        nodes = sr.json() if isinstance(sr.json(), list) else sr.json().get('nodes', [])
                        for n in nodes:
                            if n.get('source_platform') == 'csv_import':
                                all_signals.append({
                                    'account_id': aid,
                                    'account_name': acct.get('account_name', ''),
                                    'signal_type': n.get('node_subtype', n.get('properties', {}).get('signal_type', '')),
                                    'content': n.get('title', ''),
                                    'signal_date': n.get('occurred_at', ''),
                                    'properties': n.get('properties', {}),
                                })
                return all_signals
        except Exception as e:
            logger.warning("Failed to fetch signals: %s", e)

        return []

    def _generate_and_submit(self, sig: dict, verbose: bool) -> Optional[dict]:
        """Generate raw text for a signal and submit to signal engine."""
        signal_type = sig.get('signal_type', '')
        if not signal_type or signal_type not in SIGNAL_TO_INTENT:
            return None

        expected_intent = SIGNAL_TO_INTENT[signal_type]
        if expected_intent is None:
            return None  # No matching intent for this signal type

        # Pick channel
        channels = SIGNAL_TO_CHANNEL.get(signal_type, ['slack'])
        channel = self.rng.choice(channels)

        # Pick template
        type_templates = TEMPLATES.get(signal_type, {})
        channel_templates = type_templates.get(channel, FALLBACK_TEMPLATES.get(channel, []))
        if not channel_templates:
            channel_templates = FALLBACK_TEMPLATES.get(channel, ["Update on {account}: {content}"])
        template = self.rng.choice(channel_templates)

        # Build context for interpolation
        props = sig.get('properties', {})
        account_name = sig.get('account_name', 'the account')
        stakeholder = props.get('stakeholder_name', 'the champion')
        title = props.get('stakeholder_title', 'VP')
        content = sig.get('content', signal_type.replace('_', ' '))
        csm = 'CSM'

        try:
            raw_text = template.format(
                account=account_name,
                stakeholder=stakeholder,
                title=title,
                content=content,
                csm=csm,
                date=sig.get('signal_date', '')[:10],
            )
        except (KeyError, IndexError):
            raw_text = f"Signal from {account_name}: {content}"

        # Build payload
        account_id = sig.get('account_id')
        if not account_id:
            return None

        payload = {
            'customer_id': self.customer_id,
            'account_id': account_id,
            'raw_text': raw_text,
            'timestamp': sig.get('signal_date', datetime.utcnow().isoformat()),
        }
        if channel == 'transcript':
            payload['consent_verified'] = True

        # Submit
        try:
            resp = self.session.post(
                f"{self.base_url}/api/signals/ingest/{channel}",
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201, 202):
                result = resp.json()
                signal_id = result.get('raw_signal_id', '')
                if verbose:
                    print(f"    [{channel:10}] {signal_type:25} → submitted ({signal_id[:8]}...)")
                return {
                    'signal_id': signal_id,
                    'channel': channel,
                    'signal_type': signal_type,
                    'expected_intent': expected_intent,
                    'account_id': account_id,
                    'account_name': account_name,
                    'raw_text_preview': raw_text[:80],
                }
            else:
                if verbose:
                    print(f"    [{channel:10}] {signal_type:25} → FAILED {resp.status_code}")
                return None
        except Exception as e:
            if verbose:
                print(f"    [{channel:10}] {signal_type:25} → ERROR {e}")
            return None

    def _score_results(self, submitted: List[dict], verbose: bool) -> dict:
        """Fetch enriched signals and compare intents."""
        matched = 0
        mismatched = 0
        unenriched = 0
        collided = 0
        details = []

        for sub in submitted:
            signal_id = sub['signal_id']
            expected = sub['expected_intent']

            # Fetch the enriched signal
            enriched = self._fetch_enriched_signal(signal_id)
            if not enriched:
                unenriched += 1
                details.append({
                    **sub,
                    'actual_intents': None,
                    'match': False,
                    'reason': 'not_enriched',
                })
                continue

            actual_intents = enriched.get('intent_signals', [])
            was_suppressed = enriched.get('alert_suppressed', False)
            if was_suppressed:
                collided += 1

            if expected in actual_intents:
                matched += 1
                details.append({
                    **sub,
                    'actual_intents': actual_intents,
                    'match': True,
                    'collided': was_suppressed,
                })
            else:
                mismatched += 1
                details.append({
                    **sub,
                    'actual_intents': actual_intents,
                    'match': False,
                    'reason': f'expected {expected}, got {actual_intents}',
                    'collided': was_suppressed,
                })

        total = len(submitted)
        enriched_count = total - unenriched
        match_rate = (matched / enriched_count * 100) if enriched_count > 0 else 0

        return {
            'status': 'completed',
            'customer_id': self.customer_id,
            'submitted': total,
            'enriched': enriched_count,
            'matched': matched,
            'mismatched': mismatched,
            'unenriched': unenriched,
            'collided': collided,
            'match_rate_pct': round(match_rate, 1),
            'details': details,
        }

    def _fetch_enriched_signal(self, signal_id: str) -> Optional[dict]:
        """Fetch a signal's enrichment result from DB via API."""
        try:
            resp = self.session.get(
                f"{self.base_url}/api/signals/review-queue",
                params={'signal_id': signal_id},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                signals = data if isinstance(data, list) else data.get('signals', [])
                for s in signals:
                    if s.get('signal_id') == signal_id:
                        return s
        except Exception:
            pass

        # Fallback: query qualitative_signals directly
        try:
            resp = self.session.get(
                f"{self.base_url}/api/dc2s/{self.customer_id}/qualitative-signals",
                params={'signal_id': signal_id},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json()
                signals = data if isinstance(data, list) else data.get('signals', [])
                for s in signals:
                    if s.get('signal_id') == signal_id:
                        return s
        except Exception:
            pass

        return None

    def _print_scorecard(self, scorecard: dict):
        """Print formatted scorecard."""
        print(f"\n  {'─'*50}")
        print(f"  SIGNAL 360 SCORECARD:")
        print(f"    Submitted:    {scorecard['submitted']}")
        print(f"    Enriched:     {scorecard['enriched']}/{scorecard['submitted']}")
        print(f"    Matched:      {scorecard['matched']}/{scorecard['enriched']} "
              f"({scorecard['match_rate_pct']}%)")
        print(f"    Mismatched:   {scorecard['mismatched']}")
        print(f"    Unenriched:   {scorecard['unenriched']}")
        print(f"    Collided:     {scorecard['collided']} (correctly linked to CSV CG node)")

        mismatches = [d for d in scorecard.get('details', []) if not d.get('match')]
        if mismatches:
            print(f"\n  MISMATCHES:")
            for m in mismatches[:10]:
                print(f"    {m['signal_type']:25} → expected {m['expected_intent']}, "
                      f"got {m.get('actual_intents', m.get('reason', '?'))}")


# ═══════════════════════════════════════════════════════════════════════
# CLI entrypoint
# ═══════════════════════════════════════════════════════════════════════

def run_signal_360(customer_id: int, base_url: str, api_key: str,
                   seed: int = 42, max_signals: int = 30,
                   enrichment_wait_s: int = 60, verbose: bool = False) -> dict:
    """Convenience function for CLI/test harness integration."""
    gen = Signal360Generator(
        customer_id=customer_id,
        base_url=base_url,
        api_key=api_key,
        seed=seed,
        max_signals=max_signals,
        enrichment_wait_s=enrichment_wait_s,
    )
    return gen.run(verbose=verbose)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Signal Engine 360 Fidelity Test')
    parser.add_argument('--customer-id', type=int, required=True)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--api-key', required=True)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--max-signals', type=int, default=30)
    parser.add_argument('--wait', type=int, default=60, help='Seconds to wait for enrichment')
    parser.add_argument('--verbose', action='store_true')
    args = parser.parse_args()

    result = run_signal_360(
        customer_id=args.customer_id,
        base_url=args.base_url,
        api_key=args.api_key,
        seed=args.seed,
        max_signals=args.max_signals,
        enrichment_wait_s=args.wait,
        verbose=args.verbose,
    )
    print(f"\n  Result: {json.dumps({k:v for k,v in result.items() if k != 'details'}, indent=2)}")
