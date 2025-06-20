#!/usr/bin/env python3

"""
Wisteria Research Hypothesis Generator v5.0 - Curses Multi-Pane Interface

Usage:
    python curses_wisteria_v5.py <research_goal_file.txt> --model <model_shortname> [--num-hypotheses <N>] [--output <output_file.json>]
    python curses_wisteria_v5.py --goal "<research_goal_text>" --model <model_shortname> [--num-hypotheses <N>] [--output <output_file.json>]
    python curses_wisteria_v5.py --resume <session_file.json> --model <model_shortname> [--output <output_file.json>]

Where:
    - research_goal_file.txt: A text file containing the research goal/question
    - --goal: Specify the research goal directly as a command line argument
    - --resume: Resume from a previous session JSON file
    - --model: The shortname of the model to use from model_servers.yaml
    - --num-hypotheses: Number of initial hypotheses to generate (default: 1)
    - --output: Output JSON file for the hypotheses (default: hypotheses_<timestamp>.json)

Examples:
    python curses_wisteria_v5.py research_goal.txt --model gpt41
    python curses_wisteria_v5.py --goal "How can we improve renewable energy storage efficiency?" --model scout --num-hypotheses 3
    python curses_wisteria_v5.py --resume hypotheses_interactive_gpt41_20250531_165238.json --model gpt41
    python curses_wisteria_v5.py --goal "What causes neurodegenerative diseases?" --model gpt41 --num-hypotheses 5 --output my_hypotheses.json

The script:
1) Reads a research goal from a text file OR accepts it directly via --goal argument OR resumes from a previous session
2) Uses the specified MODEL to generate creative and novel hypotheses interactively
3) For each hypothesis:
   - Presents it to the user with title, description, experimental validation plan, and hallmarks analysis
   - Requests user feedback for improvement
   - Uses feedback to refine the hypothesis
   - Allows user to generate new hypotheses or quit
4) Interactive commands during session:
   - f - Provide feedback to improve the current hypothesis
   - n - Generate a new hypothesis different from previous ones
   - l - Load from a JSON file a previous session log
   - v - View the titles of hypotheses in current session
   - s - Select a hypothesis to continue to refine
   - h - Toggle hallmarks analysis display
   - r - Toggle references display
   - p - Print current hypothesis to PDF document
   - q - Quit and save all hypotheses
5) Ensures each new hypothesis is different from previous ones
6) Outputs all hypotheses and refinements to JSON file
"""

import sys
import os
import json
import argparse
import yaml
import time
import openai
import random
from datetime import datetime
import backoff
import difflib
import re
import curses
import textwrap
import threading

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ---------------------------------------------------------------------
# Helper functions (from argonium_score_parallel_v9.py)
# ---------------------------------------------------------------------

def clean_json_string(text):
    """Clean control characters from JSON string to prevent parsing errors."""
    if not text:
        return text
    # Remove ASCII control characters (0x00-0x1F and 0x7F) except for whitespace
    # Keep: \t (0x09), \n (0x0A), \r (0x0D)
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text

# ---------------------------------------------------------------------
# Curses Interface Classes and Pane Management
# ---------------------------------------------------------------------

