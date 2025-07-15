# Wisteria Research Hypothesis Generator v6.0

Wisteria is an interactive research hypothesis generation tool that uses AI models to create, refine, and analyze scientific hypotheses based on research goals.

## What's New in v6.0

- **🎯 Focus Navigation System**: Revolutionary interface control with visual feedback
  - Left/Right arrows switch between hypothesis list and details pane
  - Visual [FOCUSED] indicators show active pane
  - Independent scrolling and navigation for each pane
  - Intuitive pane management for enhanced productivity

- **⚡ Performance Optimizations**: Eliminated screen flicker with selective rendering
  - Dirty flag system for intelligent component updates
  - Single refresh cycle prevents visual artifacts
  - 200ms timeout reduces CPU usage and improves responsiveness
  - Smooth, professional interface experience

- **📚 Semantic Scholar Integration**: Automated paper and abstract fetching
  - 'a' command fetches abstracts and PDFs for hypothesis references
  - Organized papers/abstracts directory structure
  - Progress tracking during paper retrieval
  - Seamless integration with research workflow

- **🖥️ Enhanced Curses Interface**: Refined multi-pane design from v5.0
  - Header pane with research goal and model information
  - Left pane for hypothesis navigation and selection
  - Right pane for detailed hypothesis viewing with scrolling
  - Status bar with real-time command feedback

- **📝 Comprehensive Feedback Tracking**: Complete history of all user feedback
  - Each hypothesis maintains a full feedback history
  - Timestamps and version tracking for all improvements
  - Professional PDF export includes complete feedback timeline

- **📄 Enhanced PDF Export**: Professional document generation with ReportLab
  - Comprehensive hypothesis documentation
  - Complete feedback history with timestamps
  - Version change tracking
  - Professional styling and formatting

- **⚡ Real-time Progress Tracking**: Live updates during hypothesis generation
  - Animated progress indicators
  - Threaded generation for non-blocking interface
  - Batch hypothesis generation with progress display

- **🧪 Experimental Validation Planning**: Dedicated section for each hypothesis
  - Specific experimental methodology
  - Controls and measurements
  - Timeline and expected outcomes

- **⌨️ Advanced Navigation**: Vim-style and arrow key navigation with focus control
  - Cross-platform keyboard compatibility
  - Intuitive scrolling and selection
  - Mac keyboard support (j/k/d/u keys)
  - Pane-specific navigation commands

## Features

- **Interactive Hypothesis Generation**: Generate creative and novel scientific hypotheses
- **Multi-Pane Interface**: Professional curses-based terminal interface with real-time navigation
- **Comprehensive Feedback Tracking**: Complete history of user feedback with timestamps and version tracking
- **Professional PDF Export**: Generate publication-ready documents with complete feedback history
- **Hypothesis Refinement**: Improve hypotheses based on user feedback with visual change highlighting
- **Multi-Model Support**: Configure multiple AI models through YAML configuration
- **Session Management**: Save, load, and resume hypothesis generation sessions
- **Batch Generation**: Generate multiple hypotheses with progress tracking
- **Scientific Rigor**: Evaluates hypotheses against five hallmarks of strong scientific hypotheses:
  - Testability (Falsifiability)
  - Specificity and Clarity
  - Grounded in Prior Knowledge
  - Predictive Power & Novel Insight
  - Parsimony (Principle of Simplicity)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd Wisteria
