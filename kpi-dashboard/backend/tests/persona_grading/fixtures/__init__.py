"""Persona-specific question fixtures.

Importing this module aggregates all 5 personas into ALL_FIXTURES.
"""
from .cro import CRO_QUESTIONS
from .cfo import CFO_QUESTIONS
from .ceo import CEO_QUESTIONS
from .vpcs import VPCS_QUESTIONS
from .csm import CSM_QUESTIONS

ALL_FIXTURES = (
    CRO_QUESTIONS + CFO_QUESTIONS + CEO_QUESTIONS
    + VPCS_QUESTIONS + CSM_QUESTIONS
)

BY_PERSONA = {
    'cro': CRO_QUESTIONS,
    'cfo': CFO_QUESTIONS,
    'ceo': CEO_QUESTIONS,
    'vpcs': VPCS_QUESTIONS,
    'csm': CSM_QUESTIONS,
}
