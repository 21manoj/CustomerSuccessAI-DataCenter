"""Sync primary stakeholder_type, flags, and bulk persona import helpers."""

import csv
import io
import re
from typing import Iterable, List, Optional, Tuple

from django.contrib.auth import get_user_model

from apps.stakeholders.models import Organization, UserProfile, UserStakeholderPersona

User = get_user_model()

# Highest-privilege first (used for profile.stakeholder_type display / legacy single field)
PRIMARY_PERSONA_PRIORITY = (
    UserProfile.StakeholderType.FOUNDATION_ADMIN,
    UserProfile.StakeholderType.GOVERNANCE,
    UserProfile.StakeholderType.FINANCE_CONTROLLER,
    UserProfile.StakeholderType.AUDITOR,
    UserProfile.StakeholderType.HOD,
    UserProfile.StakeholderType.PROJECT_LEAD,
    UserProfile.StakeholderType.DONOR,
    UserProfile.StakeholderType.VOLUNTEER,
)

VALID_PERSONA_CODES = frozenset(c[0] for c in UserProfile.StakeholderType.choices)


def pick_primary_persona(codes: Iterable[str]) -> Optional[str]:
    s = set(codes)
    for p in PRIMARY_PERSONA_PRIORITY:
        if p in s:
            return p
    return next(iter(s), None) if s else None


def sync_primary_stakeholder_and_flag(user_id: int) -> None:
    """After persona rows change: set primary stakeholder_type and clear needs_persona_assignment when tagged."""
    user = User.objects.get(pk=user_id)
    prof = user.profile
    codes = list(user.stakeholder_personas.values_list("persona_type", flat=True))
    updates = []
    if codes and prof.needs_persona_assignment:
        prof.needs_persona_assignment = False
        updates.append("needs_persona_assignment")
    primary = pick_primary_persona(codes)
    if primary and prof.stakeholder_type != primary:
        prof.stakeholder_type = primary
        updates.append("stakeholder_type")
    if updates:
        prof.save(update_fields=updates)


def replace_user_personas(user, persona_types: list[str]) -> None:
    """Replace all persona links for user (may be empty)."""
    UserStakeholderPersona.objects.filter(user=user).delete()
    for p in persona_types:
        UserStakeholderPersona.objects.create(user=user, persona_type=p)
    sync_primary_stakeholder_and_flag(user.pk)


def parse_persona_cell(raw: str) -> Tuple[List[str], List[str]]:
    """
    Parse CSV cell into valid persona codes and unknown tokens.
    Separators: | , ; whitespace
    """
    if raw is None:
        return [], []
    s = (raw or "").strip()
    if not s:
        return [], []
    parts = re.split(r"[\s,|;]+", s, flags=re.IGNORECASE)
    valid = []
    unknown = []
    seen = set()
    for part in parts:
        t = part.strip().lower().replace(" ", "_")
        if not t:
            continue
        if t in VALID_PERSONA_CODES:
            if t not in seen:
                seen.add(t)
                valid.append(t)
        else:
            unknown.append(part.strip())
    return valid, unknown


def _norm_jurisdiction(raw: str) -> str:
    t = (raw or "").strip().lower()
    allowed = {c[0] for c in UserProfile.Jurisdiction.choices}
    if t in allowed:
        return t
    return UserProfile.Jurisdiction.INDIA


