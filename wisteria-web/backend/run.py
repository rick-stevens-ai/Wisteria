from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("Starting Wisteria Web API...")
    print("API will be available at: http://localhost:5001")
    print("WebSocket support enabled for real-time updates")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True) 