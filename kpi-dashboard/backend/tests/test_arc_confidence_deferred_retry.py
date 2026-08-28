"""
retry_deferred_evaluation_after_arc_classification() (state-of-play.md item
32 follow-up, 2026-08-27).

test_arc_confidence_no_fabrication.py confirmed evaluate_playbook_trigger_
for_account() correctly defers (returns None) rather than fabricating
arc_confidence=0.5 when Wizard A hasn't classified an account yet. That
alone leaves a gap flagged directly by review: nothing re-fires that
deferred evaluation once Wizard A actually sets the real value, since
HEALTH_SCORES_UPDATED is only published once per account during onboarding
(mcp_server/process_data_pipeline.py's publish_health_events) and
ArcPlaybookSubscriber's cooldown would very likely swallow a naively
re-published event fired seconds later in the same pipeline run anyway.

wizard_a_journey_db.py now calls retry_deferred_evaluation_after_arc_
classification() synchronously, right after committing the real arc_type/
arc_confidence, bypassing the event/cooldown machinery entirely. This
covers: the retry actually produces a real decision once real data exists,
it respects the same health-classification gate (skip when healthy) and
feature flags handle_event uses, and it never raises into Wizard A's
per-account loop even if something inside it fails.

Run against a dedicated postgres test DB:
    DATABASE_URL="postgresql://manojgupta@localhost:5432/cs_pulse_test" \\
        python3 -m pytest tests/test_arc_confidence_deferred_retry.py -v
"""
import os
import sys
import uuid
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_v3_minimal import app, db
from models import Account, Customer, HealthScore
from push_intelligence_subscriber import (
    evaluate_playbook_trigger_for_account,
    retry_deferred_evaluation_after_arc_classification,
)


def _assert_isolated_test_db(uri: str) -> None:
    """See tests/test_context_graph_invariants.py — same guard, same reason."""
    if os.environ.get('ALLOW_DESTRUCTIVE_TEST_DB') == '1':
        return
    db_name = uri.rsplit('/', 1)[-1].split('?', 1)[0]
    if 'test' not in db_name.lower():
        raise RuntimeError(
            f"test_arc_confidence_deferred_retry.py refuses to run "
            f"db.drop_all() against database {db_name!r} — its name "
            f"doesn't contain 'test'."
        )


@pytest.fixture(scope='module')
def ctx():
    app.config['TESTING'] = True
    db_uri = os.environ.get(
        'DATABASE_URL', 'postgresql://manojgupta@localhost:5432/cs_pulse_test'
    )
    _assert_isolated_test_db(db_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    with app.app_context():
        db.create_all()
        unique_email = f'arc_retry_{uuid.uuid4().hex[:8]}@test.com'
        customer = Customer(customer_name='Arc Retry Test Co', email=unique_email)
        db.session.add(customer)
        db.session.commit()
        yield {'customer_id': customer.customer_id}
        db.session.remove()
        db.drop_all()


def _make_account_with_health(ctx, *, health_score, arc_type=None, arc_confidence=None, name):
    account = Account(
        customer_id=ctx['customer_id'],
        account_name=name,
        revenue=1_000_000,
        external_account_id=f'RETRY-{uuid.uuid4().hex[:8]}',
        account_status='at_risk',
        arc_type=arc_type,
        arc_confidence=arc_confidence,
    )
    db.session.add(account)
    db.session.commit()
    db.session.add(HealthScore(
        account_id=account.account_id,
        measurement_month=date(2026, 3, 1),
        health_score=health_score,
        health_status='critical' if health_score < 50 else 'at_risk',
    ))
    db.session.commit()
    return account


class TestDeferredRetryAfterArcClassification:
    def test_deferred_evaluation_produces_no_decision_before_retry(self, ctx):
        """Sanity baseline: matches test_arc_confidence_no_fabrication.py --
        confirms the account genuinely starts in the deferred state this
        test's retry is meant to recover from."""
        with app.app_context():
            account = _make_account_with_health(
                ctx, health_score=35.0, arc_type='crisis_recovery',
                arc_confidence=None, name='Pre-retry Co',
            )
            result = evaluate_playbook_trigger_for_account(
                ctx['customer_id'], account.account_id, health_score=35.0,
            )
            assert result is None

    def test_retry_produces_a_real_decision_once_classified(self, ctx):
        """Simulates wizard_a_journey_db.py's hook: after Account.arc_type/
        arc_confidence get set for real, the retry call must produce an
        actual decision, not another deferral."""
        with app.app_context():
            account = _make_account_with_health(
                ctx, health_score=35.0, arc_type=None, arc_confidence=None,
                name='Post-retry Co',
            )
            # Simulate the HEALTH_SCORES_UPDATED event firing before Wizard A
            # -- confirms it defers, same as above.
            assert evaluate_playbook_trigger_for_account(
                ctx['customer_id'], account.account_id, health_score=35.0,
            ) is None

            # Simulate Wizard A completing (what wizard_a_journey_db.py does
            # immediately before calling the retry function).
            account.arc_type = 'crisis_recovery'
            account.arc_confidence = 0.85
            db.session.commit()

            retry_deferred_evaluation_after_arc_classification(
                ctx['customer_id'], account.account_id,
            )

            from models import PlaybookExecutionV2
            execution = PlaybookExecutionV2.query.filter_by(
                account_id=account.account_id,
            ).first()
            assert execution is not None, (
                "retry must produce a real playbook decision once arc "
                "classification exists — the original event must not stay "
                "permanently lost"
            )

    def test_retry_skips_healthy_accounts_same_as_live_event_path(self, ctx):
        """The retry must apply the same health-classification gate
        handle_event does — no decision for a healthy account."""
        with app.app_context():
            account = _make_account_with_health(
                ctx, health_score=92.0, arc_type='crisis_recovery',
                arc_confidence=0.9, name='Healthy Co',
            )
            retry_deferred_evaluation_after_arc_classification(
                ctx['customer_id'], account.account_id,
            )
            from models import PlaybookExecutionV2
            execution = PlaybookExecutionV2.query.filter_by(
                account_id=account.account_id,
            ).first()
            assert execution is None

    def test_retry_never_raises_on_a_nonexistent_account(self, ctx):
        """Must be safe to call unconditionally from Wizard A's per-account
        loop -- never propagate an exception into the caller."""
        with app.app_context():
            retry_deferred_evaluation_after_arc_classification(
                ctx['customer_id'], 999_999_999,
            )  # no assertion needed -- test passes if this doesn't raise


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