def apply_profile_bulk_rows(rows: List[dict]) -> dict:
    """
    rows: list of dicts with keys username, email, first_name, last_name, personas, organization, jurisdiction.
    Returns { "created": int, "updated": int, "errors": [str, ...], "warnings": [str, ...] }
    """
    created = updated = 0
    errors: list[str] = []
    warnings: list[str] = []

    for i, row in enumerate(rows, start=1):
        line = f"Row {i}"
        username = (row.get("username") or "").strip()
        email = (row.get("email") or "").strip()
        if not username:
            errors.append(f"{line}: missing username")
            continue
        if not email:
            errors.append(f"{line}: missing email for {username!r}")
            continue

        personas_raw = row.get("personas") or ""
        valid_personas, unknown = parse_persona_cell(personas_raw)
        if unknown:
            warnings.append(f"{line} ({username}): unknown persona token(s): {', '.join(unknown)}")

        org_name = (row.get("organization") or "").strip()
        org = None
        if org_name:
            org, _ = Organization.objects.get_or_create(
                name=org_name,
                defaults={
                    "org_type": Organization.OrgType.DEPARTMENT,
                    "jurisdiction": Organization.Jurisdiction.INDIA,
                },
            )

        jurisdiction = _norm_jurisdiction(row.get("jurisdiction"))

        fn = (row.get("first_name") or "").strip()
        ln = (row.get("last_name") or "").strip()

        existing = User.objects.filter(username__iexact=username).first()
        if existing:
            u = existing
            if email and u.email.lower() != email.lower():
                errors.append(f"{line}: username {username!r} exists with different email")
                continue
            u.email = email or u.email
            u.first_name = fn or u.first_name
            u.last_name = ln or u.last_name
            u.save()
            updated += 1
        else:
            email_taken = User.objects.filter(email__iexact=email).exclude(username__iexact=username).exists()
            if email_taken:
                errors.append(f"{line}: email {email!r} already used by another username")
                continue
            u = User.objects.create(username=username, email=email, first_name=fn, last_name=ln)
            u.set_unusable_password()
            u.save()
            created += 1

        prof = u.profile
        prof.organization = org if org else prof.organization
        prof.jurisdiction = jurisdiction
        if valid_personas:
            prof.needs_persona_assignment = False
            prof.save(update_fields=["organization", "jurisdiction", "needs_persona_assignment"])
            replace_user_personas(u, valid_personas)
        else:
            UserStakeholderPersona.objects.filter(user=u).delete()
            prof.needs_persona_assignment = True
            prof.stakeholder_type = UserProfile.StakeholderType.VOLUNTEER
            prof.save(update_fields=["organization", "jurisdiction", "needs_persona_assignment", "stakeholder_type"])

    return {"created": created, "updated": updated, "errors": errors, "warnings": warnings}


def parse_profile_upload_csv(file_obj) -> Tuple[Optional[List[dict]], Optional[str]]:
    """Read uploaded file; return (rows, error_message)."""
    try:
        raw = file_obj.read()
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = raw
    except UnicodeDecodeError:
        return None, "File must be UTF-8 encoded."

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return None, "CSV has no header row."

    fields_lower = {f.strip().lower(): f for f in reader.fieldnames if f}
    required_aliases = {
        "username": ["username", "user", "login"],
        "email": ["email", "e-mail"],
    }
    col_map = {}
    for canonical, aliases in required_aliases.items():
        for a in aliases:
            if a in fields_lower:
                col_map[canonical] = fields_lower[a]
                break
        else:
            return None, f"Missing required column: {canonical} (expected one of {aliases})"

    optional = {
        "first_name": ["first_name", "firstname", "given"],
        "last_name": ["last_name", "lastname", "family", "surname"],
        "personas": ["personas", "persona", "roles", "stakeholder_types"],
        "organization": ["organization", "org", "department"],
        "jurisdiction": ["jurisdiction", "region"],
    }
    for canonical, aliases in optional.items():
        for a in aliases:
            if a in fields_lower:
                col_map[canonical] = fields_lower[a]
                break

    rows = []
    for r in reader:
        row = {k: (r.get(col_map[k]) or "").strip() if k in col_map else "" for k in col_map}
        rows.append(row)
    return rows, None


def sample_csv_text() -> str:
    header = "username,email,first_name,last_name,personas,organization,jurisdiction"
    example1 = "jdoe,jane.doe@example.com,Jane,Doe,donor|volunteer,Alumni Council,india"
    example2 = "rsmith,rob@example.com,Rob,Smith,,Operations,us"
    return "\n".join([header, example1, example2])
