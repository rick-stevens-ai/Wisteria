#!/bin/bash

# Wisteria Research Hypothesis Generator Installation Script

set -e  # Exit on any error

echo "=== Wisteria Research Hypothesis Generator Installation ==="
echo

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.7"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✓ Python $python_version detected (>= 3.7 required)"
else
    echo "✗ Python 3.7 or higher is required. Current version: $python_version"
    exit 1
fi

# Check if pip is available
echo "Checking pip availability..."
if command -v pip3 &> /dev/null; then
    echo "✓ pip3 found"
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    echo "✓ pip found"
    PIP_CMD="pip"
else
    echo "✗ pip not found. Please install pip first."
    exit 1
fi

# Install required packages
echo
echo "Installing required Python packages..."
echo

packages=(
    "openai>=1.0.0"
    "PyYAML>=6.0"
    "backoff>=2.0.0"
)

for package in "${packages[@]}"; do
    echo "Installing $package..."
    $PIP_CMD install "$package"
done

echo
echo "✓ All required packages installed successfully!"

# Make the script executable
echo "Making wisteria_v3.py executable..."
chmod +x wisteria_v3.py

# Check if environment variables are set
echo
echo "Checking environment variables..."

if [ -z "$OPENAI_API_KEY" ] && [ -z "$VLLM_API_KEY" ]; then
    echo "⚠️  Warning: Neither OPENAI_API_KEY nor VLLM_API_KEY environment variables are set."
    echo "   You'll need to set at least one of these depending on which models you want to use:"
    echo "   - OPENAI_API_KEY for OpenAI models (gpt41, o3, o4mini)"
    echo "   - VLLM_API_KEY for local/custom models (scout, qwen, llama, l31)"
    echo
    echo "   Example:"
    echo "   export OPENAI_API_KEY='your-openai-api-key-here'"
    echo "   export VLLM_API_KEY='your-vllm-api-key-here'"
else
    if [ ! -z "$OPENAI_API_KEY" ]; then
        echo "✓ OPENAI_API_KEY is set"
    fi
    if [ ! -z "$VLLM_API_KEY" ]; then
        echo "✓ VLLM_API_KEY is set"
    fi
fi

echo
echo "=== Installation Complete! ==="
echo
echo "Usage examples:"
echo "  python3 wisteria_v3.py --goal \"Your research question\" --model gpt41"
echo "  python3 wisteria_v3.py research_goal.txt --model scout"
echo
echo "Available models in model_servers.yaml:"
echo "  - gpt41    (OpenAI GPT-4.1)"
echo "  - o3       (OpenAI O3)"
echo "  - o4mini   (OpenAI O4-mini)"
echo "  - scout    (Scout model on rbh101)"
echo "  - qwen     (Qwen model on hcdgx2)"
echo "  - llama    (Llama 3.3 70B on rbdgx2)"
echo "  - l31      (Llama 3.1 8B on localhost)"
echo
echo "For help: python3 wisteria_v3.py --help"
echo