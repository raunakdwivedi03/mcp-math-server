# launcher.py — Production entrypoint for Render / Cloud deployment
import os
import sys
import time
import subprocess

def main():
    print("🚀 Starting FastMCP Server on port 8000...")
    # Start FastMCP server in background
    server_process = subprocess.Popen([
        sys.executable, "-m", "fastmcp", "run", "server.py",
        "--transport", "streamable-http",
        "--port", "8000"
    ])

    # Brief delay for server initialization
    time.sleep(3)

    # Render provides $PORT for the web service
    port = os.getenv("PORT", "8501")
    print(f"🌟 Starting Streamlit Web UI on port {port}...")

    # Run Streamlit on assigned PORT bound to 0.0.0.0
    streamlit_process = subprocess.Popen([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true"
    ])

    try:
        streamlit_process.wait()
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        server_process.terminate()
        streamlit_process.terminate()

if __name__ == "__main__":
    main()
