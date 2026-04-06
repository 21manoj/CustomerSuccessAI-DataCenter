import os
import uuid

from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

ALLOWED_EXTENSIONS = frozenset({".pdf", ".doc", ".docx", ".xlsx", ".jpg", ".jpeg", ".png"})
MAX_BYTES = 25 * 1024 * 1024


def program_stage_attachment_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ""
    return f"program_stage_attachments/{instance.stage_id}/{uuid.uuid4().hex}{ext}"


def validate_stage_attachment_file(f):
    if not f:
        return
    name = (f.name or "").lower()
    ext = os.path.splitext(name)[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File type not allowed: {ext or '(none)'}. Use PDF, Word, Excel, or image (jpg, png)."
        )
    if f.size > MAX_BYTES:
        raise ValidationError(f"File too large (max {MAX_BYTES // (1024 * 1024)} MB).")


def safe_original_name(f):
    return get_valid_filename(os.path.basename(f.name)) or "document"
