"""Top-level orchestrator for --profile eval (fix-load-generator-prompt-v2.md).

generate_eval_tenant(world_id, seed, knobs, out_dir, customer_name) writes:
  account_details.csv, kpi_measurements.csv, qualitative_signals.csv,
  outcomes.csv    — same shapes process_data() already ingests
  ground_truth.json, run_manifest.json  — eval-profile-only outputs

GENERATOR_VERSION bumps whenever event_engine/ground_truth/csv_emitter change
the actual output for a fixed (world_id, seed, knobs) — run_manifest.json
records it so a stale golden/ground_truth mismatch is diagnosable.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import world_schema
import event_engine
import ground_truth as gt_module
import csv_emitter

GENERATOR_VERSION = '2026.08.25-1'

DEFAULT_KNOBS = {
    'observation_rate': event_engine.DEFAULT_OBSERVATION_RATE,
    'per_type_observation_rate': dict(event_engine.DEFAULT_PER_TYPE_OBSERVATION_RATE),
    'account_count': 12,
}


def generate_eval_tenant(world_id: str, seed: int, out_dir: str,
                          knobs: dict | None = None,
                          customer_name: str = 'Eval Profile Tenant',
                          start_date: datetime | None = None) -> dict:
    """Returns the assembled ground_truth dict (also written to disk)."""
    world = world_schema.load_world(world_id)
    knobs = {**DEFAULT_KNOBS, **(knobs or {})}
    start_date = start_date or datetime(2025, 1, 1)

    accounts = event_engine.generate_accounts(
        world, seed, knobs['account_count'], start_date,
    )
    event_engine.apply_dropout(
        accounts, seed, knobs['observation_rate'], knobs['per_type_observation_rate'],
    )
    event_engine.apply_lag_window(accounts, world)

    dollars_by_account_by_event = csv_emitter.assign_outcome_dollars(world, accounts, seed)
    dollars_by_account_total = {
        idx: sum(abs(v) for v in evs.values())
        for idx, evs in dollars_by_account_by_event.items()
    }

    gt = gt_module.build_ground_truth(world, accounts, seed, knobs, dollars_by_account_total)
    run_manifest = gt_module.build_run_manifest(world_id, seed, knobs, GENERATOR_VERSION)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    (out_path / 'account_details.csv').write_text(
        csv_emitter.emit_account_details_csv(world, accounts, customer_name))
    (out_path / 'kpi_measurements.csv').write_text(
        csv_emitter.emit_kpi_measurements_csv(accounts))
    (out_path / 'qualitative_signals.csv').write_text(
        csv_emitter.emit_qualitative_signals_csv(world, accounts))
    (out_path / 'outcomes.csv').write_text(
        csv_emitter.emit_outcomes_csv(world, accounts, dollars_by_account_by_event))

    with open(out_path / 'ground_truth.json', 'w') as f:
        json.dump(gt, f, indent=2, default=str)
    with open(out_path / 'run_manifest.json', 'w') as f:
        json.dump(run_manifest, f, indent=2)

    return gt


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate an eval-profile tenant')
    parser.add_argument('--world-id', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--account-count', type=int, default=DEFAULT_KNOBS['account_count'])
    parser.add_argument('--observation-rate', type=float, default=DEFAULT_KNOBS['observation_rate'])
    args = parser.parse_args()

    result = generate_eval_tenant(
        args.world_id, args.seed, args.out,
        knobs={'account_count': args.account_count, 'observation_rate': args.observation_rate},
    )
    print(f"Generated {args.world_id} (seed={args.seed}) -> {args.out}")
    print(f"  accounts: {result['accounts']['count']}, with_no_arc: {len(result['accounts']['with_no_arc'])}")
    print(f"  revenue_model: {result['revenue_model']}")
