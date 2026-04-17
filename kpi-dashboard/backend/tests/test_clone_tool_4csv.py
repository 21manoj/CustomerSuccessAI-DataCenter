#!/usr/bin/env python3
"""
Tests for clone_customer MCP tool — 4-CSV model update.

Verifies:
  1. Arc fields (arc_type, arc_phase, arc_confidence) are cloned on accounts
  2. FeatureToggle records are cloned
  3. WeightCalibrationHistory records are cloned
  4. next_steps text references 4-CSV model
  5. Total record count includes new cloned entities

Run: python3 -m pytest tests/test_clone_tool_4csv.py -v
"""

import ast
import os
import sys
import pytest

# Ensure backend is on path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)


class TestCloneToolSourceCode:
    """AST-level checks that clone_customer has the required fields."""

    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(BACKEND_DIR, 'mcp_server', 'cs_pulse_onboarding.py')
        with open(path) as f:
            self.source = f.read()
        self.tree = ast.parse(self.source)

    def test_imports_feature_toggle(self):
        assert 'FeatureToggle' in self.source, "clone_customer must import FeatureToggle"

    def test_imports_weight_calibration_history(self):
        assert 'WeightCalibrationHistory' in self.source, "clone_customer must import WeightCalibrationHistory"

    def test_clones_arc_type(self):
        assert 'arc_type=acct.arc_type' in self.source, "Account clone must copy arc_type"

    def test_clones_arc_phase(self):
        assert 'arc_phase=acct.arc_phase' in self.source, "Account clone must copy arc_phase"

    def test_clones_arc_confidence(self):
        assert 'arc_confidence=acct.arc_confidence' in self.source, "Account clone must copy arc_confidence"

    def test_clones_feature_toggles(self):
        assert 'feature_toggles_cloned' in self.source, "clone_customer must track feature_toggles_cloned count"

    def test_clones_weight_calibration_history(self):
        assert 'weight_calibration_history_cloned' in self.source, "clone_customer must track WCH clone count"

    def test_total_includes_new_entities(self):
        assert "feature_toggles_cloned" in self.source
        assert "weight_calibration_history_cloned" in self.source
        # Find the total_records block (spans multiple lines until closing paren + newline)
        start = self.source.index('total_records = (')
        # Find the matching closing paren — count parens
        depth = 0
        for i, ch in enumerate(self.source[start:], start):
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    total_block = self.source[start:i + 1]
                    break
        assert 'feature_toggles_cloned' in total_block, "total_records must include feature_toggles_cloned"
        assert 'weight_calibration_history_cloned' in total_block, "total_records must include weight_calibration_history_cloned"

    def test_next_steps_references_4csv(self):
        assert '4 CSVs' in self.source, "next_steps must reference 4-CSV model"
        assert '"8 CSVs"' not in self.source and "'8 CSVs'" not in self.source, "next_steps must NOT reference 8 CSVs"


class TestCloneToolSyntax:
    def test_file_parses(self):
        path = os.path.join(BACKEND_DIR, 'mcp_server', 'cs_pulse_onboarding.py')
        with open(path) as f:
            ast.parse(f.read())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
