import io
import os

import requests

BASE_URL = "http://localhost:8000"


def get_available_pdfs():
    pdf_files = [
        "pdfs/Rajkumar et al. - 2022 - Evaluating the Text-to-SQL Capabilities of Large L.pdf",
        "pdfs/Chang and Fosler-Lussier - 2023 - How to Prompt LLMs for Text-to-SQL A Study in Zer.pdf",
    ]

    # Check if files exist
    existing_files = []
    for pdf_file in pdf_files:
        if os.path.exists(pdf_file):
            existing_files.append(pdf_file)
        else:
            print(f"Warning: PDF file not found: {pdf_file}")

    return existing_files


def create_mock_pdf(filename="test_document.pdf"):
    # Simple PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 24 Tf
100 700 Td
(Test Document) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000173 00000 n
0000000301 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""

    return filename, io.BytesIO(pdf_content)


def test_single_file_upload():
    """Test uploading a single PDF file"""
    print("📁 Testing Single File Upload...")

    try:
        available_pdfs = get_available_pdfs()

        if available_pdfs:
            # Use the first available real PDF
            pdf_path = available_pdfs[0]
            filename = os.path.basename(pdf_path)

            print(f"   Using real PDF: {filename}")

            with open(pdf_path, "rb") as f:
                files = {"files": (filename, f, "application/pdf")}

                response = requests.post(f"{BASE_URL}/api/upload", files=files)
                response.raise_for_status()
        else:
            # Fallback to mock PDF
            print("   Using mock PDF (real PDFs not found)")
            filename, file_content = create_mock_pdf("single_test.pdf")

            files = {"files": (filename, file_content, "application/pdf")}

            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            response.raise_for_status()

        data = response.json()
        print(f"✅ Upload successful: {data['message']}")
        print(f"   Files uploaded: {len(data['files'])}")

        for file_info in data["files"]:
            print(f"- {file_info['filename']} ({file_info['size']} bytes)")
            print(f"  ID: {file_info['id']}")
            print(f"  Upload time: {file_info['upload_time']}")

        assert len(data["files"]) == 1
        return data

    except Exception as e:
        print(f"❌ Single file upload failed: {e}")
        return None


def test_multiple_file_upload():
    """Test uploading multiple PDF files"""
    print("\n📁 Testing Multiple File Upload...")

    try:
        available_pdfs = get_available_pdfs()

        if len(available_pdfs) >= 2:
            # Use both real PDFs
            print(f"   Using {len(available_pdfs)} real PDFs")

            files = []
            for pdf_path in available_pdfs:
                filename = os.path.basename(pdf_path)
                with open(pdf_path, "rb") as f:
                    files.append(("files", (filename, f.read(), "application/pdf")))

            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            response.raise_for_status()
            expected_count = len(available_pdfs)

        elif len(available_pdfs) == 1:
            # Use one real PDF and create mock PDFs
            print("   Using 1 real PDF + 2 mock PDFs")
            pdf_path = available_pdfs[0]
            filename1 = os.path.basename(pdf_path)

            file2_name, file2_content = create_mock_pdf("document2.pdf")
            file3_name, file3_content = create_mock_pdf("report.pdf")

            with open(pdf_path, "rb") as f:
                files = [
                    ("files", (filename1, f, "application/pdf")),
                    ("files", (file2_name, file2_content, "application/pdf")),
                    ("files", (file3_name, file3_content, "application/pdf")),
                ]

            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            response.raise_for_status()
            expected_count = 3

        else:
            # Fallback to all mock PDFs
            print("   Using mock PDFs (real PDFs not found)")
            file1_name, file1_content = create_mock_pdf("document1.pdf")
            file2_name, file2_content = create_mock_pdf("document2.pdf")
            file3_name, file3_content = create_mock_pdf("report.pdf")

            files = [
                ("files", (file1_name, file1_content, "application/pdf")),
                ("files", (file2_name, file2_content, "application/pdf")),
                ("files", (file3_name, file3_content, "application/pdf")),
            ]

            response = requests.post(f"{BASE_URL}/api/upload", files=files)
            response.raise_for_status()
            expected_count = 3

        data = response.json()
        print(f"✅ Upload successful: {data['message']}")
        print(f"   Files uploaded: {len(data['files'])}")

        total_size = 0
        for file_info in data["files"]:
            print(f"- {file_info['filename']} ({file_info['size']} bytes)")
            total_size += file_info["size"]

        print(f"   Total size: {total_size} bytes")

        assert len(data["files"]) == expected_count
        return data

    except Exception as e:
        print(f"❌ Multiple file upload failed: {e}")
        return None


def test_invalid_file_upload():
    print("\n📁 Testing Invalid File Upload...")

    try:
        # Create a text file instead of PDF
        text_content = b"This is not a PDF file"
        files = {"files": ("test.txt", io.BytesIO(text_content), "text/plain")}

        response = requests.post(f"{BASE_URL}/api/upload", files=files)

        if response.status_code == 400:
            error_data = response.json()
            print(f"✅ Invalid file correctly rejected: {error_data['detail']}")
            return True
        else:
            print("❌ Invalid file was accepted (should have been rejected)")
            return False

    except Exception as e:
        print(f"❌ Invalid file test failed: {e}")
        return False


def test_empty_upload():
    """Test uploading with no files (should fail)"""
    print("\n📁 Testing Empty Upload...")

    try:
        response = requests.post(f"{BASE_URL}/api/upload")

        if response.status_code == 422:  # FastAPI validation error
            print("✅ Empty upload correctly rejected")
            return True
        else:
            print("❌ Empty upload was accepted (should have been rejected)")
            return False

    except Exception as e:
        print(f"❌ Empty upload test failed: {e}")
        return False


def main():
    print("🧪 Testing File Upload Endpoints")
    print("=" * 50)

    single_result = test_single_file_upload()
    multiple_result = test_multiple_file_upload()
    invalid_result = test_invalid_file_upload()
    empty_result = test_empty_upload()

    print("\n" + "=" * 50)
    if single_result and multiple_result and invalid_result and empty_result:
        print("🎉 All upload tests passed!")
        print("📄 PDF files uploaded successfully")
        print("🛡️ Invalid uploads properly rejected")
    else:
        print("❌ Some upload tests failed.")


if __name__ == "__main__":
    main()
