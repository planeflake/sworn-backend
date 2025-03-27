import subprocess
import time
import signal
import sys
import os
from multiprocessing import Process

def check_port_in_use(port):
    """Check if a port is already in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def find_available_port(start_port=8081, max_attempts=5):
    """Find an available port starting from start_port"""
    port = start_port
    for _ in range(max_attempts):
        if not check_port_in_use(port):
            return port
        port += 1
    return None

def run_uvicorn():
    """Run the FastAPI application with uvicorn"""
    port = find_available_port()
    if port is None:
        print(f"❌ Could not find an available port after several attempts. Please free up ports and try again.")
        return
        
    # Kill any process that might be using port 8081 but showing as CLOSED
    if port != 8081:
        try:
            subprocess.run(["lsof", "-i", ":8081", "-t"], capture_output=True, text=True)
            pid_output = subprocess.run(["lsof", "-i", ":8081", "-t"], capture_output=True, text=True)
            if pid_output.stdout.strip():
                for pid in pid_output.stdout.strip().split('\n'):
                    print(f"⚠️ Killing process {pid} that was using port 8081...")
                    subprocess.run(["kill", "-9", pid])
                # Wait a moment for the process to be killed
                time.sleep(1)
                # Check if port 8081 is now available
                if not check_port_in_use(8081):
                    port = 8081
        except Exception as e:
            print(f"⚠️ Error attempting to free port 8081: {e}")

    print(f"🚀 Starting Uvicorn server on port {port}...")
    subprocess.run(["uvicorn", "app.main:app", "--reload", "--port", str(port), "--host", "0.0.0.0"])

def run_redis():
    """Start Redis server if not already running"""
    try:
        # Check if Redis is already running
        result = subprocess.run(["redis-cli", "ping"], capture_output=True, text=True)
        if "PONG" in result.stdout:
            print("✅ Redis is already running")
            return
    except:
        pass

    print("🔄 Starting Redis server...")
    return subprocess.Popen(["redis-server"])

def run_celery_worker():
    """Run Celery worker"""
    print("👷 Starting Celery worker...")
    # Set the current directory to project root to ensure imports work
    os.environ['PYTHONPATH'] = os.getcwd()
    return subprocess.Popen(["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info"])

def run_celery_beat():
    """Run Celery beat scheduler"""
    print("⏰ Starting Celery beat scheduler...")
    # Set the current directory to project root to ensure imports work
    os.environ['PYTHONPATH'] = os.getcwd()
    return subprocess.Popen(["celery", "-A", "app.workers.celery_app", "beat", "--loglevel=info"])

def cleanup(processes):
    """Terminate all processes cleanly"""
    print("\n🛑 Shutting down services...")
    for process in processes:
        if process:
            if isinstance(process, subprocess.Popen) and process.poll() is None:
                process.terminate()
                process.wait()
            elif isinstance(process, Process) and process.is_alive():
                process.terminate()
                process.join()
    print("✓ All services stopped")

def main():
    """Start all services"""
    print("🌟 Starting Sworn Backend Services 🌟")
    
    # Set Python path to include project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.environ["PYTHONPATH"] = project_root
    print(f"🔧 Setting PYTHONPATH to: {project_root}")
    
    # Start Redis first
    redis_process = run_redis()
    time.sleep(2)  # Give Redis time to start
    
    # Start Celery worker and beat in separate processes
    celery_worker_process = run_celery_worker()
    time.sleep(2)  # Give worker time to connect to Redis
    
    celery_beat_process = run_celery_beat()
    time.sleep(2)  # Give beat time to start
    
    # Keep track of all processes for cleanup
    processes = [redis_process, celery_worker_process, celery_beat_process]
    
    # Start Uvicorn in a separate process
    try:
        uvicorn_process = Process(target=run_uvicorn)
        uvicorn_process.start()
        processes.append(uvicorn_process)
        
        # Wait for keyboard interrupt
        print("\n✅ All services started. Press Ctrl+C to stop.\n")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n⚠️ Received interrupt signal")
    finally:
        cleanup(processes)

if __name__ == "__main__":
    main()