#!/usr/bin/env python3
"""
Test script to validate alembic configuration and create initial migration
This simulates what the user needs to do on their Mac
"""
import sys
import os
import subprocess

# Colors
GREEN = '\033[0;32m'
BLUE = '\033[0;34m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
NC = '\033[0m'

def run_command(cmd, cwd=None, check=True):
    """Run a command and return result"""
    print(f"{BLUE}Running: {' '.join(cmd)}{NC}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result
    except subprocess.CalledProcessError as e:
        print(f"{RED}Command failed: {e}{NC}")
        if e.stdout:
            print(e.stdout)
        if e.stderr:
            print(e.stderr)
        if check:
            raise
        return e

def main():
    """Main test function"""
    print(f"\n{BLUE}{'=' * 70}{NC}")
    print(f"{BLUE}  Alembic Configuration Test{NC}")
    print(f"{BLUE}{'=' * 70}{NC}\n")

    backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
    backend_dir = os.path.abspath(backend_dir)

    # Test 1: Check alembic.ini exists
    print(f"\n{BLUE}[1/5] Checking alembic.ini...{NC}")
    alembic_ini = os.path.join(backend_dir, 'alembic.ini')
    if os.path.exists(alembic_ini):
        print(f"{GREEN}✓ alembic.ini exists{NC}")
    else:
        print(f"{RED}✗ alembic.ini not found{NC}")
        return False

    # Test 2: Check alembic directory structure
    print(f"\n{BLUE}[2/5] Checking alembic directory structure...{NC}")
    alembic_dir = os.path.join(backend_dir, 'alembic')
    env_py = os.path.join(alembic_dir, 'env.py')
    script_mako = os.path.join(alembic_dir, 'script.py.mako')
    versions_dir = os.path.join(alembic_dir, 'versions')

    checks = [
        (alembic_dir, "alembic/"),
        (env_py, "alembic/env.py"),
        (script_mako, "alembic/script.py.mako"),
        (versions_dir, "alembic/versions/"),
    ]

    all_exist = True
    for path, name in checks:
        if os.path.exists(path):
            print(f"{GREEN}✓ {name} exists{NC}")
        else:
            print(f"{RED}✗ {name} not found{NC}")
            all_exist = False

    if not all_exist:
        return False

    # Test 3: Check if .env exists
    print(f"\n{BLUE}[3/5] Checking .env file...{NC}")
    env_file = os.path.join(backend_dir, '.env')
    if os.path.exists(env_file):
        print(f"{GREEN}✓ .env exists{NC}")

        # Check DATABASE_URL
        with open(env_file) as f:
            content = f.read()
            if 'DATABASE_URL' in content:
                print(f"{GREEN}✓ DATABASE_URL configured{NC}")
                # Extract and display (hide password)
                for line in content.split('\n'):
                    if line.startswith('DATABASE_URL='):
                        url = line.split('=', 1)[1]
                        # Hide password
                        if '@' in url:
                            parts = url.split('@')
                            user_part = parts[0]
                            if ':' in user_part:
                                user, pwd = user_part.rsplit(':', 1)
                                hidden = f"{user}:****@{parts[1]}"
                                print(f"  {hidden}")
            else:
                print(f"{RED}✗ DATABASE_URL not found in .env{NC}")
                return False
    else:
        print(f"{YELLOW}⚠ .env not found (will use defaults){NC}")
        print(f"{YELLOW}  Run: cp backend/.env.example backend/.env{NC}")

    # Test 4: Test Settings import
    print(f"\n{BLUE}[4/5] Testing Settings import...{NC}")
    sys.path.insert(0, backend_dir)
    try:
        from app.core.config import settings
        print(f"{GREEN}✓ Settings imported successfully{NC}")
        print(f"  Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    except Exception as e:
        print(f"{RED}✗ Failed to import Settings: {e}{NC}")
        return False

    # Test 5: Test alembic command availability
    print(f"\n{BLUE}[5/5] Testing alembic command...{NC}")
    result = run_command(['alembic', '--version'], cwd=backend_dir, check=False)
    if result.returncode == 0:
        print(f"{GREEN}✓ alembic command available{NC}")
    else:
        print(f"{RED}✗ alembic command not found{NC}")
        print(f"{YELLOW}  Install with: pip install alembic{NC}")
        return False

    # Summary
    print(f"\n{GREEN}{'=' * 70}{NC}")
    print(f"{GREEN}✅ Alembic configuration is valid!{NC}")
    print(f"{GREEN}{'=' * 70}{NC}\n")

    print(f"{BLUE}Next steps on your Mac:{NC}\n")
    print(f"{YELLOW}1. Ensure Docker services are running:{NC}")
    print(f"   docker-compose up -d postgres redis\n")

    print(f"{YELLOW}2. Ensure .env file exists:{NC}")
    print(f"   cp backend/.env.example backend/.env\n")

    print(f"{YELLOW}3. Create initial migration:{NC}")
    print(f"   cd backend")
    print(f"   alembic revision --autogenerate -m \"Initial migration\"\n")

    print(f"{YELLOW}4. Apply migrations:{NC}")
    print(f"   alembic upgrade head\n")

    print(f"{YELLOW}5. Verify tables created:{NC}")
    print(f"   docker exec faceswap_postgres psql -U faceswap_user -d faceswap -c \"\\dt\"\n")

    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"{RED}Error: {e}{NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