class CursesInterface:
    """Main curses interface manager for multi-pane layout"""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.height, self.width = stdscr.getmaxyx()
        
        # Pane dimensions
        self.HEADER_HEIGHT = 4
        self.STATUS_HEIGHT = 2
        self.LIST_WIDTH = int(self.width * 0.35)  # 35% for hypothesis list
        self.DETAIL_WIDTH = self.width - self.LIST_WIDTH - 1  # Rest for details
        
        # Initialize color pairs
        self.init_colors()
        
        # Create panes
        self.create_panes()
        
        # Current state
        self.current_hypothesis_idx = 0
        self.list_scroll_offset = 0
        self.detail_scroll_offset = 0
        self.show_hallmarks = True
        self.show_references = True
        
        # Status message management
        self.current_status = "Ready"
        self.status_timestamp = time.time()
        self.status_timeout = 3.0  # Status messages auto-clear after 3 seconds
        self.persistent_status = False  # Some statuses should persist until user action
        
    def init_colors(self):
        """Initialize curses color pairs"""
        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            
            # Color pairs
            curses.init_pair(1, curses.COLOR_GREEN, -1)    # Added text
            curses.init_pair(2, curses.COLOR_RED, -1)      # Removed text  
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # Changed text
            curses.init_pair(4, curses.COLOR_CYAN, -1)     # Info text
            curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Header
            curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_WHITE) # Status bar
            curses.init_pair(7, curses.COLOR_MAGENTA, -1)  # Selected item
            
    def create_panes(self):
        """Create all interface panes"""
        # Header pane
        self.header_win = curses.newwin(
            self.HEADER_HEIGHT, self.width, 0, 0
        )
        
        # Hypothesis list pane (left)
        list_start_y = self.HEADER_HEIGHT
        list_height = self.height - self.HEADER_HEIGHT - self.STATUS_HEIGHT
        self.list_win = curses.newwin(
            list_height, self.LIST_WIDTH, list_start_y, 0
        )
        
        # Details pane (right)
        detail_start_x = self.LIST_WIDTH + 1
        self.detail_win = curses.newwin(
            list_height, self.DETAIL_WIDTH, list_start_y, detail_start_x
        )
        
        # Status bar
        status_start_y = self.height - self.STATUS_HEIGHT
        self.status_win = curses.newwin(
            self.STATUS_HEIGHT, self.width, status_start_y, 0
        )
        
        # Enable scrolling for list and detail panes
        self.list_win.scrollok(True)
        self.detail_win.scrollok(True)
        
    def draw_header(self, research_goal, model_name):
        """Draw the header pane with research goal and model info"""
        self.header_win.clear()
        self.header_win.attron(curses.color_pair(5) | curses.A_BOLD)
        
        # Title line
        title = f" WISTERIA v5 - Research Hypothesis Generator"
        model_info = f"[Model: {model_name}] "
        title_line = title + " " * max(0, self.width - len(title) - len(model_info)) + model_info
        self.safe_addstr(self.header_win, 0, 0, title_line[:self.width])
        
        # Separator
        self.safe_addstr(self.header_win, 1, 0, "-" * (self.width-1))
        
        self.header_win.attroff(curses.color_pair(5) | curses.A_BOLD)
        
        # Research goal (wrapped)
        goal_text = f"Research Goal: {research_goal}"
        wrapped_goal = textwrap.fill(goal_text, self.width - 2)
        goal_lines = wrapped_goal.split('\n')
        
        for i, line in enumerate(goal_lines[:2]):  # Max 2 lines for goal
            if i + 2 < self.HEADER_HEIGHT:
                self.safe_addstr(self.header_win, i + 2, 1, line)
        
        self.header_win.refresh()
        
    def draw_hypothesis_list(self, all_hypotheses):
        """Draw the hypothesis list pane"""
        self.list_win.clear()
        self.list_win.box()
        
        # Title
        list_title = " Hypothesis List "
        title_x = (self.LIST_WIDTH - len(list_title)) // 2
        self.list_win.addstr(0, title_x, list_title, curses.A_BOLD)
        
        if not all_hypotheses:
            self.list_win.addstr(2, 2, "No hypotheses yet", curses.color_pair(4))
            self.list_win.refresh()
            return
            
        # Group hypotheses by number
        hypothesis_groups = {}
        for hyp in all_hypotheses:
            hyp_num = hyp.get("hypothesis_number", 0)
            if hyp_num not in hypothesis_groups:
                hypothesis_groups[hyp_num] = []
            hypothesis_groups[hyp_num].append(hyp)
        
        # Display hypothesis list
        y_pos = 2
        list_height = self.list_win.getmaxyx()[0] - 3  # Account for borders
        
        for hyp_num in sorted(hypothesis_groups.keys()):
            if y_pos - 2 < self.list_scroll_offset:
                continue
            if y_pos >= list_height + self.list_scroll_offset:
                break
                
            hyp_versions = hypothesis_groups[hyp_num]
            latest_version = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
            
            version = latest_version.get("version", "1.0")
            title = latest_version.get("title", "Untitled")
            hyp_type = latest_version.get("type", "unknown")
            
            # Truncate title to fit
            max_title_len = self.LIST_WIDTH - 15
            if len(title) > max_title_len:
                title = title[:max_title_len-3] + "..."
            
            type_indicator = ""
            if hyp_type == "improvement":
                type_indicator = " (imp)"
            elif hyp_type == "new_alternative": 
                type_indicator = " (alt)"
                
            line_text = f"{hyp_num}. [v{version}] {title}{type_indicator}"
            
            # Highlight selected hypothesis
            attr = curses.A_REVERSE if hyp_num - 1 == self.current_hypothesis_idx else 0
            
            try:
                display_y = y_pos - self.list_scroll_offset
                if 1 <= display_y < list_height:
                    self.list_win.addstr(display_y, 2, line_text[:self.LIST_WIDTH-4], attr)
            except curses.error:
                pass  # Ignore if line doesn't fit
                
            y_pos += 1
            
        self.list_win.refresh()
        
    def draw_hypothesis_details(self, hypothesis, previous_hypothesis=None):
        """Draw the hypothesis details pane"""
        self.detail_win.clear()
        self.detail_win.box()
        
        # Title
        detail_title = " Current Hypothesis "
        title_x = (self.DETAIL_WIDTH - len(detail_title)) // 2
        self.detail_win.addstr(0, title_x, detail_title, curses.A_BOLD)
        
        if not hypothesis:
            self.detail_win.addstr(2, 2, "No hypothesis selected", curses.color_pair(4))
            self.detail_win.refresh()
            return
            
        # Content area
        content_width = self.DETAIL_WIDTH - 4
        y_pos = 2
        max_y = self.detail_win.getmaxyx()[0] - 2
        
        try:
            # Title
            version = hypothesis.get("version", "1.0")
            hyp_title = f"Title (v{version}): {hypothesis.get('title', 'Untitled')}"
            wrapped_title = textwrap.fill(hyp_title, content_width)
            for line in wrapped_title.split('\n'):
                if y_pos >= max_y:
                    break
                if y_pos - 2 >= self.detail_scroll_offset:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, line, curses.A_BOLD)
                y_pos += 1
            
            y_pos += 1  # Blank line
            
            # Description
            if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                display_y = y_pos - self.detail_scroll_offset
                if 2 <= display_y < max_y:
                    self.safe_addstr(self.detail_win, display_y, 2, "Description:", curses.A_UNDERLINE)
            y_pos += 1
            
            description = hypothesis.get('description', 'No description provided.')
            wrapped_desc = textwrap.fill(description, content_width)
            for line in wrapped_desc.split('\n'):
                if y_pos >= max_y + self.detail_scroll_offset + 20:  # Reasonable limit
                    break
                if y_pos - 2 >= self.detail_scroll_offset:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, line)
                y_pos += 1
            
            # Experimental Validation Plan
            y_pos += 1
            if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                display_y = y_pos - self.detail_scroll_offset
                if 2 <= display_y < max_y:
                    self.safe_addstr(self.detail_win, display_y, 2, "Experimental Validation Plan:", curses.A_UNDERLINE)
            y_pos += 1
            
            experimental_validation = hypothesis.get('experimental_validation', 'No experimental validation plan provided.')
            wrapped_validation = textwrap.fill(experimental_validation, content_width)
            for line in wrapped_validation.split('\n'):
                if y_pos >= max_y + self.detail_scroll_offset + 20:  # Reasonable limit
                    break
                if y_pos - 2 >= self.detail_scroll_offset:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, line)
                y_pos += 1
            
            # Show improvements if this is an improvement
            if hypothesis.get("improvements_made") and hypothesis.get("type") == "improvement":
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset  
                    if 2 <= display_y < max_y:
                        self.detail_win.addstr(display_y, 2, "Improvements made:", curses.color_pair(4) | curses.A_BOLD)
                y_pos += 1
                
                improvements = hypothesis.get("improvements_made", "")
                wrapped_imp = textwrap.fill(improvements, content_width)
                for line in wrapped_imp.split('\n'):
                    if y_pos - 2 >= self.detail_scroll_offset:
                        display_y = y_pos - self.detail_scroll_offset
                        if 2 <= display_y < max_y:
                            self.detail_win.addstr(display_y, 2, line[:content_width], curses.color_pair(4))
                    y_pos += 1
            
            # Hallmarks (if enabled)
            if self.show_hallmarks:
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.detail_win.addstr(display_y, 2, "Hallmarks Analysis:", curses.A_UNDERLINE)
                y_pos += 1
                
                hallmarks = hypothesis.get('hallmarks', {})
                hallmark_names = [
                    ('testability', '1. Testability (Falsifiability)'),
                    ('specificity', '2. Specificity and Clarity'),
                    ('grounded_knowledge', '3. Grounded in Prior Knowledge'),
                    ('predictive_power', '4. Predictive Power & Novel Insight'),
                    ('parsimony', '5. Parsimony (Principle of Simplicity)')
                ]
                
                for key, title in hallmark_names:
                    if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                        display_y = y_pos - self.detail_scroll_offset
                        if 2 <= display_y < max_y:
                            self.detail_win.addstr(display_y, 2, title, curses.A_BOLD)
                    y_pos += 1
                    
                    text = hallmarks.get(key, 'No analysis provided.')
                    wrapped_text = textwrap.fill(text, content_width - 3)
                    for line in wrapped_text.split('\n'):
                        if y_pos - 2 >= self.detail_scroll_offset:
                            display_y = y_pos - self.detail_scroll_offset
                            if 2 <= display_y < max_y:
                                self.detail_win.addstr(display_y, 5, line[:content_width-3])
                        y_pos += 1
                    y_pos += 1  # Blank line between hallmarks
            else:
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.detail_win.addstr(display_y, 2, "[Hallmarks hidden - press 'h' to toggle]", curses.color_pair(4))
                y_pos += 1
            
            # References (if enabled)
            if self.show_references:
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.detail_win.addstr(display_y, 2, "Relevant References:", curses.A_UNDERLINE)
                y_pos += 1
                
                references = hypothesis.get('references', [])
                if references:
                    for i, ref in enumerate(references, 1):
                        if isinstance(ref, dict):
                            citation = ref.get('citation', 'No citation')
                            annotation = ref.get('annotation', 'No annotation')
                            
                            # Display citation
                            citation_text = f"{i}. {citation}"
                            wrapped_citation = textwrap.fill(citation_text, content_width - 3)
                            for line in wrapped_citation.split('\n'):
                                if y_pos - 2 >= self.detail_scroll_offset:
                                    display_y = y_pos - self.detail_scroll_offset
                                    if 2 <= display_y < max_y:
                                        self.detail_win.addstr(display_y, 5, line[:content_width-3], curses.A_BOLD)
                                y_pos += 1
                            
                            # Display annotation
                            wrapped_annotation = textwrap.fill(annotation, content_width - 6)
                            for line in wrapped_annotation.split('\n'):
                                if y_pos - 2 >= self.detail_scroll_offset:
                                    display_y = y_pos - self.detail_scroll_offset
                                    if 2 <= display_y < max_y:
                                        self.detail_win.addstr(display_y, 8, line[:content_width-6])
                                y_pos += 1
                            y_pos += 1  # Blank line between references
                        else:
                            # Handle string references
                            ref_text = f"{i}. {str(ref)}"
                            wrapped_ref = textwrap.fill(ref_text, content_width - 3)
                            for line in wrapped_ref.split('\n'):
                                if y_pos - 2 >= self.detail_scroll_offset:
                                    display_y = y_pos - self.detail_scroll_offset
                                    if 2 <= display_y < max_y:
                                        self.detail_win.addstr(display_y, 5, line[:content_width-3])
                                y_pos += 1
                            y_pos += 1  # Blank line
                else:
                    if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                        display_y = y_pos - self.detail_scroll_offset
                        if 2 <= display_y < max_y:
                            self.detail_win.addstr(display_y, 5, "None provided", curses.color_pair(4))
                    y_pos += 1
            else:
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.detail_win.addstr(display_y, 2, "[References hidden - press 'r' to toggle]", curses.color_pair(4))
                y_pos += 1
                
        except curses.error:
            pass  # Ignore if content doesn't fit
            
        self.detail_win.refresh()
        
    def draw_status_bar(self, status_msg=None):
        """Draw the status bar with commands"""
        self.status_win.clear()
        self.status_win.attron(curses.color_pair(6))
        
        # Use provided message or get current status
        if status_msg is not None:
            self.set_status(status_msg)
            display_status = status_msg
        else:
            display_status = self.get_current_status()
        
        # Status message
        status_line = f" Status: {display_status}"
        self.safe_addstr(self.status_win, 0, 0, status_line)
        
        # Commands - show on two lines if needed
        commands_line1 = " f=Feedback n=New l=Load s=Select v=View h=Toggle r=Refs p=PDF q=Quit "
        commands_line2 = " Up/Down=Navigate j/k=Scroll d/u=FastScroll "
        
        # Try to fit both lines, otherwise just show main commands
        if len(commands_line1) + len(status_line) < self.width:
            cmd_start_x = max(0, self.width - len(commands_line1))
            self.safe_addstr(self.status_win, 0, cmd_start_x, commands_line1)
            
            # Add scroll commands on second line if there's room
            if self.STATUS_HEIGHT >= 2 and len(commands_line2) < self.width:
                cmd2_start_x = max(0, self.width - len(commands_line2))
                self.safe_addstr(self.status_win, 1, cmd2_start_x, commands_line2)
        else:
            # Shortened version for narrow terminals
            commands_short = " f=Feedback n=New p=PDF q=Quit j/k=Scroll "
            cmd_start_x = max(0, self.width - len(commands_short))
            if cmd_start_x > len(status_line):
                self.safe_addstr(self.status_win, 0, cmd_start_x, commands_short)
        
        # Fill rest of first line if needed
        if len(commands_line1) + len(status_line) < self.width:
            remaining = self.width - len(status_line) - len(commands_line1)
            if remaining > 0:
                self.status_win.addstr(0, len(status_line), " " * remaining)
            
        self.status_win.attroff(curses.color_pair(6))
        self.status_win.refresh()
        
    def handle_resize(self):
        """Handle terminal resize"""
        self.height, self.width = self.stdscr.getmaxyx()
        self.LIST_WIDTH = int(self.width * 0.35)
        self.DETAIL_WIDTH = self.width - self.LIST_WIDTH - 1
        
        # Recreate panes with new dimensions
        self.create_panes()
        
    def scroll_list(self, direction):
        """Scroll the hypothesis list"""
        if direction > 0:
            self.list_scroll_offset += 1
        else:
            self.list_scroll_offset = max(0, self.list_scroll_offset - 1)
            
    def scroll_detail(self, direction):
        """Scroll the hypothesis details"""
        if direction > 0:
            self.detail_scroll_offset += 1
        else:
            self.detail_scroll_offset = max(0, self.detail_scroll_offset - 1)
            
    def set_status(self, message, persistent=False, timeout=3.0):
        """Set a status message with optional persistence and timeout"""
        self.current_status = message
        self.status_timestamp = time.time()
        self.persistent_status = persistent
        self.status_timeout = timeout
        
    def clear_status_on_action(self):
        """Clear status message when user performs an action"""
        if not self.persistent_status:
            self.current_status = "Ready"
            self.persistent_status = False
            
    def get_current_status(self):
        """Get the current status message, handling timeouts"""
        current_time = time.time()
        
        # Check if status has timed out (unless it's persistent)
        if not self.persistent_status and (current_time - self.status_timestamp) > self.status_timeout:
            self.current_status = "Ready"
            
        return self.current_status
            
    def safe_addstr(self, window, y, x, text, attr=0):
        """Safely add string to window with error handling"""
        try:
            # Get window dimensions
            max_y, max_x = window.getmaxyx()
            
            # Check bounds
            if y < 0 or y >= max_y or x < 0 or x >= max_x:
                return False
                
            # Calculate maximum text length
            max_len = max_x - x - 1
            if max_len <= 0:
                return False
                
            # Clean and truncate text
            safe_text = str(text)[:max_len]
            
            # Remove or replace problematic characters
            safe_text = safe_text.encode('ascii', 'ignore').decode('ascii')
            
            # Add the string
            if attr:
                window.addstr(y, x, safe_text, attr)
            else:
                window.addstr(y, x, safe_text)
            return True
            
        except (curses.error, UnicodeEncodeError, ValueError):
            # Try without attributes as fallback
            try:
                if attr:  # If we had attributes, try without them
                    safe_text = str(text)[:max_len//2]  # Use shorter text
                    safe_text = safe_text.encode('ascii', 'ignore').decode('ascii')
                    window.addstr(y, x, safe_text)
                    return True
            except (curses.error, UnicodeEncodeError, ValueError):
                pass
            return False

# ---------------------------------------------------------------------
# PDF Generation Functions
# ---------------------------------------------------------------------

def generate_hypothesis_pdf(hypothesis, research_goal, output_filename=None):
    """
    Generate a nicely formatted PDF document for a hypothesis.
    
    Args:
        hypothesis (dict): The hypothesis data
        research_goal (str): The research goal
        output_filename (str, optional): Custom output filename
        
    Returns:
        str: Path to generated PDF file, or None if failed
    """
    if not PDF_AVAILABLE:
        return None
        
    try:
        # Generate filename if not provided
        if not output_filename:
            safe_title = "".join(c for c in hypothesis.get('title', 'hypothesis') if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"hypothesis_{safe_title}_{timestamp}.pdf"
        
        # Create the PDF document
        doc = SimpleDocTemplate(output_filename, pagesize=letter,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Define custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=HexColor('#2E4057'),
            alignment=1  # Center alignment
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=HexColor('#34495E'),
            borderWidth=1,
            borderColor=HexColor('#BDC3C7'),
            borderPadding=5,
            backColor=HexColor('#ECF0F1')
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            leading=14,
            alignment=0  # Left alignment
        )
        
        reference_style = ParagraphStyle(
            'ReferenceStyle',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            leftIndent=20,
            leading=12
        )
        
        # Build the story (content)
        story = []
        
        # Document title
        story.append(Paragraph("Scientific Hypothesis Report", title_style))
        story.append(Spacer(1, 12))
        
        # Generation info
        version = hypothesis.get("version", "1.0")
        hyp_type = hypothesis.get("type", "original")
        timestamp = hypothesis.get("generation_timestamp", "Unknown")
        if timestamp != "Unknown":
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime("%B %d, %Y at %I:%M %p")
            except:
                pass
        
        story.append(Paragraph(f"<b>Version:</b> {version} ({hyp_type})", body_style))
        story.append(Paragraph(f"<b>Generated:</b> {timestamp}", body_style))
        story.append(Spacer(1, 20))
        
        # Research Goal
        story.append(Paragraph("Research Goal", heading_style))
        story.append(Paragraph(research_goal, body_style))
        story.append(Spacer(1, 20))
        
        # Hypothesis Title
        story.append(Paragraph("Hypothesis", heading_style))
        hyp_title = hypothesis.get('title', 'Untitled Hypothesis')
        story.append(Paragraph(f"<b>{hyp_title}</b>", body_style))
        story.append(Spacer(1, 15))
        
        # Description
        story.append(Paragraph("Description", heading_style))
        description = hypothesis.get('description', 'No description provided.')
        story.append(Paragraph(description, body_style))
        story.append(Spacer(1, 20))
        
        # Experimental Validation Plan
        story.append(Paragraph("Experimental Validation Plan", heading_style))
        validation = hypothesis.get('experimental_validation', 'No experimental validation plan provided.')
        story.append(Paragraph(validation, body_style))
        story.append(Spacer(1, 20))
        
        # Improvements (if any)
        if hypothesis.get("improvements_made") and hypothesis.get("type") == "improvement":
            story.append(Paragraph("Improvements Made", heading_style))
            improvements = hypothesis.get("improvements_made", "")
            story.append(Paragraph(improvements, body_style))
            story.append(Spacer(1, 20))
        
        # Feedback History
        feedback_history = hypothesis.get("feedback_history", [])
        if feedback_history:
            story.append(Paragraph("Feedback History", heading_style))
            
            feedback_style = ParagraphStyle(
                'FeedbackStyle',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=12,
                leftIndent=15,
                rightIndent=15,
                leading=13,
                backColor=HexColor('#F8F9FA'),
                borderWidth=1,
                borderColor=HexColor('#DEE2E6'),
                borderPadding=8
            )
            
            feedback_meta_style = ParagraphStyle(
                'FeedbackMetaStyle',
                parent=styles['Normal'],
                fontSize=9,
                spaceAfter=8,
                leftIndent=15,
                textColor=HexColor('#6C757D')
            )
            
            for i, feedback_entry in enumerate(feedback_history, 1):
                feedback_text = feedback_entry.get("feedback", "No feedback text")
                timestamp = feedback_entry.get("timestamp", "Unknown time")
                version_before = feedback_entry.get("version_before", "Unknown")
                version_after = feedback_entry.get("version_after", "Unknown")
                
                # Format timestamp
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    formatted_time = dt.strftime("%B %d, %Y at %I:%M %p")
                except:
                    formatted_time = timestamp
                
                # Add feedback entry
                story.append(Paragraph(f"<b>Feedback #{i}</b>", feedback_meta_style))
                story.append(Paragraph(f"Provided: {formatted_time}", feedback_meta_style))
                story.append(Paragraph(f"Version updated: {version_before} → {version_after}", feedback_meta_style))
                story.append(Spacer(1, 6))
                story.append(Paragraph(feedback_text, feedback_style))
                story.append(Spacer(1, 15))
            
            story.append(Spacer(1, 20))
        
        # Hallmarks Analysis
        story.append(Paragraph("Hallmarks Analysis", heading_style))
        hallmarks = hypothesis.get('hallmarks', {})
        
        hallmark_names = [
            ('testability', 'Testability (Falsifiability)'),
            ('specificity', 'Specificity and Clarity'),
            ('grounded_knowledge', 'Grounded in Prior Knowledge'),
            ('predictive_power', 'Predictive Power & Novel Insight'),
            ('parsimony', 'Parsimony (Principle of Simplicity)')
        ]
        
        for key, title in hallmark_names:
            story.append(Paragraph(f"<b>{title}</b>", body_style))
            text = hallmarks.get(key, 'No analysis provided.')
            story.append(Paragraph(text, body_style))
            story.append(Spacer(1, 12))
        
        story.append(Spacer(1, 20))
        
        # References
        story.append(Paragraph("Scientific References", heading_style))
        references = hypothesis.get('references', [])
        
        if references:
            for i, ref in enumerate(references, 1):
                if isinstance(ref, dict):
                    citation = ref.get('citation', 'No citation')
                    annotation = ref.get('annotation', 'No annotation')
                    
                    story.append(Paragraph(f"<b>{i}. {citation}</b>", reference_style))
                    story.append(Paragraph(annotation, reference_style))
                    story.append(Spacer(1, 8))
                else:
                    story.append(Paragraph(f"{i}. {str(ref)}", reference_style))
                    story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("No references provided.", body_style))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            textColor=HexColor('#7F8C8D'),
            alignment=1  # Center alignment
        )
        story.append(Paragraph("Generated by Wisteria Research Hypothesis Generator v5.0", footer_style))
        story.append(Paragraph(f"Document created on {datetime.now().strftime('%B %d, %Y')}", footer_style))
        
        # Build the PDF
        doc.build(story)
        
        return output_filename
        
    except Exception as e:
        # Return None to indicate failure, error details can be logged separately
        return None

