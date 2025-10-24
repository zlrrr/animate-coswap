"""
Algorithm Validation Script

This script validates the face-swap algorithm with various test cases.
Run this during Phase 0 to ensure the algorithm meets quality requirements.

Usage:
    python scripts/validate_algorithm.py

Requirements:
    - InsightFace models downloaded to backend/models/
    - Test fixtures in tests/fixtures/
"""

import sys
import os
import time
import cv2
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from app.services.faceswap.core import FaceSwapper, INSIGHTFACE_AVAILABLE
except ImportError as e:
    print(f"Error importing FaceSwapper: {e}")
    print("Make sure backend dependencies are installed:")
    print("  cd backend && pip install -r requirements.txt")
    sys.exit(1)


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def print_test_result(test_name, passed, details=""):
    """Print test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"       {details}")


def validate_environment():
    """Validate that environment is set up correctly"""
    print_header("Phase 0: Environment Validation")

    tests_passed = 0
    total_tests = 3

    # Test 1: Check Python version
    python_version = sys.version_info
    python_ok = python_version >= (3, 10)
    print_test_result(
        "Python 3.10+ installed",
        python_ok,
        f"Current: {python_version.major}.{python_version.minor}.{python_version.micro}"
    )
    if python_ok:
        tests_passed += 1

    # Test 2: Check InsightFace availability
    print_test_result(
        "InsightFace library available",
        INSIGHTFACE_AVAILABLE,
        "Run: pip install insightface onnxruntime" if not INSIGHTFACE_AVAILABLE else ""
    )
    if INSIGHTFACE_AVAILABLE:
        tests_passed += 1

    # Test 3: Check model file
    model_path = backend_path / "models" / "inswapper_128.onnx"
    model_exists = model_path.exists()
    print_test_result(
        "inswapper_128.onnx model downloaded",
        model_exists,
        f"Path: {model_path}" if model_exists else "Download from: https://huggingface.co/ezioruan/inswapper_128.onnx"
    )
    if model_exists:
        tests_passed += 1

    print(f"\nEnvironment Tests: {tests_passed}/{total_tests} passed")

    return tests_passed == total_tests, model_path if model_exists else None


def validate_algorithm(model_path):
    """Validate face-swap algorithm with test cases"""
    print_header("Phase 0: Algorithm Validation")

    if not INSIGHTFACE_AVAILABLE:
        print("InsightFace not available. Skipping algorithm tests.")
        return False

    try:
        # Initialize swapper (use CPU for compatibility)
        print("\nInitializing FaceSwapper...")
        start_time = time.time()
        swapper = FaceSwapper(model_path=str(model_path), use_gpu=False)
        init_time = time.time() - start_time
        print(f"✓ Initialization completed in {init_time:.2f}s")

    except Exception as e:
        print(f"✗ Failed to initialize FaceSwapper: {e}")
        return False

    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"

    # Test cases as defined in PLAN.md
    test_cases = [
        ("High-quality frontal face", "person_a.jpg", "person_b.jpg"),
        ("Side-angle faces", "side_angle_a.jpg", "side_angle_b.jpg"),
        ("Multiple faces", "couple.jpg", "couple_template.jpg"),
        ("Low-resolution images", "low_res_a.jpg", "low_res_b.jpg"),
        ("Anime/ACG style", "anime_a.png", "anime_b.png"),
        ("Faces with glasses", "glasses_a.jpg", "glasses_b.jpg"),
        ("Different lighting", "dark_a.jpg", "bright_b.jpg"),
        ("Age/gender variations", "old_a.jpg", "young_b.jpg"),
        ("Facial expressions", "smile_a.jpg", "serious_b.jpg"),
        ("Group photos", "group_a.jpg", "group_b.jpg"),
    ]

    print("\nRunning test cases...")
    print("Note: Tests will be skipped if fixture images are not available.\n")

    passed_tests = 0
    total_tests = 0
    processing_times = []

    for test_name, source_img, target_img in test_cases:
        source_path = fixtures_dir / source_img
        target_path = fixtures_dir / target_img

        # Skip if fixtures don't exist
        if not (source_path.exists() and target_path.exists()):
            print(f"⊘ SKIP | {test_name} (fixtures not found)")
            continue

        total_tests += 1

        try:
            # Perform face swap
            start_time = time.time()
            result = swapper.swap_faces(str(source_path), str(target_path))
            elapsed_time = time.time() - start_time
            processing_times.append(elapsed_time)

            # Validate result
            if result is not None and result.shape[0] > 0:
                print_test_result(
                    test_name,
                    True,
                    f"Processing time: {elapsed_time:.2f}s"
                )
                passed_tests += 1

                # Save result for visual inspection
                output_dir = Path(__file__).parent.parent / "tests" / "validation_results"
                output_dir.mkdir(exist_ok=True)
                output_path = output_dir / f"result_{test_name.replace(' ', '_').lower()}.jpg"
                cv2.imwrite(str(output_path), result)

            else:
                print_test_result(test_name, False, "Invalid result")

        except Exception as e:
            print_test_result(test_name, False, f"Error: {str(e)}")

    # Summary
    print("\n" + "-" * 70)
    print(f"Algorithm Validation: {passed_tests}/{total_tests} tests passed")

    if processing_times:
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        min_time = min(processing_times)
        print(f"\nProcessing Time Statistics:")
        print(f"  Average: {avg_time:.2f}s")
        print(f"  Min:     {min_time:.2f}s")
        print(f"  Max:     {max_time:.2f}s")

        # Check performance requirement
        perf_requirement = avg_time < 10.0  # < 10s for CPU, < 5s for GPU
        print(f"\nPerformance Requirement (< 10s avg): {'✓ PASS' if perf_requirement else '✗ FAIL'}")

    # Check acceptance criteria
    acceptance_rate = passed_tests / total_tests if total_tests > 0 else 0
    acceptance_criteria = acceptance_rate >= 0.8  # 8/10 tests must pass

    print(f"\nAcceptance Criteria (>= 80% pass rate): {'✓ PASS' if acceptance_criteria else '✗ FAIL'}")
    print(f"  Pass rate: {acceptance_rate * 100:.1f}%")

    return acceptance_criteria


def main():
    """Main validation script"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║          Couple Face-Swap Algorithm Validation Script           ║
║                        Phase 0 Checkpoint                        ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
""")

    # Step 1: Validate environment
    env_ok, model_path = validate_environment()

    if not env_ok:
        print("\n" + "!" * 70)
        print("Environment validation failed. Please fix the issues above.")
        print("!" * 70)
        return 1

    # Step 2: Validate algorithm
    algo_ok = validate_algorithm(model_path)

    # Final summary
    print_header("Validation Summary")

    if env_ok and algo_ok:
        print("""
✓ All validations passed!

Next Steps:
1. Review validation results in tests/validation_results/
2. Manually verify visual quality (>= 4/5 rating)
3. If satisfied, commit Phase 0.1 checkpoint:
   git add .
   git commit -m "Phase 0.1: Face-swap algorithm validated with InsightFace"
   git tag checkpoint-0.1

4. Proceed to Phase 1: Backend MVP Development
""")
        return 0
    else:
        print("""
✗ Validation failed

Please address the issues above before proceeding to Phase 1.
Refer to docs/phase-0/algorithm-validation.md for troubleshooting.
""")
        return 1


if __name__ == "__main__":
    sys.exit(main())
