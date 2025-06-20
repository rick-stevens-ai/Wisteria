# Wisteria v5.0 - Keyboard Reference

## Quick Reference Card

### Navigation Commands
| Key | Alternative | Action | Description |
|-----|-------------|---------|-------------|
| `↑` | `k` | Move Up | Navigate to previous hypothesis |
| `↓` | `j` | Move Down | Navigate to next hypothesis |
| `Page Up` | `u` | Scroll Up | Scroll hypothesis details up |
| `Page Down` | `d` | Scroll Down | Scroll hypothesis details down |
| `Home` | `g` | Go to Top | Jump to first hypothesis |
| `End` | `G` | Go to Bottom | Jump to last hypothesis |
| `Enter` | `Space` | Select | Select highlighted hypothesis |

### Action Commands
| Key | Action | Description |
|-----|---------|-------------|
| `f` | Feedback | Provide feedback to improve hypothesis |
| `n` | New | Generate a new hypothesis |
| `p` | PDF | Export current hypothesis to PDF |
| `q` | Quit | Save session and exit |

### Session Management
| Key | Action | Description |
|-----|---------|-------------|
| `l` | Load | Load hypotheses from JSON file |
| `x` | Save | Save current session with custom filename |
| `t` | Notes | Add/edit personal notes for current hypothesis |
| `s` | Select | Jump to hypothesis by number |
| `v` | View | Show all hypothesis titles |

### Display Toggles
| Key | Action | Description |
|-----|---------|-------------|
| `h` | Hallmarks | Toggle hallmarks analysis display |
| `r` | References | Toggle references display |

### System Commands
| Key | Action | Description |
|-----|---------|-------------|
| `Esc` | Cancel | Cancel current operation |
| `Ctrl+C` | Force Quit | Emergency exit (not recommended) |

## Detailed Command Reference

### Navigation Commands

#### Basic Movement
- **Up Arrow (`↑`) / `k`**: Move selection to previous hypothesis
  - Wraps to bottom when at top
  - Updates detail pane automatically
  - Clears non-persistent status messages

- **Down Arrow (`↓`) / `j`**: Move selection to next hypothesis
  - Wraps to top when at bottom
  - Updates detail pane automatically
  - Clears non-persistent status messages

#### Detail Scrolling
- **Page Up / `u`**: Scroll hypothesis details up one page
  - Works within the right pane only
  - Useful for long descriptions and feedback history
  - Mac users: Use `u` if Page Up not available

- **Page Down / `d`**: Scroll hypothesis details down one page
  - Works within the right pane only
  - Essential for viewing complete hypothesis content
  - Mac users: Use `d` if Page Down not available

#### Quick Navigation
- **Home / `g`**: Jump to first hypothesis in list
- **End / `G`**: Jump to last hypothesis in list
- **Enter / Space**: Select current hypothesis (same as clicking)

### Action Commands

#### `f` - Provide Feedback
**Purpose**: Improve the current hypothesis based on your input

**Usage Flow**:
1. Press `f` while viewing a hypothesis
2. Status bar shows: "Enter feedback (Enter to submit, ESC to cancel)"
3. Type your feedback text
4. Press `Enter` to submit or `Esc` to cancel
5. System generates improved hypothesis
6. Feedback automatically added to history

**Example Feedback**:
```
Make this hypothesis more specific to Type 2 diabetes patients over age 65
```

**Technical Notes**:
- Feedback is processed by AI model
- Creates new version of hypothesis
- Original version preserved in history
- Feedback stored with timestamp

#### `n` - Generate New Hypothesis
**Purpose**: Create a completely new hypothesis different from existing ones

**Usage**:
1. Press `n` from anywhere in the interface
2. Shows progress indicator: "Generating new hypothesis..."
3. AI model creates novel hypothesis
4. New hypothesis added to end of list
5. Automatically selected for viewing

**Technical Notes**:
- Uses context of all existing hypotheses
- Ensures novelty and difference
- May take 10-30 seconds depending on model
- Thread-based to keep UI responsive

#### `p` - Export to PDF
**Purpose**: Generate professional PDF document of current hypothesis

**Usage**:
1. Select hypothesis to export
2. Press `p`
3. Wait for "PDF generated successfully" message
4. File saved with descriptive filename

