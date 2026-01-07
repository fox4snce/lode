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


def kill_process_on_port(port):
    """Kill any process using the specified port."""
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
            
            # Kill processes
            for pid in set(pids):
                try:
                    print(f"Killing process {pid} on port {port}...")
                    subprocess.run(["taskkill", "/F", "/PID", pid], 
                                 capture_output=True, shell=True)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Could not kill process {pid}: {e}")
        except Exception as e:
            print(f"Error checking port {port}: {e}")
    else:
        # Linux/Mac
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
                        print(f"Killing process {pid} on port {port}...")
                        subprocess.run(["kill", "-9", pid], capture_output=True)
                    except:
                        pass
        except:
            pass


def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


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
    
    # Kill any existing processes on port 8000
    if is_port_in_use(port):
        print(f"Port {port} is in use. Cleaning up old processes...")
        kill_process_on_port(port)
        time.sleep(2)  # Give processes time to die
    
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

