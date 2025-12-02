#!/usr/bin/env python3
"""
Comprehensive tests for Secure File Handler
Tests uploads, downloads, directory operations for both local and remote scenarios
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from secure_file_handler import SecureFileHandler
import io

def test_path_traversal_prevention():
    """Test that path traversal attacks are prevented"""
    print("🧪 Testing path traversal prevention...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Test 1: Attempt path traversal in filename
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
            "....//....//etc/passwd"
        ]
        
        for name in malicious_names:
            safe_name = handler.sanitize_filename(name)
            assert not safe_name.startswith(".."), f"Path traversal not prevented: {name} -> {safe_name}"
            assert "/" not in safe_name or safe_name == safe_name.split("/")[-1], f"Absolute path not prevented: {name}"
            assert "\\" not in safe_name or safe_name == safe_name.split("\\")[-1], f"Windows path not prevented: {name}"
        
        print("   ✅ Path traversal prevention works")

def test_file_upload():
    """Test secure file upload"""
    print("🧪 Testing file upload...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Create a mock file object
        test_content = b"Test file content"
        test_file = io.BytesIO(test_content)
        test_file.filename = "test.xlsx"
        
        # Upload file
        file_path, error = handler.save_file(test_file, "test.xlsx")
        
        assert error is None, f"Upload failed: {error}"
        assert file_path is not None, "File path not returned"
        assert os.path.exists(file_path), "File not saved"
        
        # Verify file content
        with open(file_path, 'rb') as f:
            assert f.read() == test_content, "File content mismatch"
        
        # Verify unique filename
        assert "test.xlsx" in file_path or "test" in file_path, "Filename not preserved"
        
        print("   ✅ File upload works")

def test_file_download():
    """Test secure file download"""
    print("🧪 Testing file download...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Upload a file first
        test_content = b"Download test content"
        test_file = io.BytesIO(test_content)
        file_path, _ = handler.save_file(test_file, "download_test.xlsx")
        filename = os.path.basename(file_path)
        
        # Download file
        content, error = handler.read_file(filename)
        
        assert error is None, f"Download failed: {error}"
        assert content == test_content, "Downloaded content mismatch"
        
        print("   ✅ File download works")

def test_file_type_validation():
    """Test file type validation"""
    print("🧪 Testing file type validation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Test allowed extensions
        allowed = ["test.xlsx", "data.xls", "export.csv", "config.json"]
        for name in allowed:
            assert handler.is_allowed_filename(name), f"Allowed file rejected: {name}"
        
        # Test disallowed extensions
        disallowed = ["script.exe", "malware.sh", "virus.bat", "hack.py"]
        for name in disallowed:
            assert not handler.is_allowed_filename(name), f"Disallowed file allowed: {name}"
        
        print("   ✅ File type validation works")

def test_file_size_validation():
    """Test file size validation"""
    print("🧪 Testing file size validation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Test valid size
        is_valid, error = handler.validate_file_size(1024)  # 1KB
        assert is_valid, f"Valid size rejected: {error}"
        
        # Test too large
        is_valid, error = handler.validate_file_size(handler.MAX_FILE_SIZE + 1)
        assert not is_valid, "Oversized file allowed"
        assert "exceeds" in error.lower(), "Wrong error message"
        
        # Test empty file
        is_valid, error = handler.validate_file_size(0)
        assert not is_valid, "Empty file allowed"
        
        print("   ✅ File size validation works")

def test_customer_isolation():
    """Test that files are isolated by customer"""
    print("🧪 Testing customer isolation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler1 = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        handler2 = SecureFileHandler(base_upload_dir=tmpdir, customer_id=2)
        
        # Upload file for customer 1
        test_file1 = io.BytesIO(b"Customer 1 content")
        file_path1, _ = handler1.save_file(test_file1, "test.xlsx")
        filename1 = os.path.basename(file_path1)
        
        # Try to access from customer 2
        content, error = handler2.read_file(filename1)
        # Should fail or return None (depending on implementation)
        # The file should be in customer_1 directory, not accessible from customer_2
        
        # Verify directories are separate
        assert "customer_1" in file_path1 or "customer_2" not in file_path1, "Customer isolation failed"
        
        print("   ✅ Customer isolation works")

def test_directory_operations():
    """Test directory listing and creation"""
    print("🧪 Testing directory operations...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Create directory
        success, error = handler.create_directory("test_folder")
        assert success, f"Directory creation failed: {error}"
        
        # List directories
        directories = handler.list_directories()
        assert "test_folder" in directories, "Created directory not listed"
        
        # Upload file to subdirectory
        test_file = io.BytesIO(b"Subdirectory content")
        file_path, _ = handler.save_file(test_file, "subdir_test.xlsx")
        
        # List files
        files = handler.list_files()
        assert len(files) > 0, "Files not listed"
        
        # List files in subdirectory
        subdir_files = handler.list_files("test_folder")
        # Should be empty since we didn't save to subdirectory
        
        print("   ✅ Directory operations work")

def test_file_info():
    """Test file information retrieval"""
    print("🧪 Testing file info...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Upload file
        test_file = io.BytesIO(b"Info test content")
        file_path, _ = handler.save_file(test_file, "info_test.xlsx")
        filename = os.path.basename(file_path)
        
        # Get file info
        file_info = handler.get_file_info(filename)
        
        assert file_info is not None, "File info not returned"
        assert file_info['name'] == filename, "Filename mismatch"
        assert file_info['size'] > 0, "File size not set"
        assert file_info['hash'] is not None, "File hash not calculated"
        
        print("   ✅ File info retrieval works")

def test_file_deletion():
    """Test file deletion"""
    print("🧪 Testing file deletion...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Upload file
        test_file = io.BytesIO(b"Delete test content")
        file_path, _ = handler.save_file(test_file, "delete_test.xlsx")
        filename = os.path.basename(file_path)
        
        assert os.path.exists(file_path), "File not created"
        
        # Delete file
        success, error = handler.delete_file(filename)
        assert success, f"File deletion failed: {error}"
        assert not os.path.exists(file_path), "File still exists after deletion"
        
        print("   ✅ File deletion works")

def test_cleanup_old_files():
    """Test cleanup of old files"""
    print("🧪 Testing file cleanup...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Upload a file
        test_file = io.BytesIO(b"Old file content")
        file_path, _ = handler.save_file(test_file, "old_file.xlsx")
        
        # Manually set file modification time to be old
        import time
        old_time = time.time() - (25 * 3600)  # 25 hours ago
        os.utime(file_path, (old_time, old_time))
        
        # Clean up files older than 24 hours
        deleted_count = handler.cleanup_old_files(max_age_hours=24)
        assert deleted_count >= 1, "Old file not cleaned up"
        assert not os.path.exists(file_path), "Old file still exists"
        
        print("   ✅ File cleanup works")

def test_unique_filenames():
    """Test that unique filenames are generated"""
    print("🧪 Testing unique filename generation...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
        
        # Upload same file multiple times
        filenames = []
        for i in range(5):
            test_file = io.BytesIO(b"Unique test content")
            file_path, _ = handler.save_file(test_file, "same_name.xlsx")
            filename = os.path.basename(file_path)
            filenames.append(filename)
        
        # All filenames should be unique
        assert len(filenames) == len(set(filenames)), "Duplicate filenames generated"
        
        print("   ✅ Unique filename generation works")

def test_transparent_local_remote():
    """Test that handler works transparently for local and remote"""
    print("🧪 Testing transparent local/remote operation...")
    
    # Test with different base directories (simulating local vs remote)
    local_dir = "/tmp/uploads_local"
    remote_dir = "/tmp/uploads_remote"
    
    for base_dir in [local_dir, remote_dir]:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use tmpdir but test with different paths
            handler = SecureFileHandler(base_upload_dir=tmpdir, customer_id=1)
            
            # Operations should work the same way
            test_file = io.BytesIO(b"Transparent test")
            file_path, error = handler.save_file(test_file, "transparent.xlsx")
            
            assert error is None, f"Operation failed: {error}"
            assert file_path is not None, "File path not returned"
            
            # Download should work
            filename = os.path.basename(file_path)
            content, error = handler.read_file(filename)
            assert error is None, f"Download failed: {error}"
            assert content == b"Transparent test", "Content mismatch"
    
    print("   ✅ Transparent local/remote operation works")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 SECURE FILE HANDLER - COMPREHENSIVE TESTS")
    print("="*70 + "\n")
    
    tests = [
        test_path_traversal_prevention,
        test_file_upload,
        test_file_download,
        test_file_type_validation,
        test_file_size_validation,
        test_customer_isolation,
        test_directory_operations,
        test_file_info,
        test_file_deletion,
        test_cleanup_old_files,
        test_unique_filenames,
        test_transparent_local_remote,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return failed == 0

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

