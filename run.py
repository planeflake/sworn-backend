import subprocess
import time
import signal
import sys
import os
from multiprocessing import Process

def run_uvicorn():
    """Run the FastAPI application with uvicorn"""
    print("🚀 Starting Uvicorn server...")
    subprocess.run(["uvicorn", "app.main:app", "--reload", "--port", "8081", "--host", "0.0.0.0"])

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
    return subprocess.Popen(["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"])

def run_celery_beat():
    """Run Celery beat scheduler"""
    print("⏰ Starting Celery beat scheduler...")
    # Set the current directory to project root to ensure imports work
    os.environ['PYTHONPATH'] = os.getcwd()
    return subprocess.Popen(["celery", "-A", "workers.celery_app", "beat", "--loglevel=info"])

def cleanup(processes):
    """Terminate all processes cleanly"""
    print("\n🛑 Shutting down services...")
    for process in processes:
        if process and process.poll() is None:
            process.terminate()
            process.wait()
    print("✓ All services stopped")

def main():
    """Start all services"""
    print("🌟 Starting Sworn Backend Services 🌟")
    
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
    
    # Start Uvicorn in the main process
    try:
        uvicorn_process = Process(target=run_uvicorn)
        uvicorn_process.start()
        processes.append(uvicorn_process)
        
        # Wait for keyboard interrupt
        uvicorn_process.join()
    except KeyboardInterrupt:
        print("\n⚠️ Received interrupt signal")
    finally:
        cleanup(processes)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))
    main()