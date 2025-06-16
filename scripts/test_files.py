import io

import requests

BASE_URL = "http://localhost:8000"


def create_mock_pdf(filename="test_file.pdf"):
    """Create a mock PDF for testing"""
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
xref
0 4
0000000000 65535 f
0000000010 00000 n
0000000053 00000 n
0000000100 00000 n
trailer<</Size 4/Root 1 0 R>>
startxref
149
%%EOF"""
    return filename, io.BytesIO(pdf_content)


def upload_test_files():
    """Upload some test files to work with"""
    print("📤 Uploading test files first...")

    try:
        file1_name, file1_content = create_mock_pdf("research_paper.pdf")
        file2_name, file2_content = create_mock_pdf("report_2024.pdf")
        file3_name, file3_content = create_mock_pdf("manual.pdf")

        files = [
            ("files", (file1_name, file1_content, "application/pdf")),
            ("files", (file2_name, file2_content, "application/pdf")),
            ("files", (file3_name, file3_content, "application/pdf")),
        ]

        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        response.raise_for_status()

        data = response.json()
        print(f"✅ Test files uploaded: {len(data['files'])} files")
        return True

    except Exception as e:
        print(f"❌ Failed to upload test files: {e}")
        return False


def test_get_files():
    """Test getting all files information"""
    print("\n📁 Testing Get Files Endpoint...")

    try:
        response = requests.get(f"{BASE_URL}/api/files")
        response.raise_for_status()

        data = response.json()
        print("✅ Files information retrieved")
        print(f"   Total files: {data['total_files']}")
        print(f"   Total size: {data['total_size_bytes']} bytes")
        print(
            f"   Average size: {data['total_size_bytes'] // max(1, data['total_files'])} bytes/file"
        )

        print("\n   File details:")
        for i, file_info in enumerate(data["files"]):
            print(f"   {i+1}. {file_info['filename']}")
            print(f"      Size: {file_info['size']} bytes")
            print(f"      ID: {file_info['id']}")
            print(f"      Uploaded: {file_info['upload_time']}")

        assert "files" in data
        assert "total_files" in data
        assert "total_size_bytes" in data
        assert len(data["files"]) == data["total_files"]

        # Verify size calculation
        calculated_size = sum(f["size"] for f in data["files"])
        assert calculated_size == data["total_size_bytes"]

        return data

    except Exception as e:
        print(f"❌ Get files failed: {e}")
        return None


def test_files_empty_state():
    print("\n📁 Testing Files Endpoint (Empty State)...")

    try:
        # First, reset to clear any files
        requests.post(f"{BASE_URL}/api/reset")

        response = requests.get(f"{BASE_URL}/api/files")
        response.raise_for_status()

        data = response.json()
        print("✅ Empty files state retrieved")
        print(f"   Total files: {data['total_files']}")
        print(f"   Total size: {data['total_size_bytes']} bytes")

        assert data["total_files"] == 0
        assert data["total_size_bytes"] == 0
        assert len(data["files"]) == 0

        return True

    except Exception as e:
        print(f"❌ Empty files test failed: {e}")
        return False


def test_files_after_multiple_uploads():
    """Test files endpoint after multiple separate uploads"""
    print("\n📁 Testing Files After Multiple Uploads...")

    try:
        # Upload files in separate requests
        uploads = [
            ("first_doc.pdf", "First upload batch"),
            ("second_doc.pdf", "Second upload batch"),
            ("third_doc.pdf", "Third upload batch"),
        ]

        upload_count = 0
        for filename, description in uploads:
            print(f"   Uploading {filename}...")
            file_name, file_content = create_mock_pdf(filename)

            files = {"files": (file_name, file_content, "application/pdf")}

            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            response.raise_for_status()
            upload_count += 1

        # Now check files endpoint
        response = requests.get(f"{BASE_URL}/api/files")
        response.raise_for_status()

        data = response.json()
        print("✅ Files after multiple uploads:")
        print(f"   Total files: {data['total_files']}")
        print(f"   Expected files: {upload_count}")

        assert data["total_files"] >= upload_count

        uploaded_filenames = [f["filename"] for f in data["files"]]
        for filename, _ in uploads:
            assert filename in uploaded_filenames, f"File {filename} not found"

        return data

    except Exception as e:
        print(f"❌ Multiple uploads test failed: {e}")
        return None


def test_file_metadata_validation():
    print("\n📁 Testing File Metadata Validation...")

    try:
        response = requests.get(f"{BASE_URL}/api/files")
        response.raise_for_status()

        data = response.json()

        if data["total_files"] == 0:
            print("⚠️ No files to validate metadata - uploading test file")
            upload_test_files()
            response = requests.get(f"{BASE_URL}/api/files")
            data = response.json()

        required_fields = ["filename", "size", "upload_time", "id"]

        for file_info in data["files"]:
            for field in required_fields:
                assert field in file_info, f"Missing field {field} in file metadata"

            # Validate data types
            assert isinstance(file_info["filename"], str)
            assert isinstance(file_info["size"], int)
            assert isinstance(file_info["upload_time"], str)
            assert isinstance(file_info["id"], str)

            # Validate size is positive
            assert (
                file_info["size"] > 0
            ), f"File size should be positive: {file_info['size']}"

        print(f"✅ All {len(data['files'])} files have valid metadata")
        return True

    except Exception as e:
        print(f"❌ Metadata validation failed: {e}")
        return False


def main():
    print("🧪 Testing Files Endpoint")
    print("=" * 50)

    # Test empty state first
    empty_test = test_files_empty_state()

    # Upload test files
    upload_success = upload_test_files()
    if not upload_success:
        print("❌ Cannot continue without uploaded files")
        return

    # Test getting files info
    files_result = test_get_files()

    # Test multiple uploads
    multiple_uploads = test_files_after_multiple_uploads()

    # Test metadata validation
    metadata_test = test_file_metadata_validation()

    print("\n" + "=" * 50)
    if all([empty_test, upload_success, files_result, multiple_uploads, metadata_test]):
        print("🎉 All files endpoint tests passed!")
        print("📁 Files information retrieved successfully")
        print("✅ Metadata validation passed")
        print("📊 Size calculations verified")
    else:
        print("❌ Some files tests failed.")


if __name__ == "__main__":
    main()
