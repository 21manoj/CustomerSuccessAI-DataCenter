#!/usr/bin/env python3
"""
Raw Unstructured Signal Generator for Signal Engine Testing
============================================================

Reads a manifest file and generates realistic unstructured data
(Slack messages, emails, meeting transcripts) from account narratives,
then POSTs them to the signal engine ingest endpoints.

Usage:
    python generate_raw_signals.py --manifest manifests/topology_test_dc2s.json \
        --base-url https://d2oqfugrb2ltg9.cloudfront.net \
        --email admin@topologytest.com --password test123

    # Dry run — generate signals to stdout without posting
    python generate_raw_signals.py --manifest manifests/topology_test_dc2s.json --dry-run

What it generates per account:
    - 2-3 Slack messages (channel discussions about the account)
    - 1-2 emails (from stakeholders to CSM team)
    - 1 meeting transcript (QBR or escalation call)
    - Key signal events as manual entries

All text is derived from the manifest's narrative, stakeholders,
and key_signals — not random. Each signal is contextually correct
for the account's story arc and health trajectory.
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Signal templates by arc type ──

SLACK_TEMPLATES = {
    'champion_loss': [
        "Just got off a call with {account}. {stakeholder} confirmed they're leaving end of month. New person {successor} seems skeptical about our platform. We need an exec-to-exec ASAP.",
        "Heads up team — {account} GPU utilization dropped to {metric}% this week. Correlates with {stakeholder}'s departure. The new team isn't using the optimization features we built for them.",
        "Anyone else seeing the {account} usage cliff? Their ticket volume spiked 3x since the leadership change. I think {successor} is evaluating alternatives.",
    ],
    'silent_churn': [
        "Has anyone heard from {account} lately? Last login was {days_ago} days ago. No response to my last 3 emails. Their usage is down {metric}% month-over-month.",
        "Flagging {account} — zero engagement for {days_ago}+ days. NPS dropped from 45 to 15 with no explanation. Classic silent churn pattern. Should we send an exec email?",
        "Checked {account}'s usage dashboard — they've migrated {metric}% of workloads off our platform in the last 30 days. No ticket, no call, no warning. Ghost mode.",
    ],
    'stalled_deployment': [
        "Update on {account}: HIPAA deployment still stuck at {metric}%. {stakeholder} says our support response times are unacceptable. 12 open tickets, oldest is 3 weeks.",
        "{account} escalation — {stakeholder} cancelled this week's deployment sync again. That's 3 in a row. They're threatening to pause the contract unless we assign a dedicated engineer.",
        "Team, {account}'s {stakeholder} just sent a pretty heated email about the stalled deployment. We promised 90% completion by EOQ and we're at {metric}%. Need a plan by Friday.",
    ],
    'expansion_champion': [
        "Great news from {account}! {stakeholder} wants to expand into {new_department}. They're asking for a capacity planning call next week. Potential {arr_delta} upsell.",
        "{account}'s {stakeholder} agreed to be a reference customer! They're keynoting at our user conference. GPU utilization at {metric}% — they're genuinely happy.",
        "FYI — {account} just submitted a request for 200% capacity increase. {stakeholder} says the ML pipeline results are exceeding expectations. Let's fast-track this.",
    ],
    'steady_performer': [
        "Quick update on {account}: QBR went well. {stakeholder} is satisfied with current setup. No issues, no expansion plans for now. Renewal should be straightforward.",
        "{account} monthly check-in: usage stable at {metric}%, no tickets, NPS steady. Low-touch account doing exactly what we want.",
    ],
    'budget_pressure': [
        "Bad news from {account} — Q4 earnings miss triggered 15% budget cuts. {stakeholder} says CFO is mandating vendor consolidation review. We need a TCO comparison ASAP.",
        "{account}'s CFO is requesting competitive bids from 3 vendors. {stakeholder} is trying to protect our deal but needs ammunition. Can we put together an ROI deck by Thursday?",
    ],
    'infrastructure_decay': [
        "URGENT: {account} had a Sev-1 outage in Pod 3. 6 hours of production downtime. {stakeholder} is furious. CEO called our VP Sales directly demanding root cause in 48 hours.",
        "{account} post-mortem update — MTBF dropped below SLA. {stakeholder} started migrating 30% of workloads to backup DC. We're at risk of losing the entire contract.",
    ],
}

EMAIL_TEMPLATES = {
    'champion_loss': [
        {
            'subject': 'Concerns about platform direction — {account}',
            'from': '{stakeholder_email}',
            'body': "Hi team,\n\nI wanted to share some concerns about our current infrastructure partnership. Since the leadership transition, our team has been evaluating several alternatives including AWS and CoreWeave for our AI workloads.\n\nOur GPU utilization has dropped significantly and the new team isn't seeing the value proposition that was originally sold. I'd like to schedule an executive review to discuss our options before the renewal date.\n\nCan we set up a call this week?\n\nBest,\n{stakeholder}",
        },
    ],
    'silent_churn': [
        {
            'subject': 'RE: Quarterly Business Review — {account}',
            'from': '{stakeholder_email}',
            'body': "Hi,\n\nApologies for the delayed response. We've been going through some internal restructuring and haven't had bandwidth for external meetings.\n\nRegarding the QBR — let's push it to next quarter. We're still evaluating our infrastructure needs.\n\nThanks,\n{stakeholder}",
        },
    ],
    'stalled_deployment': [
        {
            'subject': 'ESCALATION: HIPAA Deployment Delays — {account}',
            'from': '{stakeholder_email}',
            'body': "To whom it may concern,\n\nI'm writing to formally escalate the ongoing delays with our HIPAA-compliant deployment. We are now 4 months behind the agreed timeline, with completion at only {metric}%.\n\nKey issues:\n1. 12 support tickets remain unresolved (oldest: 3 weeks)\n2. Weekly deployment syncs have been cancelled 3 times\n3. Our clinical team cannot proceed with Phase 2 until this is resolved\n\nIf we do not see significant progress by end of month, we will need to pause our contract and evaluate alternatives.\n\nRegards,\n{stakeholder}\n{stakeholder_title}, {account}",
        },
    ],
    'expansion_champion': [
        {
            'subject': 'Expansion proposal — {account} ML Pipeline Scale-up',
            'from': '{stakeholder_email}',
            'body': "Hi team,\n\nFollowing our discussion at the last QBR, I'd like to formally request a capacity planning session for our ML training pipeline expansion.\n\nWe're looking to scale from 100 to 500 GPU hours/day. The results from our current workloads have been excellent — our data science team is publishing papers citing your infrastructure.\n\nAdditionally, our marketing analytics department has expressed interest in onboarding. Could we schedule a discovery call for next week?\n\nBest,\n{stakeholder}\n{stakeholder_title}, {account}",
        },
    ],
}

TRANSCRIPT_TEMPLATES = {
    'champion_loss': """
