#!/usr/bin/env python3
"""
Platform Detection Script
Detects the current platform and recommends the appropriate requirements file.
"""

import platform
import sys
import subprocess
import os


def detect_platform():
    """Detect operating system and architecture"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    return {
        'system': system,
        'machine': machine,
        'python_version': platform.python_version(),
        'is_64bit': sys.maxsize > 2**32
    }


def check_cuda():
    """Check if NVIDIA CUDA is available"""
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
        if result.returncode == 0:
            # Parse CUDA version from nvidia-smi output
            for line in result.stdout.split('\n'):
                if 'CUDA Version' in line:
                    return True, line.strip()
            return True, "CUDA available (version unknown)"
        return False, None
    except FileNotFoundError:
        return False, None


def detect_apple_silicon():
    """Check if running on Apple Silicon"""
    if platform.system().lower() == 'darwin':
        machine = platform.machine().lower()
        return machine in ['arm64', 'aarch64']
    return False


def check_rosetta():
    """Check if running under Rosetta 2 on macOS"""
    if platform.system().lower() == 'darwin':
        try:
            # Check sysctl to see if running under Rosetta
            result = subprocess.run(
                ['sysctl', '-n', 'sysctl.proc_translated'],
                capture_output=True,
                text=True
            )
            return result.stdout.strip() == '1'
        except:
            pass
    return False


def get_recommended_requirements():
    """Get recommended requirements file based on platform"""
    info = detect_platform()
    system = info['system']
    machine = info['machine']

    # macOS Apple Silicon
    if system == 'darwin' and machine in ['arm64', 'aarch64']:
        if check_rosetta():
            return 'requirements-macos-m.txt', 'warning', \
                   '⚠️  WARNING: Python is running under Rosetta 2! ' \
                   'Performance will be slower. Install ARM64 native Python.'
        return 'requirements-macos-m.txt', 'success', \
               '✓ Apple Silicon detected (M1/M2/M3/M4)'

    # macOS Intel
    elif system == 'darwin' and machine == 'x86_64':
        return 'requirements-linux-x86.txt', 'info', \
               'ℹ️  Intel Mac detected (using Linux x86 requirements)'

    # Linux ARM64
    elif system == 'linux' and machine in ['arm64', 'aarch64']:
        return 'requirements-linux-arm.txt', 'success', \
               '✓ Linux ARM64 detected (Raspberry Pi, Jetson, Graviton)'

    # Linux x86_64
    elif system == 'linux' and machine in ['x86_64', 'amd64']:
        cuda_available, cuda_info = check_cuda()
        if cuda_available:
            return 'requirements-linux-x86.txt', 'success', \
                   f'✓ Linux x86_64 with CUDA detected\n   {cuda_info}\n' \
                   '   Note: Install onnxruntime-gpu for GPU acceleration'
        return 'requirements-linux-x86.txt', 'info', \
               'ℹ️  Linux x86_64 detected (CPU only)'

    # Windows
    elif system == 'windows':
        cuda_available, cuda_info = check_cuda()
        if cuda_available:
            return 'requirements-windows.txt', 'success', \
                   f'✓ Windows with CUDA detected\n   {cuda_info}\n' \
                   '   Note: Install onnxruntime-gpu for GPU acceleration'
        return 'requirements-windows.txt', 'info', \
               'ℹ️  Windows detected (CPU only)'

    # Unknown platform
    else:
        return 'requirements.txt', 'warning', \
               f'⚠️  Unknown platform: {system} {machine}\n' \
               '   Using generic requirements.txt'


def print_platform_info():
    """Print detailed platform information"""
    info = detect_platform()
    requirements_file, status, message = get_recommended_requirements()

    print("=" * 70)
    print("PLATFORM DETECTION")
    print("=" * 70)
    print(f"\nOperating System: {info['system']}")
    print(f"Architecture:     {info['machine']}")
    print(f"Python Version:   {info['python_version']}")
    print(f"64-bit:           {info['is_64bit']}")

    if detect_apple_silicon():
        print(f"Apple Silicon:    Yes")
        if check_rosetta():
            print(f"Rosetta 2:        Yes (⚠️  Performance impact!)")
        else:
            print(f"Rosetta 2:        No (✓ Native ARM64)")

    cuda_available, cuda_info = check_cuda()
    if cuda_available:
        print(f"\nCUDA:             Available")
        print(f"                  {cuda_info}")
    else:
        print(f"\nCUDA:             Not available")

    print("\n" + "-" * 70)
    print("RECOMMENDATION")
    print("-" * 70)
    print(f"\n{message}")
    print(f"\nRecommended file: backend/{requirements_file}")

    print("\n" + "-" * 70)
    print("INSTALLATION COMMAND")
    print("-" * 70)
    print(f"\n  cd backend")
    print(f"  pip install -r {requirements_file}")

    print("\n" + "=" * 70)

    return requirements_file


def check_environment():
    """Check if running in virtual environment"""
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        print("\n⚠️  WARNING: Not running in a virtual environment!")
        print("   It's recommended to use a virtual environment:")
        print("   python3 -m venv venv")
        print("   source venv/bin/activate  # On Windows: venv\\Scripts\\activate")
        print()


def main():
    """Main function"""
    print_platform_info()
    check_environment()

    # Optionally install requirements
    if len(sys.argv) > 1 and sys.argv[1] == '--install':
        requirements_file, _, _ = get_recommended_requirements()
        requirements_path = os.path.join('backend', requirements_file)

        if os.path.exists(requirements_path):
            print(f"\nInstalling dependencies from {requirements_file}...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements_path])
        else:
            print(f"\n❌ Error: {requirements_path} not found!")
            sys.exit(1)


if __name__ == '__main__':
    main()
