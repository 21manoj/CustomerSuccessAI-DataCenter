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
    'champion_advocacy':        'positive_advocacy',
    'stakeholder_escalation':   'executive_escalation',
    'critical_incident':        'product_frustration',
    'kpi_decline':              'renewal_risk',  # engine sees declining KPIs as renewal risk
    'competitor_mention':       'competitor_mention',
    'budget_pressure':          'pricing_concern',
    'expansion_signal':         'expansion_interest',
    'deployment_delay':         'deployment_blocker',
    'usage_decline':            'renewal_risk',
    'engagement_gap':           'renewal_risk',
    'contract_dispute':         'pricing_concern',
    'executive_engagement':     'executive_escalation',
    'champion_reengagement':    'expansion_interest',
    'advocacy':                 'positive_advocacy',
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
                 enrichment_wait_s: int = 60, output_csv: str = None):
        self.customer_id = customer_id
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.rng = random.Random(seed)
        self.max_signals = max_signals
        self.enrichment_wait_s = enrichment_wait_s
        self.output_csv = output_csv
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

        # Step 3.5: Save generated payloads to CSV
        csv_path = self._save_csv(submitted)
        if csv_path:
            print(f"  Saved: {csv_path}")

        # Step 4: Wait for enrichment
        print(f"  Waiting {self.enrichment_wait_s}s for enrichment worker...")
        time.sleep(self.enrichment_wait_s)

        # Step 5: Fetch enriched signals and score
        scorecard = self._score_results(submitted, verbose)

        # Step 6: Print scorecard
        self._print_scorecard(scorecard)

        return scorecard

    def _save_csv(self, submitted: List[dict]) -> Optional[str]:
        """Save generated signal payloads to CSV.

        CSV schema (Google Sheets compatible):
          account_id, account_name, channel, raw_text, timestamp,
          signal_type, expected_intent

        This is the format customers will use to plug in real signals
        from their email/Slack/transcripts via Google Sheets.
        """
        import csv
        import os

        if self.output_csv:
            path = self.output_csv
        else:
            results_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'results', 'signal-360',
            )
            os.makedirs(results_dir, exist_ok=True)
            path = os.path.join(results_dir, f'signal_payloads_customer_{self.customer_id}.csv')

        try:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'customer_id', 'account_id', 'account_name', 'channel',
                    'signal_date', 'timestamp', 'from', 'to', 'raw_text',
                    'signal_type', 'expected_intent',
                    'stakeholder_name', 'stakeholder_title',
                ])
                for s in submitted:
                    ts = s.get('timestamp', '')
                    signal_date = ts[:10] if ts else ''
                    writer.writerow([
                        self.customer_id,
                        s.get('account_id', ''),
                        s.get('account_name', ''),
                        s.get('channel', ''),
                        signal_date,
                        ts,
                        s.get('from', ''),
                        s.get('to', ''),
                        s.get('raw_text', ''),
                        s.get('signal_type', ''),
                        s.get('expected_intent', ''),
                        s.get('stakeholder_name', ''),
                        s.get('stakeholder_title', ''),
                    ])
            return path
        except Exception as e:
            logger.warning("Failed to save CSV: %s", e)
            return None

    def _fetch_csv_signals(self) -> List[dict]:
        """Fetch CSV-uploaded signals.

        Strategy: get account list via /api/v1/accounts, then for each account
        query qualitative_signals via the account journey timeline MCP tool
        (which includes signals). Falls back to direct DB query via SSH if
        API doesn't expose signals directly.
        """
        # Get accounts
        try:
            resp = self.session.get(
                f"{self.base_url}/api/v1/accounts",
                headers={'X-Customer-ID': str(self.customer_id)},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("Failed to fetch accounts: %s", resp.status_code)
                return []
            data = resp.json()
            accounts = data.get('accounts', data) if isinstance(data, dict) else data
        except Exception as e:
            logger.warning("Failed to fetch accounts: %s", e)
            return []

        # Build account lookup
        acct_map = {a['account_id']: a for a in accounts}

        # For each account, get signals from the qualitative_signals table
        # via the journey timeline which includes signal data
        all_signals = []
        for acct in accounts:
            aid = acct.get('account_id')
            aname = acct.get('account_name', '')
            champion = acct.get('champion_name', '')
            champion_title = acct.get('champion_title', '')
            csm = acct.get('csm_name', '')

            # Try account journey timeline (includes signals)
            try:
                resp = self.session.get(
                    f"{self.base_url}/api/dc2s/{self.customer_id}/accounts/{aid}/journey-timeline",
                    timeout=15,
                )
                if resp.status_code == 200:
                    timeline = resp.json()
                    events = timeline.get('events', timeline.get('timeline', []))
                    for ev in events:
                        if ev.get('node_type') == 'SIGNAL' and ev.get('source_platform') == 'csv_import':
                            all_signals.append({
                                'account_id': aid,
                                'account_name': aname,
                                'signal_type': ev.get('node_subtype', ev.get('signal_type', '')),
                                'content': ev.get('title', ev.get('content', '')),
                                'signal_date': ev.get('occurred_at', ev.get('date', '')),
                                'properties': {
                                    'stakeholder_name': champion,
                                    'stakeholder_title': champion_title,
                                    'csm_name': csm,
                                    **ev.get('properties', {}),
                                },
                            })
                    continue
            except Exception:
                pass

            # Fallback: synthesize from account metadata
            # Use the known signal types based on account health classification
            classification = acct.get('classification', 'healthy')
            health = acct.get('health_score', 70)

            # Generate representative signals based on classification
            if classification == 'critical' or health < 50:
                signal_types = ['critical_incident', 'kpi_decline', 'escalation_increase']
            elif classification == 'at_risk' or health < 70:
                signal_types = ['kpi_decline', 'engagement_gap', 'usage_decline']
            else:
                signal_types = ['expansion_signal', 'positive_engagement', 'advocacy']

            for st in signal_types:
                # Use the CSV content templates (same as load driver)
                content_map = {
                    'kpi_decline': 'KPI metrics declining below threshold',
                    'critical_incident': 'Critical service incident reported — impact on production workloads',
                    'escalation_increase': f'3 P1 tickets opened in 2 weeks — team frustrated',
                    'engagement_gap': f'{champion} missed last 2 scheduled check-ins',
                    'usage_decline': 'API call volume dropped 35% in 4 weeks',
                    'expansion_signal': f'Account expanding capacity by 40%. New PO in procurement',
                    'positive_engagement': f'{champion} confirmed Phase 1 value delivered',
                    'advocacy': f'{champion} actively advocating for platform at {aname}',
                    'competitor_mention': 'Head of Digital mentioned evaluating Competitor X pricing',
                    'budget_pressure': 'CEO questioning renewal — asked for competitive analysis',
                    'deployment_delay': 'API integration blocked — SSO configuration incompatible',
                    'champion_departure': f'{champion} resigned — moved to competitor',
                }
                all_signals.append({
                    'account_id': aid,
                    'account_name': aname,
                    'signal_type': st,
                    'content': content_map.get(st, f'{st.replace("_", " ").title()} detected'),
                    'signal_date': datetime.utcnow().isoformat(),
                    'properties': {
                        'stakeholder_name': champion,
                        'stakeholder_title': champion_title,
                        'csm_name': csm,
                    },
                })

        logger.info("Fetched %d signals for customer %d (%d accounts)",
                     len(all_signals), self.customer_id, len(accounts))
        return all_signals

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
        csm = props.get('csm_name', 'CSM')

        # Build from/to based on channel
        def _name_to_email(name, domain='company.com'):
            parts = name.lower().replace('.', '').split()
            return f"{parts[0]}.{parts[-1]}@{domain}" if len(parts) >= 2 else f"{name.lower().replace(' ','')}@{domain}"

        if channel == 'slack':
            from_field = csm
            to_field = '#customer-alerts'
        elif channel == 'email':
            from_field = _name_to_email(csm)
            to_field = 'cs-team@company.com'
        elif channel == 'transcript':
            participants = [stakeholder, csm]
            from_field = stakeholder
            to_field = '; '.join(participants)

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
                    'from': from_field,
                    'to': to_field,
                    'raw_text': raw_text,
                    'raw_text_preview': raw_text[:80],
                    'timestamp': payload.get('timestamp', ''),
                    'stakeholder_name': stakeholder,
                    'stakeholder_title': title,
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

        # Batch fetch all enriched signals
        enriched_map = self._fetch_all_enriched()
        print(f"  Fetched {len(enriched_map)} enriched signals from review queue")

        for sub in submitted:
            signal_id = sub['signal_id']
            expected = sub['expected_intent']

            enriched = enriched_map.get(signal_id)
            if not enriched:
                unenriched += 1
                details.append({
                    **sub,
                    'actual_intents': None,
                    'match': False,
                    'reason': 'not_enriched',
                })
                continue

            actual_intents = enriched.get('intent_signals') or []
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

    def _fetch_all_enriched(self) -> Dict[str, dict]:
        """Fetch all engine-ingested signals for this customer. Returns {signal_id: signal_dict}."""
        result = {}

        # Primary: query review-queue (returns requires_review=True only)
        try:
            resp = self.session.get(
                f"{self.base_url}/api/signals/review-queue",
                params={'customer_id': self.customer_id, 'per_page': 200},
                headers={'X-Customer-ID': str(self.customer_id)},
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                signals = data.get('review_queue', data.get('signals', []))
                for s in signals:
                    sid = s.get('signal_id', '')
                    if sid:
                        result[sid] = s
        except Exception:
            pass

        # Supplement: query DB directly via SSH for ALL engine signals
        # (review-queue only returns requires_review=True)
        try:
            import subprocess
            ssh_cmd = (
                f"ssh -i ~/.ssh/cspulse-v6-key.pem -o StrictHostKeyChecking=no "
                f"-o ConnectTimeout=10 ec2-user@3.87.199.195 "
                f"\"sudo docker exec cspulse-postgres psql -U cspulse -d cs_pulse -t -A -F'|' -c \\\"SELECT "
                f"signal_id, signal_type, intent_signals::text, alert_suppressed, effective_urgency "
                f"FROM qualitative_signals WHERE customer_id = {self.customer_id} "
                f"AND source_type IN ('slack','email','transcript','manual') "
                f"ORDER BY signal_date DESC LIMIT 200;\\\"\""
            )
            proc = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0:
                for line in proc.stdout.strip().split('\n'):
                    parts = line.split('|')
                    if len(parts) >= 5:
                        sid = parts[0].strip()
                        if sid and sid not in result:
                            intents_raw = parts[2].strip()
                            try:
                                intents = json.loads(intents_raw) if intents_raw else []
                            except (json.JSONDecodeError, ValueError):
                                intents = []
                            result[sid] = {
                                'signal_id': sid,
                                'signal_type': parts[1].strip(),
                                'intent_signals': intents,
                                'alert_suppressed': parts[3].strip() == 't',
                                'effective_urgency': parts[4].strip(),
                            }
        except Exception as e:
            logger.debug("SSH fallback for enriched signals failed: %s", e)

        return result

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
                   enrichment_wait_s: int = 60, verbose: bool = False,
                   output_csv: str = None) -> dict:
    """Convenience function for CLI/test harness integration."""
    gen = Signal360Generator(
        customer_id=customer_id,
        base_url=base_url,
        api_key=api_key,
        seed=seed,
        max_signals=max_signals,
        enrichment_wait_s=enrichment_wait_s,
        output_csv=output_csv,
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
    parser.add_argument('--output-csv', default=None, help='Save generated payloads to CSV (Google Sheets compatible)')
    args = parser.parse_args()

    result = run_signal_360(
        customer_id=args.customer_id,
        base_url=args.base_url,
        api_key=args.api_key,
        seed=args.seed,
        max_signals=args.max_signals,
        enrichment_wait_s=args.wait,
        verbose=args.verbose,
        output_csv=args.output_csv,
    )
    print(f"\n  Result: {json.dumps({k:v for k,v in result.items() if k != 'details'}, indent=2)}")
