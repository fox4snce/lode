"""
Static analysis and code validation tests for ChatVault MVP.
Tests that don't require the server to be running.
"""
import os
import sys
from pathlib import Path
import importlib.util

# Test results
results = {"passed": [], "failed": [], "warnings": []}

def log_pass(name, message=""):
    results["passed"].append(name)
    print(f"[PASS] {name}")
    if message:
        print(f"       {message}")

def log_fail(name, message=""):
    results["failed"].append(name)
    print(f"[FAIL] {name}")
    if message:
        print(f"       {message}")

def log_warn(name, message=""):
    results["warnings"].append(name)
    print(f"[WARN] {name}")
    if message:
        print(f"       {message}")

# ============================================================================
# File Structure Tests
# ============================================================================

def test_file_structure():
    """Test that required files exist."""
    print("=" * 70)
    print("File Structure Tests")
    print("=" * 70)
    
    required_files = [
        "backend/main.py",
        "backend/db.py",
        "backend/jobs.py",
        "backend/job_runner.py",
        "app/launcher.py",
        "frontend/src/App.tsx",
        "frontend/src/main.tsx",
        "requirements.txt",
        "frontend/package.json",
        ".gitignore",
        "USER_STORIES.md",
        "API_TESTING.md"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            log_pass(f"File exists: {file_path}")
        else:
            log_fail(f"File missing: {file_path}")
    
    print()

# ============================================================================
# Python Module Tests
# ============================================================================

def test_python_imports():
    """Test that Python modules can be imported."""
    print("=" * 70)
    print("Python Module Import Tests")
    print("=" * 70)
    
    modules_to_test = [
        ("backend.db", "check_database_initialized"),
        ("backend.jobs", "create_job"),
        ("backend.job_runner", "run_import_job"),
        ("search_fts5", "search_messages"),
        ("find_tools", "find_code_blocks"),
        ("analytics", "get_usage_over_time"),
    ]
    
    for module_name, function_name in modules_to_test:
        try:
            # Try to import the module
            if module_name.startswith("backend"):
                module_path = Path(f"{module_name.replace('.', '/')}.py")
            else:
                module_path = Path(f"{module_name}.py")
            
            if not module_path.exists():
                log_warn(f"Module file not found: {module_path}")
                continue
            
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if spec is None:
                log_fail(f"Cannot create spec for: {module_name}")
                continue
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check if function exists
            if hasattr(module, function_name):
                log_pass(f"Import {module_name}.{function_name}")
            else:
                log_warn(f"Function {function_name} not found in {module_name}")
        except Exception as e:
            log_fail(f"Import {module_name}", str(e))
    
    print()

# ============================================================================
# Database Schema Tests
# ============================================================================

def test_database_scripts():
    """Test that database creation scripts exist."""
    print("=" * 70)
    print("Database Schema Script Tests")
    print("=" * 70)
    
    db_scripts = [
        "create_database.py",
        "create_fts5_tables.py",
        "create_organization_tables.py",
        "create_metadata_tables.py",
        "create_user_state_table.py",
        "create_import_report_tables.py",
        "create_deduplication_tables.py",
    ]
    
    for script in db_scripts:
        if Path(script).exists():
            log_pass(f"Database script exists: {script}")
        else:
            log_fail(f"Database script missing: {script}")
    
    print()

# ============================================================================
# API Endpoint Tests (Static Analysis)
# ============================================================================

def test_api_endpoints_defined():
    """Test that API endpoints are defined in backend/main.py."""
    print("=" * 70)
    print("API Endpoint Definition Tests")
    print("=" * 70)
    
    main_py = Path("backend/main.py")
    if not main_py.exists():
        log_fail("backend/main.py not found")
        return
    
    content = main_py.read_text(encoding='utf-8')
    
    # Check for key endpoints
    endpoints = [
        ("@app.get(\"/api/health\"", "Health check"),
        ("@app.get(\"/api/setup/check\"", "Setup check"),
        ("@app.get(\"/api/conversations\"", "List conversations"),
        ("@app.get(\"/api/search\"", "Search"),
        ("@app.post(\"/api/jobs/import\"", "Import job"),
        ("@app.get(\"/api/analytics/usage\"", "Analytics usage"),
        ("@app.get(\"/api/find/code\"", "Find code"),
        ("@app.post(\"/api/export/conversation/", "Export conversation"),
    ]
    
    for pattern, name in endpoints:
        if pattern in content:
            log_pass(f"Endpoint defined: {name}")
        else:
            log_fail(f"Endpoint missing: {name}")
    
    print()

# ============================================================================
# Frontend Component Tests
# ============================================================================

def test_frontend_components():
    """Test that frontend components exist."""
    print("=" * 70)
    print("Frontend Component Tests")
    print("=" * 70)
    
    components = [
        "frontend/src/components/ConversationList.tsx",
        "frontend/src/components/MessageViewer.tsx",
        "frontend/src/components/Inspector.tsx",
        "frontend/src/components/SearchResults.tsx",
        "frontend/src/components/MenuBar.tsx",
        "frontend/src/components/TopBar.tsx",
        "frontend/src/components/LoadingSpinner.tsx",
        "frontend/src/components/ErrorMessage.tsx",
        "frontend/src/components/EmptyState.tsx",
    ]
    
    for component in components:
        if Path(component).exists():
            log_pass(f"Component exists: {component}")
        else:
            log_fail(f"Component missing: {component}")
    
    print()

# ============================================================================
# Screen Tests
# ============================================================================

def test_frontend_screens():
    """Test that frontend screens exist."""
    print("=" * 70)
    print("Frontend Screen Tests")
    print("=" * 70)
    
    screens = [
        "frontend/src/screens/MainShell.tsx",
        "frontend/src/screens/ImportScreen.tsx",
        "frontend/src/screens/AnalyticsScreen.tsx",
        "frontend/src/screens/FindToolsScreen.tsx",
        "frontend/src/screens/ExportScreen.tsx",
        "frontend/src/screens/SettingsScreen.tsx",
        "frontend/src/screens/ImportReportsScreen.tsx",
        "frontend/src/screens/AboutScreen.tsx",
        "frontend/src/screens/WelcomeScreen.tsx",
    ]
    
    for screen in screens:
        if Path(screen).exists():
            log_pass(f"Screen exists: {screen}")
        else:
            log_fail(f"Screen missing: {screen}")
    
    print()

# ============================================================================
# Configuration Tests
# ============================================================================

def test_configuration_files():
    """Test that configuration files exist and are valid."""
    print("=" * 70)
    print("Configuration File Tests")
    print("=" * 70)
    
    configs = [
        ("frontend/package.json", "Frontend package.json"),
        ("frontend/vite.config.ts", "Vite configuration"),
        ("frontend/tsconfig.json", "TypeScript configuration"),
        ("requirements.txt", "Python requirements"),
        (".gitignore", "Git ignore file"),
    ]
    
    for file_path, name in configs:
        path = Path(file_path)
        if path.exists():
            try:
                content = path.read_text(encoding='utf-8')
                if len(content) > 0:
                    log_pass(f"{name} exists and is not empty")
                else:
                    log_warn(f"{name} exists but is empty")
            except Exception as e:
                log_fail(f"{name} exists but cannot be read", str(e))
        else:
            log_fail(f"{name} missing")
    
    print()

# ============================================================================
# Documentation Tests
# ============================================================================

def test_documentation():
    """Test that documentation exists."""
    print("=" * 70)
    print("Documentation Tests")
    print("=" * 70)
    
    docs = [
        "USER_STORIES.md",
        "API_TESTING.md",
        "RUN_INSTRUCTIONS.md",
    ]
    
    for doc in docs:
        path = Path(doc)
        if path.exists():
            size = path.stat().st_size
            if size > 100:  # At least 100 bytes
                log_pass(f"Documentation exists: {doc} ({size} bytes)")
            else:
                log_warn(f"Documentation exists but is very small: {doc}")
        else:
            log_fail(f"Documentation missing: {doc}")
    
    print()

# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all static analysis tests."""
    print("=" * 70)
    print("ChatVault MVP - Static Analysis & Code Validation")
    print("=" * 70)
    print()
    
    test_file_structure()
    test_python_imports()
    test_database_scripts()
    test_api_endpoints_defined()
    test_frontend_components()
    test_frontend_screens()
    test_configuration_files()
    test_documentation()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    total = len(results["passed"]) + len(results["failed"]) + len(results["warnings"])
    print(f"Total Tests: {total}")
    print(f"[PASS] Passed: {len(results['passed'])}")
    print(f"[FAIL] Failed: {len(results['failed'])}")
    print(f"[WARN] Warnings: {len(results['warnings'])}")
    print()
    
    if results["failed"]:
        print("Failed Tests:")
        for test in results["failed"]:
            print(f"  - {test}")
        print()
    
    if results["warnings"]:
        print("Warnings:")
        for test in results["warnings"]:
            print(f"  - {test}")
        print()
    
    success_rate = (len(results["passed"]) / total * 100) if total > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print()

if __name__ == "__main__":
    run_all_tests()

