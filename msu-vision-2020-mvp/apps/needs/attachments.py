import os
import uuid

from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

ALLOWED_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xlsx"})
# Architecture: keep MVP limit explicit; raise in deployment if needed
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024


def need_attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ""
    return f"need_attachments/{instance.need_id}/{uuid.uuid4().hex}{ext}"


def validate_need_attachment_file(f):
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


def validate_need_attachment_files(file_list):
    for f in file_list:
        validate_need_attachment_file(f)


def save_need_attachments(need, file_list, user):
    from apps.needs.models import NeedAttachment

    count = 0
    for f in file_list:
        validate_need_attachment_file(f)
        safe = get_valid_filename(os.path.basename(f.name))
        NeedAttachment.objects.create(need=need, file=f, uploaded_by=user, original_filename=safe or "document")
        count += 1
    return count
