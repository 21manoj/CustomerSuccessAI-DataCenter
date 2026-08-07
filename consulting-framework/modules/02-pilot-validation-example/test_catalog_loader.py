"""
Test suite for the Module 02 pilot implementation (catalog_loader.py),
exercising every Acceptance Criteria bullet and Reference Test Harness item
from consulting-framework/modules/02-foundation-vertical-taxonomy.md as
literally as possible.

Run with: python3 -m pytest test_catalog_loader.py -v
(from this directory, or with this directory added to PYTHONPATH).
"""

import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import catalog_loader as cl  # noqa: E402

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
SAMPLE_CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_catalog.json")
SAMPLE_TIERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_tiers.json")


@pytest.fixture(autouse=True)
def _reset_cache():
    """Every AC around caching only means something if each test starts
    from a clean slate."""
    cl.clear_cache()
    yield
    cl.clear_cache()


def _copy_fixture(src_name, dest_dir, dest_name=None):
    with open(os.path.join(FIXTURES_DIR, src_name)) as f:
        content = f.read()
    dest_name = dest_name or src_name
    dest_path = os.path.join(dest_dir, dest_name)
    with open(dest_path, "w") as f:
        f.write(content)
    return dest_path


# ---------------------------------------------------------------------------
# 1. Validation-rejection tests -- one per validation rule in the Build
#    Prompt (Reference Test Harness item 1).
# ---------------------------------------------------------------------------