**PDF Contents**:
- Research goal and metadata
- Complete hypothesis details
- **Complete feedback history** (NEW in v5.0)
- Hallmarks analysis
- Scientific references
- Professional formatting

**Filename Format**:
```
hypothesis_[title]_[timestamp].pdf
```

#### `q` - Quit and Save
**Purpose**: Save current session and exit application

**Usage**:
1. Press `q` from anywhere
2. Session automatically saved to JSON file
3. Application exits gracefully
4. Terminal restored to normal state

**Save Format**:
```
hypotheses_interactive_[model]_[timestamp].json
```

### Session Management Commands

#### `l` - Load Session
**Purpose**: Load hypotheses from a previous session file

**Usage Flow**:
1. Press `l`
2. Status bar shows: "Enter filename to load (ESC to cancel):"
3. Type filename (with or without .json extension)
4. Press `Enter` to load or `Esc` to cancel
5. Hypotheses merged into current session

**Examples**:
```
hypotheses_interactive_gpt41_20240115_103000.json
my_session.json
../sessions/climate_research.json
```

**Technical Notes**:
- Automatically migrates old data formats
- Merges without duplicating
- Preserves all feedback history
- Updates research goal if different

#### `x` - Save Session
**Purpose**: Save current session to a custom filename

**Usage Flow**:
1. Press `x`
2. Status bar shows: "Enter filename to save (ESC to cancel):"
3. Type desired filename (without .json extension)
4. Press `Enter` to save or `Esc` to cancel
5. Session saved with all hypotheses and feedback history

**Examples**:
```
my_research_session     # Saves as my_research_session.json
climate_hypotheses      # Saves as climate_hypotheses.json
backup_jan_15          # Saves as backup_jan_15.json
```

**Technical Notes**:
- Automatically adds .json extension if not provided
- Saves complete session with metadata
- Includes all feedback history and timestamps
- Preserves hypothesis version information
- Creates file in current directory

#### `t` - Notes
**Purpose**: Add or edit personal notes for the current hypothesis

**Usage Flow**:
1. Press `t` while viewing a hypothesis
2. Status bar shows: "Enter notes (Enter to save, ESC to cancel):"
3. Type or edit your personal notes
4. Use arrow keys to navigate within the text
5. Press `Enter` to save or `Esc` to cancel
6. Notes are applied to all versions of the hypothesis

**Editing Features**:
- **Text Navigation**: Left/Right arrow keys to move cursor
- **Text Editing**: Insert text at cursor position
- **Backspace**: Delete character before cursor
- **Home/End**: Jump to beginning/end of text
- **Visual Cursor**: Shows current editing position

**Examples**:
```
"This hypothesis reminds me of the 2019 Nature paper on CRISPR"
"TODO: Check if this conflicts with our previous findings"
"Promising approach - should discuss with the team"
"May need additional controls for confounding variables"
```

**Technical Notes**:
- Notes are saved to all versions of the same hypothesis number
- Maximum practical length ~1000 characters for display
- Notes appear in hypothesis details pane
- Included in PDF exports with special formatting
- Preserved during session save/load operations
- Copied to new versions when hypothesis is improved

#### `s` - Select by Number
**Purpose**: Jump directly to a specific hypothesis by its number

**Usage Flow**:
1. Press `s`
2. Status bar shows available range: "Enter hypothesis number (1-5, ESC to cancel):"
3. Type hypothesis number
4. Press `Enter` to select or `Esc` to cancel
5. Jumps directly to that hypothesis

**Examples**:
```
3     # Jump to hypothesis #3
1     # Jump to first hypothesis
```

**Technical Notes**:
- Only accepts valid hypothesis numbers
- Shows error for invalid input
- Resets detail scroll position
- Useful for large sessions

#### `v` - View All Titles
**Purpose**: Show popup with all hypothesis titles for overview

**Usage**:
1. Press `v`
2. Popup displays all hypothesis titles
3. Shows version information
4. Press any key to return

**Display Format**:
```
===============================================
           HYPOTHESIS TITLES
===============================================

Hypothesis #1 (3 versions):
  v1.0: Original Perovskite Solar Cell Design
  v1.1: Enhanced Perovskite Solar Cell Design  
  v1.2: Optimized Perovskite Solar Cell Design

Hypothesis #2 (1 version):
  v1.0: Quantum Dot Enhancement Method

Press any key to continue...
```

### Display Toggle Commands