```

2. Install required dependencies:
```bash
pip install openai pyyaml backoff reportlab
```

3. (Optional) Run the installation script:
```bash
./install.sh
```

## Configuration

Configure your AI models in `model_servers.yaml`. The file supports various model providers including:
- Local models (LM Studio, vLLM)
- OpenAI models (GPT-4, O3, O4-mini)
- Custom API endpoints

### API Key Setup

1. **Copy the example configuration:**
   ```bash
   cp model_servers.example.yaml model_servers.yaml
   ```

2. **Set required environment variables:**
   ```bash
   # For OpenAI models
   export OPENAI_API_KEY="your-openai-api-key-here"
   
   # For local vLLM server (scout model)
   export SCOUT_API_KEY="your-scout-api-key-here"
   ```

3. **For persistent environment variables, add to your shell profile:**
   ```bash
   # Add to ~/.bashrc, ~/.zshrc, or ~/.profile
   echo 'export OPENAI_API_KEY="your-openai-api-key-here"' >> ~/.zshrc
   echo 'export SCOUT_API_KEY="your-scout-api-key-here"' >> ~/.zshrc
   source ~/.zshrc
   ```

**Important:** Never commit your actual API keys to version control. The `model_servers.yaml` file uses environment variables to keep your keys secure.

## Usage

### Basic Usage

Generate hypotheses from a research goal file:
```bash
python curses_wisteria_v6.py research_goal.txt --model gpt41
```

Generate hypotheses with direct text input:
```bash
python curses_wisteria_v6.py --goal "How can we improve renewable energy storage efficiency?" --model scout
```

Generate multiple hypotheses at startup:
```bash
python curses_wisteria_v6.py --goal "What causes neurodegenerative diseases?" --model gpt41 --num-hypotheses 5
```

Resume a previous session:
```bash
python curses_wisteria_v6.py --resume hypotheses_interactive_gpt41_20250531_165238.json --model gpt41
```

### Interactive Commands

During a session, use these keyboard commands:
- `f` - Provide feedback to improve the current hypothesis
- `n` - Generate a new hypothesis different from previous ones
- `l` - Load from a JSON file a previous session log
- `x` - Save current session to a JSON file with custom filename
- `t` - Add/edit personal notes for the current hypothesis
- `v` - View the titles of hypotheses in current session
- `s` - Select a hypothesis to continue to refine
- `h` - Toggle hallmarks analysis display
- `r` - Toggle references display
- `a` - Fetch abstracts and papers from Semantic Scholar for current hypothesis references
- `u` - Update hypothesis with information from downloaded abstracts
- `b` - Browse and view downloaded abstracts
- `c` - Score hypothesis hallmarks (1-5 scale) using AI evaluation
- `p` - Print current hypothesis to PDF document
- `q` - Quit and save all hypotheses

### Navigation Commands

- `←/→` - Switch focus between hypothesis list and details pane
- `↑/↓` - Navigate between hypotheses (when list focused) or scroll details (when details focused)
- `Page Up/Page Down` - Scroll within focused pane
- `Enter` - Select highlighted hypothesis
- `Esc` - Cancel current operation

### Testing

Test the feedback tracking functionality:
```bash
python curses_wisteria_v6.py --test-feedback
```

### Command Line Options

- `research_goal_file` - Text file containing the research goal/question
- `--goal` - Specify the research goal directly as a command line argument
- `--resume` - Resume from a previous session JSON file
- `--model` - Model shortname from model_servers.yaml (required for normal operation)
- `--output` - Output JSON file (default: hypotheses_<timestamp>.json)
- `--num-hypotheses` - Number of initial hypotheses to generate (default: 1)
- `--test-feedback` - Run feedback tracking test and generate sample PDF

## Examples

```bash
# Generate hypotheses from file
python curses_wisteria_v6.py research_goal.txt --model gpt41

# Direct goal input with multiple hypotheses
python curses_wisteria_v6.py --goal "What causes neurodegenerative diseases?" --model scout --num-hypotheses 3

# Resume previous session
python curses_wisteria_v6.py --resume previous_session.json --model gpt41

# Custom output file with batch generation
python curses_wisteria_v6.py --goal "Climate change mitigation strategies" --model llama --num-hypotheses 5 --output climate_hypotheses.json

# Test feedback functionality
python curses_wisteria_v6.py --test-feedback
```

## Output

The tool generates several types of output:

### JSON Session Files
- Session metadata (research goal, model used, timestamps)
- Generated hypotheses with versions and improvements
- Complete feedback history with timestamps and version tracking
- Detailed analysis against scientific hallmarks
- Scientific references and annotations

### PDF Documents
- Professional hypothesis documentation
- Complete research goal context
- Detailed hypothesis description and experimental validation
- **Complete feedback history** with timestamps and version changes
- Comprehensive hallmarks analysis
- Scientific references with annotations
- Generation metadata and timestamps

## Requirements

- Python 3.7+
- OpenAI API library
- PyYAML
- backoff
- curses (included with Python on Unix systems)
- reportlab (for PDF generation)

Install dependencies:
```bash
pip install openai pyyaml backoff reportlab
```

## Feedback Tracking Feature

Version 5.0 introduced comprehensive feedback tracking, enhanced in v6.0:

- **Complete History**: Every piece of user feedback is preserved with timestamps
- **Version Tracking**: See exactly how feedback led to specific improvements
- **PDF Integration**: All feedback history appears in exported PDF documents
- **Migration Support**: Automatically upgrades older session files
- **Professional Display**: Formatted feedback sections with clear version progression

The feedback history shows:
- Original feedback text
- When feedback was provided
- Which version it improved (e.g., "1.0 → 1.1")
- Complete timeline of hypothesis evolution

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Version History

- **v6.0**: Focus navigation system, performance optimizations, Semantic Scholar integration
- **v5.0**: Curses multi-pane interface, comprehensive feedback tracking, enhanced PDF export
- **v4.0**: Enhanced visual feedback, toggle controls, improved session management
- **v3.0**: Interactive mode, session management, hypothesis refinement
- **v2.0**: Multi-model support, improved generation
- **v1.0**: Initial release