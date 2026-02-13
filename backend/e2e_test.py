import subprocess
import time
import requests
import json
import sys
import os
import signal

def cleanup_port(port=8000):
    """Find and kill the process that is using the specified port."""
    print(f"--- Cleaning up port {port} before test ---")
    try:
        # Find the process ID using the port
        result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if f":{port}" in line and 'LISTENING' in line:
                parts = line.split()
                pid = parts[-1]
                print(f"Found process with PID {pid} using port {port}. Terminating it.")
                # Kill the process
                os.kill(int(pid), signal.SIGTERM)
                time.sleep(1) # Give it a moment to release the port
                break
    except Exception as e:
        print(f"Could not clean up port {port}: {e}")

def run_e2e_test():
    """
    Starts the FastAPI server, makes a real HTTP request to it,
    validates the response, and then shuts it down.
    """
    cleanup_port(8000)
    server_process = None
    try:
        # Start the FastAPI server as a subprocess
        print("--- Starting FastAPI server for E2E test ---")
        python_executable = r".\venv\Scripts\python.exe"
        server_command = [python_executable, "-m", "uvicorn", "main:app"]
        
        server_process = subprocess.Popen(server_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='cp949', creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

        time.sleep(15)

        if server_process.poll() is not None:
             print("--- E2E TEST FAILED: Server failed to start. ---")
             stderr = server_process.stderr.read()
             print(f"Server errors:\n{stderr}")
             return

        ticker = "AAPL"
        url = f"http://127.0.0.1:8000/api/scrape?ticker={ticker}"
        print(f"--- Making GET request to {url} ---")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        data = response.json()

        print("--- Validating response ---")
        if (data and data.get("ticker") == ticker and 
            isinstance(data.get("investment_indicators"), list) and 
            len(data["investment_indicators"]) > 0):
            print("--- E2E TEST SUCCEEDED: Server returned valid data for AAPL. ---")
        else:
            print("--- E2E TEST FAILED: Server did not return valid data. ---")
            print("Received data:", json.dumps(data, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"--- E2E TEST FAILED with an exception: {e} ---")
        if server_process and server_process.stderr:
             stderr = server_process.stderr.read()
             print(f"Server errors during test:\n{stderr}")

    finally:
        if server_process:
            print("--- Shutting down server ---")
            # Send CTRL_BREAK_EVENT to the process group to gracefully shut down uvicorn
            server_process.send_signal(signal.CTRL_BREAK_EVENT)
            server_process.wait(timeout=10)
            if server_process.poll() is None:
                server_process.kill() # Force kill if it doesn't shut down
        print("--- E2E test finished ---")

if __name__ == "__main__":
    run_e2e_test()