QBR Call — {account} | {date}
Participants: {participants}

[00:00] CSM: Thank you all for joining. Let's start with a health check on your GPU infrastructure.
[02:15] {successor}: Before we get into metrics, I want to address the elephant in the room. Since {stakeholder} left, our team has been re-evaluating our infrastructure partnerships.
[03:30] CSM: Understood. What specific concerns does your team have?
[04:45] {successor}: Honestly? We're not sure we're getting the value we were promised. Our utilization dropped from 85% to {metric}% and the new team doesn't have the institutional knowledge to optimize.
[06:00] CSM: That's a fair concern. We have optimization playbooks specifically designed for leadership transitions. Can I walk you through what we've done for similar customers?
[07:30] {successor}: I'm open to hearing it, but I should be transparent — we've already started an RFP process with two other vendors.
[09:00] CSM: I appreciate the honesty. Let me bring in our VP of Customer Success for an executive-level discussion about your roadmap.
[10:15] {successor}: That would be helpful. But we need to see concrete improvement in the next 30 days or the decision will be made without us.
""",
    'stalled_deployment': """
Escalation Call — {account} HIPAA Deployment | {date}
Participants: {participants}

[00:00] {stakeholder}: I'll be direct. We've been at {metric}% deployment for 4 months. This is unacceptable.
[01:30] CSM: I understand your frustration. Let me share what we've identified as the blockers.
[02:45] {stakeholder}: We have 12 unresolved tickets. My team has stopped attending the weekly syncs because nothing changes between calls.
[04:00] CSM: I hear you. We're assigning a dedicated deployment engineer starting this week. They'll own the remaining 55% of the deployment with weekly accountability checkpoints.
[05:30] {stakeholder}: We've heard promises before. What's different this time?
[06:15] CSM: Two things: first, the dedicated engineer reports directly to our VP of Engineering, not through support. Second, we're committing to a 6-week completion timeline with weekly milestones.
[07:45] {stakeholder}: If you can get us to 90% in 6 weeks, we'll proceed with the Phase 2 expansion. If not, we're pausing the contract.
[08:30] CSM: Understood. I'll have the engineer reach out by end of day tomorrow with a detailed project plan.
""",
    'expansion_champion': """
