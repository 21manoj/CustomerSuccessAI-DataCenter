"""
Taxonomy loader — base + per-vertical overlay, additive merge, validated at
load time AND at boot. Modeled exactly on the Build Prompt's pseudocode
(Module 04 spec, "Taxonomy loader" section).

Taxonomy file shape (Data Shapes section):
{
  "version": "...",
  "polarity_ambiguous_outcome_subtypes": [...],
  "polarity_ambiguous_signal_subtypes": [...],
  "revenue_buckets": {bucket_name: [subtype, ...]},
  "auto_recovery_outcome_subtypes": [...]
}

An overlay additionally requires:
{
  "extends": "base",
  "vertical": "<vertical_name>",
  ... same optional keys as base, ADDITIVE only ...
}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

SUBTYPE_RE = re.compile(r"^[a-z_]+$")

REQUIRED_LIST_KEYS = (
    "polarity_ambiguous_outcome_subtypes",
    "polarity_ambiguous_signal_subtypes",
    "auto_recovery_outcome_subtypes",
)


class TaxonomyValidationError(ValueError):
    """Raised when a taxonomy file (base or overlay) fails structural or
    cross-file (overlay-vs-base) validation."""


@dataclass
class Taxonomy:
    version: str
    polarity_ambiguous_outcome_subtypes: set
    polarity_ambiguous_signal_subtypes: set
    revenue_buckets: dict  # bucket_name -> set(subtype)
    auto_recovery_outcome_subtypes: set
    vertical: Optional[str] = None
    sources: list = field(default_factory=list)  # filenames merged, for logging

    def bucket_for(self, subtype: str) -> Optional[str]:
        for bucket, subtypes in self.revenue_buckets.items():
            if subtype in subtypes:
                return bucket
        return None

    def is_outcome_polarity_ambiguous(self, subtype: str) -> bool:
        return subtype in self.polarity_ambiguous_outcome_subtypes

    def is_signal_polarity_ambiguous(self, subtype: str) -> bool:
        return subtype in self.polarity_ambiguous_signal_subtypes


class TaxonomyLoader:
    """Instantiate one per config directory. Caches per-vertical results."""

    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self._cache: dict = {}

    # -- IO helpers -------------------------------------------------------

    def _read_json(self, filename: str) -> dict:
        path = self.config_dir / filename
        with open(path, "r") as f:
            return json.load(f)

    def _exists(self, filename: str) -> bool:
        return (self.config_dir / filename).exists()

    # -- structural validation --------------------------------------------

    def _validate_structure(self, data: dict, filename: str, is_overlay: bool = False) -> None:
        if not isinstance(data, dict):
            raise TaxonomyValidationError(f"{filename}: taxonomy file must be a JSON object")

        if "version" not in data:
            raise TaxonomyValidationError(f"{filename}: missing required key 'version'")

        if is_overlay:
            if data.get("extends") != "base":
                raise TaxonomyValidationError(
                    f"{filename}: overlay must declare \"extends\": \"base\""
                )
            if not data.get("vertical"):
                raise TaxonomyValidationError(
                    f"{filename}: overlay must declare its own 'vertical'"
                )

        for key in REQUIRED_LIST_KEYS:
            if key not in data:
                continue  # optional per-file, additive
            values = data[key]
            if not isinstance(values, list):
                raise TaxonomyValidationError(f"{filename}: '{key}' must be a list")
            self._validate_no_dups_and_pattern(values, key, filename)

        if "revenue_buckets" in data:
            buckets = data["revenue_buckets"]
            if not isinstance(buckets, dict):
                raise TaxonomyValidationError(f"{filename}: 'revenue_buckets' must be an object")
            seen_subtypes: dict = {}
            for bucket_name, subtypes in buckets.items():
                if not isinstance(subtypes, list):
                    raise TaxonomyValidationError(
                        f"{filename}: revenue_buckets.{bucket_name} must be a list"
                    )
                self._validate_no_dups_and_pattern(
                    subtypes, f"revenue_buckets.{bucket_name}", filename
                )
                for st in subtypes:
                    if st in seen_subtypes:
                        raise TaxonomyValidationError(
                            f"{filename}: subtype '{st}' appears in both bucket "
                            f"'{seen_subtypes[st]}' and bucket '{bucket_name}' "
                            f"within the same file — a subtype can only belong "
                            f"to one revenue bucket"
                        )
                    seen_subtypes[st] = bucket_name

    def _validate_no_dups_and_pattern(self, values: list, key: str, filename: str) -> None:
        seen = set()
        for v in values:
            if not isinstance(v, str) or not SUBTYPE_RE.match(v):
                raise TaxonomyValidationError(
                    f"{filename}: '{key}' contains an invalid subtype name "
                    f"{v!r} (must match ^[a-z_]+$)"
                )
            if v in seen:
                raise TaxonomyValidationError(
                    f"{filename}: '{key}' contains duplicate entry {v!r}"
                )
            seen.add(v)

    # -- public loaders, matching Build Prompt signatures exactly ---------

    def load_base(self) -> dict:
        data = self._read_json("taxonomy_base.json")
        self._validate_structure(data, "taxonomy_base.json", is_overlay=False)
        return data

    def load_overlay(self, vertical: str) -> Optional[dict]:
        filename = f"taxonomy_{vertical}.json"
        if not self._exists(filename):
            return None
        data = self._read_json(filename)
        self._validate_structure(data, filename, is_overlay=True)
        return data

    def _validate_overlay_vs_base(self, overlay: dict, base: dict, filename: str) -> None:
        """Overlay may ADD subtypes/buckets. It may NEVER:
        (a) move a subtype base already placed in bucket X into a different
            bucket Y (bucket-reassignment contradiction), or
        (b) mark a subtype 'polarity-ambiguous' that base already gave a
            definitive revenue bucket to (ambiguous-vs-definitive
            contradiction) — the same class of contradiction as (a), not a
            separate rule.
        Both raise TaxonomyValidationError.
        """
        base_buckets = base.get("revenue_buckets", {})
        base_subtype_to_bucket = {}
        for bucket_name, subtypes in base_buckets.items():
            for st in subtypes:
                base_subtype_to_bucket[st] = bucket_name

        # (a) bucket reassignment
        overlay_buckets = overlay.get("revenue_buckets", {})
        for bucket_name, subtypes in overlay_buckets.items():
            for st in subtypes:
                if st in base_subtype_to_bucket and base_subtype_to_bucket[st] != bucket_name:
                    raise TaxonomyValidationError(
                        f"{filename}: overlay attempts to move subtype "
                        f"'{st}' from base bucket "
                        f"'{base_subtype_to_bucket[st]}' into '{bucket_name}' "
                        f"— overlays may only ADD, never reassign, a "
                        f"base-defined subtype's revenue bucket"
                    )

        # (b) ambiguous-vs-definitive contradiction
        for key, base_bucket_lookup in (
            ("polarity_ambiguous_outcome_subtypes", base_subtype_to_bucket),
            ("polarity_ambiguous_signal_subtypes", base_subtype_to_bucket),
        ):
            for st in overlay.get(key, []):
                if st in base_bucket_lookup:
                    raise TaxonomyValidationError(
                        f"{filename}: overlay marks '{st}' as polarity-"
                        f"ambiguous ({key}), but base already gave it a "
                        f"definitive revenue bucket "
                        f"('{base_bucket_lookup[st]}') — these are "
                        f"contradictory, not additive"
                    )

    @staticmethod
    def _merge(base: dict, overlay: Optional[dict]) -> Taxonomy:
        def merged_set(key: str) -> set:
            s = set(base.get(key, []))
            if overlay:
                s |= set(overlay.get(key, []))
            return s

        merged_buckets: dict = {}
        for bucket_name, subtypes in base.get("revenue_buckets", {}).items():
            merged_buckets[bucket_name] = set(subtypes)
        if overlay:
            for bucket_name, subtypes in overlay.get("revenue_buckets", {}).items():
                merged_buckets.setdefault(bucket_name, set())
                merged_buckets[bucket_name] |= set(subtypes)

        sources = ["taxonomy_base.json"]
        vertical = None
        if overlay:
            vertical = overlay.get("vertical")
            sources.append(f"taxonomy_{vertical}.json")

        return Taxonomy(
            version=base.get("version"),
            polarity_ambiguous_outcome_subtypes=merged_set("polarity_ambiguous_outcome_subtypes"),
            polarity_ambiguous_signal_subtypes=merged_set("polarity_ambiguous_signal_subtypes"),
            revenue_buckets=merged_buckets,
            auto_recovery_outcome_subtypes=merged_set("auto_recovery_outcome_subtypes"),
            vertical=vertical,
            sources=sources,
        )

    def get_taxonomy(self, vertical: Optional[str] = None) -> Taxonomy:
        cache_key = vertical or "__base_only__"
        if cache_key in self._cache:
            return self._cache[cache_key]

        base = self.load_base()
        overlay = self.load_overlay(vertical) if vertical else None
        if overlay:
            self._validate_overlay_vs_base(overlay, base, f"taxonomy_{vertical}.json")

        taxonomy = self._merge(base, overlay)
        self._cache[cache_key] = taxonomy
        return taxonomy

    def validate_all_at_boot(self) -> list[str]:
        """Load base + EVERY overlay file found on disk, validating each.
        Call unconditionally from application startup; let it raise on any
        invalid file — including an overlay for a vertical no current
        customer uses yet. Returns the list of verified filenames."""
        verified = []

        # base must exist and validate
        self.load_base()
        verified.append("taxonomy_base.json")
        base = self._read_json("taxonomy_base.json")

        for path in sorted(self.config_dir.glob("taxonomy_*.json")):
            if path.name == "taxonomy_base.json":
                continue
            vertical = path.name[len("taxonomy_"):-len(".json")]
            data = self._read_json(path.name)
            self._validate_structure(data, path.name, is_overlay=True)
            self._validate_overlay_vs_base(data, base, path.name)
            verified.append(path.name)

        return verified
