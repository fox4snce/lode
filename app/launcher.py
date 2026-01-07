"""
Desktop launcher for ChatVault using pywebview.
"""
import sys
from pathlib import Path

# Add project root to Python path so imports work
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import webview
import threading
import time
import subprocess
import requests
from backend.main import app
import uvicorn
import platform
import socket
import os
import atexit


class ServerThread(threading.Thread):
    """Thread to run FastAPI server."""
    def __init__(self, port):
        super().__init__(daemon=True)
        self.port = port
        self.server = None
    
    def run(self):
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="info")
        self.server = uvicorn.Server(config)
        self.server.run()
    
    def shutdown(self):
        if self.server:
            self.server.should_exit = True


def is_our_server(port):
    """Check if the process on the port is our ChatVault server."""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=1)
        if response.status_code == 200:
            data = response.json()
            # Check if it's our API (has version field)
            if isinstance(data, dict) and data.get('status') == 'ok':
                return True
    except:
        pass
    return False


def kill_chatvault_server(port):
    """Kill only ChatVault server processes on the specified port."""
    # First check if it's actually our server
    if not is_our_server(port):
        print(f"Port {port} is in use, but it's not a ChatVault server. Skipping cleanup.")
        return False
    
    if platform.system() == "Windows":
        try:
            # Find process using the port
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                shell=True
            )
            lines = result.stdout.split('\n')
            pids = []
            for line in lines:
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.split()
                    if len(parts) > 4:
                        pid = parts[-1]
                        if pid.isdigit():
                            pids.append(pid)
            
            # Verify it's a Python process running our server before killing
            for pid in set(pids):
                try:
                    # Check process command line to verify it's our server
                    result = subprocess.run(
                        ["wmic", "process", "where", f"ProcessId={pid}", "get", "CommandLine"],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    cmdline = result.stdout.lower()
                    # Only kill if it's Python running backend.main or uvicorn with our app
                    if ("python" in cmdline and 
                        ("backend.main" in cmdline or 
                         "uvicorn" in cmdline and "backend.main:app" in cmdline or
                         "app/launcher.py" in cmdline)):
                        print(f"Killing ChatVault server process {pid} on port {port}...")
                        subprocess.run(["taskkill", "/F", "/PID", pid], 
                                     capture_output=True, shell=True)
                        time.sleep(0.5)
                        return True
                except Exception as e:
                    print(f"Could not verify/kill process {pid}: {e}")
        except Exception as e:
            print(f"Error checking port {port}: {e}")
    else:
        # Linux/Mac - check if it's our process
        try:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        # Check process command
                        result = subprocess.run(
                            ["ps", "-p", pid, "-o", "command="],
                            capture_output=True,
                            text=True
                        )
                        cmdline = result.stdout.lower()
                        if ("python" in cmdline and 
                            ("backend.main" in cmdline or 
                             "uvicorn" in cmdline and "backend.main:app" in cmdline or
                             "app/launcher.py" in cmdline)):
                            print(f"Killing ChatVault server process {pid} on port {port}...")
                            subprocess.run(["kill", "-9", pid], capture_output=True)
                            return True
                    except:
                        pass
        except:
            pass
    return False


def get_lock_file_path():
    """Get path to lock file for preventing multiple instances."""
    if platform.system() == "Windows":
        # Use temp directory
        import tempfile
        return Path(tempfile.gettempdir()) / "chatvault.lock"
    else:
        # Linux/Mac: use /tmp
        return Path("/tmp") / "chatvault.lock"


def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def check_existing_instance(port):
    """Check if another ChatVault instance is running."""
    # Check lock file
    lock_file = get_lock_file_path()
    if lock_file.exists():
        try:
            # Read PID from lock file
            pid = int(lock_file.read_text().strip())
            # Check if process is still running
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                if str(pid) in result.stdout:
                    # Process exists, check if it's our server
                    if is_our_server(port):
                        return True, pid
            else:
                try:
                    os.kill(pid, 0)  # Check if process exists
                    if is_our_server(port):
                        return True, pid
                except OSError:
                    # Process doesn't exist, remove stale lock file
                    lock_file.unlink(missing_ok=True)
        except (ValueError, FileNotFoundError):
            # Invalid lock file, remove it
            lock_file.unlink(missing_ok=True)
    
    # Check if port is in use and it's our server
    if is_port_in_use(port) and is_our_server(port):
        return True, None
    
    return False, None


def create_lock_file():
    """Create lock file with current process ID."""
    lock_file = get_lock_file_path()
    lock_file.write_text(str(os.getpid()))
    
    # Register cleanup on exit
    def cleanup_lock():
        if lock_file.exists():
            try:
                lock_file.unlink()
            except:
                pass
    
    atexit.register(cleanup_lock)
    return lock_file


def wait_for_server(port, max_retries=30):
    """Wait for server to be ready."""
    for i in range(max_retries):
        try:
            response = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=1)
            if response.status_code == 200:
                return True
        except:
            if i == max_retries - 1:
                return False
            time.sleep(0.5)
    return False