class TestValidationRejection:
    def test_bad_pillar_weight_l2_sum_rejected(self, tmp_path):
        """AC: 'A catalog file whose weight_l2 values sum to 0.97 (not 1.0)
        fails to load, with an error identifying which check failed and by
        how much.'"""
        _copy_fixture("bad_l2_sum_v1_kpi_catalog.json", tmp_path)
        with pytest.raises(cl.CatalogValidationError) as exc_info:
            cl.load_catalog("bad_l2_sum_v1", config_dir=str(tmp_path))
        message = str(exc_info.value)
        assert "weight_l2" in message
        assert "0.97" in message
        assert "1.0" in message

    def test_bad_pillar_weight_l1_sum_rejected(self, tmp_path):
        """Fourth validation rule: within a pillar, weight_l1 values must
        sum to 1.0 (+/- 0.001) among that pillar's own KPIs."""
        _copy_fixture("bad_l1_sum_v1_kpi_catalog.json", tmp_path)
        with pytest.raises(cl.CatalogValidationError) as exc_info:
            cl.load_catalog("bad_l1_sum_v1", config_dir=str(tmp_path))
        message = str(exc_info.value)
        assert "weight_l1" in message
        assert "P1" in message

    def test_dangling_pillar_reference_rejected(self, tmp_path):
        """AC: 'A catalog file where a KPI's pillar field references a
        pillar not present in that file's pillars dict fails to load,
        rather than that KPI silently never contributing to any pillar
        score.'"""
        _copy_fixture("dangling_pillar_v1_kpi_catalog.json", tmp_path)
        with pytest.raises(cl.CatalogValidationError) as exc_info:
            cl.load_catalog("dangling_pillar_v1", config_dir=str(tmp_path))
        message = str(exc_info.value)
        assert "P9" in message
        assert "P2-KPI1" in message

    def test_tier_referencing_unknown_kpi_rejected(self, tmp_path):
        """AC: 'A tier definition listing a KPI code absent from the base
        catalog fails to load -- a tier can never introduce KPI knowledge
        the base catalog doesn't already have.'

        Tier validation is wired into load_catalog itself (per the Build
        Prompt), so this must fail on load_catalog, not only on a later
        get_kpis_for_tier call.
        """
        _copy_fixture("bad_tier_ref_v1_kpi_catalog.json", tmp_path)
        _copy_fixture("bad_tier_ref_v1_kpi_tiers.json", tmp_path)
        with pytest.raises(cl.CatalogValidationError) as exc_info:
            cl.load_catalog("bad_tier_ref_v1", config_dir=str(tmp_path))
        message = str(exc_info.value)
        assert "P9-KPI7" in message
        assert "starter" in message

    def test_broken_catalog_never_returns_usable_result(self, tmp_path):
        """A catalog failing validation must raise, never return a
        partially-valid (pillars, kpis) tuple that could be used downstream
        to silently produce wrong scores."""
        _copy_fixture("bad_l2_sum_v1_kpi_catalog.json", tmp_path)
        try:
            result = cl.load_catalog("bad_l2_sum_v1", config_dir=str(tmp_path))
            pytest.fail(f"expected CatalogValidationError, got a result instead: {result!r}")
        except cl.CatalogValidationError:
            pass
        # And the failed load must not have poisoned the cache with a
        # partial/broken entry.
        key = cl._cache_key("bad_l2_sum_v1", str(tmp_path), cl.DEFAULT_LEGACY_MODULE_PREFIX)
        assert key not in cl._catalog_cache

    def test_bad_weight_sum_via_legacy_tier2_module_also_rejected(self):
        """Validation must run 'regardless of how the catalog file was
        authored' (Gotcha 1) -- including the Tier 2 legacy-module path,
        not just Tier 1 JSON files. Uses the legacy_verticals/legacy_broken_v1
        fixture, which has weight_l2 summing to 0.9."""
        with pytest.raises(cl.CatalogValidationError) as exc_info:
            cl.load_catalog(
                "legacy_broken_v1",
                config_dir=str(FIXTURES_DIR),  # no JSON file here -> forces Tier 2
                legacy_module_prefix="legacy_verticals",
            )
        assert "weight_l2" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Round-trip test (Reference Test Harness item 2)
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_valid_catalog_round_trips_intact(self, tmp_path):
        """Write a valid catalog file to a temp location, load it, assert
        every field survives intact (weights, ranges, direction flags) --
        catches silent coercion bugs (e.g. a weight read as a string
        instead of a float)."""
        # copy the real sample catalog (not a fixtures/ broken one)
        with open(SAMPLE_CATALOG_PATH) as f:
            original = json.load(f)
        dest_path = tmp_path / "boutique_hotel_v1_kpi_catalog.json"
        dest_path.write_text(json.dumps(original))

        pillars, kpis = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))

        assert pillars == original["pillars"]
        assert kpis == original["kpis"]

        # Explicitly check types survived as numbers, not strings -- a
        # naive `str(weight) == "1.0"`-style check could pass with a
        # coerced string in some languages but this is Python, so assert
        # the type directly.
        p1_kpi1_weight = kpis["P1-KPI1"]["weight_l1"]
        assert isinstance(p1_kpi1_weight, (int, float))
        assert not isinstance(p1_kpi1_weight, bool)
        assert isinstance(kpis["P1-KPI1"]["higher_is_better"], bool)
        assert kpis["P1-KPI3"]["higher_is_better"] is False
        assert pillars["P1"]["weight_l2"] == pytest.approx(0.35)
        assert kpis["P1-KPI1"]["ranges"]["healthy"] == {"min": 85, "max": 100}


# ---------------------------------------------------------------------------
# 3. Auto-discovery test (Reference Test Harness item 3)
# ---------------------------------------------------------------------------