# ---------------------------------------------------------------------
# Color and Diff utilities
# ---------------------------------------------------------------------

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'  # Added text
    RED = '\033[91m'    # Removed text
    YELLOW = '\033[93m' # Changed text
    BLUE = '\033[96m'   # Light cyan for better visibility on dark backgrounds
    BOLD = '\033[1m'
    RESET = '\033[0m'   # Reset to default

def highlight_text_changes(old_text, new_text):
    """
    Compare two texts and return the new text with color-coded changes.
    
    Args:
        old_text (str): Original text
        new_text (str): New/improved text
        
    Returns:
        str: New text with ANSI color codes highlighting changes
    """
    if not old_text or not new_text:
        return new_text
    
    # Split into words for better diff granularity
    old_words = old_text.split()
    new_words = new_text.split()
    
    # Generate diff
    differ = difflib.SequenceMatcher(None, old_words, new_words)
    
    result = []
    for tag, i1, i2, j1, j2 in differ.get_opcodes():
        if tag == 'equal':
            # Unchanged text
            result.extend(new_words[j1:j2])
        elif tag == 'delete':
            # Text was removed (don't show in new version)
            continue
        elif tag == 'insert':
            # Text was added
            added_text = ' '.join(new_words[j1:j2])
            result.append(f"{Colors.GREEN}{added_text}{Colors.RESET}")
        elif tag == 'replace':
            # Text was changed
            changed_text = ' '.join(new_words[j1:j2])
            result.append(f"{Colors.YELLOW}{changed_text}{Colors.RESET}")
    
    return ' '.join(result)

def compare_hypothesis_sections(old_hypothesis, new_hypothesis):
    """
    Compare sections of two hypotheses and return a dict with color-coded changes.
    
    Args:
        old_hypothesis (dict): Original hypothesis
        new_hypothesis (dict): Improved hypothesis
        
    Returns:
        dict: New hypothesis with color-coded text showing changes
    """
    if not old_hypothesis:
        return new_hypothesis
    
    result = new_hypothesis.copy()
    
    # Compare title
    old_title = old_hypothesis.get('title', '')
    new_title = new_hypothesis.get('title', '')
    if old_title != new_title:
        result['title_highlighted'] = highlight_text_changes(old_title, new_title)
    
    # Compare description
    old_desc = old_hypothesis.get('description', '')
    new_desc = new_hypothesis.get('description', '')
    if old_desc != new_desc:
        result['description_highlighted'] = highlight_text_changes(old_desc, new_desc)
    
    # Compare hallmarks
    old_hallmarks = old_hypothesis.get('hallmarks', {})
    new_hallmarks = new_hypothesis.get('hallmarks', {})
    result['hallmarks_highlighted'] = {}
    
    for key in ['testability', 'specificity', 'grounded_knowledge', 'predictive_power', 'parsimony']:
        old_text = old_hallmarks.get(key, '')
        new_text = new_hallmarks.get(key, '')
        if old_text != new_text:
            result['hallmarks_highlighted'][key] = highlight_text_changes(old_text, new_text)
    
    # Compare references
    old_references = old_hypothesis.get('references', [])
    new_references = new_hypothesis.get('references', [])
    result['references_highlighted'] = []
    
    # Create a detailed comparison of references
    if old_references != new_references:
        # Create a mapping of old references for comparison
        old_ref_map = {}
        for i, ref in enumerate(old_references):
            if isinstance(ref, dict):
                # Use citation as key for matching similar references
                citation_key = ref.get('citation', f'ref_{i}')
                old_ref_map[citation_key] = ref
        
        # Process each new reference
        for ref in new_references:
            if isinstance(ref, dict):
                new_citation = ref.get('citation', '')
                new_annotation = ref.get('annotation', '')
                
                # Check if we have a similar reference in the old version
                if new_citation in old_ref_map:
                    # Compare with the old version to detect changes
                    old_ref = old_ref_map[new_citation]
                    old_citation = old_ref.get('citation', '')
                    old_annotation = old_ref.get('annotation', '')
                    
                    # Highlight changes within the reference
                    highlighted_citation = highlight_text_changes(old_citation, new_citation) if old_citation != new_citation else new_citation
                    highlighted_annotation = highlight_text_changes(old_annotation, new_annotation) if old_annotation != new_annotation else new_annotation
                    
                    highlighted_ref = {
                        'citation': highlighted_citation,
                        'annotation': highlighted_annotation,
                        'is_modified': old_citation != new_citation or old_annotation != new_annotation
                    }
                else:
                    # This is a completely new reference - highlight it all in green
                    highlighted_ref = {
                        'citation': f"{Colors.GREEN}{new_citation}{Colors.RESET}",
                        'annotation': f"{Colors.GREEN}{new_annotation}{Colors.RESET}",
                        'is_new': True
                    }
            else:
                # Handle string references
                old_ref_strings = [str(r) for r in old_references if not isinstance(r, dict)]
                if str(ref) not in old_ref_strings:
                    highlighted_ref = f"{Colors.GREEN}{ref}{Colors.RESET}"
                else:
                    highlighted_ref = ref
            
            result['references_highlighted'].append(highlighted_ref)
    else:
        # No changes, just copy the references
        result['references_highlighted'] = new_references
    
    return result

def load_model_config(model_shortname):
    """
    Load model configuration from the model_servers.yaml file.
    Returns a dictionary with api_key, api_base, and model_name.
    """
    yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_servers.yaml")
    
    try:
        with open(yaml_path, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)
            
        # Look for the model by shortname
        for server in config['servers']:
            if server['shortname'] == model_shortname:
                api_key = server['openai_api_key']
                # Handle environment variable in api key if present
                if api_key.startswith("${") and api_key.endswith("}"):
                    env_var = api_key[2:-1]
                    api_key = os.environ.get(env_var, "")
                    if not api_key:
                        print(f"Error: Environment variable {env_var} not set")
                        sys.exit(1)
                
                return {
                    'api_key': api_key,
                    'api_base': server['openai_api_base'],
                    'model_name': server['openai_model']
                }
                
        # If not found
        print(f"Error: Model '{model_shortname}' not found in model_servers.yaml")
        print("Available models:", ", ".join([s['shortname'] for s in config['servers']]))
        sys.exit(1)
        
    except FileNotFoundError:
        print(f"Error: model_servers.yaml not found at {yaml_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading model configuration: {e}")
        sys.exit(1)

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def generate_hypotheses(research_goal, config, num_hypotheses=5):
    """
    Generate scientific hypotheses based on a research goal.
    Returns a list of hypothesis objects.
    
    This function uses exponential backoff to handle rate limits and transient errors.
    It will retry up to 5 times with increasing delays between attempts or until max_time is reached.
    
    Args:
        research_goal (str): The research goal or question
        config (dict): Configuration for the model API
        num_hypotheses (int): Number of hypotheses to generate
    """
    # Configure the OpenAI client
    api_key = config['api_key']
    api_base = config['api_base']
    model_name = config['model_name']
    
    # System prompt for hypothesis generation
    system_message = (
        "You are an expert research scientist capable of generating creative, novel, and scientifically rigorous hypotheses. "
        "You excel at identifying unexplored research directions and formulating testable predictions that advance scientific understanding. "
        "Your hypotheses are grounded in existing knowledge while pushing the boundaries of current understanding."
    )
    
    # User prompt with detailed instructions
    user_message = f"""
Based on the following research goal, generate {num_hypotheses} creative and novel scientific hypotheses. Each hypothesis should be original, testable, and provide new insights into the research area.

RESEARCH GOAL:
{research_goal}

For each hypothesis, provide:
1. TITLE: A concise, descriptive title for the hypothesis
2. DESCRIPTION: A detailed paragraph explaining the hypothesis, its key predictions, and potential mechanisms
3. EXPERIMENTAL_VALIDATION: A comprehensive plan for experimentally validating this hypothesis, including specific methods, controls, measurements, and expected outcomes
4. ANALYSIS: Evaluate the hypothesis against each of the five hallmarks of strong scientific hypotheses:
5. REFERENCES: Include relevant scientific references that support or relate to the hypothesis (3-5 references minimum)

The Five Hallmarks of a Strong Scientific Hypothesis:

1. **Testability (Falsifiability)**
   It makes clear, empirical predictions that could be disproven by an experiment or observation, ensuring it can be rigorously evaluated.

2. **Specificity and Clarity**
   The variables, expected relationships, and scope are precisely stated, leaving minimal room for ambiguous interpretation or post-hoc rationalization.

3. **Grounded in Prior Knowledge**
   It builds on—and is logically consistent with—established theory and evidence, while still extending or challenging current understanding.

4. **Predictive Power & Novel Insight**
   Beyond explaining known data, it forecasts new, non-obvious phenomena or quantitative outcomes, guiding future investigations in a meaningful way.

5. **Parsimony (The Principle of Simplicity)**
   Among competing explanations, it employs the fewest necessary assumptions while still accounting for the phenomena, maximizing interpretability and generality.

Please format your response as a JSON array where each hypothesis is an object with the following structure:
{{
  "title": "Hypothesis title",
  "description": "Detailed paragraph description",
  "experimental_validation": "Comprehensive experimental validation plan including specific methods, controls, measurements, timeline, and expected outcomes",
  "hallmarks": {{
    "testability": "Paragraph explaining how this hypothesis satisfies testability/falsifiability",
    "specificity": "Paragraph explaining how this hypothesis satisfies specificity and clarity",
    "grounded_knowledge": "Paragraph explaining how this hypothesis is grounded in prior knowledge",
    "predictive_power": "Paragraph explaining the predictive power and novel insights",
    "parsimony": "Paragraph explaining how this hypothesis follows the principle of simplicity"
  }},
  "references": [
    {{
      "citation": "Author, A. (Year). Title of paper. Journal Name, Volume(Issue), pages.",
      "annotation": "Brief explanation of how this reference supports or relates to the hypothesis"
    }}
  ]
}}

Ensure each hypothesis is substantively different from the others and explores unique aspects or approaches to the research goal.
"""
    
    try:
        # Add a small random delay to avoid overloading the API
        jitter = random.uniform(0.1, 1.0)
        time.sleep(jitter)
        
        # Create a new client instance
        import openai as openai_module
        client = openai_module.OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=180.0  # 3 minute timeout for longer generation
        )
        
        # Check if we need to skip temperature (for reasoning models like o3 and o4mini)
        skip_temperature = any(name in model_name.lower() for name in ["o3", "o4-mini", "o4mini"])
        
        # Prepare parameters
        params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]
        }
        
        # Add temperature only for models that support it
        if not skip_temperature:
            params["temperature"] = 0.7  # Higher temperature for creativity
        
        # Call the API with the prepared parameters
        response = client.chat.completions.create(**params)
        
        # Handle the response based on the OpenAI client version
        if hasattr(response, 'choices'):
            # New OpenAI client
            generated_text = response.choices[0].message.content.strip()
        else:
            # Legacy dict-style response
            generated_text = response["choices"][0]["message"]["content"].strip()
        
        # Try to parse the JSON response
        try:
            # Extract JSON from the response (handle cases where model adds extra text)
            json_start = generated_text.find('[')
            json_end = generated_text.rfind(']') + 1
            if json_start != -1 and json_end != 0:
                json_text = generated_text[json_start:json_end]
                # Clean control characters before parsing
                json_text = clean_json_string(json_text)
                hypotheses = json.loads(json_text)
                return hypotheses
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                hypotheses = json.loads(cleaned_text)
                return hypotheses
                
        except json.JSONDecodeError as je:
            print(f"Error parsing JSON response from model: {je}")
            print(f"Raw response: {generated_text[:500]}...")
            # Return an error structure
            return [{
                "title": "Error: Could not parse model response",
                "description": f"The model returned a response that could not be parsed as JSON: {str(je)}",
                "hallmarks": {
                    "testability": "N/A",
                    "specificity": "N/A", 
                    "grounded_knowledge": "N/A",
                    "predictive_power": "N/A",
                    "parsimony": "N/A"
                },
                "references": [],
                "error": True,
                "raw_response": generated_text
            }]
            
    except Exception as e:
        # Propagate the exception to trigger backoff
        print(f"Error in generate_hypotheses (will retry): {str(e)}")
        raise

