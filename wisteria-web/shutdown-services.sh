#!/bin/bash

# Wisteria Web Services Shutdown Script
# This script shuts down both the frontend and backend services

echo "🛑 Shutting down Wisteria Web Services..."

# Function to kill processes by pattern
kill_processes() {
    local pattern="$1"
    local description="$2"
    
    echo "Looking for $description processes..."
    
    # Find PIDs of processes matching the pattern
    pids=$(pgrep -f "$pattern" 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "Found $description processes with PIDs: $pids"
        echo "Terminating $description processes..."
        
        # Kill the processes gracefully first
        echo "$pids" | xargs -r kill -TERM 2>/dev/null
        
        # Wait a moment for graceful shutdown
        sleep 2
        
        # Check if processes are still running and force kill if necessary
        remaining_pids=$(pgrep -f "$pattern" 2>/dev/null)
        if [ -n "$remaining_pids" ]; then
            echo "Force killing remaining $description processes..."
            echo "$remaining_pids" | xargs -r kill -KILL 2>/dev/null
        fi
        
        echo "✅ $description processes terminated"
    else
        echo "ℹ️  No $description processes found"
    fi
}

# Kill backend processes (Flask/Python)
kill_processes "python.*run.py" "Backend (Flask)"

# Kill frontend processes (React/Node)
kill_processes "react-scripts.*start" "Frontend (React)"

# Kill any remaining Node.js processes that might be related
kill_processes "node.*react-scripts" "Node.js React"

# Kill any processes on the specific ports we use
echo "Checking for processes on ports 3000 and 5001..."

# Check port 3000 (frontend)
port_3000_pid=$(lsof -ti:3000 2>/dev/null)
if [ -n "$port_3000_pid" ]; then
    echo "Found process on port 3000 (PID: $port_3000_pid), terminating..."
    echo "$port_3000_pid" | xargs -r kill -TERM 2>/dev/null
    sleep 1
    echo "$port_3000_pid" | xargs -r kill -KILL 2>/dev/null
fi

# Check port 5001 (backend)
port_5001_pid=$(lsof -ti:5001 2>/dev/null)
if [ -n "$port_5001_pid" ]; then
    echo "Found process on port 5001 (PID: $port_5001_pid), terminating..."
    echo "$port_5001_pid" | xargs -r kill -TERM 2>/dev/null
    sleep 1
    echo "$port_5001_pid" | xargs -r kill -KILL 2>/dev/null
fi

echo ""
echo "🎉 Wisteria Web Services shutdown complete!"
echo ""
echo "To restart the services, run:"
echo "  ./start-services.sh"
echo ""
echo "Or start them individually:"
echo "  Backend:  cd backend && source venv/bin/activate && python run.py"
echo "  Frontend: cd frontend && npm start" 