#!/usr/bin/env python3
"""
Tests for Kanban Backend Persistence.

Verifies:
  1. PATCH endpoint exists and validates column values
  2. API responses include kanban_column field
  3. Frontend source has @dnd-kit integration
  4. DraggableCard/DroppableColumn components exist
  5. Column computation respects kanban_column override

Run: python3 -m pytest tests/test_kanban_persistence.py -v
"""

import ast
import json
import os
import sys
import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KPI_DASHBOARD_DIR = os.path.dirname(BACKEND_DIR)  # kpi-dashboard/
ROOT_DIR = KPI_DASHBOARD_DIR
sys.path.insert(0, BACKEND_DIR)


# ============================================================
# Backend: PATCH Endpoint Tests
# ============================================================

class TestKanbanPatchEndpoint:
    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(BACKEND_DIR, 'kpi_api.py')
        with open(path) as f:
            self.source = f.read()

    def test_endpoint_exists(self):
        assert "'/api/accounts/<int:account_id>/kanban-column'" in self.source

    def test_accepts_patch_method(self):
        assert "methods=['PATCH']" in self.source
        assert 'def update_kanban_column' in self.source

    def test_validates_column_values(self):
        assert "VALID_COLUMNS = ('fire', 'week', 'opportunity')" in self.source

    def test_stores_in_profile_metadata(self):
        assert "kanban_column" in self.source
        assert "kanban_pinned_at" in self.source
        assert "kanban_pinned_by" in self.source

    def test_null_clears_override(self):
        assert "meta.pop('kanban_column', None)" in self.source

    def test_returns_pinned_status(self):
        assert "'pinned'" in self.source

    def test_validates_customer_ownership(self):
        assert 'account.customer_id != customer_id' in self.source


# ============================================================
# Backend: API Response Tests
# ============================================================

class TestApiResponsesIncludeKanbanColumn:
    def test_list_accounts_has_kanban_column(self):
        path = os.path.join(BACKEND_DIR, 'verticals', 'dc2_s', 'api_routes.py')
        with open(path) as f:
            source = f.read()
        assert "'kanban_column': meta.get('kanban_column')" in source

    def test_daily_actions_has_kanban_column(self):
        path = os.path.join(BACKEND_DIR, 'verticals', 'dc2_s', 'api_routes.py')
        with open(path) as f:
            source = f.read()
        assert "action['kanban_column']" in source


# ============================================================
# Frontend: @dnd-kit Integration Tests
# ============================================================

class TestDndKitIntegration:
    @pytest.fixture(autouse=True)
    def load_source(self):
        path = os.path.join(ROOT_DIR, 'src', 'components', 'csm', 'CSMCockpit.tsx')
        with open(path) as f:
            self.source = f.read()

    def test_dnd_kit_imported(self):
        assert "@dnd-kit/core" in self.source

    def test_dnd_context_used(self):
        assert "DndContext" in self.source
        assert "onDragStart" in self.source
        assert "onDragEnd" in self.source

    def test_drag_overlay_used(self):
        assert "DragOverlay" in self.source

    def test_draggable_card_component(self):
        assert "DraggableCard" in self.source
        assert "useDraggable" in self.source

    def test_droppable_column_component(self):
        assert "DroppableColumn" in self.source
        assert "useDroppable" in self.source

    def test_kanban_column_type(self):
        assert "type KanbanColumn = 'fire' | 'week' | 'opportunity'" in self.source

    def test_account_interface_has_kanban_column(self):
        assert "kanban_column?: KanbanColumn | null" in self.source

    def test_compute_column_respects_override(self):
        assert "if (a.kanban_column) return a.kanban_column" in self.source

    def test_handle_drag_end_calls_patch(self):
        assert "/api/accounts/" in self.source
        assert "kanban-column" in self.source
        assert "method: 'PATCH'" in self.source

    def test_optimistic_update(self):
        # Should update state before waiting for API
        assert "setAccounts((prev) => prev.map" in self.source

    def test_pin_indicator(self):
        assert "Pin" in self.source
        assert "isPinned" in self.source

    def test_unpin_handler(self):
        assert "handleUnpin" in self.source
        assert "onUnpin" in self.source

    def test_kanban_column_loaded_from_api(self):
        assert "kanban_column: a.kanban_column" in self.source

    def test_cursor_grab_on_cards(self):
        assert "cursor-grab" in self.source

    def test_drop_highlight(self):
        assert "bg-blue-50" in self.source
        assert "ring-blue-300" in self.source

    def test_empty_column_drop_hint(self):
        assert "Drop accounts here" in self.source


# ============================================================
# Package.json Tests
# ============================================================

class TestPackageDependencies:
    def test_dnd_kit_core_installed(self):
        path = os.path.join(ROOT_DIR, 'package.json')
        with open(path) as f:
            pkg = json.load(f)
        deps = pkg.get('dependencies', {})
        assert '@dnd-kit/core' in deps, "@dnd-kit/core not in dependencies"

    def test_dnd_kit_utilities_installed(self):
        path = os.path.join(ROOT_DIR, 'package.json')
        with open(path) as f:
            pkg = json.load(f)
        deps = pkg.get('dependencies', {})
        assert '@dnd-kit/utilities' in deps, "@dnd-kit/utilities not in dependencies"


# ============================================================
# Docker Compose Tests (FEATURE_SIGNAL_ENGINE from prior commit)
# ============================================================

class TestBackendSyntax:
    def test_kpi_api_parses(self):
        path = os.path.join(BACKEND_DIR, 'kpi_api.py')
        with open(path) as f:
            ast.parse(f.read())

    def test_api_routes_parses(self):
        path = os.path.join(BACKEND_DIR, 'verticals', 'dc2_s', 'api_routes.py')
        with open(path) as f:
            ast.parse(f.read())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