def display_hypotheses(hypotheses):
    """
    Display hypotheses in a formatted way to the console.
    
    Args:
        hypotheses (list): List of hypothesis dictionaries
    """
    print("\n" + "=" * 80)
    print("GENERATED SCIENTIFIC HYPOTHESES")
    print("=" * 80)
    
    for i, hypothesis in enumerate(hypotheses, 1):
        if hypothesis.get("error"):
            print(f"\nHYPOTHESIS {i}: ERROR")
            print(f"Title: {hypothesis.get('title', 'Unknown')}")
            print(f"Description: {hypothesis.get('description', 'No description')}")
            continue
            
        version = hypothesis.get("version", "1.0")
        print(f"\nHYPOTHESIS {i} v{version}")
        print("-" * 40)
        print(f"Title: {hypothesis.get('title', 'Untitled')}")
        print(f"\nDescription:")
        print(f"{hypothesis.get('description', 'No description provided.')}")
        
        hallmarks = hypothesis.get('hallmarks', {})
        print(f"\nHallmarks Analysis:")
        
        print(f"\n1. Testability (Falsifiability):")
        print(f"   {hallmarks.get('testability', 'No analysis provided.')}")
        
        print(f"\n2. Specificity and Clarity:")
        print(f"   {hallmarks.get('specificity', 'No analysis provided.')}")
        
        print(f"\n3. Grounded in Prior Knowledge:")
        print(f"   {hallmarks.get('grounded_knowledge', 'No analysis provided.')}")
        
        print(f"\n4. Predictive Power & Novel Insight:")
        print(f"   {hallmarks.get('predictive_power', 'No analysis provided.')}")
        
        print(f"\n5. Parsimony (Principle of Simplicity):")
        print(f"   {hallmarks.get('parsimony', 'No analysis provided.')}")
        
        print("-" * 80)

def display_single_hypothesis(hypothesis, hypothesis_number, previous_hypothesis=None, show_hallmarks=True, show_references=True):
    """
    Display a single hypothesis in a formatted way to the console for interactive review.
    
    Args:
        hypothesis (dict): Hypothesis dictionary
        hypothesis_number (int): The number of this hypothesis in the session
        previous_hypothesis (dict, optional): Previous version to compare against for highlighting changes
    """
    print("\n" + "=" * 80)
    
    # Show version number
    version = hypothesis.get("version", "1.0")
    
    # Show if this is an improvement
    if hypothesis.get("type") == "improvement" and previous_hypothesis:
        print(f"HYPOTHESIS #{hypothesis_number} v{version} (IMPROVED)")
        print(f"{Colors.GREEN}New content and additions are highlighted in green{Colors.RESET}")
        print(f"{Colors.YELLOW}Modified sections are highlighted in yellow{Colors.RESET}")
        
        # Get color-highlighted version
        highlighted = compare_hypothesis_sections(previous_hypothesis, hypothesis)
    else:
        print(f"HYPOTHESIS #{hypothesis_number} v{version}")
        highlighted = hypothesis
    
    print("=" * 80)
    
    if hypothesis.get("error"):
        print(f"ERROR: {hypothesis.get('title', 'Unknown')}")
        print(f"Description: {hypothesis.get('description', 'No description')}")
        return
    
    # Display title (with highlighting if improved)
    title_text = highlighted.get('title_highlighted', hypothesis.get('title', 'Untitled'))
    print(f"Title: {title_text}")
    
    # Display description (with highlighting if improved)
    desc_text = highlighted.get('description_highlighted', hypothesis.get('description', 'No description provided.'))
    print(f"\nDescription:")
    print(f"{desc_text}")
    
    # Display improvements made (if this is an improvement)
    if hypothesis.get("improvements_made"):
        print(f"\n{Colors.BLUE}Improvements made based on feedback:{Colors.RESET}")
        print(f"{Colors.BLUE}{hypothesis.get('improvements_made')}{Colors.RESET}")
    
    # Display hallmarks analysis only if show_hallmarks is True
    if show_hallmarks:
        hallmarks = hypothesis.get('hallmarks', {})
        highlighted_hallmarks = highlighted.get('hallmarks_highlighted', {})
        print(f"\nHallmarks Analysis:")
        
        # Display each hallmark with highlighting if available
        hallmark_names = [
            ('testability', 'Testability (Falsifiability)'),
            ('specificity', 'Specificity and Clarity'),
            ('grounded_knowledge', 'Grounded in Prior Knowledge'),
            ('predictive_power', 'Predictive Power & Novel Insight'),
            ('parsimony', 'Parsimony (Principle of Simplicity)')
        ]
        
        for i, (key, title) in enumerate(hallmark_names, 1):
            print(f"\n{i}. {title}:")
            text = highlighted_hallmarks.get(key, hallmarks.get(key, 'No analysis provided.'))
            print(f"   {text}")
    else:
        print(f"\n{Colors.BLUE}[Hallmarks analysis hidden - use \\h to toggle]{Colors.RESET}")
    
    
    # Display references only if show_references is True
    if show_references:
        references = hypothesis.get('references', [])
        highlighted_references = highlighted.get('references_highlighted', references)
        if references:
            print(f"\nRelevant References:")
            for i, ref in enumerate(highlighted_references, 1):
                if isinstance(ref, dict):
                    citation = ref.get('citation', 'No citation')
                    annotation = ref.get('annotation', 'No annotation')
                    print(f"\n{i}. {citation}")
                    print(f"   {annotation}")
                else:
                    # Handle string references (already highlighted if new)
                    print(f"\n{i}. {ref}")
        else:
            print(f"\nRelevant References: None provided")
    else:
        print(f"\n{Colors.BLUE}[References hidden - use \\r to toggle]{Colors.RESET}")
    print("=" * 80)

