"""
Wizard B — DB-Native Pattern Analysis (wrapper)
=================================================

Wraps the template's PatternAnalyzer.from_database() + analyze_patterns()
but skips save_to_database() since trigger_wizard() already manages the
WizardRun record.
"""

from __future__ import annotations


def run_wizard_b(customer_id: int) -> dict:
    """
    Run pattern analysis from DB journey data.

    Must be called inside a Flask app context.
    Requires Wizard A to have run first (journey_data table populated).
    """
    import sys as _sys
    from pathlib import Path

    # Add template wizard_b to path
    _wb_dir = str(Path(__file__).parent.parent / 'verticals' / '_template' / 'journey' / 'wizard_b')
    if _wb_dir not in _sys.path:
        _sys.path.insert(0, _wb_dir)

    from wizard_b_pattern_analyzer import PatternAnalyzer

    analyzer = PatternAnalyzer.from_database(customer_id)
    analyzer.analyze_patterns()

    # Return results without calling save_to_database() —
    # trigger_wizard() stores results in WizardRun.results.
    # Build pattern summary — PatternProfile may be a class or dict
    pattern_summary = {}
    for k, v in (analyzer.pattern_profiles or {}).items():
        if hasattr(v, '__dict__'):
            pattern_summary[k] = {
                'count': getattr(v, 'count', 0),
                'avg_starting_health': round(getattr(v, 'avg_starting_health', 0), 1),
                'avg_ending_health': round(getattr(v, 'avg_ending_health', 0), 1),
            }
        elif isinstance(v, dict):
            pattern_summary[k] = {
                'count': v.get('count', 0),
                'avg_starting_health': round(v.get('avg_starting_health', 0), 1),
                'avg_ending_health': round(v.get('avg_ending_health', 0), 1),
            }

    return {
        'status': 'completed',
        'total_patterns': len(analyzer.pattern_profiles),
        'total_transitions': len(analyzer.transition_matrix),
        'total_warnings': len(analyzer.early_warning_rules),
        'total_journeys': len(analyzer.journeys),
        'pattern_profiles': pattern_summary,
    }