class TestAutoDiscovery:
    def test_new_vertical_discovered_without_prior_registration(self, tmp_path):
        """Write a new catalog file for an invented vertical name the test
        process has never seen before, and assert it appears in the
        discovered-verticals set without any prior registration."""
        brand_new_vertical = f"invented_{uuid.uuid4().hex[:12]}_v1"
        assert brand_new_vertical not in cl.discover_verticals(config_dir=str(tmp_path))

        catalog = {
            "vertical": brand_new_vertical,
            "version": "1.0",
            "pillars": {"P1": {"name": "Only Pillar", "weight_l2": 1.0}},
            "kpis": {
                "P1-KPI1": {
                    "name": "Only KPI",
                    "pillar": "P1",
                    "weight_l1": 1.0,
                    "higher_is_better": True,
                    "ranges": {
                        "healthy": {"min": 1, "max": 10},
                        "risk": {"min": 0.5, "max": 0.99},
                        "critical": {"min": 0, "max": 0.49},
                    },
                }
            },
        }
        catalog_path = tmp_path / f"{brand_new_vertical}_kpi_catalog.json"
        catalog_path.write_text(json.dumps(catalog))

        discovered = cl.discover_verticals(config_dir=str(tmp_path))
        assert brand_new_vertical in discovered

    def test_dropping_new_valid_catalog_makes_load_catalog_succeed_zero_code_refs(self, tmp_path):
        """AC: 'Dropping a new, valid {new_vertical}_kpi_catalog.json file
        into the config directory (no code changes, no restart of any
        registration list) makes load_catalog("{new_vertical}") succeed and
        that vertical appear in the auto-discovered set -- the module's own
        code contains zero references to the new vertical's name.'

        The vertical name is generated at test run time (uuid4-derived), so
        by construction catalog_loader.py's source -- written and frozen
        before this test ever ran -- cannot contain it. We also assert that
        directly by grepping the source, as the most literal possible check
        of that specific clause.
        """
        brand_new_vertical = f"zzinvented_{uuid.uuid4().hex[:12]}_v1"

        with open(cl.__file__) as f:
            loader_source = f.read()
        assert brand_new_vertical not in loader_source

        catalog = {
            "vertical": brand_new_vertical,
            "version": "1.0",
            "pillars": {
                "P1": {"name": "Alpha", "weight_l2": 0.4},
                "P2": {"name": "Beta", "weight_l2": 0.6},
            },
            "kpis": {
                "P1-KPI1": {
                    "name": "Alpha KPI",
                    "pillar": "P1",
                    "weight_l1": 1.0,
                    "higher_is_better": True,
                    "ranges": {
                        "healthy": {"min": 1, "max": 10},
                        "risk": {"min": 0.5, "max": 0.99},
                        "critical": {"min": 0, "max": 0.49},
                    },
                },
                "P2-KPI1": {
                    "name": "Beta KPI",
                    "pillar": "P2",
                    "weight_l1": 1.0,
                    "higher_is_better": False,
                    "ranges": {
                        "healthy": {"min": 0, "max": 5},
                        "risk": {"min": 5.01, "max": 10},
                        "critical": {"min": 10.01, "max": 100},
                    },
                },
            },
        }
        catalog_path = tmp_path / f"{brand_new_vertical}_kpi_catalog.json"
        catalog_path.write_text(json.dumps(catalog))

        # No code change, no registration call -- just load it.
        pillars, kpis = cl.load_catalog(brand_new_vertical, config_dir=str(tmp_path))
        assert set(pillars.keys()) == {"P1", "P2"}
        assert set(kpis.keys()) == {"P1-KPI1", "P2-KPI1"}
        assert brand_new_vertical in cl.discover_verticals(config_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# 4. Tier resolution
# ---------------------------------------------------------------------------

class TestTierResolution:
    def _seed_valid_catalog_and_tiers(self, tmp_path):
        with open(SAMPLE_CATALOG_PATH) as f:
            catalog = json.load(f)
        with open(SAMPLE_TIERS_PATH) as f:
            tiers = json.load(f)
        (tmp_path / "boutique_hotel_v1_kpi_catalog.json").write_text(json.dumps(catalog))
        (tmp_path / "boutique_hotel_v1_kpi_tiers.json").write_text(json.dumps(tiers))
        return catalog, tiers

    def test_starter_tier_is_strict_subset_and_byte_identical(self, tmp_path):
        """AC: get_kpis_for_tier(vertical, "starter") returns a strict
        subset of load_catalog(vertical)'s KPIs, and every returned KPI's
        definition is byte-for-byte identical to its definition in the full
        catalog -- a tier never redefines a KPI, only selects which ones
        are active."""
        self._seed_valid_catalog_and_tiers(tmp_path)
        pillars, full_kpis = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))
        starter_kpis = cl.get_kpis_for_tier(
            "boutique_hotel_v1", "starter", config_dir=str(tmp_path)
        )

        assert set(starter_kpis.keys()) < set(full_kpis.keys())  # strict subset
        assert len(starter_kpis) > 0
        for code, kpi_def in starter_kpis.items():
            assert kpi_def == full_kpis[code]

    def test_default_tier_used_when_tier_name_omitted(self, tmp_path):
        self._seed_valid_catalog_and_tiers(tmp_path)
        default = cl.get_kpis_for_tier("boutique_hotel_v1", config_dir=str(tmp_path))
        starter = cl.get_kpis_for_tier(
            "boutique_hotel_v1", "starter", config_dir=str(tmp_path)
        )
        assert default == starter  # sample_tiers.json's default_tier is "starter"

    def test_full_tier_equals_entire_catalog(self, tmp_path):
        self._seed_valid_catalog_and_tiers(tmp_path)
        _, full_kpis = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))
        full_tier_kpis = cl.get_kpis_for_tier(
            "boutique_hotel_v1", "full", config_dir=str(tmp_path)
        )
        assert full_tier_kpis == full_kpis

    def test_unknown_tier_name_raises(self, tmp_path):
        self._seed_valid_catalog_and_tiers(tmp_path)
        cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))
        with pytest.raises(cl.CatalogValidationError):
            cl.get_kpis_for_tier(
                "boutique_hotel_v1", "nonexistent_tier", config_dir=str(tmp_path)
            )


