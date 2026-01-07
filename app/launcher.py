"""
Desktop launcher for Lode using pywebview.
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
        self.config = None
    
    def run(self):
        try:
            self.config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="info")
            self.server = uvicorn.Server(self.config)
            self.server.run()
        except Exception as e:
            print(f"ERROR in ServerThread: {e}")
            import traceback
            traceback.print_exc()
    
    def shutdown(self):
        if self.server:
            self.server.should_exit = True
            # Force shutdown
            try:
                import time
                time.sleep(0.5)
                if hasattr(self.server, 'force_exit'):
                    self.server.force_exit = True
            except:
                pass


def is_our_server(port):
    """Check if the process on the port is our Lode server."""
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


def kill_lode_server(port):
    """Kill only Lode server processes on the specified port."""
    # First check if it's actually our server
    if not is_our_server(port):
        print(f"Port {port} is in use, but it's not a Lode server. Skipping cleanup.")
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
                        print(f"Killing Lode server process {pid} on port {port}...")
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
                            print(f"Killing Lode server process {pid} on port {port}...")
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
        return Path(tempfile.gettempdir()) / "lode.lock"
    else:
        # Linux/Mac: use /tmp
        return Path("/tmp") / "lode.lock"


def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def check_existing_instance(port):
    """Check if another Lode instance is running."""
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
            print(f"Another Lode instance is already running (PID: {existing_pid})")
            print("Please close that instance first or wait for it to finish.")
        else:
            print(f"Port {port} is in use by another Lode server.")
            print("Attempting to clean up...")
            if kill_lode_server(port):
                print("Cleaned up old Lode server process.")
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
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        else:
            vite_process = subprocess.Popen(
                ["npm", "run", "dev", "--", "--port", "5173", "--host"],
                cwd=frontend_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        
        # Wait for Vite to start and check output
        print("Waiting for Vite dev server to start...")
        max_wait = 15
        waited = 0
        vite_ready = False
        
        while waited < max_wait:
            time.sleep(1)
            waited += 1
            
            # Check if process is still alive
            if vite_process.poll() is not None:
                print(f"ERROR: Vite process died! Exit code: {vite_process.returncode}")
                # Try to read output
                try:
                    output = vite_process.stdout.read() if vite_process.stdout else "No output"
                    print(f"Vite output: {output[:500]}")
                except:
                    pass
                break
            
            # Try to connect
            try:
                response = requests.get("http://localhost:5173", timeout=1)
                if response.status_code == 200:
                    print(f"Vite is ready after {waited} seconds!")
                    vite_ready = True
                    break
            except:
                pass
            
            # Check for "Local:" in output (Vite's ready message)
            if vite_process.stdout:
                try:
                    # Non-blocking read
                    import select
                    if platform.system() != "Windows":
                        if select.select([vite_process.stdout], [], [], 0)[0]:
                            line = vite_process.stdout.readline()
                            if line:
                                print(f"Vite: {line.strip()}")
                                if "Local:" in line or "ready" in line.lower():
                                    vite_ready = True
                                    break
                except:
                    pass
        if not vite_ready:
            print("ERROR: Vite did not start properly!")
            print("Try running manually: cd frontend && npm run dev")
            if vite_process:
                vite_process.terminate()
            sys.exit(1)
        
        # Check if Vite is actually running - try both localhost and 127.0.0.1
        vite_url_localhost = "http://localhost:5173"
        vite_url_127 = "http://127.0.0.1:5173"
        frontend_url = vite_url_localhost  # Default
        
        try:
            response = requests.get(vite_url_localhost, timeout=5)
            print(f"Vite dev server is running! Status: {response.status_code}")
            print(f"Using frontend URL: {vite_url_localhost}")
            # Check if we got actual HTML content
            if len(response.text) > 100:
                print(f"Vite returned content ({len(response.text)} bytes)")
                if '<html' in response.text.lower() or '<!doctype' in response.text.lower():
                    print("Content is HTML - good!")
                else:
                    print(f"WARNING: Content doesn't look like HTML!")
                    print(f"First 200 chars: {response.text[:200]}")
            else:
                print(f"WARNING: Vite returned very little content ({len(response.text)} bytes)")
        except Exception as e:
            print(f"WARNING: localhost:5173 not accessible: {e}")
            # Try 127.0.0.1 instead (pywebview on Windows sometimes prefers this)
            try:
                response = requests.get(vite_url_127, timeout=5)
                print(f"Vite accessible via 127.0.0.1! Status: {response.status_code}")
                frontend_url = vite_url_127
            except Exception as e2:
                print(f"ERROR: Both localhost and 127.0.0.1 failed: {e2}")
                print("You may need to manually start: cd frontend && npm run dev")
                if vite_process:
                    vite_process.terminate()
                sys.exit(1)
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
    print(f"=== Testing if URL is accessible... ===")
    try:
        test_res = requests.get(frontend_url, timeout=5)
        print(f"=== URL test: Status {test_res.status_code}, Content length: {len(test_res.text)} ===")
        if len(test_res.text) < 100:
            print(f"=== WARNING: Very little content returned! ===")
        # Check if it's HTML
        if '<html' in test_res.text.lower() or '<!doctype' in test_res.text.lower():
            print(f"=== Content appears to be HTML ===")
        else:
            print(f"=== WARNING: Content doesn't look like HTML! ===")
            print(f"=== First 200 chars: {test_res.text[:200]} ===")
    except Exception as e:
        print(f"=== URL test FAILED: {e} ===")
        import traceback
        traceback.print_exc()
    
    # Try opening in browser first to verify it works
    print(f"=== TEST: Opening {frontend_url} in default browser to verify it works ===")
    import webbrowser
    webbrowser.open(frontend_url)
    print("=== If the browser shows the app correctly, the issue is with pywebview ===")
    print("=== Waiting 3 seconds, then opening webview... ===")
    time.sleep(3)
    
    window = webview.create_window(
        title="Lode",
        url=frontend_url,
        width=1400,
        height=900,
        min_size=(1000, 700)
    )
    print(f"=== Webview created, URL should be: {frontend_url} ===")
    print(f"=== Window object: {window} ===")
    
    def on_closed():
        """Cleanup on window close."""
        print("=== CLEANUP STARTING ===")
        try:
            server_thread.shutdown()
            print("Server thread shutdown called")
        except Exception as e:
            print(f"Error shutting down server: {e}")
        
        if vite_process:
            try:
                print("Terminating Vite process...")
                vite_process.terminate()
                # Give it a moment, then kill if needed
                import time
                time.sleep(1)
                if vite_process.poll() is None:
                    print("Vite process still running, killing...")
                    vite_process.kill()
                print("Vite process terminated")
            except Exception as e:
                print(f"Error terminating Vite: {e}")
        print("=== CLEANUP COMPLETE ===")
    
    # Start webview with debug enabled to see console errors
    try:
        print("=== STARTING WEBVIEW ===")
        webview.start(debug=True)
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    except Exception as e:
        print(f"ERROR in webview.start(): {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=== FINALLY BLOCK - CLEANUP ===")
        on_closed()
        # Force exit to prevent hanging
        import os
        os._exit(0)


if __name__ == "__main__":
    main()

