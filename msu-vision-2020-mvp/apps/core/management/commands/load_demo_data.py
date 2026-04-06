"""
Full workflow seed: HOD needs, hostel 9-month project + monthly milestones, donors, July 2026 gala + media,
governance queue items. Idempotent by stable titles. Password demo123 (demo/demo for quick login).
"""
import base64
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.events.models import Event, EventMedia, EventRegistration
from apps.funding.models import Contribution, Expense, FundPool
from apps.needs.models import Need
from apps.programs.incubation_template import apply_incubation_template
from apps.programs.models import Program, ProgramMilestone, ProgramStage
from apps.projects.models import Milestone, Project, ProjectTeam
from apps.stakeholders.models import Organization, UserProfile
from apps.stakeholders.persona_utils import replace_user_personas

User = get_user_model()
IST = ZoneInfo("Asia/Kolkata")


def _apply_demo_display_names():
    """Readable names on seeded users for milestone/program owner lines."""
    mapping = {
        "admin": ("System", "Admin"),
        "demo": ("Demo", "User"),
        "finance1": ("Sanjay", "Kapoor"),
        "gov_meera": ("Meera", "Iyer"),
        "hod_hostel": ("Vikram", "Sen"),
        "hod_academic": ("Neha", "Rao"),
        "lead_hostel": ("Arjun", "Mehta"),
        "lead_career": ("Kavita", "Menon"),
        "volunteer_riya": ("Riya", "Nair"),
        "donor_anita": ("Anita", "Desai"),
        "donor_james": ("James", "Wright"),
        "auditor_kim": ("Kim", "Park"),
    }
    for username, (fn, ln) in mapping.items():
        User.objects.filter(username=username).update(first_name=fn, last_name=ln)


def _assign_program_milestone_owners(program, *users):
    """Round-robin owner on milestones missing owner (for incubation template etc.)."""
    if not users:
        return
    idx = 0
    for stage in program.stages.order_by("sequence", "id"):
        for pm in stage.milestones.order_by("sequence", "id"):
            if pm.owner_id is None:
                pm.owner = users[idx % len(users)]
                pm.save(update_fields=["owner", "updated_at"])
                idx += 1

# 1×1 PNG for seeded “photos”
MINI_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


def _user(username, email, password, role, org=None):
    u, created = User.objects.get_or_create(username=username, defaults={"email": email})
    if created:
        u.set_password(password)
        u.save()
    prof = u.profile
    prof.stakeholder_type = role
    prof.organization = org
    prof.save()
    return u


