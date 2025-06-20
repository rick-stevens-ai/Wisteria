# Wisteria v5.0 - Feedback Tracking System

## Table of Contents
1. [Overview](#overview)
2. [How Feedback Tracking Works](#how-feedback-tracking-works)
3. [Using the Feedback System](#using-the-feedback-system)
4. [Feedback History](#feedback-history)
5. [Data Structure](#data-structure)
6. [PDF Integration](#pdf-integration)
7. [Migration from Previous Versions](#migration-from-previous-versions)
8. [Best Practices](#best-practices)
9. [Examples](#examples)
10. [Technical Implementation](#technical-implementation)

## Overview

Wisteria v5.0 introduces **comprehensive feedback tracking**, a revolutionary feature that maintains a complete history of all user feedback and hypothesis improvements. This system transforms how you interact with and refine scientific hypotheses by preserving the entire evolution timeline.

### What's New in v5.0

- **Complete Feedback History**: Every piece of feedback is preserved with timestamps
- **Version Tracking**: See exactly how each feedback led to improvements
- **PDF Integration**: All feedback history appears in exported documents
- **Automatic Migration**: Seamlessly upgrades older session files
- **Professional Display**: Formatted feedback sections with clear progression

## How Feedback Tracking Works

### The Feedback Loop

```
1. User provides feedback → 2. AI improves hypothesis → 3. New version created
                    ↓
4. Feedback stored with timestamp and version info
                    ↓
5. History maintained for complete audit trail
```

### Version Management

Each hypothesis starts as version `1.0`. When you provide feedback:

- Current version: `1.0`
- Feedback: "Make more specific to diabetes"
- AI generates improvement
- New version: `1.1`
- Feedback stored: `1.0 → 1.1`

### Data Preservation

**Everything is preserved**:
- Original feedback text
- Exact timestamp when provided
- Version before improvement
- Version after improvement
- Complete hypothesis evolution

## Using the Feedback System

### Providing Feedback

1. **Select Hypothesis**: Navigate to the hypothesis you want to improve
2. **Press `f`**: Enter feedback mode
3. **Type Your Feedback**: Be specific about what needs improvement
4. **Submit**: Press `Enter` to process or `Esc` to cancel
5. **Wait for Processing**: AI generates improved version
6. **Review Result**: New version appears with your feedback automatically tracked

### Example Feedback Session

```
Original Hypothesis v1.0:
"CRISPR can be used to treat genetic diseases"

Feedback #1: "Make this more specific to sickle cell disease"
→ Creates v1.1: "CRISPR-Cas9 can be used to treat sickle cell disease 
                 by correcting the HbS mutation in patient stem cells"

Feedback #2: "Add details about the delivery mechanism"
→ Creates v1.2: "CRISPR-Cas9 delivered via lentiviral vectors can treat 
                 sickle cell disease by correcting the HbS mutation..."

Feedback #3: "Include potential side effects and limitations"
→ Creates v1.3: "CRISPR-Cas9 delivered via lentiviral vectors can treat 
                 sickle cell disease... However, potential off-target 
                 effects and delivery efficiency limitations must be considered..."
```

### Real-Time Feedback Display

In the curses interface, you can see feedback as it's processed:

```
Status: "Enter feedback (Enter to submit, ESC to cancel)"
Input:  "Make more specific to Type 2 diabetes"
Status: "Processing feedback..."
Status: "Hypothesis improved!"
```

## Feedback History

### Viewing Feedback History

Feedback history appears in the hypothesis details pane:

```
═══════════════════════════════════════════════════════════════
                     HYPOTHESIS DETAILS
═══════════════════════════════════════════════════════════════

Title: Enhanced CRISPR Gene Therapy for Sickle Cell Disease

Description:
This improved hypothesis proposes using CRISPR-Cas9 delivered via
optimized lentiviral vectors to correct the HbS mutation in 
hematopoietic stem cells...

Experimental Validation:
The hypothesis can be tested by isolating patient HSCs, applying
the CRISPR system ex vivo, and measuring correction efficiency...

Feedback History:
─────────────────────────────────────────────────────────────

Feedback #1
Provided: January 15, 2024 at 10:35 AM
Version updated: 1.0 → 1.1
┌─────────────────────────────────────────────────────────────┐
│ Make this more specific to sickle cell disease instead of  │
│ general genetic diseases                                    │
└─────────────────────────────────────────────────────────────┘

Feedback #2  
Provided: January 15, 2024 at 11:20 AM
Version updated: 1.1 → 1.2
┌─────────────────────────────────────────────────────────────┐
│ Add details about the delivery mechanism and target cells  │
└─────────────────────────────────────────────────────────────┘

Feedback #3
Provided: January 15, 2024 at 2:15 PM  
Version updated: 1.2 → 1.3
┌─────────────────────────────────────────────────────────────┐
│ Include potential side effects, limitations, and safety    │
│ considerations for clinical application                     │
└─────────────────────────────────────────────────────────────┘
```

### Scrolling Through History

For hypotheses with extensive feedback:
- Use `Page Down` / `d` to scroll through long feedback histories
- Use `Page Up` / `u` to scroll back up
- Each feedback entry is clearly separated and timestamped

## Data Structure

### Feedback Entry Format

Each feedback entry contains:

```json
{
  "feedback": "User's exact feedback text",
  "timestamp": "2024-01-15T10:35:00.123456",
  "version_before": "1.0",
  "version_after": "1.1"
}
```

### Complete Hypothesis Structure

```json
{
  "hypothesis_number": 1,
  "version": "1.3",
  "type": "improvement",
  "title": "Enhanced CRISPR Gene Therapy",
  "description": "Detailed description...",
  "experimental_validation": "Testing methodology...",
  
  "feedback_history": [
    {
      "feedback": "Make more specific to sickle cell disease",
      "timestamp": "2024-01-15T10:35:00",
      "version_before": "1.0", 
      "version_after": "1.1"
    },
    {
      "feedback": "Add delivery mechanism details",
      "timestamp": "2024-01-15T11:20:00",
      "version_before": "1.1",
      "version_after": "1.2"
    }
  ],
  
  "user_feedback": "Add delivery mechanism details",  // Legacy field
  "generation_timestamp": "2024-01-15T11:20:00",
  "improvements_made": "Added specific delivery mechanism details..."
}
```

### Session-Level Tracking

Sessions now track feedback statistics:

```json
{
  "metadata": {
    "research_goal": "CRISPR improvements",
    "total_hypotheses": 3,
    "total_feedback_entries": 7,
    "average_feedback_per_hypothesis": 2.3,
    "session_duration": "2h 15m"
  }
}
```

## PDF Integration

### Enhanced PDF Export

When you press `p` to export a hypothesis to PDF, the document now includes:

#### New Feedback History Section

```
───────────────────────────────────────────────────────────────
                      FEEDBACK HISTORY
───────────────────────────────────────────────────────────────

Feedback #1
Provided: January 15, 2024 at 10:35 AM
Version updated: 1.0 → 1.1

    Make this more specific to sickle cell disease instead of 
    general genetic diseases. Focus on the HbS mutation and its 
    cellular effects.

Feedback #2
Provided: January 15, 2024 at 11:20 AM  
Version updated: 1.1 → 1.2

    Add details about the delivery mechanism and target cells.
    How will the CRISPR system reach the right cells in vivo?

Feedback #3
Provided: January 15, 2024 at 2:15 PM
Version updated: 1.2 → 1.3

    Include potential side effects, limitations, and safety
    considerations for clinical application. What could go wrong?
```

#### Professional Formatting

- **Styled Boxes**: Each feedback entry in a visually distinct box
- **Timeline Format**: Clear chronological progression
- **Version Tracking**: Prominent display of version changes
- **Readable Typography**: Professional fonts and spacing

### PDF Table of Contents

Updated to include feedback section:

```
Table of Contents
─────────────────
1. Research Goal
2. Hypothesis Overview
3. Detailed Description  
4. Experimental Validation
5. Feedback History          ← NEW in v5.0
6. Improvements Made
7. Hallmarks Analysis
8. Scientific References
```

## Migration from Previous Versions

### Automatic Migration

When you load old session files (v1.0-v4.0), the system automatically:

1. **Creates feedback_history Array**: Initializes empty array if missing
2. **Migrates Legacy Data**: Converts old `user_feedback` field
3. **Preserves Original Data**: Never deletes existing information
4. **Updates Structure**: Adds new fields while maintaining compatibility

### Migration Example

**Before (v4.0 format)**:
```json
{
  "title": "Solar Cell Improvement",
  "user_feedback": "Add efficiency calculations",
  "version": "1.1"
}
```

**After (v5.0 format)**:
```json
{
  "title": "Solar Cell Improvement", 
  "user_feedback": "Add efficiency calculations",  // Preserved
  "version": "1.1",
  "feedback_history": [                            // Added
    {
      "feedback": "Add efficiency calculations",
      "timestamp": "2024-01-15T10:00:00",  // Estimated from generation_timestamp
      "version_before": "1.0",              // Estimated
      "version_after": "1.1"
    }
  ]
}
```

### Manual Migration

For complex cases, you can manually migrate:

```python
import json
from datetime import datetime

# Load old session
with open('old_session.json', 'r') as f:
    data = json.load(f)

# Migrate each hypothesis
for hyp in data['hypotheses']:
    if 'feedback_history' not in hyp:
        hyp['feedback_history'] = []
        
        if 'user_feedback' in hyp and hyp['user_feedback']:
            entry = {
                "feedback": hyp['user_feedback'],
                "timestamp": hyp.get('generation_timestamp', 
                                   datetime.now().isoformat()),
                "version_before": "1.0",
                "version_after": hyp.get('version', '1.1')
            }
            hyp['feedback_history'].append(entry)

# Save migrated session
with open('migrated_session.json', 'w') as f:
    json.dump(data, f, indent=2)
```

## Best Practices

### Effective Feedback Writing

#### Be Specific
```
❌ Poor: "Make it better"
✅ Good: "Add specific dosage information and administration schedule"
```

#### Focus on One Aspect
```
❌ Poor: "Fix everything about this hypothesis"
✅ Good: "Include control group methodology in the experimental design"
```

#### Use Scientific Language
```
❌ Poor: "This seems wrong"
✅ Good: "The mechanism lacks specificity - clarify which cellular pathway is targeted"
```

#### Provide Context
```
❌ Poor: "Add more details"
✅ Good: "Add more details about patient selection criteria and exclusion factors"
```

### Iterative Improvement Strategy

#### Start Broad, Get Specific
1. **Round 1**: Overall scope and direction
2. **Round 2**: Methodology and experimental design
3. **Round 3**: Details, limitations, and considerations

#### Example Improvement Sequence
```
Feedback #1: "Focus specifically on Type 2 diabetes in elderly patients"
Feedback #2: "Add details about dosing regimen and monitoring protocols"  
Feedback #3: "Include contraindications and drug interaction considerations"
Feedback #4: "Specify outcome measures and statistical analysis methods"
```

### Session Management

#### Organize by Research Phase
- **Exploratory Phase**: 3-5 hypotheses with 2-3 feedback rounds each
- **Refinement Phase**: Focus on 1-2 best hypotheses with detailed feedback
- **Finalization Phase**: Polish and validate final hypotheses

#### Documentation Strategy
- **Export Early**: Create PDFs after major improvements
- **Name Descriptively**: Use clear session filenames
- **Archive Completed**: Move finished sessions to separate directory

## Examples

### Example 1: Drug Development Hypothesis

**Original (v1.0)**:
```
Title: New diabetes drug
Description: A new drug could help diabetes patients
```

**After Feedback Loop**:
```
Feedback #1: "Specify the type of diabetes and target population"
→ v1.1: GLP-1 receptor agonist for Type 2 diabetes in overweight adults

Feedback #2: "Add mechanism of action details"  
→ v1.2: GLP-1 receptor agonist that enhances glucose-dependent insulin 
        secretion and delays gastric emptying...

Feedback #3: "Include clinical trial design"
→ v1.3: Randomized controlled trial comparing efficacy and safety
        against standard metformin therapy...

Feedback #4: "Add safety profile and contraindications"
→ v1.4: Comprehensive safety analysis including pancreatitis risk
        assessment and contraindications for patients with...
```

### Example 2: Climate Research Hypothesis

**Feedback Evolution**:
```
Original: "Solar panels could be more efficient"

Feedback #1: "Specify the technology and efficiency improvement target"
→ "Perovskite-silicon tandem solar cells could achieve >30% efficiency"

Feedback #2: "Add details about the perovskite layer composition"
→ "Mixed-cation perovskite (FA/MA/Cs) with optimized bandgap..."

Feedback #3: "Include manufacturing challenges and solutions"
→ "Scalable solution processing techniques to address stability..."

Feedback #4: "Add economic feasibility analysis"
→ "Cost-benefit analysis showing ROI within 5 years considering..."
```

### Example 3: Medical Research Hypothesis

**Complete Feedback Timeline**:
```
Research Goal: "How can we improve cancer immunotherapy?"

Hypothesis #1 Evolution:
v1.0: CAR-T therapy improvements
├─ Feedback: "Focus on solid tumors, not blood cancers"
v1.1: CAR-T therapy for solid tumor infiltration
├─ Feedback: "Address tumor microenvironment challenges"  
v1.2: Enhanced CAR-T with cytokine support for solid tumors
├─ Feedback: "Include safety mechanisms for cytokine storms"
v1.3: Conditional CAR-T system with safety switches
└─ Feedback: "Add patient selection criteria"
v1.4: Stratified CAR-T approach based on tumor profiling

Final Result: Comprehensive hypothesis with 4 rounds of refinement
Total Development Time: 2 hours
Feedback Entries: 4 detailed improvements
PDF Export: 8-page professional document with complete history
```

## Technical Implementation

### Database Schema

The feedback tracking system uses a nested document structure:

```
Hypothesis
├── Core Fields (title, description, etc.)
├── feedback_history[]
│   ├── feedback: string
│   ├── timestamp: ISO datetime
│   ├── version_before: string  
│   └── version_after: string
├── Legacy Fields (user_feedback)
└── Metadata (timestamps, etc.)
```

### Processing Pipeline

```
User Input → Validation → AI Processing → Version Update → History Storage
     ↓
Status Updates → UI Refresh → Auto-save → Backup Creation
```

### Performance Considerations

- **Memory Usage**: Each feedback entry ~200 bytes average
- **Storage**: JSON compression reduces file size ~40%
- **UI Performance**: Pagination for >50 feedback entries
- **PDF Generation**: Optimized rendering for long histories

### API Integration

The feedback system integrates with AI models:

```python
def process_feedback(hypothesis, feedback, config):
    # Create feedback entry
    entry = create_feedback_entry(feedback, hypothesis['version'])
    
    # Call AI model for improvement
    improved = improve_hypothesis(hypothesis, feedback, config)
    
    # Update version and history
    improved['feedback_history'].append(entry)
    improved['version'] = increment_version(hypothesis['version'])
    
    return improved
```

---

*This feedback tracking system represents a major advancement in hypothesis development workflows, providing unprecedented visibility into the iterative improvement process and creating valuable documentation for research methodology.*

*For general usage information, see [USER_GUIDE.md](USER_GUIDE.md)*

*For technical implementation details, see [TECHNICAL_DOCS.md](TECHNICAL_DOCS.md)*