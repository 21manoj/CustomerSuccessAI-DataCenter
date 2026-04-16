#!/usr/bin/env python3
"""
Ring 1 — Generic Data Ingestion API for CS Pulse
=================================================

Source-agnostic endpoints that accept structured JSON from any integration
layer (n8n, Zapier, custom scripts, direct API calls).  The endpoints
normalise, validate and upsert data into the platform tables, then
publish events so downstream processors (health-score rollup, RAG
rebuild, signal analyst) can react.

Blueprint prefix: /api/data-ingestion/

Endpoints
---------
POST /api/data-ingestion/kpis      — Ingest KPI measurements
POST /api/data-ingestion/signals   — Ingest qualitative signals
POST /api/data-ingestion/contacts  — Ingest / update champion contacts
"""

import uuid
import logging
from datetime import datetime, date

from flask import Blueprint, request, jsonify
from sqlalchemy.dialects.postgresql import insert

from extensions import db
from models import DC2SKPI, QualitativeSignal, Account
from auth_middleware import get_current_customer_id

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------
try:
    from logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event publishing helper
# ---------------------------------------------------------------------------

def _try_publish_event(event_type_name: str, customer_id: int, data: dict):
    """
    Best-effort event publish.  If the event system is not wired up (e.g.
    in unit tests) we log a warning but never fail the request.
    """
    try:
        from event_system import EventPublisher, EventType
        publisher = EventPublisher()
        event_type = getattr(EventType, event_type_name, None)
        if event_type:
            publisher.publish(event_type, customer_id, data)
            logger.info("Published event %s for customer %s", event_type_name, customer_id)
        else:
            logger.warning("Unknown EventType: %s — skipped publish", event_type_name)
    except Exception as exc:
        logger.warning("Event publish failed (non-fatal): %s", exc)

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

data_ingestion_api = Blueprint('data_ingestion_api', __name__)

# ===========================================================================
#  POST /api/data-ingestion/kpis
# ===========================================================================

KPI_REQUIRED_FIELDS = {'account_id', 'kpi_code', 'measured_at', 'value'}

