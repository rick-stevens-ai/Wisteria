# Wisteria v6.0 Curses Interface - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Interface Overview](#interface-overview)
3. [Focus Navigation System](#focus-navigation-system)
4. [Basic Usage](#basic-usage)
5. [Navigation Guide](#navigation-guide)
6. [Interactive Commands](#interactive-commands)
7. [Paper and Abstract Fetching](#paper-and-abstract-fetching)
8. [Feedback System](#feedback-system)
9. [PDF Export](#pdf-export)
10. [Session Management](#session-management)
11. [Tips and Best Practices](#tips-and-best-practices)

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

Wisteria v6.0 features a professional multi-pane curses interface with focus navigation:

## Focus Navigation System

### Revolutionary Interface Control

Wisteria v6.0 introduces a revolutionary focus navigation system that allows you to control which pane is active and responsive to your keyboard input. This system provides:

#### Visual Focus Indicators
- **[FOCUSED] Labels**: Active panes show `[FOCUSED]` in their title bars
- **Clear Visual Feedback**: Always know which pane will respond to your commands
- **Instant Recognition**: No guessing which area is currently active

#### Independent Pane Control
- **Left Arrow (←)**: Switch focus to the hypothesis list pane
- **Right Arrow (→)**: Switch focus to the details pane
- **Context-Sensitive Keys**: Up/Down arrows work differently based on focused pane
- **Isolated Operations**: Actions only affect the currently focused pane

#### Enhanced Productivity
- **Rapid Navigation**: Quickly jump between list browsing and content reading
- **Parallel Workflows**: Browse hypotheses while maintaining reading position
- **Efficient Scrolling**: Navigate long content without losing list position
- **Intuitive Control**: Natural left/right metaphor matches visual layout

### How Focus Works

```
List Focused:                    Details Focused:
┌─────────────────────┐         ┌─────────────────────┐
│ Hypothesis List     │         │ Hypothesis List     │
│     [FOCUSED]       │         │                     │
│                     │         │                     │
│ ► Hypothesis 1      │         │   Hypothesis 1      │
│   Hypothesis 2      │         │   Hypothesis 2      │
│   Hypothesis 3      │    ←→   │   Hypothesis 3      │
└─────────────────────┘         └─────────────────────┘
┌─────────────────────┐         ┌─────────────────────┐
│ Current Hypothesis  │         │ Current Hypothesis  │
│                     │         │     [FOCUSED]       │
│ ↑↓ = Navigate list  │         │ ↑↓ = Scroll content │
│ j/k = Navigate list │         │ j/k = Scroll content│
└─────────────────────┘         └─────────────────────┘
```

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

### Focus Control
| Key | Action |
|-----|--------|
| `←` | Switch focus to hypothesis list pane |
| `→` | Switch focus to details pane |
| Visual [FOCUSED] indicator shows active pane |

### Context-Sensitive Navigation
| Key | List Focused | Details Focused |
|-----|-------------|----------------|
| `↑` or `k` | Move to previous hypothesis | Scroll content up |
| `↓` or `j` | Move to next hypothesis | Scroll content down |
| `Enter` | Select current hypothesis | (No effect) |
| `Home` | Go to first hypothesis | Go to top of content |
| `End` | Go to last hypothesis | Go to bottom of content |

### Pane Scrolling (Works on Focused Pane)
| Key | Action |
|-----|--------|
| `Page Up` or `u` | Scroll up by page |
| `Page Down` or `d` | Scroll down by page |
| `Ctrl+Home` | Scroll to top |
| `Ctrl+End` | Scroll to bottom |

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

#### `a` - Fetch Papers and Abstracts ⭐ New in v6.0
- Automatically fetches papers and abstracts from Semantic Scholar
- Downloads PDFs when available
- Creates organized directory structure
- Shows progress during fetching process

#### `q` - Quit and Save
- Saves current session to JSON file
- Preserves all hypotheses and feedback history
- Shows final save location

## Paper and Abstract Fetching

### Semantic Scholar Integration ⭐ New in v6.0

Wisteria v6.0 introduces powerful integration with Semantic Scholar, allowing you to automatically fetch research papers and abstracts referenced in your hypotheses.

### How to Use Paper Fetching

1. **Select a Hypothesis with References**
   - Navigate to a hypothesis that contains scientific references
   - Ensure the hypothesis has citations in its references section

2. **Initiate Fetching**
   - Press `a` to start the paper fetching process
   - The system will show: "Fetching papers... (1/5)"

3. **Monitor Progress**
   - Real-time progress indicator shows current paper being processed
   - Status updates show success/failure for each reference

4. **Review Results**
   - Final status shows total papers fetched successfully
   - Failed fetches are reported with reasons

### What Gets Downloaded

#### Directory Structure
The system creates an organized directory structure:
```
papers/
└── [session_name]/
    ├── abstracts/
    │   ├── abstract_01_paper_id.txt
    │   ├── abstract_02_paper_id.txt
    │   └── ...
    └── papers/
        ├── paper_01_paper_id.pdf
        ├── paper_02_paper_id.pdf
        └── ...
```

#### Abstract Files (.txt)
Each abstract file contains:
- **Title**: Full paper title
- **Authors**: Complete author list
- **Published**: Publication year
- **Venue**: Journal or conference name
- **Semantic Scholar ID**: Unique paper identifier
- **DOI**: Digital Object Identifier (when available)
- **arXiv ID**: arXiv identifier (when available)
- **PDF URL**: Direct link to PDF (when available)
- **Abstract**: Full abstract text

#### PDF Files (.pdf)
- **Open Access PDFs**: Downloaded when freely available
- **Original Quality**: High-resolution documents
- **Organized Naming**: Consistent with abstract files

### Search and Matching Process

#### How Papers Are Found
1. **Citation Analysis**: Extracts author, title, and year from citations
2. **Smart Searching**: Uses title or author+year combinations
3. **Relevance Ranking**: Selects most relevant matches
4. **Metadata Enrichment**: Adds comprehensive paper information

#### Handling Challenges
- **Partial Information**: Works with incomplete citations
- **Multiple Matches**: Selects most relevant paper
- **Missing Papers**: Gracefully handles unfound references
- **API Limits**: Respects rate limits with delays

### Configuration and Requirements

#### Required Setup
- **Internet Connection**: Active connection for Semantic Scholar API
- **Disk Space**: Sufficient space for downloaded papers
- **Python Packages**: requests library (automatically installed)

#### Optional Configuration
- **API Key**: Set `SS_API_KEY` or `SEMANTIC_SCHOLAR_API_KEY` environment variable
  ```bash
  export SS_API_KEY="your_api_key_here"
  ```
- **Rate Limits**: Higher limits with API key (1000+ requests/5min vs 100/5min)

#### Environment Variables
```bash
# Optional: Semantic Scholar API key for higher rate limits
export SS_API_KEY="your_semantic_scholar_api_key"
export SEMANTIC_SCHOLAR_API_KEY="your_semantic_scholar_api_key"  # Alternative name
```

### Error Handling and Troubleshooting

#### Common Issues
1. **No Internet Connection**
   - Error: "Failed to fetch papers - check internet connection"
   - Solution: Ensure stable internet access

2. **No References Found**
   - Error: "No references found in hypothesis"
   - Solution: Select hypothesis with scientific citations

3. **Rate Limit Exceeded**
   - Error: "API rate limit exceeded"
   - Solution: Wait and retry, or add API key for higher limits

4. **Papers Not Found**
   - Status: "No papers found" for specific citations
   - Reason: Citations may be incomplete or papers not in Semantic Scholar

#### Success Indicators
- **Progress Updates**: Real-time fetching status
- **Completion Summary**: "Fetched X papers, Y failed"
- **File Creation**: Visible files in papers directory
- **Status Messages**: Clear success/failure reporting

### Best Practices

#### For Better Results
1. **Quality Citations**: Use complete, well-formatted references
2. **Standard Format**: Follow academic citation conventions
3. **Recent Papers**: Newer papers more likely to be found
4. **Popular Venues**: Papers from major journals/conferences more available

#### Managing Downloads
1. **Regular Cleanup**: Remove unneeded paper directories
2. **Selective Fetching**: Only fetch for important hypotheses
3. **Backup Important Papers**: Save critical papers separately
4. **Check Disk Space**: Monitor available storage

### Integration with Workflow

#### Research Process
1. **Generate Hypothesis**: Create hypothesis with AI model
2. **Review References**: Check generated scientific citations
3. **Fetch Papers**: Use `a` command to download supporting material
4. **Deep Research**: Read abstracts and full papers offline
5. **Refine Hypothesis**: Provide feedback based on paper insights

#### Offline Access
- **Abstract Reading**: Review paper summaries without internet
- **PDF Access**: Read full papers when downloaded
- **Citation Verification**: Check reference accuracy
- **Research Validation**: Verify hypothesis claims against literature

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
| **Focus Navigation** | | |
| Focus List Pane | `←` | Switch focus to hypothesis list |
| Focus Details Pane | `→` | Switch focus to details pane |
| Context Move Up | `↑` or `k` | Previous hypothesis (list) / Scroll up (details) |
| Context Move Down | `↓` or `j` | Next hypothesis (list) / Scroll down (details) |
| Scroll Up | `Page Up` or `u` | Scroll focused pane up |
| Scroll Down | `Page Down` or `d` | Scroll focused pane down |
| **Actions** | | |
| Feedback | `f` | Provide improvement feedback |
| New Hypothesis | `n` | Generate new hypothesis |
| PDF Export | `p` | Export to PDF document |
| **Research** | | |
| Fetch Papers | `a` | Download papers and abstracts from Semantic Scholar |
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