def get_user_feedback(all_hypotheses=None, current_hypothesis=None):
    """
    Collect user feedback for hypothesis improvement.
    
    Returns:
        str: User feedback text, or special command strings
    """
    print("\n" + "-" * 60)
    print("What would you like to do with this hypothesis?")
    print("-" * 60)
    print("\\f - Provide feedback to improve this hypothesis")
    print("\\n - Generate a new hypothesis (different from previous ones)")
    print("\\l - Load from a JSON file a previous session log")
    print("\\v - View the titles of hypotheses in current session")
    print("\\s - Select a hypothesis to continue to refine")
    print("\\h - Toggle hallmarks analysis display")
    print("\\r - Toggle references display")
    print("\\q - Quit and save all hypotheses")
    print("-" * 60)
    
    while True:
        choice = input("\nEnter your choice (\\f, \\n, \\l, \\v, \\s, \\h, \\r, or \\q): ").strip()
        
        if choice == "\\f":
            print("\nPlease provide your feedback for improving this hypothesis:")
            print("(Be specific about what aspects need improvement, what's missing, or what should be changed)")
            feedback = input("\nYour feedback: ").strip()
            if feedback:
                return feedback
            else:
                print("Please provide some feedback or choose a different option.")
                continue
                
        elif choice == "\\n":
            return "GENERATE_NEW"
            
        elif choice == "\\l":
            filename = input("\nEnter JSON filename to load: ").strip()
            if filename:
                return f"LOAD_SESSION:{filename}"
            else:
                print("Please provide a filename or choose a different option.")
                continue
                
        elif choice == "\\v":
            if all_hypotheses:
                view_hypothesis_titles(all_hypotheses)
            else:
                print("No hypotheses available to view.")
            continue
            
        elif choice == "\\s":
            if all_hypotheses:
                selected_num = select_hypothesis(all_hypotheses)
                if selected_num is not None:
                    return f"SELECT_HYPOTHESIS:{selected_num}"
            else:
                print("No hypotheses available to select.")
            continue
            
        elif choice == "\\h":
            return "TOGGLE_HALLMARKS"
            
        elif choice == "\\r":
            return "TOGGLE_REFERENCES"
            
        elif choice == "\\q":
            return "QUIT"
            
        else:
            print("Invalid choice. Please enter \\f, \\n, \\l, \\v, \\s, \\h, \\r, or \\q.")

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def improve_hypothesis(research_goal, current_hypothesis, user_feedback, config):
    """
    Improve a hypothesis based on user feedback.
    
    Args:
        research_goal (str): The original research goal
        current_hypothesis (dict): The current hypothesis to improve
        user_feedback (str): User feedback for improvement
        config (dict): Configuration for the model API
        
    Returns:
        dict: Improved hypothesis object
    """
    # Configure the OpenAI client
    api_key = config['api_key']
    api_base = config['api_base']
    model_name = config['model_name']
    
    # System prompt for hypothesis improvement
    system_message = (
        "You are an expert research scientist who excels at refining and improving scientific hypotheses based on feedback. "
        "You take existing hypotheses and user feedback to create enhanced versions that address the concerns and suggestions "
        "while maintaining scientific rigor and novelty."
    )
    
    # User prompt with detailed instructions
    user_message = f"""
Based on the original research goal, current hypothesis, and user feedback provided below, please improve the hypothesis to address the feedback while maintaining scientific quality.

ORIGINAL RESEARCH GOAL:
{research_goal}

CURRENT HYPOTHESIS:
Title: {current_hypothesis.get('title', 'Untitled')}
Description: {current_hypothesis.get('description', 'No description')}
Experimental Validation: {current_hypothesis.get('experimental_validation', 'No validation plan provided')}

USER FEEDBACK:
{user_feedback}

Please provide an improved version of this hypothesis that:
1. Addresses the specific concerns and suggestions in the user feedback
2. Maintains or enhances scientific rigor and testability
3. Keeps the core innovative insights while making requested improvements
4. Ensures the hypothesis remains relevant to the original research goal
5. Includes relevant scientific references that support the improved hypothesis (3-5 references minimum)

Please format your response as a JSON object with the following structure:
{{
  "title": "Improved hypothesis title",
  "description": "Detailed paragraph description incorporating the feedback",
  "experimental_validation": "Comprehensive experimental validation plan including specific methods, controls, measurements, timeline, and expected outcomes",
  "hallmarks": {{
    "testability": "Paragraph explaining how this improved hypothesis satisfies testability/falsifiability",
    "specificity": "Paragraph explaining how this improved hypothesis satisfies specificity and clarity", 
    "grounded_knowledge": "Paragraph explaining how this improved hypothesis is grounded in prior knowledge",
    "predictive_power": "Paragraph explaining the predictive power and novel insights",
    "parsimony": "Paragraph explaining how this improved hypothesis follows the principle of simplicity"
  }},
  "references": [
    {{
      "citation": "Author, A. (Year). Title of paper. Journal Name, Volume(Issue), pages.",
      "annotation": "Brief explanation of how this reference supports or relates to the hypothesis"
    }}
  ],
  "improvements_made": "Brief explanation of what specific changes were made based on the user feedback"
}}
"""
    
    try:
        # Add a small random delay to avoid overloading the API
        jitter = random.uniform(0.1, 1.0)
        time.sleep(jitter)
        
        # Create a new client instance
        import openai as openai_module
        client = openai_module.OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=180.0  # 3 minute timeout for longer generation
        )
        
        # Check if we need to skip temperature (for reasoning models like o3 and o4mini)
        skip_temperature = any(name in model_name.lower() for name in ["o3", "o4-mini", "o4mini"])
        
        # Prepare parameters
        params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]
        }
        
        # Add temperature only for models that support it
        if not skip_temperature:
            params["temperature"] = 0.7  # Higher temperature for creativity
        
        # Call the API with the prepared parameters
        response = client.chat.completions.create(**params)
        
        # Handle the response based on the OpenAI client version
        if hasattr(response, 'choices'):
            # New OpenAI client
            generated_text = response.choices[0].message.content.strip()
        else:
            # Legacy dict-style response
            generated_text = response["choices"][0]["message"]["content"].strip()
        
        # Try to parse the JSON response
        try:
            # Extract JSON from the response (handle cases where model adds extra text)
            json_start = generated_text.find('{')
            json_end = generated_text.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_text = generated_text[json_start:json_end]
                # Clean control characters before parsing
                json_text = clean_json_string(json_text)
                improved_hypothesis = json.loads(json_text)
                # Initialize feedback history if not present
                if "feedback_history" not in improved_hypothesis:
                    improved_hypothesis["feedback_history"] = []
                return improved_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                improved_hypothesis = json.loads(cleaned_text)
                # Initialize feedback history if not present
                if "feedback_history" not in improved_hypothesis:
                    improved_hypothesis["feedback_history"] = []
                return improved_hypothesis
                
        except json.JSONDecodeError as je:
            print(f"Error parsing JSON response from model: {je}")
            print(f"Raw response: {generated_text[:500]}...")
            # Return an error structure
            return {
                "title": "Error: Could not parse model response",
                "description": f"The model returned a response that could not be parsed as JSON: {str(je)}",
                "hallmarks": {
                    "testability": "N/A",
                    "specificity": "N/A", 
                    "grounded_knowledge": "N/A",
                    "predictive_power": "N/A",
                    "parsimony": "N/A"
                },
                "references": [],
                "improvements_made": "N/A",
                "error": True,
                "raw_response": generated_text
            }
            
    except Exception as e:
        # Propagate the exception to trigger backoff
        print(f"Error in improve_hypothesis (will retry): {str(e)}")
        raise

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def generate_new_hypothesis(research_goal, previous_hypotheses, config):
    """
    Generate a new hypothesis that is different from previous ones.
    
    Args:
        research_goal (str): The research goal or question
        previous_hypotheses (list): List of previously generated hypotheses
        config (dict): Configuration for the model API
        
    Returns:
        dict: New hypothesis object
    """
    # Configure the OpenAI client
    api_key = config['api_key']
    api_base = config['api_base']
    model_name = config['model_name']
    
    # System prompt for new hypothesis generation
    system_message = (
        "You are an expert research scientist capable of generating creative, novel, and scientifically rigorous hypotheses. "
        "You excel at identifying unexplored research directions and formulating testable predictions that advance scientific understanding. "
        "You are particularly skilled at generating hypotheses that are substantively different from existing ones while remaining relevant to the research goal."
    )
    
    # Create a summary of previous hypotheses to avoid duplication
    previous_summaries = []
    for i, hyp in enumerate(previous_hypotheses, 1):
        title = hyp.get('title', 'Untitled')
        description = hyp.get('description', 'No description')[:200] + "..." if len(hyp.get('description', '')) > 200 else hyp.get('description', 'No description')
        previous_summaries.append(f"Hypothesis {i}: {title}\nBrief description: {description}")
    
    previous_hypotheses_text = "\n\n".join(previous_summaries)
    
    # User prompt with detailed instructions
    user_message = f"""
Based on the following research goal, generate 1 creative and novel scientific hypothesis that is SUBSTANTIVELY DIFFERENT from the previous hypotheses listed below.

RESEARCH GOAL:
{research_goal}

PREVIOUS HYPOTHESES TO AVOID DUPLICATING:
{previous_hypotheses_text}

Your new hypothesis should:
1. Explore a different aspect, mechanism, or approach related to the research goal
2. Be clearly distinct from all previous hypotheses in its core concept and methodology
3. Be original, testable, and provide new insights into the research area
4. Still be relevant and valuable for addressing the research goal
5. Include relevant scientific references that support the new hypothesis (3-5 references minimum)

Please format your response as a JSON object with the following structure:
{{
  "title": "Hypothesis title",
  "description": "Detailed paragraph explanation of the hypothesis, its key predictions, and potential mechanisms",
  "experimental_validation": "Comprehensive experimental validation plan including specific methods, controls, measurements, timeline, and expected outcomes",
  "hallmarks": {{
    "testability": "Paragraph explaining how this hypothesis satisfies testability/falsifiability",
    "specificity": "Paragraph explaining how this hypothesis satisfies specificity and clarity",
    "grounded_knowledge": "Paragraph explaining how this hypothesis is grounded in prior knowledge",
    "predictive_power": "Paragraph explaining the predictive power and novel insights",
    "parsimony": "Paragraph explaining how this hypothesis follows the principle of simplicity"
  }},
  "references": [
    {{
      "citation": "Author, A. (Year). Title of paper. Journal Name, Volume(Issue), pages.",
      "annotation": "Brief explanation of how this reference supports or relates to the hypothesis"
    }}
  ]
}}

Ensure this hypothesis explores a unique angle that has not been covered by the previous hypotheses.
"""
    
    try:
        # Add a small random delay to avoid overloading the API
        jitter = random.uniform(0.1, 1.0)
        time.sleep(jitter)
        
        # Create a new client instance
        import openai as openai_module
        client = openai_module.OpenAI(
            api_key=api_key,
            base_url=api_base,
            timeout=180.0  # 3 minute timeout for longer generation
        )
        
        # Check if we need to skip temperature (for reasoning models like o3 and o4mini)
        skip_temperature = any(name in model_name.lower() for name in ["o3", "o4-mini", "o4mini"])
        
        # Prepare parameters
        params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]
        }
        
        # Add temperature only for models that support it
        if not skip_temperature:
            params["temperature"] = 0.8  # Higher temperature for more creativity
        
        # Call the API with the prepared parameters
        response = client.chat.completions.create(**params)
        
        # Handle the response based on the OpenAI client version
        if hasattr(response, 'choices'):
            # New OpenAI client
            generated_text = response.choices[0].message.content.strip()
        else:
            # Legacy dict-style response
            generated_text = response["choices"][0]["message"]["content"].strip()
        
        # Try to parse the JSON response
        try:
            # Extract JSON from the response (handle cases where model adds extra text)
            json_start = generated_text.find('{')
            json_end = generated_text.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_text = generated_text[json_start:json_end]
                # Clean control characters before parsing
                json_text = clean_json_string(json_text)
                new_hypothesis = json.loads(json_text)
                # Initialize feedback history for new hypotheses
                if "feedback_history" not in new_hypothesis:
                    new_hypothesis["feedback_history"] = []
                return new_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                new_hypothesis = json.loads(cleaned_text)
                # Initialize feedback history for new hypotheses
                if "feedback_history" not in new_hypothesis:
                    new_hypothesis["feedback_history"] = []
                return new_hypothesis
                
        except json.JSONDecodeError as je:
            print(f"Error parsing JSON response from model: {je}")
            print(f"Raw response: {generated_text[:500]}...")
            # Return an error structure
            return {
                "title": "Error: Could not parse model response",
                "description": f"The model returned a response that could not be parsed as JSON: {str(je)}",
                "hallmarks": {
                    "testability": "N/A",
                    "specificity": "N/A", 
                    "grounded_knowledge": "N/A",
                    "predictive_power": "N/A",
                    "parsimony": "N/A"
                },
                "references": [],
                "error": True,
                "raw_response": generated_text
            }
            
    except Exception as e:
        # Propagate the exception to trigger backoff
        print(f"Error in generate_new_hypothesis (will retry): {str(e)}")
        raise