@data_ingestion_api.route('/api/data-ingestion/kpis', methods=['POST'])
def ingest_kpis():
    """Ingest an array of KPI measurements.

    Expects JSON body::

        {
          "source": "google_sheets",          // optional, for audit trail
          "records": [
            {
              "account_id": 1001,
              "kpi_code": "nrr",
              "measured_at": "2026-03-01",    // ISO date or datetime
              "value": 95.5,
              "target": 100.0,                // optional
              "pillar": "financial_health"    // optional
            }
          ]
        }

    Returns::

        {
          "status": "ok",
          "source": "google_sheets",
          "inserted": 5,
          "updated": 2,
          "skipped": 0,
          "errors": [ ... ]
        }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    payload = request.get_json(silent=True)
    if not payload or 'records' not in payload:
        return jsonify({'error': 'Request body must contain a "records" array'}), 400

    source = payload.get('source', 'unknown')
    records = payload['records']

    if not isinstance(records, list):
        return jsonify({'error': '"records" must be an array'}), 400

    if len(records) == 0:
        return jsonify({
            'status': 'ok', 'source': source,
            'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': [],
        }), 200

    errors = []
    valid_rows = []

    for idx, rec in enumerate(records):
        missing = KPI_REQUIRED_FIELDS - set(rec.keys())
        if missing:
            errors.append({
                'index': idx,
                'error': f'Missing required fields: {", ".join(sorted(missing))}',
                'record': rec,
            })
            continue

        # Parse measured_at
        try:
            measured_at = _parse_datetime(rec['measured_at'])
        except (ValueError, TypeError) as exc:
            errors.append({
                'index': idx,
                'error': f'Invalid measured_at: {exc}',
                'record': rec,
            })
            continue

        # Validate value is numeric
        try:
            value = float(rec['value'])
        except (ValueError, TypeError):
            errors.append({
                'index': idx,
                'error': f'Invalid value (must be numeric): {rec["value"]}',
                'record': rec,
            })
            continue

        row = {
            'account_id': int(rec['account_id']),
            'kpi_code': str(rec['kpi_code']).strip(),
            'measured_at': measured_at,
            'value': value,
        }
        if 'target' in rec and rec['target'] is not None:
            row['target'] = float(rec['target'])
        if 'pillar' in rec and rec['pillar'] is not None:
            row['pillar'] = str(rec['pillar']).strip()

        valid_rows.append(row)

    # Upsert valid rows in one batch via PostgreSQL INSERT ... ON CONFLICT
    inserted = 0
    updated = 0
    if valid_rows:
        try:
            # Count existing rows to determine inserted vs updated
            existing_keys = set()
            for row in valid_rows:
                key = (row['account_id'], row['kpi_code'], row['measured_at'])
                exists = db.session.query(DC2SKPI.kpi_id).filter(
                    DC2SKPI.account_id == key[0],
                    DC2SKPI.kpi_code == key[1],
                    DC2SKPI.measured_at == key[2],
                ).first()
                if exists:
                    existing_keys.add(key)

            stmt = insert(DC2SKPI).values(valid_rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=['account_id', 'kpi_code', 'measured_at'],
                set_={
                    'value': stmt.excluded.value,
                    'target': stmt.excluded.target,
                    'pillar': stmt.excluded.pillar,
                },
            )
            db.session.execute(stmt)
            db.session.commit()

            updated = len(existing_keys)
            inserted = len(valid_rows) - updated

            logger.info(
                "KPI ingestion complete: source=%s customer=%s inserted=%d updated=%d errors=%d",
                source, customer_id, inserted, updated, len(errors),
            )
        except Exception as exc:
            db.session.rollback()
            logger.exception("KPI ingestion failed: %s", exc)
            return jsonify({
                'error': f'Database error: {exc}',
                'source': source,
                'inserted': 0, 'updated': 0,
                'skipped': 0, 'errors': errors,
            }), 500

    # Publish event for downstream processing (health score recalculation, RAG rebuild)
    if inserted or updated:
        account_ids = list({r['account_id'] for r in valid_rows})
        _try_publish_event('KPI_DATA_UPLOADED', customer_id, {
            'source': source,
            'account_ids': account_ids,
            'inserted': inserted,
            'updated': updated,
        })

    return jsonify({
        'status': 'ok',
        'source': source,
        'inserted': inserted,
        'updated': updated,
        'skipped': 0,
        'errors': errors,
    }), 200


# ===========================================================================
#  POST /api/data-ingestion/signals
# ===========================================================================

SIGNAL_REQUIRED_FIELDS = {'account_id', 'signal_date', 'signal_type', 'content'}

@data_ingestion_api.route('/api/data-ingestion/signals', methods=['POST'])
def ingest_signals():
    """Ingest an array of qualitative signals (tickets, emails, meetings, etc.).

    Expects JSON body::

        {
          "source": "servicenow",
          "records": [
            {
              "account_id": 1001,
              "signal_date": "2026-03-01",
              "signal_type": "support_ticket",
              "content": "Critical P1 issue reported",
              "source": "ServiceNow",
              "severity": "high",
              "sentiment_score": -0.8
            }
          ]
        }

    Returns::

        {
          "status": "ok",
          "source": "servicenow",
          "inserted": 3,
          "updated": 1,
          "skipped": 0,
          "errors": [ ... ]
        }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    payload = request.get_json(silent=True)
    if not payload or 'records' not in payload:
        return jsonify({'error': 'Request body must contain a "records" array'}), 400

    source = payload.get('source', 'unknown')
    records = payload['records']

    if not isinstance(records, list):
        return jsonify({'error': '"records" must be an array'}), 400

    if len(records) == 0:
        return jsonify({
            'status': 'ok', 'source': source,
            'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': [],
        }), 200

    # Map severity text to a sentiment bucket for convenience
    SEVERITY_SENTIMENT_MAP = {
        'critical': 'negative',
        'high': 'negative',
        'medium': 'neutral',
        'low': 'positive',
    }

    errors = []
    valid_rows = []

    for idx, rec in enumerate(records):
        missing = SIGNAL_REQUIRED_FIELDS - set(rec.keys())
        if missing:
            errors.append({
                'index': idx,
                'error': f'Missing required fields: {", ".join(sorted(missing))}',
                'record': rec,
            })
            continue

        # Parse signal_date
        try:
            signal_date = _parse_date(rec['signal_date'])
        except (ValueError, TypeError) as exc:
            errors.append({
                'index': idx,
                'error': f'Invalid signal_date: {exc}',
                'record': rec,
            })
            continue

        # Generate a deterministic signal_id if not provided
        signal_id = rec.get('signal_id')
        if not signal_id:
            signal_id = f"SIG-{rec['account_id']}-{signal_date.isoformat()}-{uuid.uuid4().hex[:8]}"

        # Derive sentiment from severity if not explicitly provided
        severity = rec.get('severity', '').lower()
        sentiment = rec.get('sentiment') or SEVERITY_SENTIMENT_MAP.get(severity, 'neutral')

        row = {
            'signal_id': str(signal_id),
            'customer_id': customer_id,
            'account_id': int(rec['account_id']),
            'signal_date': signal_date,
            'signal_type': str(rec['signal_type']).strip(),
            'content': str(rec['content']),
            'sentiment': sentiment,
        }

        # Optional fields
        if 'sentiment_score' in rec and rec['sentiment_score'] is not None:
            try:
                row['sentiment_score'] = float(rec['sentiment_score'])
            except (ValueError, TypeError):
                pass  # ignore bad sentiment_score, use default

        if 'stakeholder_level' in rec:
            row['stakeholder_level'] = str(rec['stakeholder_level']).strip()
        if 'stakeholder_title' in rec:
            row['stakeholder_title'] = str(rec['stakeholder_title']).strip()
        if 'keywords' in rec:
            row['keywords'] = str(rec['keywords']) if rec['keywords'] else None

        valid_rows.append(row)

    # Upsert via PostgreSQL INSERT ... ON CONFLICT
    inserted = 0
    updated = 0
    if valid_rows:
        try:
            # Determine which signal_ids already exist
            existing_ids = set()
            batch_ids = [r['signal_id'] for r in valid_rows]
            existing_rows = db.session.query(QualitativeSignal.signal_id).filter(
                QualitativeSignal.customer_id == customer_id,
                QualitativeSignal.signal_id.in_(batch_ids)
            ).all()
            existing_ids = {row[0] for row in existing_rows}

            stmt = insert(QualitativeSignal).values(valid_rows)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_customer_signal_id',
                set_={
                    'content': stmt.excluded.content,
                    'sentiment': stmt.excluded.sentiment,
                    'sentiment_score': stmt.excluded.sentiment_score,
                    'signal_type': stmt.excluded.signal_type,
                },
            )
            db.session.execute(stmt)
            db.session.commit()

            updated = len(existing_ids)
            inserted = len(valid_rows) - updated

            logger.info(
                "Signal ingestion complete: source=%s customer=%s inserted=%d updated=%d errors=%d",
                source, customer_id, inserted, updated, len(errors),
            )
        except Exception as exc:
            db.session.rollback()
            logger.exception("Signal ingestion failed: %s", exc)
            return jsonify({
                'error': f'Database error: {exc}',
                'source': source,
                'inserted': 0, 'updated': 0,
                'skipped': 0, 'errors': errors,
            }), 500

    # Publish event for downstream processing
    if inserted or updated:
        account_ids = list({r['account_id'] for r in valid_rows})
        _try_publish_event('ACCOUNT_DATA_CHANGED', customer_id, {
            'source': source,
            'reason': 'signals_ingested',
            'account_ids': account_ids,
            'inserted': inserted,
            'updated': updated,
        })

    return jsonify({
        'status': 'ok',
        'source': source,
        'inserted': inserted,
        'updated': updated,
        'skipped': 0,
        'errors': errors,
    }), 200


