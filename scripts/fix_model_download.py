#!/usr/bin/env python3
"""
Fix Model Download Script
Diagnoses and fixes the inswapper_128.onnx model download issue
"""

import os
import sys
import hashlib
from pathlib import Path

# Expected model file info
EXPECTED_MODEL_SIZE = 554950545  # ~529 MB
EXPECTED_MD5 = "e4a3f08c753cb72d04e10aa0f7dbe153"  # InsightFace inswapper_128.onnx
MODEL_PATH = Path(__file__).parent.parent / "backend" / "models" / "inswapper_128.onnx"

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")

def calculate_md5(file_path):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return None

def diagnose_model():
    """Diagnose the model file"""
    print_header("Model File Diagnosis")

    print(f"📍 Model Path: {MODEL_PATH}")

    # Check if file exists
    if not MODEL_PATH.exists():
        print("❌ Model file does NOT exist")
        return False

    print("✓ Model file exists")

    # Check file size
    file_size = MODEL_PATH.stat().st_size
    print(f"📊 File Size: {file_size:,} bytes ({file_size / 1024 / 1024:.2f} MB)")

    if file_size == 0:
        print("❌ PROBLEM: File is EMPTY (0 bytes)")
        print("   This is why you're getting the INVALID_PROTOBUF error")
        return False

    if file_size < EXPECTED_MODEL_SIZE * 0.9:
        print(f"⚠️  WARNING: File size is smaller than expected")
        print(f"   Expected: ~{EXPECTED_MODEL_SIZE / 1024 / 1024:.2f} MB")
        print(f"   Actual: {file_size / 1024 / 1024:.2f} MB")
        return False

    print(f"✓ File size looks good ({file_size / 1024 / 1024:.2f} MB)")

    # Calculate MD5 (for files > 0)
    if file_size > 0:
        print("\n🔍 Calculating MD5 checksum (this may take a moment)...")
        md5 = calculate_md5(MODEL_PATH)
        if md5:
            print(f"   MD5: {md5}")
            # Note: We're not strictly validating MD5 as there might be different versions
            # but we can use it to verify the file is not corrupted
        else:
            print("⚠️  Could not calculate MD5")

    return True

def print_download_instructions():
    """Print instructions for downloading the model"""
    print_header("How to Download inswapper_128.onnx")

    print("""
The inswapper_128.onnx model needs to be downloaded manually.

📦 OPTION 1: Download from Hugging Face (RECOMMENDED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Visit: https://huggingface.co/deepinsight/inswapper/tree/main

2. Download the file: inswapper_128.onnx (~529 MB)

3. Move it to your models directory:
   {model_dir}

   macOS/Linux command:
   mv ~/Downloads/inswapper_128.onnx {model_path}


📦 OPTION 2: Download from Google Drive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Visit the InsightFace Google Drive (search for "inswapper_128.onnx")

2. Download the file

3. Move to: {model_path}


📦 OPTION 3: Use wget with authentication token
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

wget --header="Authorization: Bearer YOUR_HF_TOKEN" \\
  https://huggingface.co/deepinsight/inswapper/resolve/main/inswapper_128.onnx \\
  -O {model_path}

(Requires Hugging Face account and access token)


✅ After Download - Verify the file:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run this script again to verify:
python scripts/fix_model_download.py

Expected file size: ~529 MB (554,950,545 bytes)

""".format(
        model_dir=MODEL_PATH.parent,
        model_path=MODEL_PATH
    ))

def main():
    """Main function"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "     InsightFace Model Download Fix Script".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    # Diagnose
    is_valid = diagnose_model()

    if not is_valid:
        print_download_instructions()
        print("\n❌ Model file needs to be downloaded or replaced\n")
        sys.exit(1)
    else:
        print_header("✅ Model File is Valid")
        print("Your inswapper_128.onnx model appears to be valid!")
        print("\nYou can now run:")
        print("  python scripts/validate_algorithm.py")
        print()
        sys.exit(0)

if __name__ == "__main__":
    main()