#### `h` - Toggle Hallmarks
**Purpose**: Show or hide scientific hallmarks analysis

**What It Toggles**:
- Testability (Falsifiability) analysis
- Specificity and Clarity evaluation
- Grounded in Prior Knowledge assessment
- Predictive Power & Novel Insight review
- Parsimony (Principle of Simplicity) analysis

**Usage**:
- Press `h` to toggle on/off
- Status shows: "Hallmarks analysis enabled/disabled"
- Setting preserved during session
- Useful for focusing on core content

#### `r` - Toggle References
**Purpose**: Show or hide scientific references section

**What It Toggles**:
- Scientific citations
- Reference annotations
- Supporting literature

**Usage**:
- Press `r` to toggle on/off
- Status shows: "References display enabled/disabled"
- Setting preserved during session
- Helpful for cleaner hypothesis view

### System Commands

#### `Esc` - Cancel Operation
**Purpose**: Cancel any current input operation

**Use Cases**:
- Cancel feedback input
- Cancel filename input for loading
- Cancel hypothesis number selection
- Exit any prompt mode

**Behavior**:
- Returns to normal navigation mode
- Clears any partial input
- Shows "Operation cancelled" status
- Safe to use anytime

#### Emergency Commands

#### `Ctrl+C` - Force Quit
**Purpose**: Emergency exit (not recommended for normal use)

**When to Use**:
- Application appears frozen
- Terminal issues
- Last resort only

**Consequences**:
- May not save current session
- Terminal may not restore properly
- Potential data loss

**Better Alternative**: Use `q` for proper exit

## Platform-Specific Notes

### Mac Users
**Missing Keys**: Mac keyboards often lack Page Up/Down keys

**Solutions**:
- Use `u` instead of Page Up
- Use `d` instead of Page Down  
- Use `j/k` instead of arrow keys
- Function key combinations: `fn+↑` = Page Up, `fn+↓` = Page Down

### Windows Users
**Standard Keys**: All keys should work as expected

**Terminal Notes**:
- Use Windows Terminal or PowerShell for best experience
- Command Prompt may have limited color support
- Consider WSL for enhanced compatibility

### Linux Users
**Standard Keys**: Full compatibility expected

**Terminal Notes**:
- Most terminals fully supported
- tmux/screen compatible
- SSH sessions supported

## Troubleshooting Key Issues

### Keys Not Responding
**Possible Causes**:
- Terminal doesn't support key codes
- Application in wrong mode
- Terminal size too small

**Solutions**:
1. Try vim-style alternatives (`j/k/d/u`)
2. Resize terminal to minimum 80x24
3. Restart application
4. Check terminal type and capabilities

### Input Not Working
**Symptoms**:
- Typing doesn't appear
- Keys do wrong actions
- No response to keystrokes

**Solutions**:
1. Press `Esc` to ensure normal mode
2. Check if in feedback/input mode
3. Verify terminal has focus
4. Restart application if needed

### Display Issues
**Symptoms**:
- Text cut off
- Layout broken
- Colors missing

**Solutions**:
1. Increase terminal size (minimum 80x24, recommended 120x40)
2. Enable color support in terminal
3. Check terminal type (TERM environment variable)
4. Use standard terminal emulator

## Keyboard Shortcuts Summary Card

```
┌─────────────────────────────────────────────────────────────┐
│                    WISTERIA v5.0 KEYS                      │
├─────────────────────────────────────────────────────────────┤
│ NAVIGATION           │ ACTIONS              │ DISPLAY       │
│ ↑/k  - Previous      │ f - Feedback         │ h - Hallmarks │
│ ↓/j  - Next          │ n - New hypothesis   │ r - References│
│ PgUp/u - Scroll up   │ p - Export PDF       │               │
│ PgDn/d - Scroll down │ q - Quit & save      │               │
│ Enter - Select       │                      │               │
├─────────────────────────────────────────────────────────────┤
│ SESSION              │ SYSTEM               │               │
│ l - Load session     │ Esc - Cancel         │               │
│ x - Save session     │ Ctrl+C - Force quit  │               │
│ t - Notes            │                      │               │
│ s - Select by #      │                      │               │
│ v - View titles      │                      │               │
└─────────────────────────────────────────────────────────────┘
```

---

*For complete usage instructions, see [USER_GUIDE.md](USER_GUIDE.md)*

*For technical details, see [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md)*