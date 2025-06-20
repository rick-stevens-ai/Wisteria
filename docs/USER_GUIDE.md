# Wisteria v5.0 Curses Interface - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Interface Overview](#interface-overview)
3. [Basic Usage](#basic-usage)
4. [Navigation Guide](#navigation-guide)
5. [Interactive Commands](#interactive-commands)
6. [Feedback System](#feedback-system)
7. [PDF Export](#pdf-export)
8. [Session Management](#session-management)
9. [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### System Requirements
- Python 3.7 or higher
- Terminal with color support
- Minimum terminal size: 80x24 characters
- Recommended: 120x40 for optimal experience

### Installation
```bash
pip install openai pyyaml backoff reportlab
```

### First Launch
```bash
python curses_wisteria_v5.py --goal "Your research question" --model gpt41
```

## Interface Overview

Wisteria v5.0 features a professional multi-pane curses interface:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Wisteria v5.0 | Model: GPT-4 | Goal: How can we improve solar efficiency?   │
├───────────────────────┬─────────────────────────────────────────────────────┤
│                       │                                                     │
│     HYPOTHESIS        │              HYPOTHESIS DETAILS                     │
│        LIST           │                                                     │
│                       │  Title: Novel Perovskite Solar Cell Design         │
│  1. Novel Perovskite  │                                                     │
│     Solar Cell ►      │  Description:                                       │
│  2. Quantum Dot       │  This hypothesis proposes using a novel tandem     │
│     Enhancement       │  perovskite structure that combines traditional    │
│  3. Bio-inspired      │  silicon with advanced perovskite materials to     │
│     Light Capture     │  achieve higher efficiency rates...                │
│                       │                                                     │
│                       │  Experimental Validation:                          │
│                       │  The hypothesis can be tested by constructing      │
│                       │  prototype solar cells using the proposed design   │
│                       │  and measuring their efficiency under controlled   │
│                       │  laboratory conditions...                          │
│                       │                                                     │
├───────────────────────┴─────────────────────────────────────────────────────┤
│ f:feedback n:new l:load v:view s:select h:hallmarks r:refs p:pdf q:quit     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Interface Components

#### 1. Header Pane (Top)
- **Research Goal**: Your current research question
- **Model Information**: Which AI model is being used
- **Session Status**: Current mode and activity

#### 2. Left Pane - Hypothesis List
- **Numbered List**: All generated hypotheses
- **Selection Indicator**: `►` shows currently selected hypothesis
- **Navigation**: Use arrow keys or vim-style keys to move
- **Color Coding**: Different colors for original vs. improved hypotheses

#### 3. Right Pane - Hypothesis Details
- **Title**: Hypothesis name
- **Description**: Detailed explanation
- **Experimental Validation**: How to test the hypothesis
- **Hallmarks Analysis**: Scientific rigor evaluation (toggleable)
- **References**: Supporting scientific literature (toggleable)
- **Feedback History**: Complete feedback timeline (in v5.0)

#### 4. Status Bar (Bottom)
- **Available Commands**: Quick reference for keyboard shortcuts
- **Real-time Feedback**: Status messages and progress indicators
- **Auto-clearing**: Messages automatically disappear after 3 seconds

## Basic Usage

### Starting a New Session

1. **From Command Line Goal**:
   ```bash
   python curses_wisteria_v5.py --goal "How can CRISPR be improved?" --model gpt41
   ```

2. **From Text File**:
   ```bash
   python curses_wisteria_v5.py research_goal.txt --model scout
   ```

3. **Generate Multiple Hypotheses**:
   ```bash
   python curses_wisteria_v5.py --goal "What causes aging?" --model gpt41 --num-hypotheses 5
   ```

### Resuming a Session

```bash
python curses_wisteria_v5.py --resume previous_session.json --model gpt41
```

## Navigation Guide

### Hypothesis Navigation
| Key | Action |
|-----|--------|
| `↑` or `k` | Move to previous hypothesis |
| `↓` or `j` | Move to next hypothesis |
| `Enter` | Select current hypothesis |
| `Home` | Go to first hypothesis |
| `End` | Go to last hypothesis |

### Detail Pane Scrolling
| Key | Action |
|-----|--------|
| `Page Up` or `u` | Scroll up in details |
| `Page Down` or `d` | Scroll down in details |
| `Ctrl+Home` | Scroll to top of details |
| `Ctrl+End` | Scroll to bottom of details |

### Cross-Platform Keys
- **Mac Users**: Use `j/k` for up/down, `d/u` for page up/down
- **Windows/Linux**: Standard arrow keys and Page Up/Down work
- **Universal**: All vim-style keys work on all platforms

## Interactive Commands

### Core Commands

#### `f` - Provide Feedback
1. Press `f` to enter feedback mode
2. Type your feedback text
3. Press `Enter` to submit or `Esc` to cancel
4. The system will generate an improved hypothesis
5. Feedback is automatically tracked with timestamps

**Example Feedback**:
- "Make the hypothesis more specific to Type 2 diabetes"
- "Add more details about the experimental methodology"
- "Include potential side effects and limitations"

#### `n` - Generate New Hypothesis
- Creates a completely new hypothesis different from existing ones
- Takes into account all previous hypotheses to ensure novelty
- Shows progress indicator during generation

#### `p` - Export to PDF
- Generates professional PDF document
- Includes complete feedback history
- Saves with descriptive filename
- Shows success/failure status

### Session Management Commands

#### `l` - Load Session
1. Press `l` to enter filename
2. Type the JSON session filename
3. Press `Enter` to load or `Esc` to cancel
4. Hypotheses are merged into current session

#### `x` - Save Session
1. Press `x` to save current session
2. Type desired filename (without .json extension)
3. Press `Enter` to save or `Esc` to cancel
4. Session saved with all hypotheses and feedback history
5. Automatic .json extension added if not provided

#### `t` - Notes
1. Press `t` to add/edit notes for current hypothesis
2. Type your personal notes and observations
3. Use arrow keys to navigate within text
4. Press `Enter` to save or `Esc` to cancel
5. Notes are preserved across all versions of the hypothesis
6. Notes appear in both interface and PDF exports

**Notes Features**:
- **Personal Observations**: Add your own insights and thoughts
- **Research Context**: Note connections to other work or ideas
- **Todo Items**: Track what needs to be investigated further
- **Version Persistence**: Notes carry forward to improved versions
- **Editing Support**: Cursor navigation and text editing
- **Visual Display**: Highlighted section in hypothesis details
- **PDF Integration**: Professional formatting in exported documents

#### `s` - Select Hypothesis
1. Press `s` to choose by number
2. Enter hypothesis number (e.g., "3")
3. Press `Enter` to select or `Esc` to cancel
4. Jumps directly to that hypothesis

#### `v` - View All Titles
- Shows popup with all hypothesis titles
- Grouped by hypothesis number
- Shows version information
- Press any key to return to main interface

### Display Toggle Commands

#### `h` - Toggle Hallmarks Analysis
- Shows/hides scientific hallmarks evaluation
- Includes testability, specificity, grounded knowledge, etc.
- Helps assess scientific rigor

#### `r` - Toggle References
- Shows/hides scientific references
- Includes citations and annotations
- Valuable for research validation

#### `q` - Quit and Save
- Saves current session to JSON file
- Preserves all hypotheses and feedback history
- Shows final save location

## Feedback System

### How Feedback Works

1. **Provide Feedback**: Press `f` and enter your comments
2. **Automatic Tracking**: Every feedback is saved with timestamp
3. **Version Control**: Each improvement creates a new version
4. **History Preservation**: Complete feedback timeline maintained

### Types of Effective Feedback

#### Specificity Feedback
```
"Make this hypothesis more specific to cardiovascular disease 
rather than general health"
```

#### Methodology Feedback
```
"Add more details about the control groups and statistical 
analysis methods"
```

#### Scope Feedback
```
"Consider the ethical implications and potential limitations 
of this approach"
```

### Feedback History Display

In the hypothesis details pane, you'll see:
```
Feedback History:
1. "Make more specific to Type 2 diabetes" (Jan 15, 2024 - v1.0 → v1.1)
2. "Add control group details" (Jan 15, 2024 - v1.1 → v1.2)
3. "Include potential side effects" (Jan 15, 2024 - v1.2 → v1.3)
```

## PDF Export

### What's Included in PDFs

1. **Header Information**
   - Research goal
   - Hypothesis title and version
   - Generation timestamp

2. **Core Content**
   - Detailed description
   - Experimental validation plan
   - Improvements made (if applicable)

3. **Feedback History** ⭐ New in v5.0
   - Complete feedback timeline
   - Timestamps for each feedback
   - Version progression tracking

4. **Scientific Analysis**
   - Hallmarks evaluation
   - Scientific references with annotations

5. **Professional Formatting**
   - Styled headers and sections
   - Proper typography
   - Clean, publication-ready layout

### PDF Export Process

1. Select hypothesis you want to export
2. Press `p` for PDF export
3. Wait for "PDF generated successfully" message
4. File saved as `hypothesis_[title]_[timestamp].pdf`

## Session Management

### Automatic Saving
- Sessions auto-save when you quit (`q`)
- Filename format: `hypotheses_interactive_[model]_[timestamp].json`
- All feedback history preserved

### Manual Session Loading
- Use `l` command during session
- Merges loaded hypotheses with current ones
- Maintains complete history and timestamps

### Session File Contents
```json
{
  "metadata": {
    "research_goal": "Your research question",
    "model_used": "gpt41",
    "start_time": "2024-01-15T10:30:00",
    "end_time": "2024-01-15T11:45:00"
  },
  "hypotheses": [
    {
      "title": "Hypothesis Title",
      "description": "Detailed description...",
      "feedback_history": [
        {
          "feedback": "User feedback text",
          "timestamp": "2024-01-15T10:35:00",
          "version_before": "1.0",
          "version_after": "1.1"
        }
      ]
    }
  ]
}
```

## Tips and Best Practices

### Getting Better Results

1. **Clear Research Goals**
   - Be specific about your research domain
   - Include context and constraints
   - Example: "How can we improve Type 2 diabetes treatment for elderly patients?"

2. **Effective Feedback**
   - Be specific about what needs improvement
   - Provide constructive suggestions
   - Focus on one aspect at a time

3. **Iterative Refinement**
   - Start with broad hypotheses
   - Gradually refine through feedback
   - Use multiple feedback rounds for complex topics

### Interface Tips

1. **Terminal Size**
   - Use at least 120x40 characters for best experience
   - Resize terminal if text appears cramped
   - Enable color support for better visual distinction

2. **Keyboard Efficiency**
   - Learn vim-style keys (`j/k/d/u`) for faster navigation
   - Use `Enter` to quickly select hypotheses
   - Remember `Esc` cancels any input operation

3. **Session Organization**
   - Use descriptive research goals
   - Save sessions frequently
   - Export important hypotheses to PDF for archiving

### Troubleshooting

#### Common Issues

1. **Text Cut Off**
   - Increase terminal size
   - Use horizontal scrolling if available

2. **Keys Not Working**
   - Try vim-style alternatives (`j/k` instead of arrows)
   - Check if terminal has proper key support

3. **PDF Generation Fails**
   - Install reportlab: `pip install reportlab`
   - Check file permissions in current directory

4. **Model Connection Issues**
   - Verify API keys are set correctly
   - Check model_servers.yaml configuration
   - Ensure internet connection is stable

### Performance Tips

1. **Large Sessions**
   - Use `s` command to jump to specific hypotheses
   - Consider splitting very large sessions
   - Export completed hypotheses to PDF

2. **Feedback History**
   - Long feedback histories may slow scrolling
   - Use Page Up/Down for faster navigation
   - Consider starting new sessions for unrelated topics

## Keyboard Reference Quick Card

| Command | Key | Description |
|---------|-----|-------------|
| **Navigation** | | |
| Move Up | `↑` or `k` | Previous hypothesis |
| Move Down | `↓` or `j` | Next hypothesis |
| Scroll Up | `Page Up` or `u` | Scroll details up |
| Scroll Down | `Page Down` or `d` | Scroll details down |
| **Actions** | | |
| Feedback | `f` | Provide improvement feedback |
| New Hypothesis | `n` | Generate new hypothesis |
| PDF Export | `p` | Export to PDF document |
| **Session** | | |
| Load Session | `l` | Load previous session |
| Save Session | `x` | Save current session with custom filename |
| Notes | `t` | Add/edit personal notes for current hypothesis |
| Select Hypothesis | `s` | Jump to hypothesis by number |
| View Titles | `v` | Show all hypothesis titles |
| **Display** | | |
| Toggle Hallmarks | `h` | Show/hide hallmarks analysis |
| Toggle References | `r` | Show/hide references |
| **System** | | |
| Quit | `q` | Save and exit |
| Cancel | `Esc` | Cancel current operation |

---

*For technical documentation and developer information, see [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md)*

*For troubleshooting help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md)*