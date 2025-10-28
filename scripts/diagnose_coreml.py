#!/usr/bin/env python3
"""
CoreML Availability Diagnostic Script
Checks if CoreML Execution Provider is available for ONNX Runtime on macOS
"""

import sys
import platform
import subprocess

def print_header(title):
    """Print formatted header"""
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + f" {title} ".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

def print_section(title):
    """Print section header"""
    print("\n" + "─" * 70)
    print(f"  {title}")
    print("─" * 70)

def check_system_info():
    """Check basic system information"""
    print_section("System Information")

    system = platform.system()
    machine = platform.machine()
    python_version = platform.python_version()

    print(f"Operating System: {system}")
    print(f"Architecture: {machine}")
    print(f"Python Version: {python_version}")

    is_macos = system == "Darwin"
    is_arm64 = machine in ["arm64", "aarch64"]

    if is_macos and is_arm64:
        print("✅ Running on macOS Apple Silicon (ARM64)")

        # Check if running under Rosetta 2
        try:
            result = subprocess.run(
                ["sysctl", "-n", "sysctl.proc_translated"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip() == "1":
                print("⚠️  WARNING: Python is running under Rosetta 2!")
                print("   This will significantly reduce performance.")
                print("   Install ARM64 native Python instead.")
                return False
            else:
                print("✅ Python is running natively (not under Rosetta 2)")
        except Exception as e:
            print(f"⚠️  Could not determine Rosetta status: {e}")

    elif is_macos and not is_arm64:
        print("⚠️  Running on macOS but NOT ARM64 (likely Intel x86_64)")
        print("   CoreML Execution Provider may not be available")
        return False

    elif not is_macos:
        print("ℹ️  Not running on macOS")
        print("   CoreML Execution Provider is only available on macOS")
        return False

    return is_macos and is_arm64

def check_onnxruntime():
    """Check ONNX Runtime installation"""
    print_section("ONNX Runtime Installation")

    try:
        import onnxruntime as ort
        print(f"✅ ONNX Runtime is installed")
        print(f"   Version: {ort.__version__}")

        # Check available providers
        providers = ort.get_available_providers()
        print(f"\n📦 Available Execution Providers:")
        for provider in providers:
            print(f"   • {provider}")

        # Check for CoreML
        has_coreml = "CoreMLExecutionProvider" in providers

        if has_coreml:
            print("\n✅ CoreMLExecutionProvider IS available!")
            print("   Your ONNX models can use Apple Neural Engine acceleration")
        else:
            print("\n❌ CoreMLExecutionProvider is NOT available")
            print("\n   Possible reasons:")
            print("   1. Wrong onnxruntime version installed")
            print("   2. Not running on macOS ARM64")
            print("   3. Running under Rosetta 2")
            print("   4. onnxruntime built without CoreML support")

        return has_coreml

    except ImportError:
        print("❌ ONNX Runtime is NOT installed")
        print("\n   Install it with:")
        print("   pip install onnxruntime==1.16.3")
        return False

def check_package_source():
    """Check where onnxruntime was installed from"""
    print_section("Package Installation Source")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "onnxruntime"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print(result.stdout)

            # Check for multiple installations
            result2 = subprocess.run(
                [sys.executable, "-m", "pip", "list", "|", "grep", "onnx"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            if "onnxruntime-gpu" in result2.stdout or "onnxruntime-silicon" in result2.stdout:
                print("\n⚠️  WARNING: Multiple onnxruntime packages detected!")
                print("   You should ONLY have 'onnxruntime' installed, not:")
                print("   • onnxruntime-gpu (for NVIDIA CUDA)")
                print("   • onnxruntime-silicon (deprecated)")
                print("\n   Uninstall all and reinstall:")
                print("   pip uninstall onnxruntime onnxruntime-gpu onnxruntime-silicon -y")
                print("   pip install onnxruntime==1.16.3")
        else:
            print("❌ Could not find package information")

    except Exception as e:
        print(f"⚠️  Error checking package: {e}")

def provide_fix_instructions(has_coreml, is_correct_platform):
    """Provide instructions to fix CoreML issues"""
    print_section("Fix Instructions")

    if has_coreml and is_correct_platform:
        print("✅ Everything looks good! CoreML is available.")
        print("\n   Your models will use Apple Neural Engine acceleration.")
        print("   No action needed.")
        return

    if not is_correct_platform:
        print("❌ Platform Issue Detected")
        print("\n   CoreML requires macOS Apple Silicon (M1/M2/M3/M4)")
        print("\n   If you ARE on Apple Silicon Mac:")
        print("   1. Check you're using ARM64 native Python:")
        print("      python -c \"import platform; print(platform.machine())\"")
        print("      Should output: arm64")
        print("\n   2. If it shows 'x86_64', you're using Intel Python")
        print("      Install ARM64 Python from: https://www.python.org/downloads/macos/")
        print("\n   3. Create a new venv with ARM64 Python:")
        print("      /path/to/arm64/python3 -m venv venv")
        print("      source venv/bin/activate")
        print("      pip install -r backend/requirements-macos-m.txt")
        return

    if not has_coreml:
        print("❌ CoreML Not Available")
        print("\n   Step 1: Uninstall all onnxruntime packages")
        print("   ─────────────────────────────────────────")
        print("   pip uninstall onnxruntime onnxruntime-gpu onnxruntime-silicon -y")
        print("\n   Step 2: Reinstall correct version")
        print("   ──────────────────────────────────────")
        print("   pip install onnxruntime==1.16.3")
        print("\n   Step 3: Verify installation")
        print("   ───────────────────────────────")
        print("   python -c \"import onnxruntime; print(onnxruntime.get_available_providers())\"")
        print("\n   Expected output should include: 'CoreMLExecutionProvider'")
        print("\n   Step 4: Re-run this diagnostic")
        print("   ──────────────────────────────────")
        print("   python scripts/diagnose_coreml.py")

def main():
    """Main diagnostic function"""
    print_header("CoreML Execution Provider Diagnostic Tool")

    is_correct_platform = check_system_info()
    has_coreml = check_onnxruntime()
    check_package_source()
    provide_fix_instructions(has_coreml, is_correct_platform)

    print("\n" + "═" * 70)
    if has_coreml and is_correct_platform:
        print("✅ DIAGNOSTIC RESULT: CoreML is properly configured")
        print("═" * 70 + "\n")
        sys.exit(0)
    else:
        print("❌ DIAGNOSTIC RESULT: CoreML needs configuration")
        print("═" * 70 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
