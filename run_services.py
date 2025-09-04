#!/usr/bin/env python3
"""
NexusEnroll - Main Service Runner
Starts all microservices for the student enrollment system
"""

import subprocess
import sys
import time
import os
from pathlib import Path

# Service configurations
SERVICES = [
    {
        'name': 'Authentication Service',
        'script': 'services/auth_service.py',
        'port': 8001,
        'url': 'http://127.0.0.1:8001'
    },
    {
        'name': 'Student Service',
        'script': 'services/student_service.py',
        'port': 8002,
        'url': 'http://127.0.0.1:8002'
    },
    {
        'name': 'Faculty Service',
        'script': 'services/faculty_service.py',
        'port': 8003,
        'url': 'http://127.0.0.1:8003'
    },
    {
        'name': 'Admin Service',
        'script': 'services/admin_service.py',
        'port': 8004,
        'url': 'http://127.0.0.1:8004'
    },
    {
        'name': 'Notification Service',
        'script': 'services/notification_service.py',
        'port': 8005,
        'url': 'http://127.0.0.1:8005'
    }
]

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("✓ All required dependencies are installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Please install dependencies with: pip install -r requirements.txt")
        return False

def start_service(service):
    """Start a single service"""
    script_path = Path(service['script'])
    if not script_path.exists():
        print(f"✗ Service script not found: {script_path}")
        return None
    
    try:
        print(f"Starting {service['name']} on port {service['port']}...")
        
        # Start the service using Python
        process = subprocess.Popen([
            sys.executable, str(script_path)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Give the service a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            print(f"✓ {service['name']} started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"✗ Failed to start {service['name']}")
            print(f"Error: {stderr.decode()}")
            return None
            
    except Exception as e:
        print(f"✗ Error starting {service['name']}: {e}")
        return None

def check_service_health(service):
    """Check if a service is responding"""
    try:
        import requests
        response = requests.get(f"{service['url']}/health", timeout=5)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def main():
    """Main function to start all services"""
    print("=" * 60)
    print("NexusEnroll - Student Enrollment System")
    print("Starting all microservices...")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Change to the script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    processes = []
    failed_services = []
    
    # Start all services
    for service in SERVICES:
        process = start_service(service)
        if process:
            processes.append((service, process))
        else:
            failed_services.append(service['name'])
    
    if failed_services:
        print(f"\n✗ Failed to start: {', '.join(failed_services)}")
    
    if processes:
        print(f"\n✓ Successfully started {len(processes)} services")
        print("\nService URLs:")
        for service, _ in processes:
            print(f"  • {service['name']}: {service['url']}")
        
        print(f"\n🌐 Frontend available at: file://{script_dir}/frontend/index.html")
        print("\nDemo Credentials:")
        print("  • Admin: admin / admin123")
        print("  • Faculty: prof_smith / prof123") 
        print("  • Student: john_doe / student123")
        
        print("\nPress Ctrl+C to stop all services...")
        
        try:
            # Keep the main process running
            while True:
                time.sleep(1)
                
                # Check if any process has died
                for i, (service, process) in enumerate(processes):
                    if process.poll() is not None:
                        print(f"\n⚠️  {service['name']} has stopped unexpectedly")
                        # Try to restart
                        new_process = start_service(service)
                        if new_process:
                            processes[i] = (service, new_process)
                        else:
                            print(f"✗ Failed to restart {service['name']}")
                
        except KeyboardInterrupt:
            print("\n\nShutting down all services...")
            for service, process in processes:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                    print(f"✓ Stopped {service['name']}")
                except:
                    try:
                        process.kill()
                        print(f"✓ Force stopped {service['name']}")
                    except:
                        print(f"✗ Could not stop {service['name']}")
            
            print("All services stopped. Goodbye!")
    
    else:
        print("✗ No services could be started")
        sys.exit(1)

if __name__ == "__main__":
    main()
