"""World file loading + structural validation.

Worlds are data, not code (see fix-load-generator-prompt-v2.md's "World
definitions" section) — this module's only job is to load a world JSON file
and confirm it's internally consistent before the event engine trusts it:
every edge references declared vocabulary or a declared latent, every
archetype references real edge_ids, every absence pair references declared
vocabulary. It does NOT import utils.arc_edge_generator or reference
ARC_TEMPLATES — see tests/test_independence_guard.py (AT-5).
"""
from __future__ import annotations

import json
from pathlib import Path

ABSENCE_KINDS = {
    'no_relationship',
    'unobserved_intermediate',
    'latent_common_cause',
    'beyond_lag_window',
}

WORLDS_ROOT = Path(__file__).resolve().parent / 'worlds'


class WorldValidationError(ValueError):
    pass


def load_world(world_id: str) -> dict:
    """Load a world by its internal `world_id` field, searching every
    worlds/<vertical>/*.json file (world_id is unique platform-wide; the
    filename itself is just world_a.json/world_b.json per vertical dir, not
    the lookup key)."""
    for f in WORLDS_ROOT.glob('*/*.json'):
        with open(f) as fh:
            world = json.load(fh)
        if world.get('world_id') == world_id:
            validate_world(world)
            return world
    raise WorldValidationError(f"no world file found for world_id={world_id!r} under {WORLDS_ROOT}")


def load_world_from_path(path: Path) -> dict:
    with open(path) as fh:
        world = json.load(fh)
    validate_world(world)
    return world


def list_worlds(vertical: str | None = None) -> list[str]:
    pattern = f'{vertical}/*.json' if vertical else '*/*.json'
    ids = []
    for f in WORLDS_ROOT.glob(pattern):
        with open(f) as fh:
            ids.append(json.load(fh).get('world_id', f.stem))
    return sorted(ids)


def validate_world(world: dict) -> None:
    """Raise WorldValidationError on any structural inconsistency. Called at
    load time so a broken world fails fast, not partway through generation."""
    required = ('world_id', 'vertical', 'observed_vocabulary', 'dag',
                'absences', 'account_archetypes', 'revenue_model')
    missing = [k for k in required if k not in world]
    if missing:
        raise WorldValidationError(f"world missing required keys: {missing}")

    outcome_types = world['observed_vocabulary'].get('outcome_types', [])
    outcome_type_names = set(outcome_types.keys()) if isinstance(outcome_types, dict) else set(outcome_types)
    if isinstance(outcome_types, dict):
        bad_polarity = {v for v in outcome_types.values()} - {'at_risk', 'lost', 'expansion', 'protected'}
        if bad_polarity:
            raise WorldValidationError(f"outcome_types has unknown polarity values: {bad_polarity}")
    vocab = set(world['observed_vocabulary'].get('signal_types', [])) | outcome_type_names
    latents = set(world.get('latents', []))

    edge_ids = set()
    for edge in world['dag']:
        for req in ('edge_id', 'from', 'to', 'lag_days_mean', 'lag_days_std', 'strength'):
            if req not in edge:
                raise WorldValidationError(f"dag edge missing {req!r}: {edge}")
        if edge['edge_id'] in edge_ids:
            raise WorldValidationError(f"duplicate edge_id: {edge['edge_id']}")
        edge_ids.add(edge['edge_id'])
        for endpoint_key in ('from', 'to'):
            endpoint = edge[endpoint_key]
            if endpoint not in vocab and endpoint not in latents:
                raise WorldValidationError(
                    f"edge {edge['edge_id']} references {endpoint_key}={endpoint!r} "
                    f"which is in neither observed_vocabulary nor latents"
                )
        if not (0.0 <= edge['strength'] <= 1.0):
            raise WorldValidationError(f"edge {edge['edge_id']} strength out of [0,1]: {edge['strength']}")

    for absence in world['absences']:
        if 'pair' not in absence or 'kind' not in absence:
            raise WorldValidationError(f"absence missing pair/kind: {absence}")
        if absence['kind'] not in ABSENCE_KINDS:
            raise WorldValidationError(f"absence kind {absence['kind']!r} not in {ABSENCE_KINDS}")
        for member in absence['pair']:
            if member not in vocab:
                raise WorldValidationError(
                    f"absence pair member {member!r} not in observed_vocabulary: {absence}"
                )
        if absence['kind'] == 'unobserved_intermediate' and 'hidden_event' not in absence:
            raise WorldValidationError(f"unobserved_intermediate absence missing hidden_event: {absence}")
        if absence['kind'] == 'latent_common_cause' and 'via' not in absence:
            raise WorldValidationError(f"latent_common_cause absence missing 'via': {absence}")
        if absence['kind'] == 'beyond_lag_window' and 'true_lag_days' not in absence:
            raise WorldValidationError(f"beyond_lag_window absence missing true_lag_days: {absence}")

    present_kinds = {a['kind'] for a in world['absences']}
    missing_kinds = ABSENCE_KINDS - present_kinds
    if missing_kinds:
        raise WorldValidationError(
            f"world {world['world_id']} is missing absence kinds {missing_kinds} — "
            f"every world must contain at least one of each (fix-load-generator-prompt-v2.md §4)"
        )

    for arche in world['account_archetypes']:
        for req in ('archetype_id', 'active_edges', 'arr_range', 'weight'):
            if req not in arche:
                raise WorldValidationError(f"account_archetype missing {req!r}: {arche}")
        for eid in arche['active_edges']:
            if eid not in edge_ids:
                raise WorldValidationError(
                    f"archetype {arche['archetype_id']} references unknown edge_id {eid!r}"
                )

    if 'per_account_bound' not in world['revenue_model']:
        raise WorldValidationError("revenue_model missing per_account_bound")
