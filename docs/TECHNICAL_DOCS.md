# Wisteria v5.0 - Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Data Structures](#data-structures)
4. [Curses Interface Implementation](#curses-interface-implementation)
5. [Feedback Tracking System](#feedback-tracking-system)
6. [PDF Generation](#pdf-generation)
7. [Session Management](#session-management)
8. [API Integration](#api-integration)
9. [Error Handling](#error-handling)
10. [Testing](#testing)
11. [Development Setup](#development-setup)

## Architecture Overview

Wisteria v5.0 follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Application                         │
│                 (curses_wisteria_v5.py)                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────── │
│  │ CursesInterface │  │ Hypothesis Gen  │  │ PDF Generation │
│  │                 │  │                 │  │                │
│  │ - Multi-pane UI │  │ - AI API calls  │  │ - ReportLab    │
│  │ - Input handling│  │ - JSON parsing  │  │ - Professional │
│  │ - Status mgmt   │  │ - Feedback proc │  │   formatting   │
│  └─────────────────┘  └─────────────────┘  └─────────────── │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────── │
│  │ Session Manager │  │ Feedback System │  │ Error Handling │
│  │                 │  │                 │  │                │
│  │ - JSON I/O      │  │ - History track │  │ - Safe display │
│  │ - Data migration│  │ - Version ctrl  │  │ - API retries  │
│  │ - Merging logic │  │ - Timestamps    │  │ - Graceful deg │
│  └─────────────────┘  └─────────────────┘  └─────────────── │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separation of Concerns**: UI, business logic, and data layers are clearly separated
2. **Modularity**: Each component can be tested and modified independently
3. **Error Resilience**: Comprehensive error handling at all levels
4. **Thread Safety**: UI remains responsive during AI API calls
5. **Data Integrity**: Robust data structures with migration support

## Core Components

### 1. CursesInterface Class

**Purpose**: Manages the entire terminal-based user interface

**Key Responsibilities**:
- Multi-pane layout management
- Real-time input handling
- Status message system
- Display rendering with error boundaries

**Core Methods**:
```python
class CursesInterface:
    def __init__(self, stdscr):
        """Initialize interface with terminal screen object"""
        
    def draw_header(self, research_goal, model_name):
        """Render header pane with research goal and model info"""
        
    def draw_hypothesis_list(self, all_hypotheses):
        """Render left pane with hypothesis navigation list"""
        
    def draw_hypothesis_details(self, hypothesis):
        """Render right pane with detailed hypothesis view"""
        
    def draw_status_bar(self, status_msg=None):
        """Render bottom status bar with commands and messages"""
        
    def safe_addstr(self, y, x, text, attr=0):
        """Safe text rendering with boundary checking"""
        
    def set_status(self, message, persistent=False, timeout=3.0):
        """Status message management with auto-clearing"""
```

### 2. Hypothesis Generation Engine

**Purpose**: Interface with AI models to generate and improve hypotheses

**Core Functions**:
```python
def generate_new_hypothesis(research_goal, previous_hypotheses, config):
    """Generate novel hypothesis different from existing ones"""
    
def improve_hypothesis(research_goal, current_hypothesis, user_feedback, config):
    """Improve existing hypothesis based on user feedback"""
    
def load_model_config(model_shortname):
    """Load AI model configuration from YAML"""
```

### 3. Session Management System

**Purpose**: Handle data persistence, loading, and merging

**Core Functions**:
```python
def save_session_to_json(all_hypotheses, research_goal, model_config, output_file):
    """Save complete session with metadata and feedback history"""
    
def load_session_from_json(filename):
    """Load session with automatic data migration"""
    
def merge_hypotheses(existing, loaded):
    """Merge hypothesis collections avoiding duplicates"""
```

## Data Structures

### Hypothesis Object Schema

```python
hypothesis = {
    # Core identification
    "hypothesis_number": 1,           # Unique identifier within session
    "version": "1.3",                 # Version string (major.minor)
    "type": "improvement",            # "original" | "improvement"
    
    # Content
    "title": "Hypothesis Title",
    "description": "Detailed description...",
    "experimental_validation": "How to test...",
    
    # Feedback tracking (NEW in v5.0)
    "feedback_history": [
        {
            "feedback": "User feedback text",
            "timestamp": "2024-01-15T10:35:00",
            "version_before": "1.0",
            "version_after": "1.1"
        }
    ],
    
    # Legacy support
    "user_feedback": "Latest feedback text",  # Backward compatibility
    
    # Scientific analysis
    "hallmarks": {
        "testability": "Analysis of falsifiability...",
        "specificity": "Analysis of clarity...",
        "grounded_knowledge": "Analysis of prior knowledge...",
        "predictive_power": "Analysis of novel insights...",
        "parsimony": "Analysis of simplicity..."
    },
    
    # References
    "references": [
        {
            "citation": "Author, A. (2024). Title. Journal, 1(1), 1-10.",
            "annotation": "How this supports the hypothesis..."
        }
    ],
    
    # Metadata
    "generation_timestamp": "2024-01-15T10:30:00",
    "original_hypothesis_id": 1,      # For improvements, points to original
    "improvements_made": "Summary of changes made..."
}
```

### Session Data Schema

```python
session_data = {
    "metadata": {
        "research_goal": "Research question text",
        "model_used": "gpt41",
        "model_config": {...},
        "start_time": "2024-01-15T10:00:00",
        "end_time": "2024-01-15T12:00:00",
        "version": "5.0",
        "total_hypotheses": 5
    },
    "hypotheses": [
        # Array of hypothesis objects
    ]
}
```

## Curses Interface Implementation

### Multi-Pane Layout System

The interface uses a calculated layout system:

```python
# Layout calculations
HEADER_HEIGHT = 4
STATUS_HEIGHT = 2
LIST_WIDTH = int(width * 0.35)  # 35% for hypothesis list
DETAIL_WIDTH = width - LIST_WIDTH - 1  # Remaining for details

# Pane boundaries
list_start_y = HEADER_HEIGHT
list_height = height - HEADER_HEIGHT - STATUS_HEIGHT
detail_start_y = HEADER_HEIGHT
detail_height = height - HEADER_HEIGHT - STATUS_HEIGHT
```

### Safe Text Rendering

Critical for preventing crashes from terminal size changes:

```python
def safe_addstr(self, y, x, text, attr=0):
    """Safely add string with boundary checking and encoding"""
    try:
        if 0 <= y < self.height and 0 <= x < self.width:
            # Truncate text to fit within boundaries
            max_width = self.width - x - 1
            if len(text) > max_width:
                text = text[:max_width-3] + "..."
            
            # Ensure ASCII encoding for terminal compatibility
            text = text.encode('ascii', 'replace').decode('ascii')
            self.stdscr.addstr(y, x, text, attr)
    except curses.error:
        # Ignore curses errors (terminal resize, etc.)
        pass
```

### Input Handling System

Robust keyboard input with cross-platform support:

```python
def handle_input(self, key):
    """Process keyboard input with fallback handling"""
    
    # Standard navigation
    if key in [curses.KEY_UP, ord('k')]:
        return "navigate_up"
    elif key in [curses.KEY_DOWN, ord('j')]:
        return "navigate_down"
    elif key in [curses.KEY_PPAGE, ord('u')]:
        return "scroll_up"
    elif key in [curses.KEY_NPAGE, ord('d')]:
        return "scroll_down"
    
    # Command keys
    elif key in [ord('f'), ord('F')]:
        return "feedback"
    elif key in [ord('n'), ord('N')]:
        return "new_hypothesis"
    # ... etc
```

### Status Message System

Auto-clearing status messages with timeout management:

```python
class StatusManager:
    def __init__(self):
        self.current_status = "Ready"
        self.status_timestamp = time.time()
        self.status_timeout = 3.0
        self.persistent_status = False
    
    def set_status(self, message, persistent=False, timeout=3.0):
        """Set status with optional persistence and timeout"""
        self.current_status = message
        self.status_timestamp = time.time()
        self.persistent_status = persistent
        self.status_timeout = timeout
    
    def clear_status_on_action(self):
        """Clear non-persistent status when user takes action"""
        if not self.persistent_status:
            self.current_status = "Ready"
    
    def update_status_display(self):
        """Auto-clear status after timeout"""
        if (not self.persistent_status and 
            time.time() - self.status_timestamp > self.status_timeout):
            self.current_status = "Ready"
```

## Feedback Tracking System

### Feedback History Implementation

The feedback system maintains complete history with metadata:

```python
def process_feedback(current_hypothesis, feedback_text, version_tracker):
    """Process user feedback and update history"""
    
    # Get current version info
    hypothesis_number = current_hypothesis["hypothesis_number"]
    current_version = current_hypothesis.get("version", "1.0")
    
    # Calculate new version
    version_tracker[hypothesis_number] += 1
    new_version = f"1.{version_tracker[hypothesis_number]}"
    
    # Create feedback entry
    feedback_entry = {
        "feedback": feedback_text,
        "timestamp": datetime.now().isoformat(),
        "version_before": current_version,
        "version_after": new_version
    }
    
    # Initialize or append to feedback history
    feedback_history = current_hypothesis.get("feedback_history", [])
    feedback_history.append(feedback_entry)
    
    return feedback_history, new_version
```

### Data Migration for Legacy Sessions

Automatic migration ensures compatibility:

```python
def migrate_feedback_data(hypothesis):
    """Migrate legacy feedback data to new structure"""
    
    if "feedback_history" not in hypothesis:
        hypothesis["feedback_history"] = []
        
        # Migrate old user_feedback if present
        if "user_feedback" in hypothesis and hypothesis["user_feedback"]:
            legacy_entry = {
                "feedback": hypothesis["user_feedback"],
                "timestamp": hypothesis.get("generation_timestamp", 
                                          datetime.now().isoformat()),
                "version_before": "1.0",
                "version_after": hypothesis.get("version", "1.1")
            }
            hypothesis["feedback_history"].append(legacy_entry)
    
    return hypothesis
```

## PDF Generation

### ReportLab Integration

Professional PDF generation with styled content:

```python
def generate_hypothesis_pdf(hypothesis, research_goal, output_filename=None):
    """Generate professional PDF with feedback history"""
    
    # Document setup
    doc = SimpleDocTemplate(output_filename, pagesize=letter,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Custom styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'],
                                fontSize=18, spaceAfter=30,
                                textColor=HexColor('#2E4057'),
                                alignment=1)
    
    # Feedback section styling
    feedback_style = ParagraphStyle('FeedbackStyle',
                                   parent=styles['Normal'],
                                   fontSize=10, spaceAfter=12,
                                   leftIndent=15, rightIndent=15,
                                   backColor=HexColor('#F8F9FA'),
                                   borderWidth=1,
                                   borderColor=HexColor('#DEE2E6'),
                                   borderPadding=8)
```

### Feedback History Rendering

```python
def render_feedback_history(story, feedback_history, styles):
    """Render feedback history section in PDF"""
    
    if not feedback_history:
        return
    
    story.append(Paragraph("Feedback History", heading_style))
    
    for i, feedback_entry in enumerate(feedback_history, 1):
        feedback_text = feedback_entry.get("feedback", "No feedback text")
        timestamp = feedback_entry.get("timestamp", "Unknown time")
        version_before = feedback_entry.get("version_before", "Unknown")
        version_after = feedback_entry.get("version_after", "Unknown")
        
        # Format timestamp
        formatted_time = format_timestamp(timestamp)
        
        # Add feedback entry with styling
        story.append(Paragraph(f"<b>Feedback #{i}</b>", feedback_meta_style))
        story.append(Paragraph(f"Provided: {formatted_time}", feedback_meta_style))
        story.append(Paragraph(f"Version updated: {version_before} → {version_after}", 
                              feedback_meta_style))
        story.append(Spacer(1, 6))
        story.append(Paragraph(feedback_text, feedback_style))
        story.append(Spacer(1, 15))
```

## Session Management

### JSON Serialization

Robust serialization with error handling:

```python
def save_session_to_json(all_hypotheses, research_goal, model_config, output_file):
    """Save session with comprehensive metadata"""
    
    session_data = {
        "metadata": {
            "research_goal": research_goal,
            "model_used": model_config.get("model_name", "unknown"),
            "model_config": model_config,
            "start_time": session_start_time,
            "end_time": datetime.now().isoformat(),
            "version": "5.0",
            "total_hypotheses": len(all_hypotheses),
            "feedback_entries": sum(len(h.get("feedback_history", [])) 
                                  for h in all_hypotheses)
        },
        "hypotheses": all_hypotheses
    }
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Failed to save session: {e}")
        return False
```

### Session Loading with Migration

```python
def load_session_from_json(filename):
    """Load session with automatic data structure migration"""
    
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        metadata = data.get("metadata", {})
        hypotheses = data.get("hypotheses", [])
        research_goal = metadata.get("research_goal", "")
        
        # Migrate data structures
        for hypothesis in hypotheses:
            hypothesis = migrate_feedback_data(hypothesis)
            hypothesis = ensure_required_fields(hypothesis)
        
        return research_goal, hypotheses, metadata
        
    except Exception as e:
        logging.error(f"Failed to load session: {e}")
        return None, None, None
```

## API Integration

### OpenAI Client Management

Robust API client with retry logic:

```python
@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def call_openai_api(messages, config):
    """Call OpenAI API with exponential backoff retry"""
    
    client = openai.OpenAI(
        api_key=config['api_key'],
        base_url=config['api_base']
    )
    
    # Prepare parameters
    params = {
        "model": config['model_name'],
        "messages": messages
    }
    
    # Add temperature for supported models
    if not config.get('skip_temperature', False):
        params["temperature"] = 0.8
    
    # Make API call
    response = client.chat.completions.create(**params)
    
    # Handle response
    if hasattr(response, 'choices'):
        return response.choices[0].message.content.strip()
    else:
        return response["choices"][0]["message"]["content"].strip()
```

### JSON Response Parsing

Safe parsing with fallback handling:

```python
def parse_hypothesis_response(generated_text):
    """Parse AI model response with robust error handling"""
    
    try:
        # Extract JSON from response
        json_start = generated_text.find('{')
        json_end = generated_text.rfind('}') + 1
        
        if json_start != -1 and json_end != 0:
            json_text = generated_text[json_start:json_end]
            # Clean control characters
            json_text = clean_json_string(json_text)
            hypothesis = json.loads(json_text)
            
            # Initialize feedback history
            if "feedback_history" not in hypothesis:
                hypothesis["feedback_history"] = []
                
            return hypothesis
        else:
            return create_error_hypothesis("No valid JSON found in response")
            
    except json.JSONDecodeError as e:
        return create_error_hypothesis(f"JSON parsing failed: {e}")
```

## Error Handling

### Curses Error Resilience

The interface handles various curses-related errors:

```python
def safe_curses_operation(operation, *args, **kwargs):
    """Wrapper for safe curses operations"""
    try:
        return operation(*args, **kwargs)
    except curses.error:
        # Terminal resize, invalid coordinates, etc.
        pass
    except UnicodeEncodeError:
        # Handle unicode issues in terminal display
        pass
    except Exception as e:
        logging.error(f"Unexpected curses error: {e}")
```

### API Error Handling

Comprehensive API error management:

```python
def handle_api_error(error, context="API call"):
    """Handle various API errors with appropriate responses"""
    
    if "authentication" in str(error).lower():
        return {
            "error": True,
            "message": "Authentication failed. Check your API key.",
            "retry": False
        }
    elif "rate limit" in str(error).lower():
        return {
            "error": True,
            "message": "Rate limit exceeded. Please wait and try again.",
            "retry": True,
            "wait_time": 60
        }
    elif "timeout" in str(error).lower():
        return {
            "error": True,
            "message": "Request timed out. Check your connection.",
            "retry": True,
            "wait_time": 10
        }
    else:
        return {
            "error": True,
            "message": f"Unexpected error in {context}: {str(error)[:100]}",
            "retry": False
        }
```

## Testing

### Unit Testing Framework

```python
import unittest
from unittest.mock import Mock, patch

class TestFeedbackSystem(unittest.TestCase):
    
    def setUp(self):
        self.sample_hypothesis = {
            "hypothesis_number": 1,
            "version": "1.0",
            "feedback_history": []
        }
    
    def test_feedback_entry_creation(self):
        """Test creation of feedback history entries"""
        feedback_text = "Test feedback"
        entry = create_feedback_entry(feedback_text, "1.0", "1.1")
        
        self.assertEqual(entry["feedback"], feedback_text)
        self.assertEqual(entry["version_before"], "1.0")
        self.assertEqual(entry["version_after"], "1.1")
        self.assertIn("timestamp", entry)
    
    def test_feedback_history_migration(self):
        """Test migration of legacy feedback data"""
        legacy_hypothesis = {
            "user_feedback": "Legacy feedback",
            "version": "1.1"
        }
        
        migrated = migrate_feedback_data(legacy_hypothesis)
        
        self.assertIn("feedback_history", migrated)
        self.assertEqual(len(migrated["feedback_history"]), 1)
        self.assertEqual(migrated["feedback_history"][0]["feedback"], 
                        "Legacy feedback")

class TestCursesInterface(unittest.TestCase):
    
    @patch('curses.initscr')
    def test_interface_initialization(self, mock_initscr):
        """Test curses interface initialization"""
        mock_stdscr = Mock()
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        interface = CursesInterface(mock_stdscr)
        
        self.assertEqual(interface.height, 24)
        self.assertEqual(interface.width, 80)
        self.assertIsNotNone(interface.current_status)
```

### Integration Testing

```python
class TestSessionManagement(unittest.TestCase):
    
    def test_save_load_cycle(self):
        """Test complete save/load cycle preserves data"""
        original_hypotheses = [
            {
                "title": "Test Hypothesis",
                "feedback_history": [
                    {
                        "feedback": "Test feedback",
                        "timestamp": "2024-01-15T10:00:00",
                        "version_before": "1.0",
                        "version_after": "1.1"
                    }
                ]
            }
        ]
        
        # Save session
        filename = "test_session.json"
        save_session_to_json(original_hypotheses, "Test goal", {}, filename)
        
        # Load session
        goal, loaded_hypotheses, metadata = load_session_from_json(filename)
        
        # Verify data preservation
        self.assertEqual(len(loaded_hypotheses), 1)
        self.assertEqual(loaded_hypotheses[0]["title"], "Test Hypothesis")
        self.assertEqual(len(loaded_hypotheses[0]["feedback_history"]), 1)
        
        # Cleanup
        os.remove(filename)
```

## Development Setup

### Environment Setup

1. **Python Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

2. **Dependencies**:
   ```bash
   pip install openai pyyaml backoff reportlab
   pip install pytest pytest-mock  # For testing
   ```

3. **Configuration**:
   ```bash
   cp model_servers.yaml.example model_servers.yaml
   # Edit with your API keys and endpoints
   ```

### Development Workflow

1. **Code Structure**:
   ```
   curses_wisteria_v5.py    # Main application
   docs/                    # Documentation
   tests/                   # Unit tests
   examples/                # Example configurations
   ```

2. **Testing**:
   ```bash
   python -m pytest tests/
   python curses_wisteria_v5.py --test-feedback  # Integration test
   ```

3. **Code Quality**:
   ```bash
   python -m py_compile curses_wisteria_v5.py  # Syntax check
   pylint curses_wisteria_v5.py                # Code analysis
   ```

### Debugging

1. **Curses Debugging**:
   - Use `curses.wrapper()` for proper terminal restoration
   - Log to file instead of stdout when debugging
   - Test with different terminal sizes

2. **API Debugging**:
   - Enable request logging in OpenAI client
   - Test with different models and parameters
   - Verify JSON response parsing with edge cases

3. **Session Debugging**:
   - Validate JSON files with external tools
   - Test migration with various legacy formats
   - Verify data integrity after load/save cycles

### Performance Considerations

1. **Memory Management**:
   - Large sessions with many hypotheses
   - Feedback history can grow significantly
   - PDF generation memory usage

2. **Response Time**:
   - API call optimization
   - UI responsiveness during long operations
   - Efficient text rendering and scrolling

3. **Terminal Compatibility**:
   - Different terminal emulators
   - Various screen sizes and color support
   - Unicode and encoding handling

---

*For user documentation, see [USER_GUIDE.md](USER_GUIDE.md)*

*For troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)*