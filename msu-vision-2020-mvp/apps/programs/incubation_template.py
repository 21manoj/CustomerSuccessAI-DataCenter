"""
Sample incubation workflow — applied as stages + milestones (admin-editable after apply).
"""

# Each entry: stage name, criteria, list of {name, criteria} milestones
INCUBATION_TEMPLATE = [
    {
        "name": "Applications",
        "criteria": "Publicize the call; collect submissions; record all applicants in the system.",
        "milestones": [
            {"name": "Application form live", "criteria": "Form published and linked from program page."},
            {"name": "Application deadline", "criteria": "Deadline communicated; submissions closed."},
            {"name": "Initial triage", "criteria": "Eligibility check completed for all submissions."},
        ],
    },
    {
        "name": "Shortlist",
        "criteria": "Panel review; publish shortlist; notify teams.",
        "milestones": [
            {"name": "Panel review complete", "criteria": "Rubric applied; scores recorded."},
            {"name": "Shortlist published", "criteria": "Shortlist visible to applicants and stakeholders."},
        ],
    },
    {
        "name": "Allocation",
        "criteria": "Per-team budget approved; agreements signed; funded from the chosen pool.",
        "milestones": [
            {"name": "Per-team budget approved", "criteria": "Amounts aligned with pool and governance rules."},
            {"name": "Agreements signed", "criteria": "Executed agreements on file."},
        ],
    },
    {
        "name": "Mentorship & execution",
        "criteria": "Run the program for the full cycle (e.g. academic year); mentorship and checkpoints.",
        "milestones": [
            {"name": "Kickoff", "criteria": "Teams onboarded; mentors assigned."},
            {"name": "Mid-year review", "criteria": "Progress review completed; course corrections noted."},
            {"name": "Demo day prep", "criteria": "Final presentations scheduled; judges briefed."},
        ],
    },
    {
        "name": "Awards & closure",
        "criteria": "Select winners; disburse prize money; document outcomes.",
        "milestones": [
            {"name": "Final judging", "criteria": "Judging complete; rankings recorded."},
            {"name": "Top teams selected", "criteria": "e.g. top 3 identified and published."},
            {"name": "Prize disbursement documented", "criteria": "Payments recorded against pool; receipts stored."},
        ],
    },
]


def apply_incubation_template(program):
    """
    Create ProgramStage and ProgramMilestone rows from INCUBATION_TEMPLATE.
    Skips if the program already has any stages.
    Returns number of stages created (0 if skipped).
    """
    from apps.programs.models import ProgramMilestone, ProgramStage

    if program.stages.exists():
        return 0
    created = 0
    for order, block in enumerate(INCUBATION_TEMPLATE):
        stage = ProgramStage.objects.create(
            program=program,
            sequence=order,
            name=block["name"],
            criteria=block.get("criteria", ""),
            status=ProgramStage.Status.NOT_STARTED,
        )
        created += 1
        for m_order, m in enumerate(block.get("milestones", [])):
            ProgramMilestone.objects.create(
                stage=stage,
                sequence=m_order,
                name=m["name"],
                criteria=m.get("criteria", ""),
            )
    return created
