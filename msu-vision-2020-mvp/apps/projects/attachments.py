import os
import uuid

from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

ALLOWED_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xlsx"})
MILESTONE_PROOF_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"})
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
MAX_MILESTONE_PROOF_BYTES = MAX_ATTACHMENT_BYTES


def milestone_proof_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in MILESTONE_PROOF_EXTENSIONS:
        ext = ""
    sid = instance.pk or uuid.uuid4().hex[:8]
    return f"milestone_proofs/{instance.project_id}/{sid}/{uuid.uuid4().hex}{ext}"


def validate_milestone_proof_file(f):
    if not f:
        return
    name = (f.name or "").lower()
    ext = os.path.splitext(name)[1]
    if ext not in MILESTONE_PROOF_EXTENSIONS:
        raise ValidationError(
            f"Proof file type not allowed: {ext or '(none)'}. Use PDF, Word, Excel, or image (jpg, png)."
        )
    if f.size > MAX_MILESTONE_PROOF_BYTES:
        raise ValidationError(f"File too large (max {MAX_MILESTONE_PROOF_BYTES // (1024 * 1024)} MB).")


def project_attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ""
    return f"project_attachments/{instance.project_id}/{uuid.uuid4().hex}{ext}"


def validate_project_attachment_file(f):
    if not f:
        return
    name = (f.name or "").lower()
    ext = os.path.splitext(name)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type not allowed: {ext or '(none)'}. Use PDF, Word (.doc, .docx), or Excel (.xlsx)."
        )
    if f.size > MAX_ATTACHMENT_BYTES:
        raise ValidationError(f"File too large (max {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB).")


def validate_project_attachment_files(file_list):
    for f in file_list:
        validate_project_attachment_file(f)


def save_project_attachments(project, file_list, user):
    from apps.projects.models import ProjectAttachment

    count = 0
    for f in file_list:
        validate_project_attachment_file(f)
        safe = get_valid_filename(os.path.basename(f.name))
        ProjectAttachment.objects.create(
            project=project, file=f, uploaded_by=user, original_filename=safe or "document"
        )
        count += 1
    return count