# ---------------------------------------------------------------------------
# 5. Caching
# ---------------------------------------------------------------------------

class TestCaching:
    def test_second_load_does_not_re_read_file_from_disk(self, tmp_path):
        """AC: 'Calling the loader for the SAME valid catalog twice returns
        equal results without re-reading the file from disk the second
        time (validated catalogs are cached).'

        Proven by deleting the file from disk after the first load and
        confirming the second load still succeeds and returns an equal
        result -- if the loader were re-reading, this would raise
        FileNotFoundError.
        """
        with open(SAMPLE_CATALOG_PATH) as f:
            original = json.load(f)
        catalog_path = tmp_path / "boutique_hotel_v1_kpi_catalog.json"
        catalog_path.write_text(json.dumps(original))

        first = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))

        os.remove(catalog_path)  # prove the second call can't be re-reading this

        second = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))
        assert first == second
        assert first[0] is second[0]  # same cached dict object, not just equal

    def test_cache_is_per_vertical_not_global(self, tmp_path):
        """A second, different vertical dropped into the same config_dir
        must load correctly and independently -- the cache must be keyed
        per vertical, not a single-slot cache that the second load
        overwrites."""
        with open(SAMPLE_CATALOG_PATH) as f:
            catalog_a = json.load(f)
        (tmp_path / "boutique_hotel_v1_kpi_catalog.json").write_text(json.dumps(catalog_a))

        catalog_b = {
            "vertical": "second_vertical_v1",
            "version": "1.0",
            "pillars": {"P1": {"name": "Solo", "weight_l2": 1.0}},
            "kpis": {
                "P1-KPI1": {
                    "name": "Solo KPI",
                    "pillar": "P1",
                    "weight_l1": 1.0,
                    "higher_is_better": True,
                    "ranges": {
                        "healthy": {"min": 1, "max": 10},
                        "risk": {"min": 0.5, "max": 0.99},
                        "critical": {"min": 0, "max": 0.49},
                    },
                }
            },
        }
        (tmp_path / "second_vertical_v1_kpi_catalog.json").write_text(json.dumps(catalog_b))

        pillars_a, kpis_a = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))
        pillars_b, kpis_b = cl.load_catalog("second_vertical_v1", config_dir=str(tmp_path))

        assert set(pillars_a.keys()) == {"P1", "P2", "P3", "P4"}
        assert set(pillars_b.keys()) == {"P1"}
        assert set(kpis_b.keys()) == {"P1-KPI1"}


# ---------------------------------------------------------------------------
# 6. 3-tier resolution order (Build Prompt step 1)
# ---------------------------------------------------------------------------

