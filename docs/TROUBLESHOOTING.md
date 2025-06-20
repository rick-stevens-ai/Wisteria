# Wisteria v5.0 - Troubleshooting Guide

## Table of Contents
1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Interface Issues](#interface-issues)
4. [API and Model Problems](#api-and-model-problems)
5. [PDF Generation Issues](#pdf-generation-issues)
6. [Session Management Problems](#session-management-problems)
7. [Performance Issues](#performance-issues)
8. [Platform-Specific Issues](#platform-specific-issues)
9. [Error Messages](#error-messages)
10. [Advanced Troubleshooting](#advanced-troubleshooting)

## Common Issues

### Application Won't Start

#### Symptom: `python curses_wisteria_v5.py` fails immediately

**Possible Causes & Solutions**:

1. **Missing Dependencies**
   ```bash
   # Error: ModuleNotFoundError: No module named 'openai'
   pip install openai pyyaml backoff reportlab
   ```

2. **Python Version Too Old**
   ```bash
   # Check version
   python --version
   # Should be 3.7 or higher
   ```

3. **Missing Model Configuration**
   ```bash
   # Error: Model 'gpt41' not found
   # Solution: Check model_servers.yaml exists and contains your model
   ```

4. **Invalid Command Line Arguments**
   ```bash
   # Correct usage
   python curses_wisteria_v5.py --goal "Your question" --model gpt41
   ```

### Terminal Display Problems

#### Symptom: Interface looks broken, text cut off, or garbled

**Solutions**:

1. **Increase Terminal Size**
   - Minimum: 80x24 characters
   - Recommended: 120x40 characters
   - Check current size: `echo $COLUMNS x $LINES`

2. **Enable Color Support**
   ```bash
   # Check if colors are supported
   echo $TERM
   # Should show something like 'xterm-256color'
   
   # Enable colors if needed
   export TERM=xterm-256color
   ```

3. **Fix Character Encoding**
   ```bash
   # Ensure UTF-8 support
   export LANG=en_US.UTF-8
   export LC_ALL=en_US.UTF-8
   ```

## Installation Problems

### Dependency Installation Failures

#### ReportLab Installation Issues

**Common Error**: 
```
ERROR: Failed building wheel for reportlab
```

**Solutions**:

1. **macOS**: Install system dependencies
   ```bash
   # Install Xcode command line tools
   xcode-select --install
   
   # Install via Homebrew if available
   brew install freetype
   
   # Then install reportlab
   pip install reportlab
   ```

2. **Ubuntu/Debian**:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-dev python3-pip build-essential
   sudo apt-get install libfreetype6-dev
   pip install reportlab
   ```

3. **Windows**:
   ```bash
   # Use pre-compiled wheel
   pip install --upgrade pip
   pip install reportlab
   
   # If still failing, try conda
   conda install reportlab
   ```

#### OpenAI Library Issues

**Error**: `ImportError: cannot import name 'OpenAI' from 'openai'`

**Solution**: Update to latest OpenAI library
```bash
pip install --upgrade openai
# Should be version 1.0 or higher
```

### API Key Configuration

#### Missing API Keys

**Error**: `Authentication failed. Check your API key.`

**Solutions**:

1. **Set Environment Variables**:
   ```bash
   # For OpenAI
   export OPENAI_API_KEY="your-api-key-here"
   
   # For local models
   export VLLM_API_KEY="your-vllm-key-here"
   ```

2. **Check model_servers.yaml**:
   ```yaml
   gpt41:
     model_name: "gpt-4"
     api_base: "https://api.openai.com/v1"
     api_key_env: "OPENAI_API_KEY"
   ```

3. **Verify API Key**:
   ```bash
   # Test OpenAI key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

## Interface Issues

### Keyboard Not Working

#### Keys Don't Respond or Do Wrong Actions

**Solutions**:

1. **Try Alternative Keys**:
   - Use `j/k` instead of arrow keys
   - Use `d/u` instead of Page Up/Down
   - Use `Esc` to reset to normal mode

2. **Check Terminal Type**:
   ```bash
   echo $TERM
   # Should show a capable terminal type
   ```

3. **Test Basic Input**:
   - Press `q` to see if quit works
   - Try typing letters during feedback mode
   - Verify terminal has focus

4. **Platform-Specific Fixes**:
   - **Mac**: Try `fn + arrow keys`
   - **SSH**: Enable key forwarding
   - **tmux/screen**: Check key binding conflicts

### Display Corruption

#### Text Overlapping, Wrong Colors, or Layout Issues

**Immediate Fixes**:

1. **Refresh Display**: Resize terminal window slightly
2. **Restart Application**: Press `q` and restart
3. **Clear Terminal**: Run `clear` before starting

**Permanent Solutions**:

1. **Terminal Settings**:
   ```bash
   # Ensure proper terminal type
   export TERM=xterm-256color
   
   # Check terminal capabilities
   infocmp | grep colors
   ```

2. **Font Issues**:
   - Use monospace font
   - Avoid complex Unicode characters
   - Test with standard terminal fonts

### Status Messages Not Clearing

#### Status bar shows old messages or doesn't update

**Causes & Solutions**:

1. **Persistent Messages**: Some messages stay until user action
   - Press any navigation key to clear
   - Check if operation is still in progress

2. **Display Refresh Issues**:
   - Resize terminal slightly
   - Press `Ctrl+L` if supported
   - Restart application

## API and Model Problems

### Model Connection Failures

#### Error: "Failed to connect to model server"

**Diagnostic Steps**:

1. **Check Internet Connection**:
   ```bash
   ping api.openai.com
   ```

2. **Verify Model Configuration**:
   ```bash
   # Check if model exists in config
   grep -A 5 "gpt41:" model_servers.yaml
   ```

3. **Test API Endpoint**:
   ```bash
   curl -v https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

### Rate Limiting Issues

#### Error: "Rate limit exceeded"

**Solutions**:

1. **Wait and Retry**: Rate limits reset over time
2. **Check Usage**: Monitor API usage in provider dashboard
3. **Upgrade Plan**: Consider higher rate limit plans
4. **Batch Operations**: Reduce frequency of requests

### Model Response Issues

#### Generated Text Is Garbled or Invalid

**Possible Causes**:

1. **Model Overload**: Try different model or wait
2. **Temperature Settings**: Check if temperature is appropriate
3. **Prompt Length**: Very long prompts may cause issues

**Solutions**:

1. **Try Different Model**:
   ```bash
   python curses_wisteria_v5.py --goal "test" --model scout
   ```

2. **Simplify Research Goal**:
   - Shorter, clearer questions
   - Avoid special characters
   - Use standard English

## PDF Generation Issues

### ReportLab Errors

#### Error: "PDF generation requires reportlab"

**Solution**:
```bash
pip install reportlab
```

#### Error: "Failed to generate PDF"

**Diagnostic Steps**:

1. **Check File Permissions**:
   ```bash
   # Test write access
   touch test_pdf.pdf
   rm test_pdf.pdf
   ```

2. **Check Disk Space**:
   ```bash
   df -h .
   ```

3. **Test Basic PDF Generation**:
   ```bash
   python curses_wisteria_v5.py --test-feedback
   ```

### PDF Content Issues

#### Missing Sections or Formatting Problems

**Solutions**:

1. **Verify Hypothesis Data**: Ensure hypothesis has all required fields
2. **Check Feedback History**: Verify feedback_history array exists
3. **Unicode Issues**: Some characters may not render properly

## Session Management Problems

### Session Loading Failures

#### Error: "Failed to load session"

**Diagnostic Steps**:

1. **Check File Exists**:
   ```bash
   ls -la your_session.json
   ```

2. **Validate JSON Format**:
   ```bash
   python -m json.tool your_session.json
   ```

3. **Check File Permissions**:
   ```bash
   chmod 644 your_session.json
   ```

### Data Migration Issues

#### Old Sessions Won't Load Properly

**Solutions**:

1. **Automatic Migration**: v5.0 should auto-migrate old formats
2. **Manual Backup**: Copy old session files before loading
3. **Check Log Messages**: Look for migration warnings

### Session Corruption

#### Partial Data Loss or Corrupted Sessions

**Recovery Steps**:

1. **Check Backup Files**: Look for `.bak` files
2. **Partial Recovery**: Extract working hypotheses manually
3. **Start Fresh**: Begin new session if corruption is severe

## Performance Issues

### Slow Response Times

#### Application Feels Sluggish

**Causes & Solutions**:

1. **Large Session Size**:
   - Limit to ~50 hypotheses per session
   - Export completed work to PDF
   - Start new sessions for different topics

2. **Network Latency**:
   - Check internet speed
   - Try different API endpoints
   - Use local models if available

3. **Terminal Performance**:
   - Reduce terminal size if very large
   - Close other terminal applications
   - Use hardware acceleration if available

### Memory Usage

#### High Memory Consumption

**Solutions**:

1. **Limit Feedback History**: Very long feedback chains use more memory
2. **Restart Periodically**: Restart application for long sessions
3. **Monitor Usage**: Use `top` or `htop` to monitor

## Platform-Specific Issues

### macOS Issues

#### Keyboard Problems
- **Missing Page Up/Down**: Use `d/u` instead
- **Function Keys**: Try `fn + arrow keys`
- **Terminal App**: Use iTerm2 for better compatibility

#### Installation Issues
```bash
# If pip install fails
brew install python3
pip3 install --upgrade pip
```

### Windows Issues

#### Terminal Compatibility
- **Use Windows Terminal**: Better than Command Prompt
- **PowerShell**: Usually works well
- **WSL**: Consider Windows Subsystem for Linux

#### Path Issues
```batch
# Use full path if needed
python C:\path\to\curses_wisteria_v5.py --goal "test" --model gpt41
```

### Linux Issues

#### Missing Dependencies
```bash
# Ubuntu/Debian
sudo apt-get install python3-curses python3-dev

# CentOS/RHEL
sudo yum install python3-devel ncurses-devel
```

#### SSH Issues
- **X11 Forwarding**: Not needed for curses interface
- **Terminal Type**: Ensure proper TERM variable
- **Key Codes**: May need terminal-specific configuration

## Error Messages

### Common Error Messages and Solutions

#### "addwstr() returned ERR"
**Cause**: Text doesn't fit in terminal boundaries
**Solution**: Increase terminal size or restart application

#### "Invalid authentication credentials"
**Cause**: Wrong or missing API key
**Solution**: Check API key environment variables

#### "Model 'xyz' not found"
**Cause**: Model not configured in model_servers.yaml
**Solution**: Add model configuration or use existing model

#### "JSON decode error"
**Cause**: Corrupted session file or invalid API response
**Solution**: Check file format or try different model

#### "Permission denied"
**Cause**: Cannot write to current directory
**Solution**: Change to writable directory or fix permissions

## Advanced Troubleshooting

### Debug Mode

#### Enable Verbose Logging

Add this to the beginning of curses_wisteria_v5.py:
```python
import logging
logging.basicConfig(filename='wisteria_debug.log', level=logging.DEBUG)
```

### Manual Session Repair

#### Fix Corrupted Session File

```python
import json

# Load and inspect session
with open('corrupted_session.json', 'r') as f:
    data = json.load(f)

# Check structure
print("Keys:", data.keys())
print("Hypotheses count:", len(data.get('hypotheses', [])))

# Repair if needed
for hyp in data.get('hypotheses', []):
    if 'feedback_history' not in hyp:
        hyp['feedback_history'] = []

# Save repaired version
with open('repaired_session.json', 'w') as f:
    json.dump(data, f, indent=2)
```

### Network Diagnostics

#### Test API Connectivity

```bash
# Test OpenAI API
curl -v https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json"

# Test local model server
curl -v http://localhost:8000/v1/models \
  -H "Authorization: Bearer $VLLM_API_KEY"
```

### Terminal Diagnostics

#### Check Terminal Capabilities

```bash
# Check terminal type and capabilities
echo "TERM: $TERM"
echo "COLUMNS: $COLUMNS"
echo "LINES: $LINES"

# Test color support
tput colors

# Test special keys
read -n1 -s key; echo "Key code: $(printf '%d' "'$key")"
```

## Getting Help

### Log Files

Check these locations for error information:
- Current directory: `wisteria_debug.log` (if debug mode enabled)
- System logs: `/var/log/` (Linux/macOS)
- Terminal output: Copy any error messages

### Reporting Issues

When reporting problems, include:

1. **System Information**:
   - Operating system and version
   - Python version (`python --version`)
   - Terminal emulator and version

2. **Error Details**:
   - Exact error message
   - Steps to reproduce
   - Command line used

3. **Configuration**:
   - Model being used
   - Session size (number of hypotheses)
   - API provider (OpenAI, local, etc.)

4. **Log Files**:
   - Any error logs
   - Debug output if available

### Contact Information

- **GitHub Issues**: https://github.com/rick-stevens-ai/Wisteria/issues
- **Documentation**: Check docs/ directory for additional help
- **Wiki**: Community-maintained troubleshooting tips

---

*For basic usage help, see [USER_GUIDE.md](USER_GUIDE.md)*

*For technical details, see [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md)*