QBR Call — {account} Expansion Planning | {date}
Participants: {participants}

[00:00] CSM: Great to see everyone. {stakeholder}, congratulations on the conference keynote — your team's results were impressive.
[01:15] {stakeholder}: Thank you! The ML pipeline has been transformative. Which brings me to why I wanted this meeting.
[02:30] {stakeholder}: We want to scale from 100 to 500 GPU hours per day. And our marketing analytics department wants to onboard as a new use case.
[03:45] CSM: That's fantastic. Can you walk us through the timeline you're envisioning?
[05:00] {stakeholder}: Ideally Q2 for the scale-up, Q3 for marketing onboarding. {finance_person} has approved the budget contingent on a volume discount.
[06:30] {finance_person}: Yes, we're looking at a 3-year commitment if the pricing works. The ROI from the current deployment is clear — 12% cost savings on our training pipeline.
[08:00] CSM: I'll put together a proposal by end of week. For the marketing use case, we'll need a discovery session to understand the workload profile.
[09:15] {stakeholder}: Perfect. Also, I've agreed to be a reference customer for your next user conference. Happy to share our story.
""",
}


def _pick_stakeholder(account: dict, role: str = 'champion') -> dict:
    """Pick a stakeholder by role, or first available."""
    stakeholders = account.get('stakeholders', [])
    for s in stakeholders:
        if s.get('role') == role:
            return s
    return stakeholders[0] if stakeholders else {'name': 'Unknown Contact', 'role': 'champion', 'title': 'Director'}


def _gen_email(name: str) -> str:
    """Generate email from name."""
    return name.lower().replace(' ', '.').replace("'", '') + '@company.com'


def generate_signals_for_account(account: dict, customer_id: int, account_id: int) -> list:
    """Generate raw unstructured signals for one account."""
    signals = []
    arc = account.get('story_arc', 'steady_performer')
    name = account.get('name', f'Account {account_id}')
    champion = _pick_stakeholder(account, 'champion')
    successor = _pick_stakeholder(account, 'successor') or _pick_stakeholder(account, 'technical_lead')
    exec_sponsor = _pick_stakeholder(account, 'executive_sponsor') or champion
    finance = _pick_stakeholder(account, 'economic_buyer') or _pick_stakeholder(account, 'finance')

    health = account.get('target_health', 70)
    metric = random.randint(25, 45) if health < 50 else random.randint(60, 85)
    days_ago = random.randint(60, 120) if arc == 'silent_churn' else random.randint(5, 30)
    arr_delta = f"${random.randint(500, 2000)}K"
    new_department = random.choice(['Marketing Analytics', 'Data Science', 'Security Operations', 'Product Engineering'])

    base_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))

    context = {
        'account': name,
        'stakeholder': champion.get('name', 'Champion'),
        'stakeholder_email': _gen_email(champion.get('name', 'contact')),
        'stakeholder_title': champion.get('title', 'Director'),
        'successor': successor.get('name', 'New Lead'),
        'finance_person': finance.get('name', 'Finance Lead'),
        'metric': str(metric),
        'days_ago': str(days_ago),
        'arr_delta': arr_delta,
        'new_department': new_department,
        'date': base_date.strftime('%B %d, %Y'),
        'participants': ', '.join([s.get('name', '?') for s in account.get('stakeholders', [])[:4]] + ['CSM Team']),
    }

    # Map arc to template key (normalize)
    arc_key = arc
    for alias, canonical in [
        ('competitor_evaluation', 'champion_loss'),
        ('engagement_decline', 'silent_churn'),
        ('crisis_recovery', 'infrastructure_decay'),
        ('exec_sponsor_change', 'champion_loss'),
        ('land_and_expand', 'expansion_champion'),
        ('seasonal_surge', 'steady_performer'),
    ]:
        if arc == alias:
            arc_key = canonical
            break

    # 1. Slack messages (2-3)
    slack_templates = SLACK_TEMPLATES.get(arc_key, SLACK_TEMPLATES['steady_performer'])
    for i, tmpl in enumerate(random.sample(slack_templates, min(len(slack_templates), random.randint(2, 3)))):
        ts = base_date - timedelta(days=i * 3, hours=random.randint(0, 8))
        signals.append({
            'source_type': 'slack',
            'account_id': account_id,
            'customer_id': customer_id,
            'raw_text': tmpl.format(**context),
            'timestamp': ts.isoformat() + 'Z',
            'thread_or_channel_id': f'C-{name.replace(" ", "-").lower()}-{random.randint(1000,9999)}',
            'participant_list': [
                {'name': 'CSM Team', 'role': 'csm'},
                {'name': champion.get('name', '?'), 'role': champion.get('role', 'champion')},
            ],
        })

    # 2. Emails (1-2)
    email_templates = EMAIL_TEMPLATES.get(arc_key, [])
    for tmpl in email_templates[:random.randint(1, 2)]:
        ts = base_date - timedelta(days=random.randint(2, 14))
        signals.append({
            'source_type': 'email',
            'account_id': account_id,
            'customer_id': customer_id,
            'raw_text': f"Subject: {tmpl['subject'].format(**context)}\nFrom: {tmpl['from'].format(**context)}\n\n{tmpl['body'].format(**context)}",
            'timestamp': ts.isoformat() + 'Z',
        })

    # 3. Meeting transcript (1 per account if template exists)
    transcript_tmpl = TRANSCRIPT_TEMPLATES.get(arc_key)
    if transcript_tmpl:
        ts = base_date - timedelta(days=random.randint(5, 20))
        signals.append({
            'source_type': 'transcript',
            'account_id': account_id,
            'customer_id': customer_id,
            'raw_text': transcript_tmpl.format(**context),
            'timestamp': ts.isoformat() + 'Z',
            'consent_verified': True,
            'participant_list': [
                {'name': s.get('name', '?'), 'role': s.get('role', 'stakeholder')}
                for s in account.get('stakeholders', [])[:4]
            ] + [{'name': 'CSM Team', 'role': 'csm'}],
        })

    # 4. Key signals as manual entries
    for sig in account.get('key_signals', []):
        ts = base_date - timedelta(days=random.randint(0, 60))
        signals.append({
            'source_type': 'manual',
            'account_id': account_id,
            'customer_id': customer_id,
            'raw_text': f"[{sig.get('type', 'observation')}] {sig.get('description', sig.get('content', ''))}",
            'timestamp': ts.isoformat() + 'Z',
        })

    return signals


def main():
    parser = argparse.ArgumentParser(description='Generate raw unstructured signals from manifest')
    parser.add_argument('--manifest', required=True, help='Path to manifest JSON')
    parser.add_argument('--base-url', default='https://d2oqfugrb2ltg9.cloudfront.net', help='CS Pulse base URL')
    parser.add_argument('--email', default=None, help='Admin email for login')
    parser.add_argument('--password', default='test123', help='Admin password')
    parser.add_argument('--customer-id', type=int, default=None, help='Customer ID (auto-detected from login)')
    parser.add_argument('--dry-run', action='store_true', help='Print signals without posting')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
    args = parser.parse_args()

    random.seed(args.seed)

    # Load manifest
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Manifest not found: {manifest_path}")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    customer_name = manifest['customer']['name']
    admin_email = args.email or manifest['customer'].get('admin_email', '')
    accounts = manifest.get('accounts', [])

    print(f"=== Raw Signal Generator ===")
    print(f"  Manifest:  {manifest_path.name}")
    print(f"  Customer:  {customer_name}")
    print(f"  Accounts:  {len(accounts)}")
    print()

    if args.dry_run:
        # Generate and print
        for idx, acct in enumerate(accounts):
            account_id = (args.customer_id or 999) * 1000 + 1 + idx
            signals = generate_signals_for_account(acct, args.customer_id or 999, account_id)
            print(f"--- {acct['name']} ({acct.get('story_arc', '?')}) --- {len(signals)} signals")
            for sig in signals:
                print(f"  [{sig['source_type']}] {sig['raw_text'][:120]}...")
            print()

        total = sum(
            len(generate_signals_for_account(a, 0, i))
            for i, a in enumerate(accounts)
        )
        print(f"Total: {total} signals across {len(accounts)} accounts")
        return

    # Live mode — login and POST signals
    import requests

    session = requests.Session()
    login_resp = session.post(
        f"{args.base_url}/api/login",
        json={'email': admin_email, 'password': args.password},
    )
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.status_code} {login_resp.text[:200]}")
        sys.exit(1)

    login_data = login_resp.json()
    customer_id = args.customer_id or login_data.get('user', {}).get('customer_id')
    print(f"  Logged in as {admin_email} (customer_id={customer_id})")

    # Get account IDs from the platform
    acct_resp = session.get(f"{args.base_url}/api/dc2s/accounts")
    if acct_resp.ok:
        platform_accounts = acct_resp.json().get('accounts', [])
        account_id_map = {a.get('account_name', ''): a['account_id'] for a in platform_accounts}
        print(f"  Platform accounts: {len(platform_accounts)}")
    else:
        account_id_map = {}
        print(f"  Warning: couldn't fetch accounts ({acct_resp.status_code})")

    total_posted = 0
    total_errors = 0

    for idx, acct in enumerate(accounts):
        acct_name = acct['name']
        # Resolve account_id: try platform match, fall back to generated ID
        account_id = account_id_map.get(acct_name, customer_id * 1000 + 1 + idx)

        signals = generate_signals_for_account(acct, customer_id, account_id)
        print(f"\n  {acct_name} (arc={acct.get('story_arc', '?')}, id={account_id}): {len(signals)} signals")

        for sig in signals:
            source = sig.pop('source_type')
            endpoint = f"{args.base_url}/api/signals/ingest/{source}"
            resp = session.post(endpoint, json=sig)

            if resp.status_code == 202:
                total_posted += 1
                print(f"    [{source}] 202 OK — {sig['raw_text'][:80]}...")
            elif resp.status_code == 403:
                print(f"    [{source}] 403 — Signal engine not enabled for customer {customer_id}")
                print(f"    Hint: enable via MCP: enable_features(customer_id={customer_id}, features=['signal_engine'])")
                return
            else:
                total_errors += 1
                err = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                print(f"    [{source}] {resp.status_code} — {err.get('error', resp.text[:100])}")

    print(f"\n=== Done ===")
    print(f"  Posted: {total_posted} signals")
    print(f"  Errors: {total_errors}")
    if total_posted > 0:
        print(f"  Enrichment worker will process these within 30 seconds.")
        print(f"  Check logs: docker compose exec cs-pulse grep 'QSIM enrichment' /proc/1/fd/1")


if __name__ == '__main__':
    main()