def main():
    """Launch the desktop application."""
    # Use fixed port 8000 for FastAPI (matches Vite proxy config)
    port = 8000
    
    # Check for existing instance
    has_instance, existing_pid = check_existing_instance(port)
    if has_instance:
        if existing_pid:
            print(f"Another ChatVault instance is already running (PID: {existing_pid})")
            print("Please close that instance first or wait for it to finish.")
        else:
            print(f"Port {port} is in use by another ChatVault server.")
            print("Attempting to clean up...")
            if kill_chatvault_server(port):
                print("Cleaned up old ChatVault server process.")
                time.sleep(2)  # Give process time to die
            else:
                print(f"ERROR: Could not clean up. Port {port} is in use.")
                print("Please stop that application or use a different port.")
                sys.exit(1)
    
    # Create lock file to prevent multiple instances
    create_lock_file()
    
    # Check if we should use Vite dev server or built files
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    use_dev_server = not frontend_dist.exists()
    
    # FORCE use dev server for now
    use_dev_server = True
    print(f"FORCING dev server mode. Dist exists: {frontend_dist.exists()}")
    
    if use_dev_server:
        # Start Vite dev server (it proxies /api to FastAPI on port 8000)
        frontend_dir = Path(__file__).parent.parent / "frontend"
        print(f"Starting Vite dev server in {frontend_dir}...")
        print(f"Dist folder exists: {frontend_dist.exists()}")
        
        # On Windows, npm might not be in PATH, so use shell=True
        if platform.system() == "Windows":
            # Use shell=True on Windows so it can find npm in PATH
            vite_process = subprocess.Popen(
                "npm run dev -- --port 5173 --host",
                cwd=frontend_dir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
        else:
            vite_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "5173", "--host"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
        # Wait for Vite to start
        print("Waiting for Vite dev server to start...")
        time.sleep(5)  # Increased wait time
        # Check if Vite is actually running
        try:
            response = requests.get("http://localhost:5173", timeout=2)
            print(f"Vite dev server is running! Status: {response.status_code}")
            print(f"Using frontend URL: http://localhost:5173")
        except Exception as e:
            print(f"WARNING: Vite dev server may not be running: {e}")
            print("You may need to manually start: cd frontend && npm run dev")
            print("Falling back to FastAPI static serving (which won't work)")
        frontend_url = "http://localhost:5173"
        print(f"Webview will load: {frontend_url}")
    else:
        vite_process = None
        frontend_url = f"http://127.0.0.1:{port}"
    
    # Start FastAPI server
    server_thread = ServerThread(port)
    server_thread.start()
    
    # Wait for server
    if not wait_for_server(port):
        print("Failed to start server")
        if vite_process:
            vite_process.terminate()
        sys.exit(1)
    
    # Create webview window
    print(f"=== CREATING WEBVIEW WITH URL: {frontend_url} ===")
    print(f"=== Vite process exists: {vite_process is not None} ===")
    window = webview.create_window(
        title="ChatVault",
        url=frontend_url,
        width=1400,
        height=900,
        min_size=(1000, 700)
    )
    print(f"=== Webview created, URL should be: {frontend_url} ===")
    
    def on_closed():
        """Cleanup on window close."""
        server_thread.shutdown()
        if vite_process:
            vite_process.terminate()
    
    # Start webview
    try:
        webview.start(debug=False)
    finally:
        on_closed()


if __name__ == "__main__":
    main()

