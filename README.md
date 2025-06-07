# Wisteria Research Hypothesis Generator

Wisteria is an interactive research hypothesis generation tool that uses AI models to create, refine, and analyze scientific hypotheses based on research goals.

## Features

- **Interactive Hypothesis Generation**: Generate creative and novel scientific hypotheses
- **Hypothesis Refinement**: Improve hypotheses based on user feedback with change highlighting
- **Multi-Model Support**: Configure multiple AI models through YAML configuration
- **Session Management**: Save, load, and resume hypothesis generation sessions
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

2. Run the installation script:
```bash
./install.sh
```

## Configuration

Configure your AI models in `model_servers.yaml`. The file supports various model providers including:
- Local models (LM Studio, vLLM)
- OpenAI models (GPT-4, O3, O4-mini)
- Custom API endpoints

Set required environment variables:
- `VLLM_API_KEY` - For local/custom model servers
- `OPENAI_API_KEY` - For OpenAI models

## Usage

### Basic Usage

Generate hypotheses from a research goal file:
```bash
python wisteria_v3.py research_goal.txt --model gpt41
```

Generate hypotheses with direct text input:
```bash
python wisteria_v3.py --goal "How can we improve renewable energy storage efficiency?" --model scout
```

Resume a previous session:
```bash
python wisteria_v3.py --resume hypotheses_interactive_gpt41_20250531_165238.json --model gpt41
```

### Interactive Commands

During a session, use these commands:
- `\f` - Provide feedback to improve the current hypothesis
- `\n` - Generate a new hypothesis different from previous ones
- `\l` - Load from a JSON file a previous session log
- `\v` - View the titles of hypotheses in current session
- `\s` - Select a hypothesis to continue to refine
- `\q` - Quit and save all hypotheses

### Command Line Options

- `research_goal_file` - Text file containing the research goal/question
- `--goal` - Specify the research goal directly as a command line argument
- `--resume` - Resume from a previous session JSON file
- `--model` - Model shortname from model_servers.yaml (required)
- `--output` - Output JSON file (default: hypotheses_<timestamp>.json)

## Examples

```bash
# Generate hypotheses from file
python wisteria_v3.py research_goal.txt --model gpt41

# Direct goal input
python wisteria_v3.py --goal "What causes neurodegenerative diseases?" --model scout

# Resume previous session
python wisteria_v3.py --resume previous_session.json --model gpt41

# Custom output file
python wisteria_v3.py --goal "Climate change mitigation strategies" --model llama --output climate_hypotheses.json
```

## Output

The tool generates JSON files containing:
- Session metadata (research goal, model used, timestamps)
- Generated hypotheses with versions and improvements
- Detailed analysis against scientific hallmarks
- User feedback and refinement history

## Requirements

- Python 3.7+
- OpenAI API library
- PyYAML
- backoff

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]