class Command(BaseCommand):
    help = "Seed workflow personas: HOD, lead, volunteer, donors, governance, finance + hostel project & July 2026 gala."

    @transaction.atomic
    def handle(self, *args, **options):
        Site.objects.update_or_create(
            pk=1, defaults={"domain": "localhost:8000", "name": "MSU Vision 2020"}
        )

        india, _ = FundPool.objects.get_or_create(
            jurisdiction=FundPool.Jurisdiction.INDIA,
            defaults={"name": "India CSR pool", "description": "India CSR"},
        )
        us_pool, _ = FundPool.objects.get_or_create(
            jurisdiction=FundPool.Jurisdiction.US,
            defaults={"name": "US 501(c)(3) pool", "description": "US"},
        )

        org_hostel, _ = Organization.objects.get_or_create(
            name="Estate & Hostels",
            defaults={
                "org_type": Organization.OrgType.DEPARTMENT,
                "jurisdiction": Organization.Jurisdiction.INDIA,
            },
        )
        org_academic, _ = Organization.objects.get_or_create(
            name="Academic Affairs",
            defaults={
                "org_type": Organization.OrgType.DEPARTMENT,
                "jurisdiction": Organization.Jurisdiction.INDIA,
            },
        )

        admin = _user("admin", "admin@msu-vision.example", "demo123", UserProfile.StakeholderType.FOUNDATION_ADMIN)
        demo_u, _ = User.objects.get_or_create(username="demo", defaults={"email": "demo@local"})
        demo_u.set_password("demo")
        demo_u.save()
        demo_u.profile.stakeholder_type = UserProfile.StakeholderType.FOUNDATION_ADMIN
        demo_u.profile.needs_persona_assignment = False
        demo_u.profile.save()
        replace_user_personas(demo_u, [UserProfile.StakeholderType.FOUNDATION_ADMIN])

        finance = _user(
            "finance1", "finance@msu-vision.example", "demo123", UserProfile.StakeholderType.FINANCE_CONTROLLER
        )
        gov_meera = _user(
            "gov_meera", "governance@msu-vision.example", "demo123", UserProfile.StakeholderType.GOVERNANCE
        )
        hod_hostel = _user(
            "hod_hostel", "hod.hostel@msu-vision.example", "demo123", UserProfile.StakeholderType.HOD, org=org_hostel
        )
        hod_academic = _user(
            "hod_academic",
            "hod.academic@msu-vision.example",
            "demo123",
            UserProfile.StakeholderType.HOD,
            org=org_academic,
        )
        lead_hostel = _user(
            "lead_hostel", "lead.hostel@msu-vision.example", "demo123", UserProfile.StakeholderType.PROJECT_LEAD
        )
        volunteer_riya = _user(
            "volunteer_riya", "riya.vol@msu-vision.example", "demo123", UserProfile.StakeholderType.VOLUNTEER
        )
        donor_anita = _user(
            "donor_anita", "anita.donor@example.com", "demo123", UserProfile.StakeholderType.DONOR
        )
        donor_james = _user(
            "donor_james", "james.donor@example.com", "demo123", UserProfile.StakeholderType.DONOR
        )
        auditor = _user("auditor_kim", "audit@msu-vision.example", "demo123", UserProfile.StakeholderType.AUDITOR)
        lead_career = _user(
            "lead_career", "lead.career@msu-vision.example", "demo123", UserProfile.StakeholderType.PROJECT_LEAD
        )
        _apply_demo_display_names()

        org_csr, _ = Organization.objects.get_or_create(
            name="CSR Partners Roundtable",
            defaults={
                "org_type": Organization.OrgType.CSR_PARTNER,
                "jurisdiction": Organization.Jurisdiction.INDIA,
            },
        )

        # --- Programs first (projects may FK here) ---
        prog_demo, prog_created = Program.objects.get_or_create(
            slug="demo-incubation",
            defaults={
                "title": "Demo student incubation cohort",
                "description": "Sample long-running program with incubation-style stages and milestones (fully editable).",
                "status": Program.Status.ACTIVE,
                "fund_pool": india,
                "created_by": admin,
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 12, 31),
            },
        )
        prog_demo.admins.add(admin, gov_meera)
        if prog_created:
            apply_incubation_template(prog_demo)

        prog_mentorship, _ = Program.objects.get_or_create(
            slug="alumni-mentorship-pilot",
            defaults={
                "title": "Alumni mentorship pilot",
                "description": "Mentor–mentee cohort; cross-links to Wi-Fi execution project for lab walkthroughs.",
                "status": Program.Status.PLANNED,
                "fund_pool": us_pool,
                "created_by": gov_meera,
                "start_date": date(2026, 2, 1),
                "end_date": date(2026, 11, 30),
            },
        )
        prog_mentorship.admins.add(gov_meera, lead_hostel)
        if not prog_mentorship.stages.exists():
            s0 = ProgramStage.objects.create(
                program=prog_mentorship,
                sequence=0,
                name="Recruitment & matching",
                description="Recruit mentors and match mentees.",
                criteria="≥80% of mentees paired with a mentor.",
                status=ProgramStage.Status.IN_PROGRESS,
            )
            ProgramMilestone.objects.create(
                stage=s0,
                sequence=0,
                name="Mentor signup window",
                criteria="Target 50 alumni mentors.",
                due_date=date(2026, 3, 15),
                owner=gov_meera,
            )
            ProgramMilestone.objects.create(
                stage=s0,
                sequence=1,
                name="Mentee intake & pairing",
                criteria="Background survey + manual matching.",
                due_date=date(2026, 4, 1),
                owner=lead_hostel,
            )
            s1 = ProgramStage.objects.create(
                program=prog_mentorship,
                sequence=1,
                name="Quarterly cadence",
                description="Running the year-long program.",
                criteria="Two retros completed.",
                status=ProgramStage.Status.NOT_STARTED,
            )
            ProgramMilestone.objects.create(
                stage=s1,
                sequence=0,
                name="Q1 mentor–mentee retro",
                due_date=date(2026, 6, 30),
                owner=volunteer_riya,
            )
            ProgramMilestone.objects.create(
                stage=s1,
                sequence=1,
                name="Mid-year showcase",
                due_date=date(2026, 8, 15),
                owner=hod_academic,
            )

        prog_sustain, _ = Program.objects.get_or_create(
            slug="campus-sustainability-rollups",
            defaults={
                "title": "Campus sustainability rollups",
                "description": "Cross-cutting green initiatives; solar pilot project links here.",
                "status": Program.Status.ACTIVE,
                "fund_pool": india,
                "created_by": hod_hostel,
                "start_date": date(2025, 6, 1),
                "end_date": date(2027, 5, 31),
            },
        )
        prog_sustain.admins.add(hod_hostel, finance)
        if not prog_sustain.stages.exists():
            sa = ProgramStage.objects.create(
                program=prog_sustain,
                sequence=0,
                name="Assessment & approvals",
                criteria="Energy audit signed off.",
                status=ProgramStage.Status.COMPLETED,
            )
            ProgramMilestone.objects.create(
                stage=sa,
                sequence=0,
                name="Campus energy audit complete",
                criteria="Third-party report filed.",
                due_date=date(2025, 12, 1),
                owner=hod_hostel,
                completed_at=datetime(2025, 12, 5, 12, 0, tzinfo=IST),
                completed_by=finance,
            )
            sb = ProgramStage.objects.create(
                program=prog_sustain,
                sequence=1,
                name="Pilot execution",
                criteria="Block A solar live.",
                status=ProgramStage.Status.IN_PROGRESS,
            )
            ProgramMilestone.objects.create(
                stage=sb,
                sequence=0,
                name="Vendor selection & PO",
                due_date=date(2026, 2, 28),
                owner=finance,
            )
            ProgramMilestone.objects.create(
                stage=sb,
                sequence=1,
                name="Install & commissioning",
                due_date=date(2026, 5, 31),
                owner=lead_hostel,
            )

        # --- HOD: draft need (academic) ---
        need_wifi, _ = Need.objects.get_or_create(
            title="Campus Wi-Fi upgrade — Phase 2 (draft)",
            defaults={
                "created_by": hod_academic,
                "department": org_academic,
                "description": "HOD priority: expand coverage in lecture blocks. Submit for foundation review when ready.",
                "status": Need.Status.DRAFT,
                "target_amount": Decimal("350000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )
        need_girls, _ = Need.objects.get_or_create(
            title="Girls hostel — minor repair & painting (draft)",
            defaults={
                "created_by": hod_hostel,
                "department": org_hostel,
                "description": "Monsoon touch-ups; estimate pending from estates.",
                "status": Need.Status.DRAFT,
                "target_amount": Decimal("180000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )
        need_career, _ = Need.objects.get_or_create(
            title="Career center — AV & interview pods (matched)",
            defaults={
                "created_by": hod_academic,
                "department": org_academic,
                "description": "Recording kits and two interview pods; US donor anchor.",
                "status": Need.Status.MATCHED,
                "funding_model": Need.FundingModel.ANCHOR,
                "target_amount": Decimal("2200000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )
        need_career.matched_donors.add(donor_james)

        # --- Governance: high-value need awaiting approval ---
        need_gov, _ = Need.objects.get_or_create(
            title="Alumni Innovation & Research Wing",
            defaults={
                "created_by": hod_academic,
                "department": org_academic,
                "description": "Multi-year research floor; exceeds governance threshold for approval.",
                "status": Need.Status.PENDING_GOVERNANCE,
                "target_amount": Decimal("15000000"),
                "target_currency": "INR",
                "requires_governance_approval": True,
            },
        )
        need_csr, _ = Need.objects.get_or_create(
            title="Joint CSR — village STEM outreach (cataloged)",
            defaults={
                "created_by": admin,
                "department": org_csr,
                "description": "Partner-funded mobile lab; cataloged for matching (no project yet).",
                "status": Need.Status.CATALOGED,
                "target_amount": Decimal("4500000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )

        # --- HOD hostel: matched need + flagship project ---
        need_hostel, _ = Need.objects.get_or_create(
            title="Boys Hostel Remodeling (2025–2026)",
            defaults={
                "created_by": hod_hostel,
                "department": org_hostel,
                "description": "Structural refresh, bathrooms, fire safety, and common room for 240 residents. "
                "Timeline ~9 months from kickoff.",
                "status": Need.Status.MATCHED,
                "funding_model": Need.FundingModel.POOLED,
                "target_amount": Decimal("8500000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )
        need_hostel.matched_donors.add(donor_anita, donor_james)

        proj_hostel, _ = Project.objects.get_or_create(
            need=need_hostel,
            title="Boys Hostel Remodeling Program",
            defaults={
                "lead": lead_hostel,
                "description": "Six–nine month delivery: civil, MEP, interiors, furniture, handover. "
                "Lead: alumni volunteer coordinator; Riya supports on-site checks.",
                "status": Project.Status.IN_PROGRESS,
                "budget": Decimal("8200000"),
                "budget_currency": "INR",
                "start_date": date(2025, 9, 1),
                "target_end_date": date(2026, 5, 31),
            },
        )
        if proj_hostel.title != need_hostel.title:
            proj_hostel.title = need_hostel.title
            proj_hostel.save(update_fields=["title"])
        ProjectTeam.objects.get_or_create(
            project=proj_hostel,
            user=volunteer_riya,
            defaults={"role": ProjectTeam.Role.VOLUNTEER},
        )
        Project.objects.filter(pk=proj_hostel.pk).update(program=prog_demo)

        monthly = [
            ("Sep 2025 — Kickoff & resident communication", Milestone.Status.DONE, date(2025, 9, 1), date(2025, 9, 28)),
            ("Oct 2025 — Structural & MEP design sign-off", Milestone.Status.DONE, date(2025, 10, 1), date(2025, 10, 31)),
            ("Nov 2025 — Tender, award & mobilization", Milestone.Status.DONE, date(2025, 11, 1), date(2025, 11, 30)),
            ("Dec 2025 — Demolition & shell civil", Milestone.Status.DONE, date(2025, 12, 1), date(2025, 12, 31)),
            ("Jan 2026 — Masonry, waterproofing", Milestone.Status.DONE, date(2026, 1, 1), date(2026, 1, 31)),
            ("Feb 2026 — Electrical & plumbing rough-in", Milestone.Status.DONE, date(2026, 2, 1), date(2026, 2, 28)),
            (
                "Mar 2026 — Interior phase: wet areas & corridors",
                Milestone.Status.IN_PROGRESS,
                date(2026, 3, 1),
                date(2026, 3, 31),
            ),
            ("Apr 2026 — Room interiors & fixtures", Milestone.Status.PENDING, date(2026, 4, 1), date(2026, 4, 30)),
            ("May 2026 — QA, furniture, handover & closeout", Milestone.Status.PENDING, date(2026, 5, 1), date(2026, 5, 31)),
        ]
        # % of project budget per milestone gate (need not sum to 100). Done + released = funded in rollup.
        hostel_tranche_pcts = [10, 10, 10, 10, 12, 12, 15, 10, 4]
        if not proj_hostel.milestones.exists():
            for seq, (title, st, sd, ed) in enumerate(monthly):
                pct = hostel_tranche_pcts[seq] if seq < len(hostel_tranche_pcts) else 0
                gov = Milestone.TrancheGovernance.NOT_APPLICABLE
                if pct > 0 and st == Milestone.Status.DONE:
                    gov = Milestone.TrancheGovernance.RELEASED
                Milestone.objects.create(
                    project=proj_hostel,
                    title=title,
                    description="",
                    start_date=sd,
                    due_date=ed,
                    status=st,
                    sequence=seq,
                    weight_percent=0,
                    completed_date=ed if st == Milestone.Status.DONE else None,
                    next_tranche_budget_percent=pct,
                    tranche_governance_status=gov,
                )

        for m in proj_hostel.milestones.filter(assigned_to__isnull=True):
            m.assigned_to = lead_hostel if m.sequence < 6 else volunteer_riya
            m.save(update_fields=["assigned_to"])

        # --- Project pending governance (USD budget over threshold) ---
        need_isc, _ = Need.objects.get_or_create(
            title="International Student Center (matched)",
            defaults={
                "created_by": admin,
                "department": org_academic,
                "description": "Feasibility cleared; project charter pending board sign-off.",
                "status": Need.Status.MATCHED,
                "target_amount": Decimal("200000"),
                "target_currency": "USD",
                "requires_governance_approval": False,
            },
        )
        need_wifi_exec, _ = Need.objects.get_or_create(
            title="Campus Wi-Fi Phase 2 — execution build (matched)",
            defaults={
                "created_by": hod_academic,
                "department": org_academic,
                "description": "Execution track for lecture-hall coverage; linked to mentorship program for lab tours.",
                "status": Need.Status.MATCHED,
                "funding_model": Need.FundingModel.POOLED,
                "target_amount": Decimal("2800000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )
        need_solar, _ = Need.objects.get_or_create(
            title="Rooftop solar pilot — Block A (matched)",
            defaults={
                "created_by": hod_hostel,
                "department": org_hostel,
                "description": "First campus solar block; part of sustainability rollup program.",
                "status": Need.Status.MATCHED,
                "funding_model": Need.FundingModel.POOLED,
                "target_amount": Decimal("4200000"),
                "target_currency": "INR",
                "requires_governance_approval": False,
            },
        )
        need_wifi_exec.matched_donors.add(donor_anita)
        need_solar.matched_donors.add(donor_james, donor_anita)

        proj_isc, _ = Project.objects.get_or_create(
            need=need_isc,
            title="International Student Center — Build",
            defaults={
                "lead": lead_hostel,
                "description": "High-budget build; requires governance approval on budget.",
                "status": Project.Status.PENDING_GOVERNANCE,
                "budget": Decimal("18500"),
                "budget_currency": "USD",
                "requires_governance_approval": True,
                "start_date": date(2026, 6, 1),
                "target_end_date": date(2027, 3, 31),
            },
        )
        if proj_isc.title != need_isc.title:
            proj_isc.title = need_isc.title
            proj_isc.save(update_fields=["title"])

        proj_wifi, _ = Project.objects.get_or_create(
            need=need_wifi_exec,
            title="Wi-Fi Phase 2 — deployment",
            defaults={
                "program": prog_mentorship,
                "lead": lead_hostel,
                "description": "AP rollout to lecture blocks; mentorship program uses labs for demos.",
                "status": Project.Status.IN_PROGRESS,
                "budget": Decimal("2650000"),
                "budget_currency": "INR",
                "start_date": date(2026, 1, 5),
                "target_end_date": date(2026, 4, 30),
            },
        )
        proj_solar, _ = Project.objects.get_or_create(
            need=need_solar,
            title="Solar pilot — Block A install",
            defaults={
                "program": prog_sustain,
                "lead": lead_hostel,
                "description": "Vendor-led install under sustainability rollup.",
                "status": Project.Status.IN_PROGRESS,
                "budget": Decimal("4100000"),
                "budget_currency": "INR",
                "start_date": date(2026, 1, 15),
                "target_end_date": date(2026, 6, 15),
            },
        )
        proj_career, _ = Project.objects.get_or_create(
            need=need_career,
            title="Career center AV & pods — delivery",
            defaults={
                "program": None,
                "lead": lead_career,
                "description": "Standalone delivery project (no program); anchor-funded.",
                "status": Project.Status.APPROVED,
                "budget": Decimal("2100000"),
                "budget_currency": "INR",
                "funding_model": Project.FundingModel.ANCHOR,
                "start_date": date(2026, 3, 1),
                "target_end_date": date(2026, 8, 31),
            },
        )

        def _wifi_solar_career_milestones():
            wifi_specs = [
                ("Site survey & backbone design", Milestone.Status.DONE, date(2026, 1, 5), date(2026, 1, 25), lead_hostel),
                ("AP deployment wave 1", Milestone.Status.IN_PROGRESS, date(2026, 2, 1), date(2026, 3, 15), volunteer_riya),
                ("Acceptance & heatmaps", Milestone.Status.PENDING, date(2026, 3, 16), date(2026, 4, 20), hod_academic),
            ]
            for seq, (title, st, sd, ed, assignee) in enumerate(wifi_specs):
                m, created = Milestone.objects.get_or_create(
                    project=proj_wifi,
                    title=title,
                    defaults={
                        "description": "",
                        "start_date": sd,
                        "due_date": ed,
                        "status": st,
                        "sequence": seq,
                        "weight_percent": 0,
                        "assigned_to": assignee,
                        "completed_date": ed if st == Milestone.Status.DONE else None,
                    },
                )
                if created:
                    m.owners.set([lead_hostel.pk, assignee.pk])

            solar_specs = [
                ("Structural assessment & load letter", Milestone.Status.DONE, date(2026, 1, 10), date(2026, 1, 28), finance),
                ("Racking & module install", Milestone.Status.IN_PROGRESS, date(2026, 2, 1), date(2026, 4, 30), lead_hostel),
                ("Grid tie & SCADA handover", Milestone.Status.PENDING, date(2026, 5, 1), date(2026, 6, 10), hod_hostel),
            ]
            for seq, (title, st, sd, ed, assignee) in enumerate(solar_specs):
                m, created = Milestone.objects.get_or_create(
                    project=proj_solar,
                    title=title,
                    defaults={
                        "description": "",
                        "start_date": sd,
                        "due_date": ed,
                        "status": st,
                        "sequence": seq,
                        "weight_percent": 0,
                        "assigned_to": assignee,
                        "completed_date": ed if st == Milestone.Status.DONE else None,
                    },
                )
                if created:
                    m.owners.set([hod_hostel.pk, finance.pk, assignee.pk])

            career_specs = [
                ("Vendor RFQ & shortlist", Milestone.Status.IN_PROGRESS, date(2026, 3, 1), date(2026, 3, 31), lead_career),
                ("Install & UAT", Milestone.Status.PENDING, date(2026, 4, 1), date(2026, 7, 31), lead_career),
            ]
            for seq, (title, st, sd, ed, assignee) in enumerate(career_specs):
                m, created = Milestone.objects.get_or_create(
                    project=proj_career,
                    title=title,
                    defaults={
                        "description": "",
                        "start_date": sd,
                        "due_date": ed,
                        "status": st,
                        "sequence": seq,
                        "weight_percent": 0,
                        "assigned_to": assignee,
                        "completed_date": None,
                    },
                )
                if created:
                    m.owners.set([lead_career.pk, hod_academic.pk])

        _wifi_solar_career_milestones()

        Project.objects.filter(pk=proj_hostel.pk).update(students_impacted=240)
        Project.objects.filter(pk=proj_isc.pk).update(students_impacted=800)
        Project.objects.filter(pk=proj_wifi.pk).update(students_impacted=1200)
        Project.objects.filter(pk=proj_solar.pk).update(students_impacted=400)
        Project.objects.filter(pk=proj_career.pk).update(students_impacted=3500)

        # --- Contributions ---
        if not Contribution.objects.filter(donor=donor_anita, project=proj_hostel).exists():
            Contribution.objects.create(
                donor=donor_anita,
                project=proj_hostel,
                fund_pool=india,
                recorded_by=finance,
                amount=Decimal("4250000"),
                currency="INR",
                jurisdiction_origin=Contribution.JurisdictionOrigin.INDIA,
                status=Contribution.Status.RECEIVED,
                received_date=date(2025, 11, 10),
                notes="Pooled gift toward hostel remodeling",
            )
        if not Contribution.objects.filter(donor=donor_james, project=proj_hostel).exists():
            Contribution.objects.create(
                donor=donor_james,
                project=proj_hostel,
                fund_pool=us_pool,
                recorded_by=finance,
                amount=Decimal("12000"),
                currency="USD",
                jurisdiction_origin=Contribution.JurisdictionOrigin.US,
                status=Contribution.Status.RECEIVED,
                received_date=date(2025, 12, 5),
                notes="US chapter alumni gift",
            )
        if not Contribution.objects.filter(donor=donor_anita, project=proj_wifi).exists():
            Contribution.objects.create(
                donor=donor_anita,
                project=proj_wifi,
                fund_pool=india,
                recorded_by=finance,
                amount=Decimal("800000"),
                currency="INR",
                jurisdiction_origin=Contribution.JurisdictionOrigin.INDIA,
                status=Contribution.Status.RECEIVED,
                received_date=date(2026, 1, 20),
                notes="Tranche toward Wi-Fi Phase 2 execution",
            )
        if not Contribution.objects.filter(donor=donor_james, project=proj_solar).exists():
            Contribution.objects.create(
                donor=donor_james,
                project=proj_solar,
                fund_pool=us_pool,
                recorded_by=finance,
                amount=Decimal("9500"),
                currency="USD",
                jurisdiction_origin=Contribution.JurisdictionOrigin.US,
                status=Contribution.Status.PLEDGED,
                pledge_date=date(2026, 2, 1),
                notes="US pledge toward solar pilot (Block A)",
            )
        if not Contribution.objects.filter(
            donor=donor_james, project__isnull=True, event__isnull=True, fund_pool=india
        ).exists():
            Contribution.objects.create(
                donor=donor_james,
                project=None,
                event=None,
                fund_pool=india,
                recorded_by=finance,
                amount=Decimal("250000"),
                currency="INR",
                jurisdiction_origin=Contribution.JurisdictionOrigin.INDIA,
                status=Contribution.Status.RECEIVED,
                received_date=date(2025, 10, 15),
                notes="Unrestricted pool gift (no project/event link) — FK check",
            )
        if not Contribution.objects.filter(donor=donor_james, project=proj_career).exists():
            Contribution.objects.create(
                donor=donor_james,
                project=proj_career,
                fund_pool=us_pool,
                recorded_by=finance,
                amount=Decimal("18000"),
                currency="USD",
                jurisdiction_origin=Contribution.JurisdictionOrigin.US,
                status=Contribution.Status.RECEIVED,
                received_date=date(2026, 2, 10),
                notes="Anchor tranche — career center AV (no program FK)",
            )

        # --- Expense: governance threshold (hostel) ---
        expense_gov, _ = Expense.objects.get_or_create(
            project=proj_hostel,
            description="Bulk sanitary & CP fittings — hostel block A–D",
            defaults={
                "fund_pool": india,
                "requested_by": lead_hostel,
                "amount": Decimal("320000"),
                "currency": "INR",
                "expense_date": date(2026, 3, 20),
                "status": Expense.Status.PENDING_GOVERNANCE,
                "requires_governance_approval": True,
            },
        )

        expense_wifi_std, _ = Expense.objects.get_or_create(
            project=proj_wifi,
            description="Ruggedized indoor AP spares — Wi-Fi Phase 2",
            defaults={
                "fund_pool": india,
                "requested_by": lead_hostel,
                "approved_by": finance,
                "amount": Decimal("185000"),
                "currency": "INR",
                "expense_date": date(2026, 2, 12),
                "status": Expense.Status.APPROVED,
                "requires_governance_approval": False,
            },
        )
        expense_solar_pending, _ = Expense.objects.get_or_create(
            project=proj_solar,
            description="Module uplift & string combiner — advance to vendor",
            defaults={
                "fund_pool": india,
                "requested_by": lead_hostel,
                "amount": Decimal("980000"),
                "currency": "INR",
                "expense_date": date(2026, 3, 1),
                "status": Expense.Status.PENDING,
                "requires_governance_approval": False,
            },
        )

        # --- July 2026 fundraising gala + plan + “photos” ---
        gala_desc = """## Roadmap to July 2026 gala

| When | Milestone |
|------|-----------|
| Jan 2026 | Steering committee & budget locked |
| Feb 2026 | Venue contract + catering shortlist |
| Mar 2026 | Save-the-date + alumni email series |
| Apr 2026 | Sponsor tiers & recognition packages |
| May 2026 | Ticket sales open (early bird) |
| Jun 2026 | Volunteer briefing, run-of-show dry run |
| **18 Jul 2026** | **Gala night — program, auction, donor recognition** |

Linked to **Boys Hostel Remodeling** for storytelling and impact updates to donors.
Post-event: thank-you, publish photos, reconcile pledges."""

        gala, _ = Event.objects.get_or_create(
            title="Hostel Renewal Gala & Donor Appreciation — July 2026",
            defaults={
                "organized_by": admin,
                "linked_project": proj_hostel,
                "linked_need": need_hostel,
                "description": gala_desc,
                "event_type": Event.EventType.FUNDRAISING,
                "venue": "MSU Foundation Auditorium",
                "location": "Campus — Main auditorium + foyer",
                "start_datetime": datetime(2026, 7, 18, 17, 30, tzinfo=IST),
                "end_datetime": datetime(2026, 7, 18, 22, 0, tzinfo=IST),
                "status": Event.Status.REGISTRATION_OPEN,
                "target_amount": Decimal("2500000"),
                "jurisdiction": Event.Jurisdiction.BOTH,
            },
        )

        if not Contribution.objects.filter(donor=donor_anita, event=gala).exists():
            Contribution.objects.create(
                donor=donor_anita,
                project=None,
                event=gala,
                fund_pool=india,
                recorded_by=finance,
                amount=Decimal("100000"),
                currency="INR",
                jurisdiction_origin=Contribution.JurisdictionOrigin.INDIA,
                status=Contribution.Status.PLEDGED,
                pledge_date=date(2026, 3, 1),
                notes="Table sponsorship pledge for July gala",
            )

        captions = [
            "Planning committee — Feb 2026 venue walkthrough",
            "Save-the-date creative (mock)",
            "Volunteer team briefing agenda — Jun 2026",
        ]
        for i, cap in enumerate(captions):
            if not gala.media_items.filter(caption=cap).exists():
                em = EventMedia(
                    event=gala,
                    uploaded_by=admin,
                    caption=cap,
                    media_type=EventMedia.MediaType.PHOTO,
                )
                em.file.save(f"gala_seed_{i}.png", ContentFile(MINI_PNG), save=True)

        EventRegistration.objects.get_or_create(
            event=gala,
            user=donor_anita,
            defaults={"role": EventRegistration.Role.ATTENDEE},
        )
        EventRegistration.objects.get_or_create(
            event=gala,
            user=donor_james,
            defaults={"role": EventRegistration.Role.ATTENDEE},
        )

        event_fireside, _ = Event.objects.get_or_create(
            title="Alumni fireside — AI, careers & ethics",
            defaults={
                "organized_by": gov_meera,
                "linked_need": need_gov,
                "linked_project": None,
                "description": "Evening panel; narrative ties to **Research Wing** need (need-only FK).",
                "event_type": Event.EventType.LECTURE,
                "venue": "Innovation Gallery",
                "location": "MSU main campus",
                "start_datetime": datetime(2026, 5, 8, 18, 0, tzinfo=IST),
                "end_datetime": datetime(2026, 5, 8, 20, 0, tzinfo=IST),
                "status": Event.Status.PUBLISHED,
                "jurisdiction": Event.Jurisdiction.INDIA,
            },
        )
        event_site, _ = Event.objects.get_or_create(
            title="Donor site visit — hostel construction walkthrough",
            defaults={
                "organized_by": lead_hostel,
                "linked_need": need_hostel,
                "linked_project": proj_hostel,
                "description": "Hard-hat tour for major donors; **need + project** FKs.",
                "event_type": Event.EventType.NETWORKING,
                "venue": "Boys hostel site — Block B",
                "location": "North campus",
                "start_datetime": datetime(2026, 4, 22, 10, 0, tzinfo=IST),
                "end_datetime": datetime(2026, 4, 22, 12, 30, tzinfo=IST),
                "status": Event.Status.REGISTRATION_OPEN,
                "jurisdiction": Event.Jurisdiction.INDIA,
            },
        )
        event_isc_internal, _ = Event.objects.get_or_create(
            title="ISC build — steering workshop (internal)",
            defaults={
                "organized_by": admin,
                "linked_need": need_isc,
                "linked_project": proj_isc,
                "description": "Draft event for governance-heavy project (**ISC** links).",
                "event_type": Event.EventType.LECTURE,
                "venue": "Foundation board room",
                "location": "Admin annex",
                "start_datetime": datetime(2026, 6, 3, 15, 0, tzinfo=IST),
                "end_datetime": datetime(2026, 6, 3, 17, 0, tzinfo=IST),
                "status": Event.Status.DRAFT,
                "jurisdiction": Event.Jurisdiction.BOTH,
            },
        )
        EventRegistration.objects.get_or_create(
            event=event_fireside,
            user=donor_anita,
            defaults={"role": EventRegistration.Role.ATTENDEE},
        )
        EventRegistration.objects.get_or_create(
            event=event_fireside,
            user=gov_meera,
            defaults={"role": EventRegistration.Role.VOLUNTEER},
        )

        # Stewardship / receipt / comms capture (idempotent updates)
        Contribution.objects.filter(donor=donor_anita, project=proj_hostel).update(
            receipt_sent=True,
            receipt_sent_date=date(2025, 11, 18),
            communication_capture_url="https://msu-vision-demo.s3.amazonaws.com/comms/anita-hostel-80g-letter.pdf",
            volunteer_lead=lead_hostel,
        )
        Contribution.objects.filter(donor=donor_james, project=proj_hostel).update(
            receipt_sent=False,
            receipt_sent_date=None,
            volunteer_lead=volunteer_riya,
        )
        Contribution.objects.filter(donor=donor_anita, event=gala).update(volunteer_lead=lead_hostel)

        # Owners (registered users only; idempotent .set)
        need_wifi.owners.set([hod_academic])
        need_girls.owners.set([hod_hostel, volunteer_riya])
        need_career.owners.set([hod_academic, lead_career])
        need_gov.owners.set([hod_academic, gov_meera])
        need_csr.owners.set([admin, finance])
        need_hostel.owners.set([hod_hostel, lead_hostel])
        need_isc.owners.set([hod_academic, gov_meera])
        need_wifi_exec.owners.set([hod_academic, lead_hostel])
        need_solar.owners.set([hod_hostel, finance])
        proj_hostel.owners.set([lead_hostel, hod_hostel, finance])
        proj_isc.owners.set([lead_hostel, gov_meera])
        proj_wifi.owners.set([lead_hostel, volunteer_riya, hod_academic])
        proj_solar.owners.set([lead_hostel, hod_hostel, finance])
        proj_career.owners.set([lead_career, hod_academic, finance])
        for m in proj_hostel.milestones.all():
            uids = [lead_hostel.pk]
            if m.assigned_to_id:
                uids.append(m.assigned_to_id)
            m.owners.set(list(dict.fromkeys(uids)))
        expense_gov.owners.set([lead_hostel, finance])
        expense_wifi_std.owners.set([lead_hostel, finance])
        expense_solar_pending.owners.set([lead_hostel, finance])

        _assign_program_milestone_owners(
            prog_demo,
            admin,
            gov_meera,
            lead_hostel,
            volunteer_riya,
            finance,
            hod_academic,
            hod_hostel,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "\n=== Seed complete (password demo123 unless noted) ===\n"
                "• demo — password demo (Foundation admin quick login)\n"
                "• hod_hostel — Create/edit hostel needs; matched need + project exist\n"
                "• hod_academic — Draft need (Wi-Fi phase 2)\n"
                "• lead_hostel — Boys hostel project + monthly milestones\n"
                "• volunteer_riya — On project team for hostel\n"
                "• donor_anita / donor_james — Contributions + July gala pledge/registration\n"
                "• gov_meera — Governance queue: research wing need, ISC project, large expense\n"
                "• finance1 — Record funding; approve standard expenses\n"
                "• auditor_kim — Read-only visibility\n"
                "• lead_career — Career center delivery project (no program FK)\n"
                "• admin — Full access\n\n"
                "Coverage: 10+ needs (draft/catalog/gov/matched), 5 projects (program FK + standalone), "
                "3 programs, 4 events (mixed FKs), pool-only contribution, multi-currency expenses.\n"
                "Open Events for gala + fireside + site visit + ISC draft.\n"
                "Programs: demo incubation, mentorship pilot, sustainability rollups.\n"
            )
        )