def save_hypotheses_to_json(hypotheses, output_file, metadata):
    """
    Save hypotheses to a JSON file with metadata.
    
    Args:
        hypotheses (list): List of hypothesis dictionaries
        output_file (str): Path to output file
        metadata (dict): Metadata about the generation process
    """
    output_data = {
        "metadata": metadata,
        "hypotheses": hypotheses
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

def load_session_from_json(filename):
    """
    Load a previous session from a JSON file.
    
    Args:
        filename (str): Path to the JSON file
        
    Returns:
        tuple: (research_goal, all_hypotheses, metadata) or (None, None, None) if error
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        metadata = data.get("metadata", {})
        hypotheses = data.get("hypotheses", [])
        research_goal = metadata.get("research_goal", "")
        
        # Ensure all loaded hypotheses have feedback_history field
        for hypothesis in hypotheses:
            if "feedback_history" not in hypothesis:
                hypothesis["feedback_history"] = []
                # Migrate old user_feedback to feedback_history if present
                if "user_feedback" in hypothesis and hypothesis["user_feedback"]:
                    feedback_entry = {
                        "feedback": hypothesis["user_feedback"],
                        "timestamp": hypothesis.get("generation_timestamp", datetime.now().isoformat()),
                        "version_before": "1.0",  # Default since we don't have this info
                        "version_after": hypothesis.get("version", "1.1")
                    }
                    hypothesis["feedback_history"].append(feedback_entry)
        
        print(f"Loaded session from {filename}")
        print(f"Original research goal: {research_goal}")
        print(f"Found {len(hypotheses)} hypothesis versions")
        
        return research_goal, hypotheses, metadata
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in file '{filename}': {e}")
        return None, None, None
    except Exception as e:
        print(f"Error loading session from '{filename}': {e}")
        return None, None, None

def view_hypothesis_titles(all_hypotheses):
    """
    Display the titles of all hypotheses in the current session.
    
    Args:
        all_hypotheses (list): List of hypothesis dictionaries
    """
    if not all_hypotheses:
        print("No hypotheses available.")
        return
    
    print("\\n" + "=" * 60)
    print("HYPOTHESIS TITLES IN CURRENT SESSION")
    print("=" * 60)
    
    # Group hypotheses by hypothesis number
    hypothesis_groups = {}
    for hyp in all_hypotheses:
        hyp_num = hyp.get("hypothesis_number", 0)
        if hyp_num not in hypothesis_groups:
            hypothesis_groups[hyp_num] = []
        hypothesis_groups[hyp_num].append(hyp)
    
    for hyp_num in sorted(hypothesis_groups.keys()):
        hyp_versions = hypothesis_groups[hyp_num]
        # Get the latest version
        latest_version = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
        
        version = latest_version.get("version", "1.0")
        title = latest_version.get("title", "Untitled")
        hyp_type = latest_version.get("type", "unknown")
        
        type_indicator = ""
        if hyp_type == "improvement":
            type_indicator = " (improved)"
        elif hyp_type == "new_alternative":
            type_indicator = " (alternative)"
        
        print(f"{hyp_num}. [v{version}] {title}{type_indicator}")
    
    print("=" * 60)

def select_hypothesis(all_hypotheses):
    """
    Allow user to select a hypothesis to continue refining.
    
    Args:
        all_hypotheses (list): List of hypothesis dictionaries
        
    Returns:
        int: Selected hypothesis number, or None if cancelled
    """
    if not all_hypotheses:
        print("No hypotheses available.")
        return None
    
    # Group hypotheses by hypothesis number
    hypothesis_groups = {}
    for hyp in all_hypotheses:
        hyp_num = hyp.get("hypothesis_number", 0)
        if hyp_num not in hypothesis_groups:
            hypothesis_groups[hyp_num] = []
        hypothesis_groups[hyp_num].append(hyp)
    
    available_numbers = sorted(hypothesis_groups.keys())
    
    print("\\n" + "-" * 50)
    print("SELECT HYPOTHESIS TO REFINE")
    print("-" * 50)
    
    for hyp_num in available_numbers:
        hyp_versions = hypothesis_groups[hyp_num]
        latest_version = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
        
        version = latest_version.get("version", "1.0")
        title = latest_version.get("title", "Untitled")
        
        print(f"{hyp_num}. [v{version}] {title}")
    
    print("-" * 50)
    
    while True:
        try:
            choice = input("Enter hypothesis number to select (or 'c' to cancel): ").strip()
            
            if choice.lower() == 'c':
                return None
                
            choice_num = int(choice)
            if choice_num in available_numbers:
                return choice_num
            else:
                print(f"Invalid choice. Please select from: {available_numbers}")
                
        except ValueError:
            print("Please enter a valid number or 'c' to cancel.")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Wisteria Research Hypothesis Generator v5.0 - Curses Multi-Pane Interface')
    
    # Create mutually exclusive group for goal input
    goal_group = parser.add_mutually_exclusive_group(required=False)
    goal_group.add_argument('research_goal_file', nargs='?', help='Text file containing the research goal')
    goal_group.add_argument('--goal', help='Research goal specified directly as text')
    
    parser.add_argument('--model', help='Model shortname from model_servers.yaml')
    parser.add_argument('--output', help='Output JSON file (default: hypotheses_<timestamp>.json)')
    parser.add_argument('--resume', help='Resume from a previous session JSON file')
    parser.add_argument('--num-hypotheses', type=int, default=1, 
                       help='Number of initial hypotheses to generate (default: 1)')
    parser.add_argument('--test-feedback', action='store_true',
                       help='Run feedback tracking test and generate sample PDF')
    return parser.parse_args()

def curses_hypothesis_session(stdscr, research_goal, model_config, initial_hypotheses=None, num_initial_hypotheses=1):
    """
    Run a curses-based interactive hypothesis generation and refinement session.
    
    Args:
        stdscr: Curses standard screen object
        research_goal (str): The research goal or question
        model_config (dict): Configuration for the model API
        initial_hypotheses (list, optional): Previously loaded hypotheses to continue from
        
    Returns:
        list: All hypotheses generated during the session (including refinements)
    """
    # Initialize curses interface
    interface = CursesInterface(stdscr)
    
    # Setup initial data
    if initial_hypotheses:
        all_hypotheses = initial_hypotheses.copy()
        hypothesis_counter = max([h.get("hypothesis_number", 0) for h in all_hypotheses] + [0])
        # Rebuild version tracker
        version_tracker = {}
        hypothesis_groups = {}
        for hyp in all_hypotheses:
            hyp_num = hyp.get("hypothesis_number", 0)
            if hyp_num not in hypothesis_groups:
                hypothesis_groups[hyp_num] = []
            hypothesis_groups[hyp_num].append(hyp)
        
        for hyp_num, hyp_versions in hypothesis_groups.items():
            max_version = 0
            for hyp in hyp_versions:
                version_str = hyp.get("version", "1.0")
                try:
                    version_parts = version_str.split('.')
                    if len(version_parts) >= 2:
                        minor_version = int(version_parts[1])
                        max_version = max(max_version, minor_version)
                except:
                    pass
            version_tracker[hyp_num] = max_version
        
        # Start with the most recent hypothesis
        current_hypothesis = max(all_hypotheses, key=lambda h: h.get("generation_timestamp", ""))
        interface.current_hypothesis_idx = current_hypothesis.get("hypothesis_number", 1) - 1
        
    else:
        all_hypotheses = []
        hypothesis_counter = 0
        version_tracker = {}
        
        # Generate initial hypotheses with progress display
        if num_initial_hypotheses == 1:
            try:
                # Show animated progress for single hypothesis
                animation_chars = ['|', '/', '-', '\\']
                generation_complete = False
                generated_hypothesis = None
                generation_error = None
                
                def generate_single_with_progress():
                    nonlocal generation_complete, generated_hypothesis, generation_error
                    try:
                        generated_hypothesis = generate_hypotheses(research_goal, model_config, num_hypotheses=1)
                    except Exception as e:
                        generation_error = e
                    finally:
                        generation_complete = True
                
                # Start generation in background thread
                generation_thread = threading.Thread(target=generate_single_with_progress)
                generation_thread.start()
                
                # Animate progress while generation is running
                animation_counter = 0
                while not generation_complete:
                    anim_char = animation_chars[animation_counter % len(animation_chars)]
                    working_msg = f"Generating initial hypothesis {anim_char} Working..."
                    interface.draw_status_bar(working_msg)
                    interface.stdscr.refresh()
                    time.sleep(0.3)  # Update animation every 300ms
                    animation_counter += 1
                
                # Wait for thread to complete
                generation_thread.join()
                
                # Handle results
                if generation_error:
                    raise generation_error
                
                initial_hypotheses = generated_hypothesis
                if initial_hypotheses and not initial_hypotheses[0].get("error"):
                    interface.draw_status_bar("Initial hypothesis completed!")
                    interface.stdscr.refresh()
                    time.sleep(0.5)
                    
            except Exception as e:
                interface.draw_status_bar(f"Error: {str(e)[:50]}")
                interface.stdscr.refresh()
                stdscr.getch()
                return []
        else:
            # Generate hypotheses one by one to show progress
            initial_hypotheses = []
            
            for i in range(num_initial_hypotheses):
                # Update progress display with visual progress bar
                progress_percent = (i / num_initial_hypotheses) * 100
                bar_length = 20
                filled_length = int(bar_length * i // num_initial_hypotheses)
                bar = '█' * filled_length + '░' * (bar_length - filled_length)
                progress_msg = f"Generating hypothesis {i+1}/{num_initial_hypotheses} [{bar}] {progress_percent:.0f}%"
                interface.draw_status_bar(progress_msg)
                interface.stdscr.refresh()
                
                try:
                    # Show animated "working" status during generation
                    animation_chars = ['|', '/', '-', '\\']
                    generation_complete = False
                    generated_hypothesis = None
                    generation_error = None
                    
                    def generate_with_progress():
                        nonlocal generation_complete, generated_hypothesis, generation_error
                        try:
                            generated_hypothesis = generate_hypotheses(research_goal, model_config, num_hypotheses=1)
                        except Exception as e:
                            generation_error = e
                        finally:
                            generation_complete = True
                    
                    # Start generation in background thread
                    generation_thread = threading.Thread(target=generate_with_progress)
                    generation_thread.start()
                    
                    # Animate progress while generation is running
                    animation_counter = 0
                    while not generation_complete:
                        anim_char = animation_chars[animation_counter % len(animation_chars)]
                        working_msg = f"Generating hypothesis {i+1}/{num_initial_hypotheses} [{bar}] {anim_char} Working..."
                        interface.draw_status_bar(working_msg)
                        interface.stdscr.refresh()
                        time.sleep(0.3)  # Update animation every 300ms
                        animation_counter += 1
                    
                    # Wait for thread to complete
                    generation_thread.join()
                    
                    # Handle results
                    if generation_error:
                        raise generation_error
                    
                    single_hypothesis = generated_hypothesis
                    
                    if single_hypothesis and not single_hypothesis[0].get("error"):
                        initial_hypotheses.extend(single_hypothesis)
                        # Show completion for this hypothesis
                        completed_msg = f"Hypothesis {i+1}/{num_initial_hypotheses} completed! [{bar}]"
                        interface.draw_status_bar(completed_msg)
                        interface.stdscr.refresh()
                        time.sleep(0.5)  # Brief pause to show completion
                    else:
                        # Show error but continue with others
                        error_msg = f"Error generating hypothesis {i+1}, continuing..."
                        interface.draw_status_bar(error_msg)
                        interface.stdscr.refresh()
                        time.sleep(1)  # Brief pause to show error
                        
                except Exception as e:
                    # Show error but continue with others
                    error_msg = f"Error on hypothesis {i+1}: {str(e)[:30]}"
                    interface.draw_status_bar(error_msg)
                    interface.stdscr.refresh()
                    time.sleep(1)  # Brief pause to show error
        
        # Check if we got any valid hypotheses
        if not initial_hypotheses or all(h.get("error") for h in initial_hypotheses):
            interface.draw_status_bar("Error: No valid hypotheses generated")
            interface.stdscr.refresh()
            stdscr.getch()  # Wait for user input before exiting
            return []
        
        # Show final progress if multiple hypotheses were generated
        if num_initial_hypotheses > 1:
            bar = '█' * 20  # Full progress bar
            final_progress_msg = f"Generated {len(initial_hypotheses)}/{num_initial_hypotheses} [{bar}] 100% - Processing..."
            interface.draw_status_bar(final_progress_msg)
            interface.stdscr.refresh()
        else:
            interface.draw_status_bar("Processing generated hypothesis...")
            interface.stdscr.refresh()
        
        for i, hypothesis in enumerate(initial_hypotheses):
            if not hypothesis.get("error"):
                hypothesis_counter += 1
                version_tracker[hypothesis_counter] = 0
                hypothesis["hypothesis_number"] = hypothesis_counter
                hypothesis["version"] = "1.0"
                hypothesis["type"] = "original"
                hypothesis["generation_timestamp"] = datetime.now().isoformat()
                all_hypotheses.append(hypothesis)
        
        if not all_hypotheses:
            interface.draw_status_bar("No valid hypotheses to display")
            interface.stdscr.refresh()
            stdscr.getch()
            return []
        
        # Show completion message
        success_count = len(all_hypotheses)
        if success_count == num_initial_hypotheses:
            completion_msg = f"Successfully generated {success_count} hypotheses! Ready to explore."
        else:
            completion_msg = f"Generated {success_count} of {num_initial_hypotheses} hypotheses. Ready to explore."
        
        interface.draw_status_bar(completion_msg)
        interface.stdscr.refresh()
        time.sleep(1.5)  # Show completion message briefly
        
        # Start with the first hypothesis
        interface.current_hypothesis_idx = 0
    
    # Main curses loop
    stdscr.nodelay(1)  # Non-blocking input
    stdscr.timeout(100)  # 100ms timeout
    
    waiting_for_feedback = False
    feedback_input = ""
    
    while True:
        try:
            # Handle terminal resize
            new_height, new_width = stdscr.getmaxyx()
            if new_height != interface.height or new_width != interface.width:
                interface.handle_resize()
            
            # Get current hypothesis
            if all_hypotheses and 0 <= interface.current_hypothesis_idx < len(all_hypotheses):
                # Group hypotheses and get latest version of selected hypothesis
                hypothesis_groups = {}
                for hyp in all_hypotheses:
                    hyp_num = hyp.get("hypothesis_number", 0)
                    if hyp_num not in hypothesis_groups:
                        hypothesis_groups[hyp_num] = []
                    hypothesis_groups[hyp_num].append(hyp)
                
                sorted_nums = sorted(hypothesis_groups.keys())
                if interface.current_hypothesis_idx < len(sorted_nums):
                    selected_num = sorted_nums[interface.current_hypothesis_idx]
                    hyp_versions = hypothesis_groups[selected_num]
                    current_hypothesis = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
                else:
                    current_hypothesis = None
            else:
                current_hypothesis = None
            
            # Draw interface
            interface.draw_header(research_goal, model_config['model_name'])
            interface.draw_hypothesis_list(all_hypotheses)
            interface.draw_hypothesis_details(current_hypothesis)
            
            if waiting_for_feedback:
                interface.draw_status_bar(f"Enter feedback: {feedback_input}")
            else:
                interface.draw_status_bar()  # Use current status
            
            # Handle input
            try:
                key = stdscr.getch()
                if key != -1:  # Key was pressed
                    if waiting_for_feedback:
                        # Handle feedback input
                        if key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                            # Submit feedback
                            if feedback_input.strip():
                                waiting_for_feedback = False
                                interface.set_status("Processing feedback...", persistent=True)
                                interface.draw_status_bar()
                                stdscr.refresh()
                                
                                try:
                                    improved_hypothesis = improve_hypothesis(
                                        research_goal, current_hypothesis, feedback_input.strip(), model_config
                                    )
                                    if improved_hypothesis.get("error"):
                                        interface.set_status("Error improving hypothesis")
                                    else:
                                        # Add improved hypothesis
                                        hypothesis_number = current_hypothesis["hypothesis_number"]
                                        version_tracker[hypothesis_number] += 1
                                        improved_hypothesis["hypothesis_number"] = hypothesis_number
                                        improved_hypothesis["version"] = f"1.{version_tracker[hypothesis_number]}"
                                        improved_hypothesis["type"] = "improvement"
                                        improved_hypothesis["original_hypothesis_id"] = current_hypothesis.get("hypothesis_number")
                                        improved_hypothesis["user_feedback"] = feedback_input.strip()
                                        
                                        # Initialize or copy feedback history
                                        feedback_history = current_hypothesis.get("feedback_history", [])
                                        feedback_entry = {
                                            "feedback": feedback_input.strip(),
                                            "timestamp": datetime.now().isoformat(),
                                            "version_before": current_hypothesis.get("version", "1.0"),
                                            "version_after": f"1.{version_tracker[hypothesis_number]}"
                                        }
                                        feedback_history.append(feedback_entry)
                                        improved_hypothesis["feedback_history"] = feedback_history
                                        
                                        improved_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                                        all_hypotheses.append(improved_hypothesis)
                                        interface.set_status("Hypothesis improved!")
                                        
                                except Exception as e:
                                    interface.set_status(f"Error: {str(e)[:50]}")
                                
                                feedback_input = ""
                            else:
                                waiting_for_feedback = False
                                interface.set_status("Feedback cancelled")
                                feedback_input = ""
                                
                        elif key == 27:  # ESC key
                            waiting_for_feedback = False
                            interface.set_status("Feedback cancelled")
                            feedback_input = ""
                        elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:
                            if feedback_input:
                                feedback_input = feedback_input[:-1]
                        elif 32 <= key <= 126:  # Printable characters
                            feedback_input += chr(key)
                    else:
                        # Handle normal commands
                        if key == ord('q') or key == ord('Q'):
                            break
                        elif key == ord('f') or key == ord('F'):
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                waiting_for_feedback = True
                                feedback_input = ""
                                interface.set_status("Enter feedback (Enter to submit, ESC to cancel)", persistent=True)
                            else:
                                interface.set_status("No hypothesis selected")
                        elif key == ord('n') or key == ord('N'):
                            interface.clear_status_on_action()
                            interface.set_status("Generating new hypothesis...", persistent=True)
                            interface.draw_status_bar()
                            stdscr.refresh()
                            
                            try:
                                new_hypothesis = generate_new_hypothesis(research_goal, all_hypotheses, model_config)
                                if new_hypothesis.get("error"):
                                    interface.set_status("Error generating new hypothesis")
                                else:
                                    hypothesis_counter += 1
                                    version_tracker[hypothesis_counter] = 0
                                    new_hypothesis["hypothesis_number"] = hypothesis_counter
                                    new_hypothesis["version"] = "1.0"
                                    new_hypothesis["type"] = "new_alternative"
                                    new_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                                    all_hypotheses.append(new_hypothesis)
                                    interface.current_hypothesis_idx = hypothesis_counter - 1
                                    interface.set_status("New hypothesis generated!")
                                    
                            except Exception as e:
                                interface.set_status(f"Error: {str(e)[:50]}")
                                
                        elif key == ord('h') or key == ord('H'):
                            interface.clear_status_on_action()
                            interface.show_hallmarks = not interface.show_hallmarks
                            status = "enabled" if interface.show_hallmarks else "disabled"
                            interface.set_status(f"Hallmarks display {status}")
                            
                        elif key == ord('r') or key == ord('R'):
                            interface.clear_status_on_action()
                            interface.show_references = not interface.show_references
                            status = "enabled" if interface.show_references else "disabled"
                            interface.set_status(f"References display {status}")
                            
                        elif key == ord('l') or key == ord('L'):
                            # Load session - prompt for filename
                            interface.set_status("Enter filename to load (ESC to cancel):")
                            interface.draw_status_bar()
                            stdscr.refresh()
                            
                            # Get filename input
                            filename_input = ""
                            loading_mode = True
                            
                            while loading_mode:
                                key_load = stdscr.getch()
                                if key_load == 27:  # ESC
                                    interface.set_status("Load cancelled")
                                    loading_mode = False
                                elif key_load == ord('\n') or key_load == curses.KEY_ENTER or key_load == 10:
                                    if filename_input.strip():
                                        # Try to load the session
                                        interface.set_status("Loading session...")
                                        interface.draw_status_bar()
                                        stdscr.refresh()
                                        
                                        loaded_goal, loaded_hypotheses, loaded_metadata = load_session_from_json(filename_input.strip())
                                        
                                        if loaded_hypotheses:
                                            # Merge loaded hypotheses into current session
                                            for hyp in loaded_hypotheses:
                                                if hyp not in all_hypotheses:  # Avoid duplicates
                                                    # Ensure feedback_history is present
                                                    if "feedback_history" not in hyp:
                                                        hyp["feedback_history"] = []
                                                    all_hypotheses.append(hyp)
                                            
                                            # Update research goal if it was loaded
                                            if loaded_goal and loaded_goal.strip():
                                                research_goal = loaded_goal
                                            
                                            # Rebuild hypothesis counter and version tracker
                                            hypothesis_counter = max([h.get("hypothesis_number", 0) for h in all_hypotheses] + [0])
                                            version_tracker = {}
                                            hypothesis_groups = {}
                                            for hyp in all_hypotheses:
                                                hyp_num = hyp.get("hypothesis_number", 0)
                                                if hyp_num not in hypothesis_groups:
                                                    hypothesis_groups[hyp_num] = []
                                                hypothesis_groups[hyp_num].append(hyp)
                                            
                                            for hyp_num, hyp_versions in hypothesis_groups.items():
                                                max_version = 0
                                                for hyp in hyp_versions:
                                                    version_str = hyp.get("version", "1.0")
                                                    try:
                                                        version_parts = version_str.split('.')
                                                        if len(version_parts) >= 2:
                                                            minor_version = int(version_parts[1])
                                                            max_version = max(max_version, minor_version)
                                                    except:
                                                        pass
                                                version_tracker[hyp_num] = max_version
                                            
                                            # Set current hypothesis to the most recent one
                                            if all_hypotheses:
                                                current_hyp = max(all_hypotheses, key=lambda h: h.get("generation_timestamp", ""))
                                                interface.current_hypothesis_idx = current_hyp.get("hypothesis_number", 1) - 1
                                            
                                            interface.set_status(f"Session loaded successfully! {len(loaded_hypotheses)} hypotheses added.")
                                        else:
                                            interface.set_status("Failed to load session - file not found or invalid format")
                                    else:
                                        interface.set_status("Load cancelled - no filename provided")
                                    loading_mode = False
                                elif key_load == curses.KEY_BACKSPACE or key_load == 127 or key_load == 8:
                                    if filename_input:
                                        filename_input = filename_input[:-1]
                                        interface.draw_status_bar(f"Enter filename: {filename_input}")
                                        stdscr.refresh()
                                elif 32 <= key_load <= 126:  # Printable characters
                                    filename_input += chr(key_load)
                                    interface.draw_status_bar(f"Enter filename: {filename_input}")
                                    stdscr.refresh()
                            
                        elif key == ord('s') or key == ord('S'):
                            # Select hypothesis - prompt for hypothesis number
                            if not all_hypotheses:
                                interface.set_status("No hypotheses available to select")
                            else:
                                # Get available hypothesis numbers
                                hypothesis_groups = {}
                                for hyp in all_hypotheses:
                                    hyp_num = hyp.get("hypothesis_number", 0)
                                    hypothesis_groups[hyp_num] = True
                                available_numbers = sorted(hypothesis_groups.keys())
                                
                                interface.set_status(f"Enter hypothesis number ({min(available_numbers)}-{max(available_numbers)}, ESC to cancel):")
                                interface.draw_status_bar()
                                stdscr.refresh()
                                
                                # Get hypothesis number input
                                number_input = ""
                                selecting_mode = True
                                
                                while selecting_mode:
                                    key_select = stdscr.getch()
                                    if key_select == 27:  # ESC
                                        interface.set_status("Selection cancelled")
                                        selecting_mode = False
                                    elif key_select == ord('\n') or key_select == curses.KEY_ENTER or key_select == 10:
                                        if number_input.strip():
                                            try:
                                                selected_num = int(number_input.strip())
                                                if selected_num in available_numbers:
                                                    # Find the latest version of the selected hypothesis
                                                    hypothesis_groups = {}
                                                    for hyp in all_hypotheses:
                                                        hyp_num = hyp.get("hypothesis_number", 0)
                                                        if hyp_num not in hypothesis_groups:
                                                            hypothesis_groups[hyp_num] = []
                                                        hypothesis_groups[hyp_num].append(hyp)
                                                    
                                                    latest_version = max(hypothesis_groups[selected_num], key=lambda h: h.get("version", "1.0"))
                                                    interface.current_hypothesis_idx = selected_num - 1
                                                    interface.detail_scroll_offset = 0  # Reset scroll
                                                    interface.set_status(f"Selected hypothesis #{selected_num} for review/refinement")
                                                else:
                                                    interface.set_status(f"Invalid hypothesis number. Available: {available_numbers}")
                                            except ValueError:
                                                interface.set_status("Invalid number format")
                                        else:
                                            interface.set_status("Selection cancelled - no number provided")
                                        selecting_mode = False
                                    elif key_select == curses.KEY_BACKSPACE or key_select == 127 or key_select == 8:
                                        if number_input:
                                            number_input = number_input[:-1]
                                            interface.draw_status_bar(f"Enter hypothesis number: {number_input}")
                                            stdscr.refresh()
                                    elif ord('0') <= key_select <= ord('9'):  # Only allow digits
                                        number_input += chr(key_select)
                                        interface.draw_status_bar(f"Enter hypothesis number: {number_input}")
                                        stdscr.refresh()
                                        
                        elif key == ord('v') or key == ord('V'):
                            # View hypothesis titles - show in a popup-like manner
                            if not all_hypotheses:
                                interface.set_status("No hypotheses available to view")
                            else:
                                # Group hypotheses by number
                                hypothesis_groups = {}
                                for hyp in all_hypotheses:
                                    hyp_num = hyp.get("hypothesis_number", 0)
                                    if hyp_num not in hypothesis_groups:
                                        hypothesis_groups[hyp_num] = []
                                    hypothesis_groups[hyp_num].append(hyp)
                                
                                # Create a temporary view mode
                                view_mode = True
                                view_scroll = 0
                                max_display_lines = interface.height - 8  # Leave room for header/footer
                                
                                while view_mode:
                                    # Clear and redraw with titles view
                                    stdscr.clear()
                                    
                                    # Header
                                    title_header = "HYPOTHESIS TITLES IN CURRENT SESSION (Press any key to return)"
                                    stdscr.addstr(1, (interface.width - len(title_header)) // 2, title_header, curses.A_BOLD)
                                    stdscr.addstr(2, 0, "=" * interface.width)
                                    
                                    # List hypotheses
                                    y_pos = 4
                                    line_count = 0
                                    
                                    for hyp_num in sorted(hypothesis_groups.keys()):
                                        if line_count < view_scroll:
                                            line_count += 1
                                            continue
                                        if y_pos >= interface.height - 3:
                                            break
                                            
                                        hyp_versions = hypothesis_groups[hyp_num]
                                        latest_version = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
                                        
                                        version = latest_version.get("version", "1.0")
                                        title = latest_version.get("title", "Untitled")
                                        hyp_type = latest_version.get("type", "unknown")
                                        
                                        type_indicator = ""
                                        if hyp_type == "improvement":
                                            type_indicator = " (improved)"
                                        elif hyp_type == "new_alternative":
                                            type_indicator = " (alternative)"
                                        
                                        line_text = f"{hyp_num}. [v{version}] {title}{type_indicator}"
                                        
                                        # Highlight current selection
                                        attr = curses.A_REVERSE if hyp_num - 1 == interface.current_hypothesis_idx else 0
                                        
                                        if y_pos < interface.height - 1:
                                            stdscr.addstr(y_pos, 2, line_text[:interface.width-4], attr)
                                        y_pos += 1
                                        line_count += 1
                                    
                                    # Footer
                                    if y_pos < interface.height - 1:
                                        total_hypotheses = len(hypothesis_groups)
                                        footer = f"Showing {min(line_count, max_display_lines)} of {total_hypotheses} hypotheses"
                                        stdscr.addstr(interface.height - 2, 2, footer)
                                    
                                    stdscr.refresh()
                                    
                                    # Wait for any key
                                    key_view = stdscr.getch()
                                    if key_view != -1:  # Any key pressed
                                        view_mode = False
                                
                                interface.set_status("Returned from hypothesis titles view")
                            
                        elif key == curses.KEY_UP:
                            interface.clear_status_on_action()
                            if interface.current_hypothesis_idx > 0:
                                interface.current_hypothesis_idx -= 1
                            interface.detail_scroll_offset = 0  # Reset detail scroll
                            
                        elif key == curses.KEY_DOWN:
                            interface.clear_status_on_action()
                            # Count unique hypotheses
                            hypothesis_groups = {}
                            for hyp in all_hypotheses:
                                hyp_num = hyp.get("hypothesis_number", 0)
                                hypothesis_groups[hyp_num] = True
                            max_idx = len(hypothesis_groups) - 1
                            
                            if interface.current_hypothesis_idx < max_idx:
                                interface.current_hypothesis_idx += 1
                            interface.detail_scroll_offset = 0  # Reset detail scroll
                            
                        elif key == curses.KEY_PPAGE:  # Page Up - scroll detail up
                            interface.scroll_detail(-5)
                            
                        elif key == curses.KEY_NPAGE:  # Page Down - scroll detail down
                            interface.scroll_detail(5)
                            
                        # Mac-friendly scrolling alternatives
                        elif key == ord('j') or key == ord('J'):  # j = scroll down (vim-style)
                            interface.scroll_detail(1)
                            
                        elif key == ord('k') or key == ord('K'):  # k = scroll up (vim-style)
                            interface.scroll_detail(-1)
                            
                        elif key == ord('d') or key == ord('D'):  # d = scroll down faster
                            interface.scroll_detail(5)
                            
                        elif key == ord('u') or key == ord('U'):  # u = scroll up faster
                            interface.scroll_detail(-5)
                            
                        elif key == ord('p') or key == ord('P'):  # p = print to PDF
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                if PDF_AVAILABLE:
                                    interface.set_status("Generating PDF...", persistent=True)
                                    interface.draw_status_bar()
                                    stdscr.refresh()
                                    
                                    try:
                                        pdf_path = generate_hypothesis_pdf(current_hypothesis, research_goal)
                                        if pdf_path:
                                            interface.set_status(f"PDF saved: {pdf_path}")
                                        else:
                                            interface.set_status("Error: Failed to generate PDF")
                                    except Exception as e:
                                        interface.set_status(f"Error: {str(e)[:50]}")
                                else:
                                    interface.set_status("Error: PDF generation requires reportlab (pip install reportlab)")
                            else:
                                interface.set_status("No hypothesis selected for PDF generation")
                            
            except curses.error:
                pass  # Ignore curses errors from input
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            interface.set_status(f"Error: {str(e)[:50]}")
    
    return all_hypotheses

# ---------------------------------------------------------------------
# Test function for feedback tracking
# ---------------------------------------------------------------------

def test_feedback_tracking():
    """
    Test function to verify feedback tracking and PDF generation.
    Creates a sample hypothesis with feedback history and generates a PDF.
    """
    if not PDF_AVAILABLE:
        print("PDF generation not available. Install reportlab to test PDF functionality.")
        return
    
    # Create a test hypothesis with feedback history
    test_hypothesis = {
        "title": "Test Hypothesis for Feedback Tracking",
        "description": "This is a test hypothesis created to verify that feedback tracking and PDF generation work correctly. It demonstrates how user feedback is collected, stored, and displayed in the generated PDF document.",
        "experimental_validation": "Test the PDF generation functionality by running this test function and examining the generated PDF document for the presence of feedback history section.",
        "hallmarks": {
            "testability": "This hypothesis can be tested by generating a PDF and checking if it contains the feedback history section.",
            "specificity": "The hypothesis is specific about testing feedback tracking in PDF generation.",
            "grounded_knowledge": "Based on software testing principles and user feedback collection.",
            "predictive_power": "Predicts that feedback history will be visible in generated PDFs.",
            "parsimony": "Simple and direct approach to testing feedback functionality."
        },
        "references": [
            {
                "citation": "Test, A. (2024). Software Testing Best Practices. Journal of Testing, 1(1), 1-10.",
                "annotation": "Provides foundation for testing user interface functionality."
            }
        ],
        "feedback_history": [
            {
                "feedback": "Please make the hypothesis more specific and testable.",
                "timestamp": "2024-01-15T10:30:00",
                "version_before": "1.0",
                "version_after": "1.1"
            },
            {
                "feedback": "Add more details about the experimental methodology.",
                "timestamp": "2024-01-15T11:45:00",
                "version_before": "1.1",
                "version_after": "1.2"
            },
            {
                "feedback": "Include additional references to support the claims.",
                "timestamp": "2024-01-15T14:20:00",
                "version_before": "1.2",
                "version_after": "1.3"
            }
        ],
        "version": "1.3",
        "type": "improvement",
        "hypothesis_number": 1,
        "generation_timestamp": "2024-01-15T14:20:00",
        "improvements_made": "Enhanced specificity, added experimental details, and included additional references based on user feedback."
    }
    
    research_goal = "Test the feedback tracking and PDF generation functionality in Wisteria v5.0"
    
    print("\nTesting feedback tracking and PDF generation...")
    pdf_path = generate_hypothesis_pdf(test_hypothesis, research_goal, "test_feedback_tracking.pdf")
    
    if pdf_path:
        print(f"✓ Test PDF generated successfully: {pdf_path}")
        print("\nThe PDF should contain:")
        print("- Hypothesis details")
        print("- Feedback History section with 3 feedback entries")
        print("- Each feedback entry showing timestamp and version changes")
        print("- Improvements Made section")
        print("\nPlease check the generated PDF to verify the feedback tracking functionality.")
    else:
        print("✗ Failed to generate test PDF")

# ---------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------

def main():
    args = parse_arguments()
    
    # Handle test feedback argument
    if args.test_feedback:
        test_feedback_tracking()
        return
    
    # Require model for normal operation
    if not args.model:
        print("Error: --model argument is required for normal operation")
        sys.exit(1)
    
    # Load model config
    model_config = load_model_config(args.model)
    
    print(f"Wisteria Research Hypothesis Generator v5.0 - Curses Multi-Pane Interface")
    print(f"Using model: {args.model} ({model_config['model_name']})")
    
    # Check PDF availability
    if not PDF_AVAILABLE:
        print("Note: PDF generation not available. Install reportlab for PDF export: pip install reportlab")
    
    initial_hypotheses = None
    
    # Handle resume option
    if args.resume:
        research_goal, initial_hypotheses, loaded_metadata = load_session_from_json(args.resume)
        if not initial_hypotheses:
            print("Failed to load session. Exiting.")
            sys.exit(1)
        goal_source = f"resumed from: {args.resume}"
    else:
        # Get research goal from file or command line argument
        if args.goal:
            research_goal = args.goal.strip()
            goal_source = "command line argument"
        elif args.research_goal_file:
            try:
                with open(args.research_goal_file, "r", encoding="utf-8") as f:
                    research_goal = f.read().strip()
                goal_source = f"file: {args.research_goal_file}"
            except Exception as e:
                print(f"Error reading research goal file: {e}")
                sys.exit(1)
        else:
            print("Error: Either provide a research goal file, use --goal, or use --resume")
            sys.exit(1)
    
    if not research_goal:
        print("Error: Research goal is empty")
        sys.exit(1)
    
    print(f"\nResearch Goal:")
    print(f"{research_goal}")
    
    # Show generation message if not resuming
    if not initial_hypotheses:
        if args.num_hypotheses == 1:
            print(f"\nGenerating initial hypothesis using {args.model}...")
            print("This may take a moment depending on the model and complexity...")
        else:
            print(f"\nGenerating {args.num_hypotheses} initial hypotheses using {args.model}...")
            print("Each hypothesis will be generated individually to show progress...")
            print("This may take several minutes depending on the model and complexity...")
    
    # Run curses session
    start_time = time.time()
    try:
        all_hypotheses = curses.wrapper(curses_hypothesis_session, research_goal, model_config, initial_hypotheses, args.num_hypotheses)
    except KeyboardInterrupt:
        print("\n\nSession interrupted by user. Saving current hypotheses...")
        all_hypotheses = []
    except Exception as e:
        print(f"Failed to run curses session: {e}")
        print(f"This might be due to terminal size or encoding issues.")
        print(f"Try running in a larger terminal window or check your terminal settings.")
        print(f"Error details: {type(e).__name__}: {str(e)}")
        sys.exit(1)
    
    session_time = time.time() - start_time
    
    if not all_hypotheses:
        print("No hypotheses were generated. Exiting.")
        sys.exit(0)
    
    # Prepare output file
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"hypotheses_interactive_{args.model}_{timestamp}.json"
    else:
        output_file = args.output
    
    # Count unique hypotheses (not counting improvements of the same hypothesis)
    unique_hypothesis_numbers = set()
    for hyp in all_hypotheses:
        unique_hypothesis_numbers.add(hyp.get("hypothesis_number", 0))
    
    # Prepare metadata
    metadata = {
        "session_type": "interactive",
        "research_goal_source": goal_source,
        "research_goal": research_goal,
        "model": args.model,
        "model_name": model_config['model_name'],
        "num_unique_hypotheses": len(unique_hypothesis_numbers),
        "total_hypothesis_versions": len(all_hypotheses),
        "timestamp": datetime.now().isoformat(),
        "session_time_seconds": session_time,
        "hypothesis_types": {
            "original": len([h for h in all_hypotheses if h.get("type") == "original"]),
            "improvements": len([h for h in all_hypotheses if h.get("type") == "improvement"]),
            "new_alternatives": len([h for h in all_hypotheses if h.get("type") == "new_alternative"])
        }
    }
    
    # Save to JSON file
    save_hypotheses_to_json(all_hypotheses, output_file, metadata)
    
    print(f"\nSession completed in {session_time:.2f} seconds")
    print(f"Generated {len(unique_hypothesis_numbers)} unique hypotheses with {len(all_hypotheses)} total versions")
    print(f"All hypotheses saved to: {output_file}")

if __name__ == "__main__":
    main()