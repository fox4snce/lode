"""
Desktop launcher for Lode using pywebview.
"""
import sys
from pathlib import Path
import ctypes
import tempfile

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
    # Use fixed port 8000 for FastAPI
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
    
    # FastAPI serves HTML directly - no Vite/React needed
    frontend_url = f"http://127.0.0.1:{port}"
    print(f"FastAPI will serve HTML directly at {frontend_url}")
    
    # Start FastAPI server
    server_thread = ServerThread(port)
    server_thread.start()
    
    # Wait for server
    if not wait_for_server(port):
        print("Failed to start server")
        sys.exit(1)
    
    # Create webview window
    print(f"=== CREATING WEBVIEW WITH URL: {frontend_url} ===")
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
    
    # No browser test - just open webview directly
    
    window_icon_ico = project_root / "docs" / "images" / "lode.ico"
    taskbar_master_png = project_root / "docs" / "images" / "master.png"

    window = webview.create_window(
        title="Lode",
        url=frontend_url,
        width=1400,
        height=900,
        min_size=(1000, 700),
        # On Windows, pywebview expects an .ico path here.
        icon=str(window_icon_ico) if window_icon_ico.exists() else None,
        # Critical UX: allow selecting/copying text everywhere (default browser behavior).
        text_select=True,
    )
    print(f"=== Webview created, URL should be: {frontend_url} ===")
    print(f"=== Window object: {window} ===")
    
    def _set_windows_taskbar_icon_from_master_png():
        """
        Windows-only:
        - Keep the window/titlebar icon from `icon=...` (lode.ico)
        - Override the BIG icon (taskbar) using master.png (converted to a temp .ico).
        """
        if platform.system() != "Windows":
            return

        if not taskbar_master_png.exists():
            print(f"Taskbar icon not found: {taskbar_master_png}")
            return

        try:
            from PIL import Image
        except Exception as e:
            print("Pillow is required to set taskbar icon from master.png. Install requirements.txt.")
            print(f"Import error: {e}")
            return

        try:
            # Convert master.png -> temp ico (Windows APIs expect .ico for setting HICON easily)
            tmp_ico = Path(tempfile.gettempdir()) / "lode_taskbar_master.ico"
            try:
                if (not tmp_ico.exists()) or (tmp_ico.stat().st_mtime < taskbar_master_png.stat().st_mtime):
                    img = Image.open(taskbar_master_png).convert("RGBA")
                    img.save(
                        tmp_ico,
                        format="ICO",
                        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
                    )
            except Exception as e:
                print(f"Failed converting {taskbar_master_png} to {tmp_ico}: {e}")
                return

            native = getattr(window, "native", None)
            hwnd = None
            if native is not None:
                handle = getattr(native, "Handle", None)
                if handle is not None:
                    try:
                        hwnd = int(handle)
                    except Exception:
                        try:
                            hwnd = int(handle.ToInt64())
                        except Exception:
                            hwnd = None

            if not hwnd:
                print("Could not resolve native window handle (HWND); skipping taskbar icon override.")
                return

            user32 = ctypes.windll.user32
            WM_SETICON = 0x0080
            ICON_BIG = 1
            IMAGE_ICON = 1
            LR_LOADFROMFILE = 0x0010
            LR_DEFAULTSIZE = 0x0040

            hicon = user32.LoadImageW(
                None,
                str(tmp_ico),
                IMAGE_ICON,
                0,
                0,
                LR_LOADFROMFILE | LR_DEFAULTSIZE,
            )
            if not hicon:
                print(f"LoadImageW failed for icon: {tmp_ico}")
                return

            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon)
            print(f"Set Windows taskbar icon from {taskbar_master_png} (via {tmp_ico})")
        except Exception as e:
            print(f"Failed setting Windows taskbar icon: {e}")

    def on_closed():
        """Cleanup on window close."""
        print("=== CLEANUP STARTING ===")
        try:
            server_thread.shutdown()
            print("Server thread shutdown called")
        except Exception as e:
            print(f"Error shutting down server: {e}")
        
        # No Vite process to clean up
        print("=== CLEANUP COMPLETE ===")
    
    # Start webview (debug disabled - no devtools)
    # webview.start() blocks until the window is closed
    try:
        print("=== STARTING WEBVIEW ===")
        print("=== webview.start() will block until window is closed ===")
        webview.start(_set_windows_taskbar_icon_from_master_png, debug=False)
        print("=== webview.start() returned - window was closed ===")
    except KeyboardInterrupt:
        print("Keyboard interrupt received")
    except Exception as e:
        print(f"ERROR in webview.start(): {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("=== FINALLY BLOCK - CLEANUP ===")
        on_closed()


if __name__ == "__main__":
    main()