class TestThreeTierResolution:
    def test_tier1_json_file_used_when_present(self, tmp_path):
        with open(SAMPLE_CATALOG_PATH) as f:
            original = json.load(f)
        (tmp_path / "boutique_hotel_v1_kpi_catalog.json").write_text(json.dumps(original))
        pillars, kpis = cl.load_catalog("boutique_hotel_v1", config_dir=str(tmp_path))
        assert set(pillars.keys()) == {"P1", "P2", "P3", "P4"}

    def test_tier2_legacy_module_used_when_no_json_file(self, tmp_path):
        """Tier 2: legacy Python module fallback, only reached when Tier 1
        (JSON file) doesn't resolve. Uses the legacy_verticals/legacy_spa_v1
        fixture module (PILLARS/KPIS dicts), simulating a vertical that
        predates the JSON catalog format."""
        # tmp_path has no *_kpi_catalog.json for "legacy_spa_v1" at all.
        pillars, kpis = cl.load_catalog(
            "legacy_spa_v1",
            config_dir=str(tmp_path),
            legacy_module_prefix="legacy_verticals",
        )
        assert set(pillars.keys()) == {"P1", "P2"}
        assert set(kpis.keys()) == {"P1-KPI1", "P2-KPI1"}

    def test_tier1_preferred_over_tier2_when_both_exist(self, tmp_path):
        """If a JSON file exists for a vertical name that also has a legacy
        module, Tier 1 must win (fixed priority order, JSON before legacy)."""
        json_catalog = {
            "vertical": "legacy_spa_v1",
            "version": "2.0",
            "pillars": {"P9": {"name": "From JSON", "weight_l2": 1.0}},
            "kpis": {
                "P9-KPI1": {
                    "name": "From JSON KPI",
                    "pillar": "P9",
                    "weight_l1": 1.0,
                    "higher_is_better": True,
                    "ranges": {
                        "healthy": {"min": 1, "max": 10},
                        "risk": {"min": 0.5, "max": 0.99},
                        "critical": {"min": 0, "max": 0.49},
                    },
                }
            },
        }
        (tmp_path / "legacy_spa_v1_kpi_catalog.json").write_text(json.dumps(json_catalog))

        pillars, kpis = cl.load_catalog(
            "legacy_spa_v1",
            config_dir=str(tmp_path),
            legacy_module_prefix="legacy_verticals",
        )
        # Tier 1 (JSON) content, not Tier 2 (legacy module: P1/P2) content.
        assert set(pillars.keys()) == {"P9"}

    def test_tier3_unknown_vertical_raises(self, tmp_path):
        """Neither a JSON file nor a legacy module exists for this name --
        must raise UnknownVerticalError (Tier 3)."""
        with pytest.raises(cl.UnknownVerticalError):
            cl.load_catalog(
                "totally_nonexistent_vertical_v1",
                config_dir=str(tmp_path),
                legacy_module_prefix="legacy_verticals",
            )

    def test_tier2_broken_internal_import_fails_loudly_not_as_unknown_vertical(
        self, tmp_path
    ):
        """Gotcha 2 regression test: 'silent import failures degrade a whole
        feature to a warning with no loud failure' -- and 'the two failure
        modes look identical from outside the except block, but one is
        this optional feature is unavailable by design and the other is
        this code is broken and no one noticed.'

        This is Gotcha 2 applied directly to catalog_loader.py's OWN Tier-2
        fallback, not to some other caller module: the Build Prompt's
        pseudocode for Tier 2 is just `if module_exists(...): ...`, and the
        obvious way to implement `module_exists` in Python is a bare
        `try/except ImportError` around the import -- which is exactly the
        anti-pattern Gotcha 2 warns against, just relocated into this
        module's own resolution logic instead of a caller's.

        legacy_verticals/legacy_internally_broken_v1/kpi_definitions.py
        exists (the vertical is real) but itself imports a module that does
        not exist. A naive Tier-2 implementation would catch that
        ImportError, conclude "no legacy module for this vertical", and
        raise the misleading UnknownVerticalError (Tier 3) -- silently
        misreporting a real code bug as a missing-config problem, the exact
        failure shape Gotcha 2 describes. This must instead propagate the
        real import error loudly.
        """
        with pytest.raises((ImportError, ModuleNotFoundError)) as exc_info:
            cl.load_catalog(
                "legacy_internally_broken_v1",
                config_dir=str(tmp_path),  # no JSON file -> forces Tier 2
                legacy_module_prefix="legacy_verticals",
            )
        # Must NOT be reported as "Unknown vertical" -- that would be the
        # silent-misreport failure mode Gotcha 2 exists to prevent.
        assert not isinstance(exc_info.value, cl.UnknownVerticalError)
        assert "this_module_does_not_exist_anywhere" in str(exc_info.value)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
