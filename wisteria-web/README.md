# Wisteria Web Application

A modern web interface for the Wisteria Research Hypothesis Generator, built with Flask and React.

## Features

- **Interactive Hypothesis Generation**: Create and refine scientific hypotheses through an intuitive web interface
- **Multi-Model Support**: Use different AI models (OpenAI, vLLM, custom endpoints) through YAML configuration
- **Session Management**: Save, load, and manage research sessions
- **Real-time Updates**: WebSocket support for live generation progress
- **Modern UI**: Clean, responsive interface built with React and Tailwind CSS
- **Database Storage**: Persistent storage of sessions and hypotheses

## Architecture

- **Backend**: Flask with SQLAlchemy, Flask-SocketIO
- **Frontend**: React with TypeScript, Tailwind CSS
- **Database**: SQLite (development) / PostgreSQL (production)
- **Real-time**: WebSocket communication for live updates

## Quick Start

### Prerequisites

- Python 3.7+
- Node.js 16+
- npm or yarn

### Option 1: Quick Start (Recommended)

Use the provided startup script to run both backend and frontend simultaneously:

```bash
cd wisteria-web
chmod +x start-services.sh
./start-services.sh
```

This will start:
- Backend API at `http://localhost:5001`
- Frontend UI at `http://localhost:3000`

### Shutting Down Services

To stop both services cleanly, use the shutdown script:

```bash
cd wisteria-web
chmod +x shutdown-services.sh
./shutdown-services.sh
```

This will:
- Gracefully terminate the Flask backend
- Stop the React development server
- Kill any processes using ports 3000 and 5001
- Provide feedback on what was terminated

### Option 2: Manual Setup

#### Backend Setup

1. **Navigate to backend directory**:
   ```bash
   cd wisteria-web/backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   export SCOUT_API_KEY="your-scout-api-key"
   ```

5. **Run the Flask server**:
   ```bash
   python run.py
   ```

The backend will be available at `http://localhost:5001`

#### Frontend Setup

1. **Navigate to frontend directory**:
   ```bash
   cd wisteria-web/frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Start the development server**:
   ```bash
   npm start
   ```

The frontend will be available at `http://localhost:3000`

## Usage

### 1. Create a New Session

1. Enter your research goal in the text area
2. Select an AI model from the dropdown
3. Click "Create Session"

### 2. Generate Hypotheses

1. Select a session from the left panel
2. Click "Generate First Hypothesis" to create your initial hypothesis
3. The system will use your selected AI model to generate a scientifically rigorous hypothesis

### 3. Refine Hypotheses

1. Review the generated hypothesis (title, description, hallmarks analysis, references)
2. Provide feedback in the text area
3. Click "Improve Hypothesis" to refine based on your feedback
4. Or click "Generate New Hypothesis" to create an alternative approach

### 4. Session Management

- All sessions are automatically saved
- Click on any session to view its hypotheses
- Sessions persist between browser sessions

## API Endpoints

### Sessions
- `GET /api/sessions` - List all sessions
- `POST /api/sessions` - Create new session
- `GET /api/sessions/<id>` - Get session details
- `DELETE /api/sessions/<id>` - Delete session

### Hypotheses
- `POST /api/sessions/<id>/hypotheses` - Generate initial hypothesis
- `POST /api/sessions/<id>/hypotheses/<hypothesis_id>/improve` - Improve hypothesis
- `POST /api/sessions/<id>/hypotheses/new` - Generate new hypothesis
- `GET /api/sessions/<id>/hypotheses` - List session hypotheses

### Models
- `GET /api/models` - List available models

### Health
- `GET /api/health` - Health check

## Configuration

### Model Configuration

Models are configured in `shared/model_servers.yaml`. The web application supports:

- **OpenAI Models**: GPT-4, GPT-3.5, O1, O1-mini
- **vLLM Models**: Local vLLM servers (like scout)
- **Custom Endpoints**: Any OpenAI-compatible API

Example configuration:
```yaml
servers:
  - server: "api.openai.com"
    shortname: "gpt4"
    openai_api_key: "${OPENAI_API_KEY}"
    openai_api_base: "https://api.openai.com/v1"
    openai_model: "gpt-4"

  - server: "localhost:9999"
    shortname: "scout"
    openai_api_key: "${SCOUT_API_KEY}"
    openai_api_base: "http://localhost:9999/v1"
    openai_model: "scout"
```

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `SCOUT_API_KEY`: Your scout API key (if using local models)
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SECRET_KEY`: Flask secret key (auto-generated in development)

## Development

### Backend Development

The backend follows Flask application factory pattern:

```
backend/
├── app/
│   ├── __init__.py      # Flask app factory
│   ├── models.py        # SQLAlchemy models
│   ├── routes.py        # API endpoints
│   └── services.py      # Core business logic
├── requirements.txt     # Python dependencies
└── run.py              # Application entry point
```

### Frontend Development

The frontend uses React with TypeScript:

```
frontend/
├── src/
│   ├── components/      # React components
│   ├── services/        # API client
│   ├── types/           # TypeScript interfaces
│   └── App.tsx          # Main application
├── package.json         # Node dependencies
└── tailwind.config.js   # Tailwind configuration
```

### Database

The application uses SQLAlchemy with automatic migrations. The database file (`wisteria.db`) is created automatically on first run.

## Production Deployment

### Using Docker

1. **Build the images**:
   ```bash
   docker-compose build
   ```

2. **Set environment variables**:
   ```bash
   export OPENAI_API_KEY="your-key"
   export DATABASE_URL="postgresql://user:pass@db:5432/wisteria"
   ```

3. **Run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

### Manual Deployment

1. **Backend**:
   ```bash
   cd backend
   pip install -r requirements.txt
   export FLASK_ENV=production
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

2. **Frontend**:
   ```bash
   cd frontend
   npm run build
   # Serve the build directory with nginx or similar
   ```

## Troubleshooting

### Common Issues

1. **API Connection Error**:
   - Ensure the Flask backend is running on port 5000
   - Check CORS settings in `backend/app/__init__.py`

2. **Model Configuration Error**:
   - Verify `shared/model_servers.yaml` exists and is valid
   - Check environment variables for API keys

3. **Database Issues**:
   - Delete `wisteria.db` to reset the database
   - Check file permissions in the backend directory

4. **Frontend Build Issues**:
   - Clear node_modules and reinstall: `rm -rf node_modules && npm install`
   - Check TypeScript compilation errors

### Logs

- Backend logs are printed to console
- Frontend errors appear in browser console
- Database queries can be enabled with `SQLALCHEMY_ECHO=True`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 