# ===========================================================================
#  POST /api/data-ingestion/contacts
# ===========================================================================

CONTACT_REQUIRED_FIELDS = {'account_id', 'champion_name'}

@data_ingestion_api.route('/api/data-ingestion/contacts', methods=['POST'])
def ingest_contacts():
    """Ingest / update champion contact information.

    Champions are stored inside the ``Account.profile_metadata`` JSON
    field under the ``champions`` key.  This endpoint merges incoming
    records by ``champion_email`` (if present) or ``champion_name``,
    so repeated pushes update rather than duplicate.

    Expects JSON body::

        {
          "source": "salesforce",
          "records": [
            {
              "account_id": 1001,
              "champion_name": "John Smith",
              "champion_role": "VP Engineering",
              "champion_email": "john@acme.com",
              "champion_sentiment": "positive"
            }
          ]
        }

    Returns::

        {
          "status": "ok",
          "source": "salesforce",
          "inserted": 2,
          "updated": 1,
          "skipped": 0,
          "errors": [ ... ]
        }
    """
    customer_id = get_current_customer_id()
    if not customer_id:
        return jsonify({'error': 'Authentication required'}), 401

    payload = request.get_json(silent=True)
    if not payload or 'records' not in payload:
        return jsonify({'error': 'Request body must contain a "records" array'}), 400

    source = payload.get('source', 'unknown')
    records = payload['records']

    if not isinstance(records, list):
        return jsonify({'error': '"records" must be an array'}), 400

    if len(records) == 0:
        return jsonify({
            'status': 'ok', 'source': source,
            'inserted': 0, 'updated': 0, 'skipped': 0, 'errors': [],
        }), 200

    errors = []
    inserted = 0
    updated = 0
    skipped = 0

    # Group records by account_id so we touch each account once
    accounts_map: dict[int, list[dict]] = {}
    for idx, rec in enumerate(records):
        missing = CONTACT_REQUIRED_FIELDS - set(rec.keys())
        if missing:
            errors.append({
                'index': idx,
                'error': f'Missing required fields: {", ".join(sorted(missing))}',
                'record': rec,
            })
            continue

        acct_id = int(rec['account_id'])
        accounts_map.setdefault(acct_id, []).append(rec)

    for acct_id, contact_records in accounts_map.items():
        try:
            account = Account.query.filter_by(
                account_id=acct_id,
                customer_id=customer_id,
            ).first()

            if not account:
                for rec in contact_records:
                    skipped += 1
                    errors.append({
                        'index': records.index(rec),
                        'error': f'Account {acct_id} not found for customer {customer_id}',
                        'record': rec,
                    })
                continue

            # Load existing champions list from profile_metadata
            meta = account.profile_metadata or {}
            champions: list[dict] = meta.get('champions', [])

            # Build a lookup index: email (lowercase) -> position, name (lower) -> position
            email_idx = {}
            name_idx = {}
            for pos, champ in enumerate(champions):
                if champ.get('email'):
                    email_idx[champ['email'].lower()] = pos
                if champ.get('name'):
                    name_idx[champ['name'].lower()] = pos

            for rec in contact_records:
                champion = {
                    'name': rec['champion_name'],
                    'role': rec.get('champion_role', ''),
                    'email': rec.get('champion_email', ''),
                    'sentiment': rec.get('champion_sentiment', 'neutral'),
                    'source': source,
                    'updated_at': datetime.utcnow().isoformat(),
                }

                # Determine if this is an update or insert
                match_pos = None
                email_lower = (rec.get('champion_email') or '').lower()
                name_lower = rec['champion_name'].lower()

                if email_lower and email_lower in email_idx:
                    match_pos = email_idx[email_lower]
                elif name_lower in name_idx:
                    match_pos = name_idx[name_lower]

                if match_pos is not None:
                    champions[match_pos] = champion
                    updated += 1
                else:
                    champions.append(champion)
                    # Update indexes
                    new_pos = len(champions) - 1
                    if email_lower:
                        email_idx[email_lower] = new_pos
                    name_idx[name_lower] = new_pos
                    inserted += 1

            # Write back to profile_metadata
            meta['champions'] = champions
            meta['champions_updated_at'] = datetime.utcnow().isoformat()
            meta['champions_source'] = source
            account.profile_metadata = meta
            # SQLAlchemy may not detect in-place JSON mutation; flag it
            db.session.bulk_save_objects([])  # no-op, but next line is the real flag
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(account, 'profile_metadata')

        except Exception as exc:
            logger.exception("Contact ingestion failed for account %s: %s", acct_id, exc)
            for rec in contact_records:
                errors.append({
                    'index': records.index(rec),
                    'error': f'Database error for account {acct_id}: {exc}',
                    'record': rec,
                })

    # Single commit for all account updates
    try:
        db.session.commit()
        logger.info(
            "Contact ingestion complete: source=%s customer=%s inserted=%d updated=%d skipped=%d errors=%d",
            source, customer_id, inserted, updated, skipped, len(errors),
        )
    except Exception as exc:
        db.session.rollback()
        logger.exception("Contact ingestion commit failed: %s", exc)
        return jsonify({
            'error': f'Database error: {exc}',
            'source': source,
            'inserted': 0, 'updated': 0,
            'skipped': 0, 'errors': errors,
        }), 500

    # Publish event for downstream processing
    if inserted or updated:
        account_ids = list(accounts_map.keys())
        _try_publish_event('ACCOUNT_DATA_CHANGED', customer_id, {
            'source': source,
            'reason': 'contacts_ingested',
            'account_ids': account_ids,
            'inserted': inserted,
            'updated': updated,
        })

    return jsonify({
        'status': 'ok',
        'source': source,
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped,
        'errors': errors,
    }), 200


# ===========================================================================
#  Helpers
# ===========================================================================

def _parse_datetime(value) -> datetime:
    """Parse a date or datetime string into a ``datetime`` object."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    s = str(value).strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f'Cannot parse datetime from "{s}"')


def _parse_date(value) -> date:
    """Parse a date string into a ``date`` object."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    for fmt in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'Cannot parse date from "{s}"')
