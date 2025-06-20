#!/bin/bash

echo "Starting Wisteria Web Application..."
echo "=================================="

# Function to cleanup background processes
cleanup() {
    echo "Shutting down services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting Flask backend..."
cd backend
source venv/bin/activate
python run.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "Starting React frontend..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo "=================================="
echo "Services started!"
echo "Backend: http://localhost:5001"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop all services"
echo "=================================="

# Wait for background processes
wait 