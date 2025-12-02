#!/usr/bin/env python3
"""
Secure File Handler
Provides safe file operations for user uploads with comprehensive security measures
"""

import os
import uuid
import hashlib
import shutil
from pathlib import Path
from werkzeug.utils import secure_filename
from typing import Optional, Tuple
import mimetypes

# Optional: python-magic for file type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    magic = None

class SecureFileHandler:
    """
    Secure file handler with multiple layers of protection:
    1. Path traversal prevention
    2. File type validation
    3. Size limits
    4. Isolated storage per customer/user
    5. Unique filenames
    6. Automatic cleanup
    """
    
    # Allowed file extensions (whitelist approach)
    ALLOWED_EXTENSIONS = {
        'xlsx', 'xls',  # Excel files
        'csv',          # CSV files
        'json',         # JSON files
        'pdf',          # PDF files (if needed)
    }
    
    # Maximum file size (16MB)
    MAX_FILE_SIZE = 16 * 1024 * 1024
    
    # MIME types that match allowed extensions
    ALLOWED_MIME_TYPES = {
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
        'text/csv',
        'application/json',
        'application/pdf',
    }
    
    def __init__(self, base_upload_dir: str = '/tmp/uploads', customer_id: Optional[int] = None):
        """
        Initialize secure file handler
        
        Args:
            base_upload_dir: Base directory for uploads (should be outside web root)
            customer_id: Customer ID for isolation (optional)
        """
        self.base_upload_dir = Path(base_upload_dir)
        self.customer_id = customer_id
        
        # Create base directory with secure permissions
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self.base_upload_dir, 0o700)  # rwx------
        
        # Create customer-specific subdirectory if customer_id provided
        if customer_id:
            self.upload_dir = self.base_upload_dir / f"customer_{customer_id}"
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(self.upload_dir, 0o700)
        else:
            self.upload_dir = self.base_upload_dir
    
    def is_allowed_filename(self, filename: str) -> bool:
        """
        Check if filename is allowed (whitelist approach)
        
        Args:
            filename: Original filename
            
        Returns:
            True if allowed, False otherwise
        """
        if not filename or '.' not in filename:
            return False
        
        ext = filename.rsplit('.', 1)[1].lower()
        return ext in self.ALLOWED_EXTENSIONS
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and other attacks
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Use werkzeug's secure_filename
        safe_name = secure_filename(filename)
        
        # Additional checks
        if not safe_name or safe_name == '':
            # Generate a safe default name
            safe_name = f"upload_{uuid.uuid4().hex[:8]}"
        
        # Remove any remaining path components
        safe_name = os.path.basename(safe_name)
        
        # Ensure it doesn't start with a dot (hidden files)
        if safe_name.startswith('.'):
            safe_name = safe_name[1:]
        
        return safe_name
    
    def generate_unique_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename to prevent collisions and overwrites
        
        Args:
            original_filename: Original filename
            
        Returns:
            Unique filename with UUID prefix
        """
        safe_name = self.sanitize_filename(original_filename)
        
        # Add UUID prefix to ensure uniqueness
        name, ext = os.path.splitext(safe_name)
        unique_name = f"{uuid.uuid4().hex[:8]}_{name}{ext}"
        
        return unique_name
    
    def validate_file_type(self, file_path: str, original_filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate file type using multiple methods:
        1. Extension check
        2. MIME type check
        3. Magic number check (if python-magic available)
        
        Args:
            file_path: Path to uploaded file
            original_filename: Original filename
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check 1: Extension validation
        if not self.is_allowed_filename(original_filename):
            return False, f"File extension not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # Check 2: MIME type validation
        mime_type, _ = mimetypes.guess_type(original_filename)
        if mime_type and mime_type not in self.ALLOWED_MIME_TYPES:
            return False, f"MIME type '{mime_type}' not allowed"
        
        # Check 3: Magic number validation (if available)
        if MAGIC_AVAILABLE and magic:
            try:
                file_mime = magic.from_file(file_path, mime=True)
                if file_mime not in self.ALLOWED_MIME_TYPES:
                    return False, f"File content type '{file_mime}' does not match extension"
            except Exception as e:
                # Log but don't fail if magic check fails
                print(f"Warning: Magic number check failed: {e}")
        
        return True, None
    
    def validate_file_size(self, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Validate file size
        
        Args:
            file_size: File size in bytes
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return False, f"File size exceeds maximum allowed size of {max_mb}MB"
        
        if file_size == 0:
            return False, "File is empty"
        
        return True, None
    
    def save_file(self, file_obj, original_filename: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Safely save uploaded file with all security checks
        Supports both Flask file objects and file-like objects (BytesIO, etc.)
        
        Args:
            file_obj: File object from Flask request or file-like object
            original_filename: Original filename from upload
            
        Returns:
            Tuple of (saved_file_path, error_message)
        """
        # Step 1: Validate filename
        if not self.is_allowed_filename(original_filename):
            return None, f"File extension not allowed. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # Step 2: Generate unique, safe filename
        unique_filename = self.generate_unique_filename(original_filename)
        file_path = self.upload_dir / unique_filename
        
        # Step 3: Prevent path traversal (double-check)
        try:
            file_path.resolve().relative_to(self.upload_dir.resolve())
        except ValueError:
            return None, "Invalid file path - path traversal detected"
        
        # Step 4: Save file temporarily first
        temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
        try:
            # Handle both Flask file objects (with .save()) and file-like objects
            if hasattr(file_obj, 'save'):
                # Flask file object
                file_obj.save(str(temp_path))
            else:
                # File-like object (BytesIO, etc.)
                # Reset to beginning if it's a stream
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
                # Read and write
                with open(temp_path, 'wb') as f:
                    if hasattr(file_obj, 'read'):
                        shutil.copyfileobj(file_obj, f)
                    else:
                        f.write(file_obj)
        except Exception as e:
            return None, f"Failed to save file: {str(e)}"
        
        # Step 5: Validate file size
        file_size = temp_path.stat().st_size
        is_valid_size, size_error = self.validate_file_size(file_size)
        if not is_valid_size:
            temp_path.unlink()
            return None, size_error
        
        # Step 6: Validate file type
        is_valid_type, type_error = self.validate_file_type(str(temp_path), original_filename)
        if not is_valid_type:
            temp_path.unlink()
            return None, type_error
        
        # Step 7: Move temp file to final location with secure permissions
        try:
            temp_path.rename(file_path)
            os.chmod(file_path, 0o600)  # rw-------
        except Exception as e:
            temp_path.unlink()
            return None, f"Failed to finalize file: {str(e)}"
        
        return str(file_path), None
    
    def get_file_path(self, filename: str) -> Optional[str]:
        """
        Get full path to a saved file (with validation)
        
        Args:
            filename: Filename (can be with or without UUID prefix)
            
        Returns:
            Full file path or None if invalid
        """
        # Try exact match first (for UUID-prefixed files)
        file_path = self.upload_dir / filename
        
        # Prevent path traversal
        try:
            file_path.resolve().relative_to(self.upload_dir.resolve())
        except ValueError:
            return None
        
        if file_path.exists():
            return str(file_path)
        
        # If not found, try sanitized version (for backwards compatibility)
        safe_name = self.sanitize_filename(filename)
        if safe_name != filename:
            file_path = self.upload_dir / safe_name
            try:
                file_path.resolve().relative_to(self.upload_dir.resolve())
                if file_path.exists():
                    return str(file_path)
            except ValueError:
                pass
        
        return None
    
    def delete_file(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Safely delete a file
        
        Args:
            filename: Filename to delete
            
        Returns:
            Tuple of (success, error_message)
        """
        file_path = self.get_file_path(filename)
        if not file_path:
            return False, "File not found or invalid path"
        
        try:
            Path(file_path).unlink()
            return True, None
        except Exception as e:
            return False, f"Failed to delete file: {str(e)}"
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up files older than max_age_hours
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of files deleted
        """
        import time
        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for file_path in self.upload_dir.glob('*'):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass
        
        return deleted_count
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """
        Calculate SHA-256 hash of file for integrity checking
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA-256 hash or None if error
        """
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception:
            return None
    
    def list_files(self, subdirectory: Optional[str] = None) -> list:
        """
        List all files in the upload directory (for directory picker)
        
        Args:
            subdirectory: Optional subdirectory to list
            
        Returns:
            List of file info dicts with name, size, modified time
        """
        files = []
        target_dir = self.upload_dir
        
        if subdirectory:
            # Validate subdirectory to prevent path traversal
            safe_subdir = self.sanitize_filename(subdirectory)
            target_dir = self.upload_dir / safe_subdir
            # Double-check it's within upload_dir
            try:
                target_dir.resolve().relative_to(self.upload_dir.resolve())
            except ValueError:
                return []  # Invalid path
        
        if not target_dir.exists() or not target_dir.is_dir():
            return []
        
        for file_path in target_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'path': str(file_path.relative_to(self.upload_dir))
                })
        
        return sorted(files, key=lambda x: x['modified'], reverse=True)
    
    def list_directories(self) -> list:
        """
        List all subdirectories in the upload directory
        
        Returns:
            List of directory names
        """
        directories = []
        for item in self.upload_dir.iterdir():
            if item.is_dir():
                directories.append(item.name)
        return sorted(directories)
    
    def get_file_info(self, filename: str) -> Optional[dict]:
        """
        Get file information (size, modified time, hash)
        
        Args:
            filename: Filename to get info for
            
        Returns:
            File info dict or None if not found
        """
        file_path = self.get_file_path(filename)
        if not file_path:
            return None
        
        try:
            stat = Path(file_path).stat()
            return {
                'name': os.path.basename(file_path),
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'hash': self.get_file_hash(file_path),
                'path': file_path
            }
        except Exception:
            return None
    
    def read_file(self, filename: str) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Safely read a file for download
        
        Args:
            filename: Filename to read
            
        Returns:
            Tuple of (file_content, error_message)
        """
        file_path = self.get_file_path(filename)
        if not file_path:
            return None, "File not found or invalid path"
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return content, None
        except Exception as e:
            return None, f"Failed to read file: {str(e)}"
    
    def create_directory(self, dirname: str) -> Tuple[bool, Optional[str]]:
        """
        Create a subdirectory (for organizing files)
        
        Args:
            dirname: Directory name
            
        Returns:
            Tuple of (success, error_message)
        """
        safe_name = self.sanitize_filename(dirname)
        if not safe_name or safe_name == '':
            return False, "Invalid directory name"
        
        dir_path = self.upload_dir / safe_name
        
        # Prevent path traversal
        try:
            dir_path.resolve().relative_to(self.upload_dir.resolve())
        except ValueError:
            return False, "Invalid directory path - path traversal detected"
        
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            os.chmod(dir_path, 0o700)
            return True, None
        except Exception as e:
            return False, f"Failed to create directory: {str(e)}"


# Convenience function for Flask apps
def get_secure_file_handler(customer_id: Optional[int] = None, base_dir: Optional[str] = None) -> SecureFileHandler:
    """
    Get a SecureFileHandler instance configured for the current environment
    
    Args:
        customer_id: Customer ID for isolation
        base_dir: Base upload directory (defaults to /tmp/uploads)
        
    Returns:
        Configured SecureFileHandler instance
    """
    if base_dir is None:
        # Use environment variable or default
        base_dir = os.getenv('UPLOAD_FOLDER', '/tmp/uploads')
    
    return SecureFileHandler(base_upload_dir=base_dir, customer_id=customer_id)

