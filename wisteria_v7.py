#!/usr/bin/env python3

"""
Wisteria Research Hypothesis Generator v6.0 - Curses Multi-Pane Interface

Usage:
    python curses_wisteria_v6.py <research_goal_file.txt> --model <model_shortname> [--num-hypotheses <N>] [--output <output_file.json>]
    python curses_wisteria_v6.py --goal "<research_goal_text>" --model <model_shortname> [--num-hypotheses <N>] [--output <output_file.json>]
    python curses_wisteria_v6.py --resume <session_file.json> --model <model_shortname> [--output <output_file.json>]

Where:
    - research_goal_file.txt: A text file containing the research goal/question
    - --goal: Specify the research goal directly as a command line argument
    - --resume: Resume from a previous session JSON file
    - --model: The shortname of the model to use from model_servers.yaml
    - --num-hypotheses: Number of initial hypotheses to generate (default: 1)
    - --output: Output JSON file for the hypotheses (default: hypotheses_<timestamp>.json)

Examples:
    python curses_wisteria_v6.py research_goal.txt --model gpt41
    python curses_wisteria_v6.py --goal "How can we improve renewable energy storage efficiency?" --model scout --num-hypotheses 3
    python curses_wisteria_v6.py --resume hypotheses_interactive_gpt41_20250531_165238.json --model gpt41
    python curses_wisteria_v6.py --goal "What causes neurodegenerative diseases?" --model gpt41 --num-hypotheses 5 --output my_hypotheses.json

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
   - x - Save current session to a JSON file with custom filename
   - t - Add/edit personal notes for the current hypothesis
   - v - View the titles of hypotheses in current session
   - s - Select a hypothesis to continue to refine
   - h - Toggle hallmarks analysis display
   - r - Toggle references display
   - a - Fetch abstracts and papers from Semantic Scholar for current hypothesis references
   - u - Update hypothesis with information from downloaded abstracts
   - b - Browse and view downloaded abstracts
   - c - Score hypothesis hallmarks (1-5 scale) using AI evaluation
   - w - Configure hypothesis generation strategies for enhanced creativity
   - p - Print current hypothesis to PDF document
   - q - Quit and save all hypotheses
   - g/Home - Return to main display and reset view
   - ←/→ - Switch focus between hypothesis list and details pane
   - ↑/↓ - Navigate between hypotheses (when list focused) 
   - j/k - Scroll focused pane by 1 line (vim-style)
   - d/u - Scroll focused pane by 5 lines (fast scroll)
   - Page Up/Down - Scroll focused pane by 5 lines
5) Ensures each new hypothesis is different from previous ones
6) Outputs all hypotheses and refinements to JSON file

HYPOTHESIS GENERATION STRATEGIES:
The 'w' command opens a strategy selection interface with 10 advanced strategies:
1. Boundary-Pushing: Challenge assumptions and push boundaries
2. Human Curiosity: Emphasize surprising and intriguing outcomes
3. Real-World Impact: Focus on practical implications and societal benefits
4. Analogical Thinking: Use creative analogies and metaphors
5. Interdisciplinary: Leverage multiple disciplines
6. What-If Scenarios: Explore provocative thought experiments
7. Provocative Reactions: Provoke curiosity and debate
8. Narrative Context: Frame within compelling stories
9. Risk-Taking: Encourage bold, high-risk ideas
0. Visionary Thinking: Future-oriented and forward-looking

Strategies can be combined and applied to both hypothesis generation (n) and improvement (f) commands.
Current strategy status is shown in the status bar.
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
import urllib.request
import urllib.parse
import urllib.error
import requests
from pathlib import Path
import queue
import uuid
from enum import Enum
from dataclasses import dataclass
from typing import Callable, Any, Optional, Dict

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
# Asynchronous Task Queue System
# ---------------------------------------------------------------------

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Task:
    id: str
    name: str
    priority: TaskPriority
    func: Callable
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[Exception] = None
    progress: float = 0.0
    created_at: float = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class TaskQueue:
    def __init__(self, max_workers=3):
        self.task_queue = queue.PriorityQueue()
        self.tasks: Dict[str, Task] = {}
        self.max_workers = max_workers
        self.workers = []
        self.running = False
        self.lock = threading.Lock()
        self.callbacks = {}  # Task completion callbacks
        
    def start(self):
        """Start the worker threads"""
        if self.running:
            return
        
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker, name=f"TaskWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
    
    def stop(self):
        """Stop all workers"""
        self.running = False
        for _ in range(self.max_workers):
            self.task_queue.put((0, None))  # Poison pill
    
    def _worker(self):
        """Worker thread that processes tasks"""
        while self.running:
            try:
                priority, task_id = self.task_queue.get(timeout=1)
                if task_id is None:  # Poison pill
                    break
                    
                with self.lock:
                    if task_id not in self.tasks:
                        continue
                    task = self.tasks[task_id]
                    
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # Execute task
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                
                try:
                    result = task.func(*task.args, **task.kwargs)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.progress = 1.0
                except Exception as e:
                    task.error = e
                    task.status = TaskStatus.FAILED
                finally:
                    task.completed_at = time.time()
                    
                # Run callback if exists
                if task_id in self.callbacks:
                    try:
                        self.callbacks[task_id](task)
                    except Exception:
                        pass  # Don't let callback errors break the worker
                        
            except queue.Empty:
                continue
            except Exception:
                continue
    
    def submit_task(self, name: str, func: Callable, *args, 
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   callback: Optional[Callable] = None, **kwargs) -> str:
        """Submit a task to the queue"""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            name=name,
            priority=priority,
            func=func,
            args=args,
            kwargs=kwargs
        )
        
        with self.lock:
            self.tasks[task_id] = task
            if callback:
                self.callbacks[task_id] = callback
        
        # Higher priority = lower number for queue ordering
        queue_priority = 5 - priority.value
        self.task_queue.put((queue_priority, task_id))
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Task]:
        """Get current status of a task"""
        with self.lock:
            return self.tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    return True
        return False
    
    def get_all_tasks(self) -> Dict[str, Task]:
        """Get all tasks"""
        with self.lock:
            return self.tasks.copy()
    
    def get_running_tasks(self) -> Dict[str, Task]:
        """Get only running tasks"""
        with self.lock:
            return {tid: task for tid, task in self.tasks.items() 
                   if task.status == TaskStatus.RUNNING}
    
    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """Clean up old completed tasks"""
        current_time = time.time()
        with self.lock:
            to_remove = []
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.completed_at and current_time - task.completed_at > max_age_seconds):
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.tasks[task_id]
                if task_id in self.callbacks:
                    del self.callbacks[task_id]

# ---------------------------------------------------------------------
# Hypothesis Generation Strategies
# ---------------------------------------------------------------------

class HypothesisStrategy:
    """Individual hypothesis generation strategy"""
    def __init__(self, name, key, description, prompt_addition):
        self.name = name
        self.key = key
        self.description = description
        self.prompt_addition = prompt_addition

# Define all available strategies
HYPOTHESIS_STRATEGIES = {
    "boundary_pushing": HypothesisStrategy(
        name="Boundary-Pushing",
        key="1",
        description="Challenge assumptions and push boundaries",
        prompt_addition="Formulate hypotheses that explicitly challenge conventional understanding or integrate concepts from distinct and unexpected scientific domains."
    ),
    "human_curiosity": HypothesisStrategy(
        name="Human Curiosity",
        key="2", 
        description="Emphasize surprising and intriguing outcomes",
        prompt_addition="Suggest hypotheses that, if confirmed, would be surprising, intriguing, or counterintuitive to scientists in this field, sparking further curiosity and exploration."
    ),
    "real_world_impact": HypothesisStrategy(
        name="Real-World Impact",
        key="3",
        description="Focus on practical implications and societal benefits",
        prompt_addition="Each hypothesis should clearly articulate its potential impact on society, medicine, technology, or fundamental understanding, highlighting why confirmation would be significant."
    ),
    "analogical_thinking": HypothesisStrategy(
        name="Analogical Thinking",
        key="4",
        description="Use creative analogies and metaphors",
        prompt_addition="Use creative analogies, metaphors, or comparisons from everyday life or unrelated fields to generate novel and intriguing scientific hypotheses."
    ),
    "interdisciplinary": HypothesisStrategy(
        name="Interdisciplinary",
        key="5",
        description="Leverage multiple disciplines",
        prompt_addition="Generate hypotheses that explicitly draw insights from multiple disciplines, combining perspectives in ways rarely or never previously explored."
    ),
    "what_if_scenarios": HypothesisStrategy(
        name="What-If Scenarios",
        key="6",
        description="Explore provocative thought experiments",
        prompt_addition="Formulate hypotheses around imaginative 'what if?' scenarios or thought experiments that expand conventional scientific thinking."
    ),
    "provocative_reactions": HypothesisStrategy(
        name="Provocative Reactions",
        key="7",
        description="Provoke curiosity and debate",
        prompt_addition="Hypotheses should provoke reactions such as curiosity, excitement, debate, or even mild controversy among scientists upon reading them."
    ),
    "narrative_context": HypothesisStrategy(
        name="Narrative Context",
        key="8",
        description="Frame within compelling stories",
        prompt_addition="Frame each hypothesis within a brief narrative or scenario that illustrates why exploring it would be scientifically exciting or culturally significant."
    ),
    "risk_taking": HypothesisStrategy(
        name="Risk-Taking",
        key="9",
        description="Encourage bold, high-risk ideas",
        prompt_addition="Prioritize bold, risky hypotheses—those with lower probability of confirmation but extremely high potential impact if validated."
    ),
    "visionary_thinking": HypothesisStrategy(
        name="Visionary Thinking",
        key="0",
        description="Future-oriented and forward-looking",
        prompt_addition="Generate visionary hypotheses that anticipate future discoveries or technological breakthroughs, proposing directions science may move in 5-10 years ahead of current thinking."
    )
}

class HypothesisStrategyManager:
    """Manages active hypothesis generation strategies"""
    def __init__(self):
        self.active_strategies = set()
        self.default_mode = True  # Start with default mode
    
    def toggle_strategy(self, strategy_key):
        """Toggle a strategy on/off"""
        strategy_name = None
        for name, strategy in HYPOTHESIS_STRATEGIES.items():
            if strategy.key == strategy_key:
                strategy_name = name
                break
        
        if strategy_name:
            if strategy_name in self.active_strategies:
                self.active_strategies.remove(strategy_name)
            else:
                self.active_strategies.add(strategy_name)
                self.default_mode = False
            return True
        return False
    
    def set_default_mode(self, enabled=True):
        """Enable/disable default mode"""
        self.default_mode = enabled
        if enabled:
            self.active_strategies.clear()
    
    def get_active_strategies(self):
        """Get list of active strategies"""
        if self.default_mode:
            return []
        return [HYPOTHESIS_STRATEGIES[name] for name in self.active_strategies]
    
    def get_strategy_prompt_additions(self):
        """Get combined prompt additions for active strategies"""
        if self.default_mode:
            return ""
        
        if not self.active_strategies:
            return ""
        
        additions = []
        for strategy_name in self.active_strategies:
            strategy = HYPOTHESIS_STRATEGIES[strategy_name]
            additions.append(f"• {strategy.prompt_addition}")
        
        return "\n\nADDITIONAL GENERATION STRATEGIES:\n" + "\n".join(additions)
    
    def get_status_text(self):
        """Get status text for display"""
        if self.default_mode:
            return "Default"
        elif not self.active_strategies:
            return "None"
        else:
            active_names = [HYPOTHESIS_STRATEGIES[name].name for name in self.active_strategies]
            return f"{len(active_names)} active: " + ", ".join(active_names[:2]) + ("..." if len(active_names) > 2 else "")

# ---------------------------------------------------------------------
# Helper functions (from argonium_score_parallel_v9.py)
# ---------------------------------------------------------------------

def clean_json_string(text):
    """Clean control characters from JSON string to prevent parsing errors."""
    if not text:
        return text
    # Remove ASCII control characters (0x00-0x1F and 0x7F) except for whitespace
    # Keep: \t (0x09), \n (0x0A), \r (0x0D)
    try:
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        return text
    except Exception:
        # Return original text if regex fails
        return text

# ---------------------------------------------------------------------
# Paper and Abstract Fetching Functions
# ---------------------------------------------------------------------

def create_papers_directory(session_name):
    """Create directory structure for storing papers and abstracts for a session"""
    papers_dir = Path("papers") / session_name
    papers_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (papers_dir / "abstracts").mkdir(exist_ok=True)
    (papers_dir / "papers").mkdir(exist_ok=True)
    
    return papers_dir

def extract_paper_info_from_citation(citation):
    """Extract author, title, and year from citation string"""
    info = {"author": "", "title": "", "year": "", "journal": ""}
    
    try:
        # Try to extract year (4 digits in parentheses)
        year_match = re.search(r'\((\d{4})\)', citation)
        if year_match:
            info["year"] = year_match.group(1)
        
        # Try to extract title (text between periods, often after year)
        # Look for pattern: Author. (Year). Title. Journal
        parts = citation.split('.')
        if len(parts) >= 3:
            # First part is usually author
            info["author"] = parts[0].strip()
            
            # Find title (usually the part after year)
            for i, part in enumerate(parts):
                if info["year"] in part and i + 1 < len(parts):
                    info["title"] = parts[i + 1].strip()
                    if i + 2 < len(parts):
                        info["journal"] = parts[i + 2].strip()
                    break
            
            # If we didn't find title after year, try second part
            if not info["title"] and len(parts) > 1:
                info["title"] = parts[1].strip()
                if len(parts) > 2:
                    info["journal"] = parts[2].strip()
    
    except Exception as e:
        print(f"Error extracting paper info: {e}")
    
    return info

def search_semantic_scholar(query, max_results=5, api_key=None):
    """Search Semantic Scholar for papers matching the query"""
    try:
        # Construct Semantic Scholar API URL
        base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            'query': query,
            'limit': max_results,
            'fields': 'title,authors,year,externalIds,url,venue,openAccessPdf,abstract,paperId'
        }
        
        headers = {}
        if api_key:
            headers['x-api-key'] = api_key
        
        # Make request
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            papers = []
            
            for paper_data in data.get('data', []):
                paper = {}
                
                # Title
                paper['title'] = paper_data.get('title', 'Unknown Title')
                
                # Authors
                authors = []
                for author in paper_data.get('authors', []):
                    if author.get('name'):
                        authors.append(author['name'])
                paper['authors'] = authors
                
                # Abstract
                paper['abstract'] = paper_data.get('abstract', 'No abstract available') or 'No abstract available'
                
                # Published year
                paper['published'] = str(paper_data.get('year', 'Unknown'))
                
                # Paper ID and PDF link
                paper['paper_id'] = paper_data.get('paperId', '')
                paper['venue'] = paper_data.get('venue', 'Unknown venue')
                
                # PDF URL from openAccessPdf
                open_access_pdf = paper_data.get('openAccessPdf')
                if open_access_pdf and open_access_pdf.get('url'):
                    paper['pdf_url'] = open_access_pdf['url']
                else:
                    paper['pdf_url'] = None
                
                # External IDs (for DOI, arXiv, etc.)
                external_ids = paper_data.get('externalIds', {})
                paper['doi'] = external_ids.get('DOI', '')
                paper['arxiv_id'] = external_ids.get('ArXiv', '')
                
                papers.append(paper)
            
            return papers
        else:
            print(f"Error from Semantic Scholar API: {response.status_code} - {response.text}")
            return []
    
    except Exception as e:
        print(f"Error searching Semantic Scholar: {e}")
        return []

def save_abstract_to_file(paper, papers_dir, citation_index):
    """Save paper abstract to a text file"""
    try:
        paper_id = paper.get('paper_id', 'unknown')
        filename = f"abstract_{citation_index:02d}_{paper_id}.txt"
        filepath = papers_dir / "abstracts" / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Title: {paper.get('title', 'Unknown')}\n")
            f.write(f"Authors: {', '.join(paper.get('authors', []))}\n")
            f.write(f"Published: {paper.get('published', 'Unknown')}\n")
            f.write(f"Venue: {paper.get('venue', 'Unknown venue')}\n")
            f.write(f"Semantic Scholar ID: {paper.get('paper_id', 'N/A')}\n")
            f.write(f"DOI: {paper.get('doi', 'N/A')}\n")
            f.write(f"arXiv ID: {paper.get('arxiv_id', 'N/A')}\n")
            f.write(f"PDF URL: {paper.get('pdf_url', 'N/A')}\n")
            f.write("\nAbstract:\n")
            f.write(paper.get('abstract', 'No abstract available'))
        
        return str(filepath)
    
    except Exception as e:
        print(f"Error saving abstract: {e}")
        return None

def download_paper_pdf(paper, papers_dir, citation_index):
    """Download paper PDF if available"""
    try:
        pdf_url = paper.get('pdf_url')
        if not pdf_url:
            return None
        
        paper_id = paper.get('paper_id', 'unknown')
        filename = f"paper_{citation_index:02d}_{paper_id}.pdf"
        filepath = papers_dir / "papers" / filename
        
        # Download PDF using requests for better error handling
        response = requests.get(pdf_url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return str(filepath)
    
    except Exception as e:
        print(f"Error downloading PDF: {e}")
        return None

def find_abstracts_for_hypothesis(hypothesis):
    """Find and read abstracts for a hypothesis from papers directory"""
    abstracts = []
    
    try:
        # Look for papers directories that might contain abstracts for this hypothesis
        papers_base_dir = Path("papers")
        if not papers_base_dir.exists():
            return abstracts
        
        # Find the most recent papers directory (by timestamp)
        papers_dirs = [d for d in papers_base_dir.iterdir() if d.is_dir() and d.name.startswith("papers_")]
        if not papers_dirs:
            return abstracts
        
        # Sort by timestamp in directory name and get the most recent
        papers_dirs.sort(key=lambda x: x.name, reverse=True)
        latest_papers_dir = papers_dirs[0]
        
        abstracts_dir = latest_papers_dir / "abstracts"
        if not abstracts_dir.exists():
            return abstracts
        
        # Read all abstract files
        for abstract_file in abstracts_dir.glob("abstract_*.txt"):
            try:
                with open(abstract_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    abstracts.append({
                        "filename": abstract_file.name,
                        "content": content
                    })
            except Exception as e:
                print(f"Error reading abstract file {abstract_file}: {e}")
        
        return abstracts
    
    except Exception as e:
        print(f"Error finding abstracts: {e}")
        return abstracts

def find_all_available_abstracts():
    """Find all available abstracts from all papers directories"""
    all_abstracts = []
    
    try:
        papers_base_dir = Path("papers")
        if not papers_base_dir.exists():
            return all_abstracts
        
        # Find all papers directories
        papers_dirs = [d for d in papers_base_dir.iterdir() if d.is_dir() and d.name.startswith("papers_")]
        if not papers_dirs:
            return all_abstracts
        
        # Sort by timestamp in directory name (most recent first)
        papers_dirs.sort(key=lambda x: x.name, reverse=True)
        
        for papers_dir in papers_dirs:
            abstracts_dir = papers_dir / "abstracts"
            if abstracts_dir.exists():
                session_name = papers_dir.name
                
                # Read all abstract files from this session
                for abstract_file in abstracts_dir.glob("abstract_*.txt"):
                    try:
                        with open(abstract_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        # Parse title from content
                        title = "Unknown Title"
                        lines = content.split('\n')
                        for line in lines:
                            if line.startswith("1|Title:"):
                                title = line.replace("1|Title:", "").strip()
                                break
                            elif line.startswith("Title:"):
                                title = line.replace("Title:", "").strip()
                                break
                        
                        all_abstracts.append({
                            "filename": abstract_file.name,
                            "title": title,
                            "content": content,
                            "session": session_name,
                            "full_path": str(abstract_file)
                        })
                    except Exception as e:
                        print(f"Error reading abstract file {abstract_file}: {e}")
        
        return all_abstracts
    
    except Exception as e:
        print(f"Error finding abstracts: {e}")
        return all_abstracts

def browse_abstracts_interface(stdscr, interface):
    """Browse abstracts using a two-panel interface"""
    # Find all available abstracts
    all_abstracts = find_all_available_abstracts()
    
    if not all_abstracts:
        interface.set_status("No abstracts found. Use 'a' command to fetch papers first.")
        return
    
    # Abstract browser state
    current_abstract_idx = 0
    abstract_scroll_offset = 0
    list_scroll_offset = 0
    
    # Save original interface state
    original_focus = interface.focus_pane
    original_show_hallmarks = interface.show_hallmarks
    original_show_references = interface.show_references
    
    # Set browse mode
    browse_mode = True
    
    while browse_mode:
        try:
            # Clear and redraw interface for abstract browsing
            stdscr.clear()
            
            # Draw header
            header_text = f" ABSTRACT BROWSER - {len(all_abstracts)} abstracts available "
            if len(header_text) > interface.width:
                header_text = f" ABSTRACT BROWSER - {len(all_abstracts)} abstracts "
            
            stdscr.addstr(0, 0, header_text, curses.A_BOLD | curses.A_REVERSE)
            if len(header_text) < interface.width:
                stdscr.addstr(0, len(header_text), " " * (interface.width - len(header_text)), curses.A_REVERSE)
            
            # Draw separator line
            stdscr.addstr(1, 0, "─" * interface.width)
            
            # Calculate panel dimensions (similar to main interface)
            content_height = interface.height - 4  # Leave room for header and commands
            list_width = int(interface.width * 0.4)  # 40% for abstract list
            detail_width = interface.width - list_width - 1  # Rest for abstract content
            
            # Draw abstract list (left panel)
            list_y_start = 2
            list_y_end = list_y_start + content_height
            
            # List header
            list_header = " Abstract List "
            stdscr.addstr(list_y_start, 0, list_header, curses.A_BOLD)
            if len(list_header) < list_width:
                stdscr.addstr(list_y_start, len(list_header), "─" * (list_width - len(list_header)))
            
            # Draw abstract list items
            for i, abstract in enumerate(all_abstracts):
                line_y = list_y_start + 2 + i - list_scroll_offset
                
                if line_y < list_y_start + 2:
                    continue
                if line_y >= list_y_end - 1:
                    break
                
                # Prepare display text
                title = abstract["title"]
                session_short = abstract["session"].replace("papers_", "")[:15]
                
                # Truncate title to fit
                max_title_len = list_width - len(session_short) - 8
                if len(title) > max_title_len:
                    title = title[:max_title_len-3] + "..."
                
                display_text = f"{i+1:2d}. {title} [{session_short}]"
                
                # Highlight current selection
                attr = curses.A_REVERSE if i == current_abstract_idx else 0
                
                interface.safe_addstr(stdscr, line_y, 2, display_text, attr)
            
            # Draw vertical separator
            for y in range(list_y_start, list_y_end):
                interface.safe_addstr(stdscr, y, list_width, "│")
            
            # Draw abstract content (right panel)
            detail_x_start = list_width + 1
            current_abstract = all_abstracts[current_abstract_idx] if all_abstracts else None
            
            if current_abstract:
                # Content header
                content_header = f" Abstract {current_abstract_idx + 1} of {len(all_abstracts)} "
                try:
                    stdscr.addstr(list_y_start, detail_x_start, content_header, curses.A_BOLD)
                    if len(content_header) < detail_width:
                        stdscr.addstr(list_y_start, detail_x_start + len(content_header), 
                                    "─" * (detail_width - len(content_header)))
                except curses.error:
                    pass
                
                # Display abstract content with scrolling
                content_lines = current_abstract["content"].split('\n')
                content_y_start = list_y_start + 2
                
                for i, line in enumerate(content_lines):
                    display_y = content_y_start + i - abstract_scroll_offset
                    
                    if display_y < content_y_start:
                        continue
                    if display_y >= list_y_end - 1:
                        break
                    
                    # Wrap long lines
                    wrapped_lines = textwrap.wrap(line, detail_width - 2) if line.strip() else [""]
                    
                    for j, wrapped_line in enumerate(wrapped_lines):
                        wrapped_y = display_y + j
                        if wrapped_y >= list_y_end - 1:
                            break
                        
                        try:
                            interface.safe_addstr(stdscr, wrapped_y, detail_x_start + 1, wrapped_line)
                        except curses.error:
                            pass
            
            # Draw command bar at bottom
            cmd_y = interface.height - 2
            commands = " ↑↓=Navigate j/k=Scroll abstract d/u=Fast scroll ESC/q=Exit "
            try:
                interface.safe_addstr(stdscr, cmd_y, 0, commands, curses.A_REVERSE)
                if len(commands) < interface.width:
                    stdscr.addstr(cmd_y, len(commands), " " * (interface.width - len(commands)), curses.A_REVERSE)
            except curses.error:
                pass
            
            # Status line
            if current_abstract:
                status_text = f" File: {current_abstract['filename']} | Session: {current_abstract['session']} "
                try:
                    interface.safe_addstr(stdscr, cmd_y + 1, 0, status_text)
                except curses.error:
                    pass
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27 or key == ord('q') or key == ord('Q'):  # ESC or Q to exit
                browse_mode = False
            elif key == curses.KEY_HOME or key == ord('g') or key == ord('G'):  # Home key or G to return to main display
                browse_mode = False
                
            elif key == curses.KEY_UP:
                if current_abstract_idx > 0:
                    current_abstract_idx -= 1
                    abstract_scroll_offset = 0  # Reset content scroll when changing abstract
                    
                    # Auto-scroll list if needed
                    if current_abstract_idx < list_scroll_offset:
                        list_scroll_offset = current_abstract_idx
                        
            elif key == curses.KEY_DOWN:
                if current_abstract_idx < len(all_abstracts) - 1:
                    current_abstract_idx += 1
                    abstract_scroll_offset = 0  # Reset content scroll when changing abstract
                    
                    # Auto-scroll list if needed
                    visible_lines = content_height - 3  # Account for headers
                    if current_abstract_idx >= list_scroll_offset + visible_lines:
                        list_scroll_offset = current_abstract_idx - visible_lines + 1
                        
            elif key == ord('j') or key == ord('J'):  # Scroll abstract content down
                abstract_scroll_offset += 1
                
            elif key == ord('k') or key == ord('K'):  # Scroll abstract content up
                abstract_scroll_offset = max(0, abstract_scroll_offset - 1)
                
            elif key == ord('d') or key == ord('D'):  # Fast scroll abstract content down
                abstract_scroll_offset += 5
                
            elif key == ord('u') or key == ord('U'):  # Fast scroll abstract content up
                abstract_scroll_offset = max(0, abstract_scroll_offset - 5)
                
            elif key == curses.KEY_PPAGE:  # Page Up - scroll abstract up
                abstract_scroll_offset = max(0, abstract_scroll_offset - 10)
                
            elif key == curses.KEY_NPAGE:  # Page Down - scroll abstract down
                abstract_scroll_offset += 10
                
        except curses.error:
            pass  # Ignore display errors
        except KeyboardInterrupt:
            browse_mode = False
    
    # Restore original interface state
    interface.focus_pane = original_focus
    interface.show_hallmarks = original_show_hallmarks
    interface.show_references = original_show_references
    
    # Clear screen and force full redraw
    stdscr.clear()
    interface.mark_dirty("all")

def strategy_selection_interface(stdscr, interface):
    """Interactive strategy selection interface"""
    # Save original interface state
    original_focus = interface.focus_pane
    original_show_hallmarks = interface.show_hallmarks
    original_show_references = interface.show_references
    
    # Clear screen
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    
    selection_mode = True
    current_selection = 0
    scroll_offset = 0
    
    # Get all strategies as a list for navigation
    strategy_items = list(HYPOTHESIS_STRATEGIES.items())
    
    while selection_mode:
        try:
            # Clear and prepare screen
            stdscr.clear()
            
            # Header
            header_text = "HYPOTHESIS GENERATION STRATEGIES"
            stdscr.addstr(1, (width - len(header_text)) // 2, header_text, curses.A_BOLD)
            
            current_status = interface.strategy_manager.get_status_text()
            status_text = f"Current: {current_status}"
            stdscr.addstr(2, (width - len(status_text)) // 2, status_text)
            
            # Instructions
            instructions = [
                "Press number keys (0-9) to toggle strategies | d=Default | ENTER=Apply | ESC/q=Cancel"
            ]
            for i, instruction in enumerate(instructions):
                try:
                    stdscr.addstr(4 + i, (width - len(instruction)) // 2, instruction)
                except curses.error:
                    pass
            
            # Strategy list
            list_start_y = 6
            visible_height = height - list_start_y - 3
            
            # Display strategies
            for i, (strategy_name, strategy) in enumerate(strategy_items):
                if i < scroll_offset:
                    continue
                if i - scroll_offset >= visible_height:
                    break
                    
                y_pos = list_start_y + (i - scroll_offset)
                
                # Check if strategy is active
                is_active = strategy_name in interface.strategy_manager.active_strategies
                is_default = interface.strategy_manager.default_mode
                
                # Status indicator
                if is_default:
                    status = " [DEFAULT] "
                    status_attr = curses.A_BOLD
                elif is_active:
                    status = " [ACTIVE] "
                    status_attr = curses.color_pair(3)  # Green
                else:
                    status = " [OFF] "
                    status_attr = curses.A_DIM
                
                # Highlight current selection
                if i == current_selection:
                    line_attr = curses.A_REVERSE
                else:
                    line_attr = curses.A_NORMAL
                
                # Strategy line
                strategy_line = f"{strategy.key}. {strategy.name}: {strategy.description}"
                if len(strategy_line) > width - 20:
                    strategy_line = strategy_line[:width-23] + "..."
                
                try:
                    stdscr.addstr(y_pos, 2, strategy_line, line_attr)
                    stdscr.addstr(y_pos, width - 12, status, status_attr)
                except curses.error:
                    pass
            
            # Footer
            footer_y = height - 2
            try:
                stdscr.addstr(footer_y, 2, f"Strategies: {len(interface.strategy_manager.active_strategies)} active")
            except curses.error:
                pass
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27 or key == ord('q') or key == ord('Q'):  # ESC or Q to cancel
                selection_mode = False
                
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:  # Apply changes
                selection_mode = False
                interface.set_status(f"Strategy settings applied: {interface.strategy_manager.get_status_text()}")
                
            elif key == ord('d') or key == ord('D'):  # Default mode
                interface.strategy_manager.set_default_mode(True)
                interface.set_status("Set to default hypothesis generation mode")
                
            elif key == curses.KEY_UP:
                if current_selection > 0:
                    current_selection -= 1
                    if current_selection < scroll_offset:
                        scroll_offset = current_selection
                        
            elif key == curses.KEY_DOWN:
                if current_selection < len(strategy_items) - 1:
                    current_selection += 1
                    if current_selection >= scroll_offset + visible_height:
                        scroll_offset = current_selection - visible_height + 1
                        
            elif ord('0') <= key <= ord('9'):  # Number keys to toggle strategies
                strategy_key = chr(key)
                if interface.strategy_manager.toggle_strategy(strategy_key):
                    # Find and update current selection to the toggled strategy
                    for i, (_, strategy) in enumerate(strategy_items):
                        if strategy.key == strategy_key:
                            current_selection = i
                            break
                
        except curses.error:
            pass  # Ignore display errors
        except KeyboardInterrupt:
            selection_mode = False
    
    # Restore original interface state
    interface.focus_pane = original_focus
    interface.show_hallmarks = original_show_hallmarks
    interface.show_references = original_show_references
    
    # Clear screen and force full redraw
    stdscr.clear()
    interface.mark_dirty("all")

def score_hypothesis_hallmarks(hypothesis, model_config):
    """Score hypothesis hallmarks on a 1-5 scale using AI evaluation"""
    try:
        # Get the hallmarks for scoring
        hallmarks = hypothesis.get('hallmarks', {})
        
        if not hallmarks:
            return {"error": "No hallmarks found in hypothesis for scoring"}
        
        # Create the scoring prompt
        scoring_prompt = f"""You are an expert research scientist evaluating the quality of scientific hypothesis hallmarks. You will score each hallmark on a scale from 1 to 5, where:

1 = Very Poor: Major flaws, fundamentally inadequate
2 = Poor: Significant weaknesses, below standard
3 = Adequate: Meets basic requirements but has notable limitations
4 = Good: Strong quality with minor weaknesses
5 = Excellent: Exceptional quality, exemplary

Be AGGRESSIVE in your scoring - use the full dynamic range. Most real hypotheses should score in the 2-4 range, with 5s being rare and reserved for truly exceptional work.

HYPOTHESIS TO EVALUATE:
Title: {hypothesis.get('title', 'N/A')}
Description: {hypothesis.get('description', 'N/A')}

HALLMARKS TO SCORE:

1. TESTABILITY (Falsifiability):
{hallmarks.get('testability', 'No analysis provided')}

2. SPECIFICITY AND CLARITY:
{hallmarks.get('specificity', 'No analysis provided')}

3. GROUNDED IN PRIOR KNOWLEDGE:
{hallmarks.get('grounded_knowledge', 'No analysis provided')}

4. PREDICTIVE POWER & NOVEL INSIGHT:
{hallmarks.get('predictive_power', 'No analysis provided')}

5. PARSIMONY (Principle of Simplicity):
{hallmarks.get('parsimony', 'No analysis provided')}

Provide your scoring in this exact JSON format:
{{
    "scores": {{
        "testability": 3,
        "specificity": 2,
        "grounded_knowledge": 4,
        "predictive_power": 3,
        "parsimony": 4
    }},
    "total_score": 16,
    "reasoning": {{
        "testability": "Brief explanation for this score",
        "specificity": "Brief explanation for this score",
        "grounded_knowledge": "Brief explanation for this score",
        "predictive_power": "Brief explanation for this score",
        "parsimony": "Brief explanation for this score"
    }},
    "overall_assessment": "Brief overall assessment of hypothesis quality"
}}"""
        
        # Call the model
        client = openai.OpenAI(
            api_key=model_config['api_key'],
            base_url=model_config['api_base']
        )
        
        response = client.chat.completions.create(
            model=model_config['model_name'],
            messages=[
                {"role": "system", "content": "You are a rigorous scientific evaluator who scores hypothesis hallmarks objectively and uses the full 1-5 scale aggressively. Always respond with valid JSON."},
                {"role": "user", "content": scoring_prompt}
            ],
            temperature=0.3,  # Lower temperature for consistent scoring
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_string(response_text)
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return {"error": "Could not extract JSON from model response"}
        
        try:
            scoring_data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            return {"error": f"JSON parsing error: {str(e)}"}
        
        # Validate scoring data
        if 'scores' not in scoring_data:
            return {"error": "No scores found in model response"}
        
        scores = scoring_data['scores']
        
        # Validate that all required hallmarks are scored
        required_hallmarks = ['testability', 'specificity', 'grounded_knowledge', 'predictive_power', 'parsimony']
        for hallmark in required_hallmarks:
            if hallmark not in scores:
                return {"error": f"Missing score for {hallmark}"}
            
            # Validate score range
            score = scores[hallmark]
            if not isinstance(score, int) or score < 1 or score > 5:
                return {"error": f"Invalid score for {hallmark}: {score} (must be 1-5)"}
        
        # Calculate total score
        total_score = sum(scores.values())
        scoring_data['total_score'] = total_score
        
        # Add metadata
        scoring_data['scoring_timestamp'] = datetime.now().isoformat()
        scoring_data['hypothesis_version'] = hypothesis.get('version', '1.0')
        scoring_data['hypothesis_title'] = hypothesis.get('title', 'Untitled')
        
        return scoring_data
        
    except Exception as e:
        return {"error": f"Error scoring hypothesis: {str(e)}"}

def update_hypothesis_with_abstracts(hypothesis, model_config):
    """Update hypothesis using information from downloaded abstracts"""
    try:
        # Find abstracts for this hypothesis
        abstracts = find_abstracts_for_hypothesis(hypothesis)
        
        if not abstracts:
            return {"error": "No abstracts found. Use 'a' command to fetch abstracts first."}
        
        # Prepare abstracts text for the prompt
        abstracts_text = "\n\n".join([f"Abstract {i+1}:\n{abstract['content']}" for i, abstract in enumerate(abstracts)])
        
        # Create the update prompt
        update_prompt = f"""You are a research scientist updating a hypothesis based on new information from scientific abstracts.

CURRENT HYPOTHESIS:
Title: {hypothesis.get('title', 'N/A')}
Description: {hypothesis.get('description', 'N/A')}
Experimental Validation Plan: {hypothesis.get('experimental_validation_plan', 'N/A')}
Theory and Computing Plan: {hypothesis.get('theory_and_computing_plan', 'N/A')}

NEW ABSTRACTS TO INCORPORATE:
{abstracts_text}

Please update the hypothesis by incorporating relevant information from these abstracts. The updated hypothesis should:
1. Retain the core concept but refine it based on new insights
2. Update the experimental validation plan with new methodologies or considerations from the abstracts
3. Enhance the theory and computing plan with new approaches or computational methods mentioned
4. Maintain scientific rigor and coherence

Provide the response in this exact JSON format:
{{
    "title": "Updated title",
    "description": "Updated detailed description incorporating insights from abstracts",
    "experimental_validation_plan": "Updated experimental plan with new methodologies and considerations",
    "theory_and_computing_plan": "Updated computational approach incorporating new methods",
    "hallmarks": [
        "Updated hallmark 1",
        "Updated hallmark 2",
        "Updated hallmark 3"
    ],
    "references": [
        {{
            "citation": "Relevant citation from abstracts or existing references",
            "relevance": "How this reference supports the updated hypothesis"
        }}
    ],
    "update_summary": "Brief summary of what was updated based on the abstracts"
}}"""
        
        # Call the model
        client = openai.OpenAI(
            api_key=model_config['api_key'],
            base_url=model_config['api_base']
        )
        
        response = client.chat.completions.create(
            model=model_config['model_name'],
            messages=[
                {"role": "system", "content": "You are a helpful research scientist assistant that updates hypotheses based on new scientific information. Always respond with valid JSON."},
                {"role": "user", "content": update_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        response_text = response.choices[0].message.content.strip()
        response_text = clean_json_string(response_text)
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if not json_match:
            return {"error": "Could not extract JSON from model response"}
        
        try:
            updated_data = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            return {"error": f"JSON parsing error: {str(e)}"}
        
        # Preserve original metadata and update version
        updated_hypothesis = hypothesis.copy()
        
        # Update core fields
        for field in ['title', 'description', 'experimental_validation_plan', 'theory_and_computing_plan', 'hallmarks', 'references']:
            if field in updated_data:
                updated_hypothesis[field] = updated_data[field]
        
        # Update version number (increment minor version)
        current_version = updated_hypothesis.get('version', '1.0')
        try:
            version_parts = current_version.split('.')
            if len(version_parts) >= 2:
                major = int(version_parts[0])
                minor = int(version_parts[1]) + 1
                updated_hypothesis['version'] = f"{major}.{minor}"
            else:
                updated_hypothesis['version'] = "1.1"
        except:
            updated_hypothesis['version'] = "1.1"
        
        # Add update metadata
        updated_hypothesis['last_updated'] = datetime.now().isoformat()
        updated_hypothesis['update_type'] = 'abstracts_integration'
        updated_hypothesis['abstracts_used'] = len(abstracts)
        
        if 'update_summary' in updated_data:
            updated_hypothesis['update_summary'] = updated_data['update_summary']
        
        # Add to feedback history
        if 'feedback_history' not in updated_hypothesis:
            updated_hypothesis['feedback_history'] = []
        
        updated_hypothesis['feedback_history'].append({
            "timestamp": datetime.now().isoformat(),
            "feedback_type": "abstracts_integration",
            "abstracts_count": len(abstracts),
            "update_summary": updated_data.get('update_summary', 'Updated with information from abstracts')
        })
        
        return updated_hypothesis
        
    except Exception as e:
        return {"error": f"Error updating hypothesis: {str(e)}"}

def fetch_papers_for_hypothesis(hypothesis, session_name, interface=None):
    """Fetch papers and abstracts for all references in a hypothesis"""
    references = hypothesis.get('references', [])
    if not references:
        return {"status": "no_references", "message": "No references found in hypothesis"}
    
    # Create papers directory
    papers_dir = create_papers_directory(session_name)
    
    # Get Semantic Scholar API key from environment
    ss_api_key = os.environ.get('SS_API_KEY') or os.environ.get('SEMANTIC_SCHOLAR_API_KEY')
    if not ss_api_key and interface:
        interface.draw_status_bar("Warning: No SS API key found. Using public rate limits...")
        time.sleep(2)
    
    results = {
        "status": "success",
        "papers_dir": str(papers_dir),
        "fetched": [],
        "failed": []
    }
    
    total_refs = len(references)
    
    # Initialize all references as pending
    if interface:
        hyp_id = hypothesis.get('hypothesis_number', 0)
        for i in range(total_refs):
            interface.update_reference_status(hyp_id, i+1, 'pending')
    
    for i, ref in enumerate(references):
        if interface:
            hyp_id = hypothesis.get('hypothesis_number', 0)
            status_msg = f"Fetching papers... ({i+1}/{total_refs})"
            interface.draw_status_bar(status_msg)
            interface.update_reference_status(hyp_id, i+1, 'fetching')
            interface.stdscr.refresh()
        
        try:
            if isinstance(ref, dict):
                citation = ref.get('citation', '')
            else:
                citation = str(ref)
            
            if not citation:
                results["failed"].append({"index": i+1, "reason": "Empty citation"})
                if interface:
                    interface.update_reference_status(hyp_id, i+1, 'failed')
                continue
            
            # Extract paper information from citation
            paper_info = extract_paper_info_from_citation(citation)
            
            # Search for papers using title or author+year
            query = paper_info.get('title', '') or f"{paper_info.get('author', '')} {paper_info.get('year', '')}"
            if not query.strip():
                query = citation[:50]  # Use first 50 chars as fallback
            
            papers = search_semantic_scholar(query.strip(), max_results=3, api_key=ss_api_key)
            
            if papers:
                # Use the most relevant paper (first one)
                best_paper = papers[0]
                
                # Save abstract
                abstract_path = save_abstract_to_file(best_paper, papers_dir, i+1)
                
                # Try to download PDF
                pdf_path = download_paper_pdf(best_paper, papers_dir, i+1)
                
                results["fetched"].append({
                    "index": i+1,
                    "citation": citation,
                    "title": best_paper.get('title'),
                    "abstract_path": abstract_path,
                    "pdf_path": pdf_path,
                    "paper_id": best_paper.get('paper_id'),
                    "doi": best_paper.get('doi'),
                    "venue": best_paper.get('venue')
                })
                
                # Update status to success
                if interface:
                    interface.update_reference_status(hyp_id, i+1, 'success')
            else:
                results["failed"].append({
                    "index": i+1, 
                    "citation": citation,
                    "reason": "No papers found"
                })
                
                # Update status to failed
                if interface:
                    interface.update_reference_status(hyp_id, i+1, 'failed')
        
        except Exception as e:
            results["failed"].append({
                "index": i+1,
                "citation": citation if 'citation' in locals() else "Unknown",
                "reason": str(e)
            })
            
            # Update status to failed
            if interface:
                interface.update_reference_status(hyp_id, i+1, 'failed')
        
        # Add delay between requests to be respectful to the API
        # Use longer delay if no API key (public rate limits are stricter)
        delay = 3 if not ss_api_key else 1
        time.sleep(delay)
    
    return results

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
        
        # Progress tracking for operations
        self.progress_operations = {}
        # Format: {operation_id: {'type': 'generating', 'current': 2, 'total': 5, 'message': 'Generating hypotheses', 'start_time': time.time()}}
        
        # Dirty flags for selective updates
        self.dirty_header = True
        self.dirty_list = True
        self.dirty_details = True
        self.dirty_status = True
        self.last_hypothesis_count = 0
        self.last_current_idx = -1
        self.last_hypothesis_content = None
        
        # Focus management for left/right arrow navigation
        self.focus_pane = "list"  # Can be "list" or "details"
        self.list_scroll_offset = 0  # For scrolling in hypothesis list
        
        # Sorting management
        self.sort_mode = "numerical"  # Can be "numerical" or "score"
        
        # Reference fetching status tracking
        self.reference_status = {}  # {hypothesis_id: {ref_index: 'pending'|'fetching'|'success'|'failed'}}
        
        # Pending operations tracking
        self.pending_operations = {
            'generating_new': 0,      # Count of pending new hypothesis generations
            'fetching_papers': 0,     # Count of pending paper fetch operations
            'improving': 0,           # Count of pending improvements
            'saving': 0,              # Count of pending save operations
            'loading': 0              # Count of pending load operations
        }
        
        # Status refresh thread management
        self.status_refresh_active = True
        self.status_refresh_thread = None
        self.status_lock = threading.Lock()
        self.start_status_refresh_thread()
        
        # Initialize TaskQueue for background operations
        self.task_queue = TaskQueue(max_workers=3)
        self.task_queue.start()
        
        # Initialize Hypothesis Strategy Manager
        self.strategy_manager = HypothesisStrategyManager()
        
    def start_status_refresh_thread(self):
        """Start background thread to refresh status display"""
        def refresh_status_loop():
            import time
            while self.status_refresh_active:
                try:
                    with self.status_lock:
                        # Update any progress operations
                        self.update_progress_display()
                        
                        # Refresh status if needed
                        if self.dirty_status:
                            self.draw_status_bar()
                            try:
                                self.status_win.refresh()
                            except:
                                pass  # Ignore refresh errors during shutdown
                            self.dirty_status = False
                    
                    time.sleep(0.5)  # Update every 500ms
                except Exception:
                    pass  # Ignore errors during shutdown
        
        self.status_refresh_thread = threading.Thread(target=refresh_status_loop, daemon=True)
        self.status_refresh_thread.start()
        
    def stop_status_refresh_thread(self):
        """Stop the status refresh thread"""
        self.status_refresh_active = False
        if self.status_refresh_thread:
            try:
                self.status_refresh_thread.join(timeout=1.0)
            except:
                pass
    
    def cleanup(self):
        """Clean up resources including TaskQueue and threads"""
        self.stop_status_refresh_thread()
        if hasattr(self, 'task_queue'):
            self.task_queue.stop()
                
    def add_progress_operation(self, operation_id, operation_type, total_items, message):
        """Add a progress operation to track"""
        with self.status_lock:
            self.progress_operations[operation_id] = {
                'type': operation_type,
                'current': 0,
                'total': total_items,
                'message': message,
                'start_time': time.time()
            }
            self.mark_dirty("status")
            
    def update_progress_operation(self, operation_id, current_item, message=None):
        """Update progress for an operation"""
        with self.status_lock:
            if operation_id in self.progress_operations:
                self.progress_operations[operation_id]['current'] = current_item
                if message:
                    self.progress_operations[operation_id]['message'] = message
                self.mark_dirty("status")
                
    def remove_progress_operation(self, operation_id):
        """Remove a completed progress operation"""
        with self.status_lock:
            if operation_id in self.progress_operations:
                del self.progress_operations[operation_id]
                self.mark_dirty("status")
                
    def update_progress_display(self):
        """Update the progress display in status bar"""
        # Check for running tasks in TaskQueue
        running_tasks = self.task_queue.get_running_tasks()
        
        if not self.progress_operations and not running_tasks:
            return
            
        # Build progress message
        progress_messages = []
        current_time = time.time()
        
        # Add TaskQueue running tasks
        for task_id, task in running_tasks.items():
            elapsed = current_time - task.started_at if task.started_at else 0
            progress_messages.append(f"{task.name} ({elapsed:.0f}s)")
        
        # Add legacy progress operations (for backward compatibility)
        for op_id, op_data in self.progress_operations.items():
            current = op_data['current']
            total = op_data['total']
            message = op_data['message']
            elapsed = current_time - op_data['start_time']
            
            if total > 1:
                # Show progress with countdown
                progress_percent = (current / total) * 100 if total > 0 else 0
                remaining = total - current
                
                # Estimate time remaining
                if current > 0 and elapsed > 0:
                    rate = current / elapsed
                    eta_seconds = remaining / rate if rate > 0 else 0
                    if eta_seconds < 60:
                        eta_str = f"{eta_seconds:.0f}s"
                    else:
                        eta_str = f"{eta_seconds/60:.1f}m"
                    progress_text = f"{message} ({current}/{total}) {progress_percent:.0f}% - ETA: {eta_str}"
                else:
                    progress_text = f"{message} ({current}/{total}) {progress_percent:.0f}%"
            else:
                # Single operation
                progress_text = f"{message} ({elapsed:.0f}s)"
            
            progress_messages.append(progress_text)
        
        # Update status with progress info
        if progress_messages:
            combined_message = " | ".join(progress_messages)
            self.set_status(combined_message, persistent=True)
        
    def get_reference_status_indicator(self, hypothesis_id, ref_index):
        """Get status indicator for a specific reference"""
        if hypothesis_id not in self.reference_status:
            return " "  # No status available
        
        status = self.reference_status[hypothesis_id].get(ref_index, 'pending')
        if status == 'pending':
            return " "  # No indicator for pending
        elif status == 'fetching':
            try:
                return "⏳"  # Hourglass for in-progress
            except (UnicodeEncodeError, curses.error):
                return "~"  # Fallback for in-progress
        elif status == 'success':
            try:
                return "✓"  # Check mark for success
            except (UnicodeEncodeError, curses.error):
                return "+"  # Fallback for success
        elif status == 'failed':
            try:
                return "✗"  # X mark for failure
            except (UnicodeEncodeError, curses.error):
                return "X"  # Fallback for failure
        else:
            return " "
            
    def update_reference_status(self, hypothesis_id, ref_index, status):
        """Update the status of a specific reference"""
        if hypothesis_id not in self.reference_status:
            self.reference_status[hypothesis_id] = {}
        self.reference_status[hypothesis_id][ref_index] = status
        # Mark details pane for refresh
        self.mark_dirty("details")
        
        # Force immediate refresh if currently displayed hypothesis matches
        current_hyp_num = getattr(self, '_current_displayed_hypothesis_id', None)
        if current_hyp_num == hypothesis_id:
            try:
                self.detail_win.refresh()
            except:
                pass  # Ignore refresh errors during threading
                
    def add_pending_operation(self, operation_type):
        """Add a pending operation and update status display"""
        self.pending_operations[operation_type] += 1
        self.update_pending_status()
        
    def remove_pending_operation(self, operation_type):
        """Remove a pending operation and update status display"""
        if self.pending_operations[operation_type] > 0:
            self.pending_operations[operation_type] -= 1
        self.update_pending_status()
        
    def update_pending_status(self):
        """Update status bar to show pending operations"""
        pending_msgs = []
        
        if self.pending_operations['generating_new'] > 0:
            count = self.pending_operations['generating_new']
            pending_msgs.append(f"Generating {count} new hypothesis{'es' if count > 1 else ''}")
            
        if self.pending_operations['fetching_papers'] > 0:
            count = self.pending_operations['fetching_papers']
            pending_msgs.append(f"Fetching papers ({count} active)")
            
        if self.pending_operations['improving'] > 0:
            count = self.pending_operations['improving']
            pending_msgs.append(f"Improving {count} hypothesis{'es' if count > 1 else ''}")
            
        if self.pending_operations['saving'] > 0:
            count = self.pending_operations['saving']
            pending_msgs.append(f"Saving {count} file{'s' if count > 1 else ''}")
            
        if self.pending_operations['loading'] > 0:
            count = self.pending_operations['loading']
            pending_msgs.append(f"Loading {count} file{'s' if count > 1 else ''}")
        
        if pending_msgs:
            status_msg = " • ".join(pending_msgs) + "..."
            self.draw_status_bar(status_msg)
            self.status_win.refresh()
        
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
        
    def draw_border(self, window):
        """Draw clean border using proper box-drawing characters"""
        height, width = window.getmaxyx()
        
        try:
            # Try to use Unicode box-drawing characters
            # Top border
            window.addch(0, 0, '┌')  # top-left corner
            for x in range(1, width - 1):
                window.addch(0, x, '─')  # horizontal line
            window.addch(0, width - 1, '┐')  # top-right corner
            
            # Side borders
            for y in range(1, height - 1):
                window.addch(y, 0, '│')  # left vertical line
                window.addch(y, width - 1, '│')  # right vertical line
            
            # Bottom border
            window.addch(height - 1, 0, '└')  # bottom-left corner
            for x in range(1, width - 1):
                window.addch(height - 1, x, '─')  # horizontal line
            window.addch(height - 1, width - 1, '┘')  # bottom-right corner
            
        except (curses.error, UnicodeEncodeError):
            # Fallback to ASCII characters if Unicode fails
            try:
                # Top border
                window.addch(0, 0, '+')
                for x in range(1, width - 1):
                    window.addch(0, x, '-')
                window.addch(0, width - 1, '+')
                
                # Side borders
                for y in range(1, height - 1):
                    window.addch(y, 0, '|')
                    window.addch(y, width - 1, '|')
                
                # Bottom border
                window.addch(height - 1, 0, '+')
                for x in range(1, width - 1):
                    window.addch(height - 1, x, '-')
                window.addch(height - 1, width - 1, '+')
            except curses.error:
                # Final fallback - use box() if all else fails
                window.box()
        
    def draw_header(self, research_goal, model_name):
        """Draw the header pane with research goal and model info"""
        self.header_win.clear()
        self.header_win.attron(curses.color_pair(5) | curses.A_BOLD)
        
        # Title line
        title = f" WISTERIA v6 - Research Hypothesis Generator"
        model_info = f"[Model: {model_name}] "
        title_line = title + " " * max(0, self.width - len(title) - len(model_info)) + model_info
        self.safe_addstr(self.header_win, 0, 0, title_line[:self.width])
        
        # Separator
        self.safe_addstr(self.header_win, 1, 0, "-" * (self.width-1))
        
        self.header_win.attroff(curses.color_pair(5) | curses.A_BOLD)
        
        # Research goal (wrapped)
        goal_text = f"Research Goal: {research_goal}"
        wrapped_goal = self.safe_wrap_text(goal_text, self.width - 2)
        goal_lines = wrapped_goal.split('\n')
        
        for i, line in enumerate(goal_lines[:2]):  # Max 2 lines for goal
            if i + 2 < self.HEADER_HEIGHT:
                self.safe_addstr(self.header_win, i + 2, 1, line)
        
        # Refresh moved to single refresh cycle
        
    def draw_hypothesis_list(self, all_hypotheses):
        """Draw the hypothesis list pane"""
        self.list_win.clear()
        # Draw clean border
        self.draw_border(self.list_win)
        
        # Title with focus indicator
        sort_indicator = f" [{self.sort_mode.upper()}]"
        if self.focus_pane == "list":
            list_title = f" Hypothesis List{sort_indicator} [FOCUSED] "
            title_attr = curses.A_BOLD | curses.A_REVERSE
        else:
            list_title = f" Hypothesis List{sort_indicator} "
            title_attr = curses.A_BOLD
        title_x = (self.LIST_WIDTH - len(list_title)) // 2
        self.list_win.addstr(0, title_x, list_title, title_attr)
        
        if not all_hypotheses:
            self.list_win.addstr(2, 2, "No hypotheses yet", curses.color_pair(4))
            # Refresh moved to single refresh cycle
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
        
        # Sort hypothesis numbers based on current sort mode
        if self.sort_mode == "score":
            # Sort by score (descending), then by hypothesis number
            def get_sort_key(hyp_num):
                latest_version = max(hypothesis_groups[hyp_num], key=lambda h: h.get("version", "1.0"))
                hallmark_scores = latest_version.get("hallmark_scores", {})
                total_score = hallmark_scores.get("total_score", -1)  # -1 for unscored
                return (-total_score, hyp_num)  # Negative for descending order
            sorted_hyp_nums = sorted(hypothesis_groups.keys(), key=get_sort_key)
        else:
            # Default numerical sorting
            sorted_hyp_nums = sorted(hypothesis_groups.keys())
        
        for hyp_num in sorted_hyp_nums:
            if y_pos - 2 < self.list_scroll_offset:
                continue
            if y_pos >= list_height + self.list_scroll_offset:
                break
                
            hyp_versions = hypothesis_groups[hyp_num]
            latest_version = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
            
            version = latest_version.get("version", "1.0")
            title = latest_version.get("title", "Untitled")
            hyp_type = latest_version.get("type", "unknown")
            
            # Check if there are hallmark scores
            score_indicator = ""
            hallmark_scores = latest_version.get("hallmark_scores", {})
            if hallmark_scores and "total_score" in hallmark_scores:
                total_score = hallmark_scores["total_score"]
                score_indicator = f" ({total_score}/25)"
            
            # Truncate title to fit (accounting for score display)
            max_title_len = self.LIST_WIDTH - 15 - len(score_indicator)
            if len(title) > max_title_len:
                title = title[:max_title_len-3] + "..."
            
            type_indicator = ""
            if hyp_type == "improvement":
                type_indicator = " (imp)"
            elif hyp_type == "new_alternative": 
                type_indicator = " (alt)"
                
            line_text = f"{hyp_num}. [v{version}]{score_indicator} {title}{type_indicator}"
            
            # Highlight selected hypothesis
            attr = curses.A_REVERSE if hyp_num - 1 == self.current_hypothesis_idx else 0
            
            try:
                display_y = y_pos - self.list_scroll_offset
                if 1 <= display_y < list_height:
                    self.safe_addstr(self.list_win, display_y, 2, line_text, attr)
            except curses.error:
                pass  # Ignore if line doesn't fit
                
            y_pos += 1
            
        # Refresh moved to single refresh cycle
        
    def draw_hypothesis_details(self, hypothesis, previous_hypothesis=None):
        """Draw the hypothesis details pane"""
        self.detail_win.clear()
        # Draw clean border
        self.draw_border(self.detail_win)
        
        # Title with focus indicator
        if self.focus_pane == "details":
            detail_title = " Current Hypothesis [FOCUSED] "
            title_attr = curses.A_BOLD | curses.A_REVERSE
        else:
            detail_title = " Current Hypothesis "
            title_attr = curses.A_BOLD
        title_x = (self.DETAIL_WIDTH - len(detail_title)) // 2
        self.detail_win.addstr(0, title_x, detail_title, title_attr)
        
        if not hypothesis:
            self.detail_win.addstr(2, 2, "No hypothesis selected", curses.color_pair(4))
            # Refresh moved to single refresh cycle
            return
            
        # Track currently displayed hypothesis for status updates
        self._current_displayed_hypothesis_id = hypothesis.get('hypothesis_number', 0)
            
        # Content area
        content_width = self.DETAIL_WIDTH - 4
        y_pos = 2
        max_y = self.detail_win.getmaxyx()[0] - 2
        
        try:
            # Title
            version = hypothesis.get("version", "1.0")
            hyp_title = f"Title (v{version}): {hypothesis.get('title', 'Untitled')}"
            wrapped_title = self.safe_wrap_text(hyp_title, content_width)
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
            wrapped_desc = self.safe_wrap_text(description, content_width)
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
            wrapped_validation = self.safe_wrap_text(experimental_validation, content_width)
            for line in wrapped_validation.split('\n'):
                if y_pos >= max_y + self.detail_scroll_offset + 20:  # Reasonable limit
                    break
                if y_pos - 2 >= self.detail_scroll_offset:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, line)
                y_pos += 1
            
            # Theory and Computation section
            theory_computation = hypothesis.get('theory_and_computation', '')
            if theory_computation.strip():
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, "Theory and Computation:", curses.A_UNDERLINE)
                y_pos += 1
                
                wrapped_theory = self.safe_wrap_text(theory_computation, content_width)
                for line in wrapped_theory.split('\n'):
                    if y_pos >= max_y + self.detail_scroll_offset + 20:  # Reasonable limit
                        break
                    if y_pos - 2 >= self.detail_scroll_offset:
                        display_y = y_pos - self.detail_scroll_offset
                        if 2 <= display_y < max_y:
                            self.safe_addstr(self.detail_win, display_y, 2, line)
                    y_pos += 1
            
            # Notes section
            notes = hypothesis.get('notes', '')
            if notes.strip():
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, "Personal Notes:", curses.A_UNDERLINE)
                y_pos += 1
                
                wrapped_notes = self.safe_wrap_text(notes, content_width)
                for line in wrapped_notes.split('\n'):
                    if y_pos >= max_y + self.detail_scroll_offset + 20:  # Reasonable limit
                        break
                    if y_pos - 2 >= self.detail_scroll_offset:
                        display_y = y_pos - self.detail_scroll_offset
                        if 2 <= display_y < max_y:
                            self.safe_addstr(self.detail_win, display_y, 2, line, curses.color_pair(5))  # Different color for notes
                    y_pos += 1
            else:
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, "[No notes - press 't' to add notes]", curses.color_pair(4))
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
                wrapped_imp = self.safe_wrap_text(improvements, content_width)
                for line in wrapped_imp.split('\n'):
                    if y_pos - 2 >= self.detail_scroll_offset:
                        display_y = y_pos - self.detail_scroll_offset
                        if 2 <= display_y < max_y:
                            self.safe_addstr(self.detail_win, display_y, 2, line, curses.color_pair(4))
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
                    wrapped_text = self.safe_wrap_text(text, content_width - 3)
                    for line in wrapped_text.split('\n'):
                        if y_pos - 2 >= self.detail_scroll_offset:
                            display_y = y_pos - self.detail_scroll_offset
                            if 2 <= display_y < max_y:
                                self.safe_addstr(self.detail_win, display_y, 5, line)
                        y_pos += 1
                    y_pos += 1  # Blank line between hallmarks
            else:
                y_pos += 1
                if y_pos - 2 >= self.detail_scroll_offset and y_pos - self.detail_scroll_offset < max_y:
                    display_y = y_pos - self.detail_scroll_offset
                    if 2 <= display_y < max_y:
                        self.safe_addstr(self.detail_win, display_y, 2, "[Hallmarks hidden - press 'h' to toggle]", curses.color_pair(4))
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
                    # Get hypothesis ID for status lookup
                    hyp_id = hypothesis.get('hypothesis_number', 0)
                    
                    for i, ref in enumerate(references, 1):
                        if isinstance(ref, dict):
                            citation = ref.get('citation', 'No citation')
                            annotation = ref.get('annotation', 'No annotation')
                            
                            # Get status indicator for this reference
                            status_indicator = self.get_reference_status_indicator(hyp_id, i)
                            
                            # Display citation with status indicator
                            citation_text = f"{status_indicator} {i}. {citation}"
                            wrapped_citation = self.safe_wrap_text(citation_text, content_width - 3)
                            for line in wrapped_citation.split('\n'):
                                if y_pos - 2 >= self.detail_scroll_offset:
                                    display_y = y_pos - self.detail_scroll_offset
                                    if 2 <= display_y < max_y:
                                        self.safe_addstr(self.detail_win, display_y, 2, line, curses.A_BOLD)
                                y_pos += 1
                            
                            # Display annotation
                            wrapped_annotation = self.safe_wrap_text(annotation, content_width - 6)
                            for line in wrapped_annotation.split('\n'):
                                if y_pos - 2 >= self.detail_scroll_offset:
                                    display_y = y_pos - self.detail_scroll_offset
                                    if 2 <= display_y < max_y:
                                        self.safe_addstr(self.detail_win, display_y, 8, line)
                                y_pos += 1
                            y_pos += 1  # Blank line between references
                        else:
                            # Handle string references
                            ref_text = f"{i}. {str(ref)}"
                            wrapped_ref = self.safe_wrap_text(ref_text, content_width - 3)
                            for line in wrapped_ref.split('\n'):
                                if y_pos - 2 >= self.detail_scroll_offset:
                                    display_y = y_pos - self.detail_scroll_offset
                                    if 2 <= display_y < max_y:
                                        self.safe_addstr(self.detail_win, display_y, 5, line)
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
                        self.safe_addstr(self.detail_win, display_y, 2, "[References hidden - press 'r' to toggle]", curses.color_pair(4))
                y_pos += 1
                
        except curses.error:
            pass  # Ignore if content doesn't fit
            
        # Refresh moved to single refresh cycle
        
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
        
        # Status message with strategy info
        strategy_status = self.strategy_manager.get_status_text()
        status_line = f" Status: {display_status} | Strategy: {strategy_status}"
        self.safe_addstr(self.status_win, 0, 0, status_line)
        
        # Commands - show on two lines if needed
        commands_line1 = " f=Feedback n=New l=Load x=Save t=Notes s=Select v=View h=Toggle r=Refs a=Papers u=Update b=Browse c=Score w=Strategy p=PDF q=Quit "
        commands_line2 = " Up/Down=Navigate j/k=Scroll d/u=FastScroll g=Home "
        
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
            commands_short = " f=Feedback n=New a=Papers u=Update b=Browse c=Score w=Strategy p=PDF q=Quit j/k=Scroll "
            cmd_start_x = max(0, self.width - len(commands_short))
            if cmd_start_x > len(status_line):
                self.safe_addstr(self.status_win, 0, cmd_start_x, commands_short)
        
        # Fill rest of first line if needed
        if len(commands_line1) + len(status_line) < self.width:
            remaining = self.width - len(status_line) - len(commands_line1)
            if remaining > 0:
                self.status_win.addstr(0, len(status_line), " " * remaining)
            
        self.status_win.attroff(curses.color_pair(6))
        # Refresh moved to single refresh cycle
        
    def mark_dirty(self, component="all"):
        """Mark components as needing redraw"""
        if component in ("all", "header"):
            self.dirty_header = True
        if component in ("all", "list"):
            self.dirty_list = True
        if component in ("all", "details"):
            self.dirty_details = True
        if component in ("all", "status"):
            self.dirty_status = True
    
    def check_changes(self, all_hypotheses, current_idx, current_hypothesis):
        """Check what has changed and mark appropriate components dirty"""
        # Check if hypothesis count changed
        if len(all_hypotheses) != self.last_hypothesis_count:
            self.dirty_list = True
            self.last_hypothesis_count = len(all_hypotheses)
        
        # Check if current hypothesis index changed
        if current_idx != self.last_current_idx:
            self.dirty_list = True
            self.dirty_details = True
            self.last_current_idx = current_idx
        
        # Check if current hypothesis content changed
        if current_hypothesis:
            hypothesis_str = str(current_hypothesis)
            if hypothesis_str != self.last_hypothesis_content:
                self.dirty_details = True
                self.last_hypothesis_content = hypothesis_str
    
    def draw_interface_selective(self, research_goal, model_name, all_hypotheses, current_hypothesis, status_msg=None):
        """Draw only the components that have changed"""
        if self.dirty_header:
            self.draw_header(research_goal, model_name)
            self.header_win.refresh()
            self.dirty_header = False
        
        if self.dirty_list:
            self.draw_hypothesis_list(all_hypotheses)
            self.list_win.refresh()
            self.dirty_list = False
        
        if self.dirty_details:
            self.draw_hypothesis_details(current_hypothesis)
            self.detail_win.refresh()
            self.dirty_details = False
        
        if self.dirty_status or status_msg:
            if status_msg:
                self.draw_status_bar(status_msg)
            else:
                self.draw_status_bar()
            self.status_win.refresh()
            self.dirty_status = False
        
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
        self.mark_dirty("list")
            
    def scroll_detail(self, direction):
        """Scroll the hypothesis details"""
        if direction > 0:
            self.detail_scroll_offset += 1
        else:
            self.detail_scroll_offset = max(0, self.detail_scroll_offset - 1)
        self.mark_dirty("details")
            
    def set_status(self, message, persistent=False, timeout=3.0):
        """Set a status message with optional persistence and timeout"""
        self.current_status = message
        self.status_timestamp = time.time()
        self.persistent_status = persistent
        self.status_timeout = timeout
        self.mark_dirty("status")
        
    def clear_status_on_action(self):
        """Clear status message when user performs an action"""
        if not self.persistent_status:
            self.current_status = "Ready"
            self.persistent_status = False
            self.mark_dirty("status")
            
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

    def safe_wrap_text(self, text, width, max_length=10000):
        """Safely wrap text with length limits to prevent memory issues"""
        if not text:
            return ""
        
        # Limit text length to prevent memory issues
        safe_text = str(text)[:max_length]
        
        try:
            return textwrap.fill(safe_text, width)
        except (MemoryError, OverflowError):
            # Fallback: return truncated text without wrapping
            return safe_text[:width]

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
        
        # Theory and Computation
        theory_computation = hypothesis.get('theory_and_computation', '')
        if theory_computation.strip():
            story.append(Paragraph("Theory and Computation", heading_style))
            story.append(Paragraph(theory_computation, body_style))
            story.append(Spacer(1, 20))
        
        # Personal Notes
        notes = hypothesis.get('notes', '')
        if notes.strip():
            notes_style = ParagraphStyle(
                'NotesStyle',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=12,
                leftIndent=10,
                rightIndent=10,
                leading=14,
                backColor=HexColor('#FFF9E6'),
                borderWidth=1,
                borderColor=HexColor('#E6CC00'),
                borderPadding=8
            )
            
            story.append(Paragraph("Personal Notes", heading_style))
            story.append(Paragraph(notes, notes_style))
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
        story.append(Paragraph("Generated by Wisteria Research Hypothesis Generator v6.0", footer_style))
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
    
    # Compare theory and computation
    old_theory_computation = old_hypothesis.get('theory_and_computation', '')
    new_theory_computation = new_hypothesis.get('theory_and_computation', '')
    if old_theory_computation != new_theory_computation:
        result['theory_and_computation_highlighted'] = highlight_text_changes(old_theory_computation, new_theory_computation)
    
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

def load_model_config(model_shortname, config_path=None):
    """
    Load model configuration from the model_servers.yaml file.
    Returns a dictionary with api_key, api_base, and model_name.
    """
    if not model_shortname or not model_shortname.strip():
        print("Error: Model shortname cannot be empty")
        sys.exit(1)
        
    if config_path:
        yaml_path = config_path
    else:
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model_servers.yaml")
    
    try:
        with open(yaml_path, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)
            
        if not config or 'servers' not in config:
            print(f"Error: Invalid format in {yaml_path} - missing 'servers' section")
            sys.exit(1)
            
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
def generate_hypotheses(research_goal, config, num_hypotheses=5, strategy_manager=None):
    """
    Generate scientific hypotheses based on a research goal.
    Returns a list of hypothesis objects.
    
    This function uses exponential backoff to handle rate limits and transient errors.
    It will retry up to 5 times with increasing delays between attempts or until max_time is reached.
    
    Args:
        research_goal (str): The research goal or question
        config (dict): Configuration for the model API
        num_hypotheses (int): Number of hypotheses to generate
        strategy_manager (HypothesisStrategyManager): Optional strategy manager for enhanced generation
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
4. THEORY_AND_COMPUTATION: Describe theoretical frameworks, computational models, simulations, mathematical analyses, or computational approaches that could be developed to explore, predict, or validate aspects of this hypothesis
5. ANALYSIS: Evaluate the hypothesis against each of the five hallmarks of strong scientific hypotheses:
6. REFERENCES: Include relevant scientific references that support or relate to the hypothesis (3-5 references minimum)

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
  "theory_and_computation": "Detailed description of theoretical frameworks, computational models, simulations, mathematical analyses, or computational approaches that could be developed to explore, predict, or validate this hypothesis",
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

{strategy_manager.get_strategy_prompt_additions() if strategy_manager else ""}
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
    
    # Display Theory and Computation section
    theory_computation = hypothesis.get('theory_and_computation', '')
    if theory_computation.strip():
        theory_computation_text = highlighted.get('theory_and_computation_highlighted', theory_computation)
        print(f"\nTheory and Computation:")
        print(f"{theory_computation_text}")
    
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
    print("\\x - Save current session to a JSON file with custom filename")
    print("\\t - Add/edit personal notes for the current hypothesis")
    print("\\v - View the titles of hypotheses in current session")
    print("\\s - Select a hypothesis to continue to refine")
    print("\\h - Toggle hallmarks analysis display")
    print("\\r - Toggle references display")
    print("\\a - Fetch abstracts and papers from Semantic Scholar for current hypothesis references")
    print("\\u - Update hypothesis with information from downloaded abstracts")
    print("\\b - Browse and view downloaded abstracts")
    print("\\c - Score hypothesis hallmarks (1-5 scale) using AI evaluation")
    print("\\p - Print current hypothesis to PDF document")
    print("\\q - Quit and save all hypotheses")
    print("-" * 60)
    
    while True:
        choice = input("\nEnter your choice (\\f, \\n, \\l, \\x, \\t, \\v, \\s, \\h, \\r, \\a, \\u, \\b, \\c, \\p, or \\q): ").strip()
        
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
            
        elif choice == "\\a":
            return "FETCH_PAPERS"
            
        elif choice == "\\u":
            return "UPDATE_WITH_ABSTRACTS"
            
        elif choice == "\\b":
            return "BROWSE_ABSTRACTS"
            
        elif choice == "\\c":
            return "SCORE_HALLMARKS"
            
        elif choice == "\\x":
            filename = input("\nEnter filename to save (without .json): ").strip()
            if filename:
                return f"SAVE_SESSION:{filename}"
            else:
                print("Please provide a filename or choose a different option.")
                continue
                
        elif choice == "\\t":
            if current_hypothesis:
                current_notes = current_hypothesis.get("notes", "")
                print(f"\nCurrent notes: {current_notes}")
                new_notes = input("Enter new notes (or press Enter to keep current): ").strip()
                if new_notes:
                    return f"EDIT_NOTES:{new_notes}"
                else:
                    print("Notes unchanged.")
                    continue
            else:
                print("No hypothesis selected for notes editing.")
                continue
                
        elif choice == "\\p":
            if PDF_AVAILABLE:
                return "GENERATE_PDF"
            else:
                print("PDF generation not available. Install reportlab: pip install reportlab")
                continue
                
        elif choice == "\\q":
            return "QUIT"
            
        else:
            print("Invalid choice. Please enter \\f, \\n, \\l, \\x, \\t, \\v, \\s, \\h, \\r, \\a, \\u, \\b, \\c, \\p, or \\q.")

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def improve_hypothesis(research_goal, current_hypothesis, user_feedback, config, strategy_manager=None):
    """
    Improve a hypothesis based on user feedback.
    
    Args:
        research_goal (str): The original research goal
        current_hypothesis (dict): The current hypothesis to improve
        user_feedback (str): User feedback for improvement
        config (dict): Configuration for the model API
        strategy_manager (HypothesisStrategyManager): Optional strategy manager for enhanced generation
        
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
  "theory_and_computation": "Detailed description of theoretical frameworks, computational models, simulations, mathematical analyses, or computational approaches that could be developed to explore, predict, or validate this improved hypothesis",
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

{strategy_manager.get_strategy_prompt_additions() if strategy_manager else ""}
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
                # Initialize notes if not present
                if "notes" not in improved_hypothesis:
                    improved_hypothesis["notes"] = ""
                return improved_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                improved_hypothesis = json.loads(cleaned_text)
                # Initialize feedback history if not present
                if "feedback_history" not in improved_hypothesis:
                    improved_hypothesis["feedback_history"] = []
                # Initialize notes if not present
                if "notes" not in improved_hypothesis:
                    improved_hypothesis["notes"] = ""
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
def revise_hypothesis(research_goal, current_hypothesis, config):
    """
    Generate a revised and improved version of a hypothesis using the complete hypothesis content as input.
    This creates a new version that improves upon the existing hypothesis.
    
    Args:
        research_goal (str): The original research goal
        current_hypothesis (dict): The current hypothesis to revise
        config (dict): Configuration for the model API
        
    Returns:
        dict: Revised hypothesis object
    """
    # Configure the OpenAI client
    api_key = config['api_key']
    api_base = config['api_base']
    model_name = config['model_name']
    
    # System prompt for hypothesis revision
    system_message = (
        "You are an expert research scientist who excels at revising and enhancing scientific hypotheses. "
        "You take existing hypotheses and create improved versions that strengthen the scientific reasoning, "
        "enhance testability, improve clarity, and advance the theoretical framework while maintaining the core insights."
    )
    
    # Get all relevant content from the current hypothesis
    title = current_hypothesis.get('title', 'Untitled')
    description = current_hypothesis.get('description', 'No description')
    experimental_validation = current_hypothesis.get('experimental_validation', 'No validation plan provided')
    theory_computation = current_hypothesis.get('theory_and_computation', 'No theoretical framework provided')
    hallmarks = current_hypothesis.get('hallmarks', {})
    references = current_hypothesis.get('references', [])
    
    # Format existing hallmarks
    hallmarks_text = ""
    for key, value in hallmarks.items():
        hallmarks_text += f"- {key.title()}: {value}\n"
    
    # Format existing references
    references_text = ""
    for ref in references:
        citation = ref.get('citation', 'No citation')
        annotation = ref.get('annotation', 'No annotation')
        references_text += f"- {citation}\n  Annotation: {annotation}\n"
    
    # User prompt with detailed instructions
    user_message = f"""
Based on the original research goal and the complete current hypothesis provided below, please create a revised and improved version that enhances the scientific quality, clarity, and impact.

ORIGINAL RESEARCH GOAL:
{research_goal}

CURRENT HYPOTHESIS CONTENT:
Title: {title}

Description: {description}

Experimental Validation: {experimental_validation}

Theory and Computation: {theory_computation}

Current Hallmarks:
{hallmarks_text}

Current References:
{references_text}

Please create a REVISED and IMPROVED version that:
1. Strengthens the scientific reasoning and theoretical foundation
2. Enhances the experimental design and validation approach
3. Improves clarity and specificity of the hypothesis
4. Strengthens the theoretical and computational framework
5. Maintains the core insights while advancing the overall quality
6. Adds new relevant scientific references (aim for 5-7 high-quality references)
7. Ensures all hallmarks demonstrate the highest scientific standards

Please format your response as a JSON object with the following structure:
{{
  "title": "Revised and improved hypothesis title",
  "description": "Enhanced detailed paragraph description with improved scientific reasoning",
  "experimental_validation": "Strengthened experimental validation plan with more rigorous methods, better controls, enhanced measurements, realistic timeline, and clearer expected outcomes",
  "theory_and_computation": "Enhanced theoretical frameworks, improved computational models, more sophisticated simulations, advanced mathematical analyses, or cutting-edge computational approaches",
  "hallmarks": {{
    "testability": "Enhanced paragraph explaining superior testability/falsifiability with specific measurable predictions",
    "specificity": "Enhanced paragraph explaining improved specificity and clarity with precise definitions", 
    "grounded_knowledge": "Enhanced paragraph explaining stronger grounding in established scientific knowledge with better integration",
    "predictive_power": "Enhanced paragraph explaining stronger predictive power and more significant novel insights",
    "parsimony": "Enhanced paragraph explaining how the revised hypothesis achieves greater elegance and simplicity"
  }},
  "references": [
    {{
      "citation": "Author, A. (Year). Title of paper. Journal Name, Volume(Issue), pages.",
      "annotation": "Detailed explanation of how this reference supports or advances the revised hypothesis"
    }}
  ],
  "revision_improvements": "Detailed explanation of the specific enhancements and improvements made in this revision"
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
                revised_hypothesis = json.loads(json_text)
                # Initialize feedback history if not present
                if "feedback_history" not in revised_hypothesis:
                    revised_hypothesis["feedback_history"] = []
                # Initialize notes if not present
                if "notes" not in revised_hypothesis:
                    revised_hypothesis["notes"] = ""
                return revised_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                revised_hypothesis = json.loads(cleaned_text)
                # Initialize feedback history if not present
                if "feedback_history" not in revised_hypothesis:
                    revised_hypothesis["feedback_history"] = []
                # Initialize notes if not present
                if "notes" not in revised_hypothesis:
                    revised_hypothesis["notes"] = ""
                return revised_hypothesis
                
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
                "revision_improvements": "N/A",
                "error": True,
                "raw_response": generated_text
            }
            
    except Exception as e:
        # Propagate the exception to trigger backoff
        print(f"Error in revise_hypothesis (will retry): {str(e)}")
        raise

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def generate_new_hypothesis(research_goal, previous_hypotheses, config, strategy_manager=None):
    """
    Generate a new hypothesis that is different from previous ones.
    
    Args:
        research_goal (str): The research goal or question
        previous_hypotheses (list): List of previously generated hypotheses
        config (dict): Configuration for the model API
        strategy_manager (HypothesisStrategyManager): Optional strategy manager for enhanced generation
        
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

{strategy_manager.get_strategy_prompt_additions() if strategy_manager else ""}

Please format your response as a JSON object with the following structure:
{{
  "title": "Hypothesis title",
  "description": "Detailed paragraph explanation of the hypothesis, its key predictions, and potential mechanisms",
  "experimental_validation": "Comprehensive experimental validation plan including specific methods, controls, measurements, timeline, and expected outcomes",
  "theory_and_computation": "Detailed description of theoretical frameworks, computational models, simulations, mathematical analyses, or computational approaches that could be developed to explore, predict, or validate this hypothesis",
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
                # Initialize notes for new hypotheses
                if "notes" not in new_hypothesis:
                    new_hypothesis["notes"] = ""
                return new_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                new_hypothesis = json.loads(cleaned_text)
                # Initialize feedback history for new hypotheses
                if "feedback_history" not in new_hypothesis:
                    new_hypothesis["feedback_history"] = []
                # Initialize notes for new hypotheses
                if "notes" not in new_hypothesis:
                    new_hypothesis["notes"] = ""
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
        
        # Ensure all loaded hypotheses have feedback_history and notes fields
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
            # Initialize notes if not present
            if "notes" not in hypothesis:
                hypothesis["notes"] = ""
        
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
    parser = argparse.ArgumentParser(description='Wisteria Research Hypothesis Generator v6.0 - Curses Multi-Pane Interface')
    
    # Create mutually exclusive group for goal input
    goal_group = parser.add_mutually_exclusive_group(required=False)
    goal_group.add_argument('research_goal_file', nargs='?', help='Text file containing the research goal')
    goal_group.add_argument('--goal', help='Research goal specified directly as text')
    
    parser.add_argument('--model', help='Model shortname from model_servers.yaml')
    parser.add_argument('--config', help='Path to model_servers.yaml file (default: model_servers.yaml in script directory)')
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
    
    # Show initial status
    interface.draw_header(research_goal, model_config['model_name'])
    interface.header_win.refresh()  # Force refresh for startup
    interface.draw_status_bar("Initializing Wisteria interface...")
    interface.status_win.refresh()  # Force refresh for startup
    stdscr.refresh()
    
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
        
        # Start with the first hypothesis (for consistent behavior)
        interface.current_hypothesis_idx = 0
        interface.focus_pane = "list"  # Ensure focus is on hypothesis list
        
        # Show loading status for resumed session
        interface.draw_status_bar("Loading resumed session... Press any key when ready.")
        interface.status_win.refresh()  # Force refresh for startup
        stdscr.refresh()
        
    else:
        all_hypotheses = []
        hypothesis_counter = 0
        version_tracker = {}
        
        # Show preparation status
        interface.draw_status_bar(f"Preparing to generate {num_initial_hypotheses} hypothesis{'es' if num_initial_hypotheses > 1 else ''}...")
        interface.status_win.refresh()  # Force refresh for startup
        stdscr.refresh()
        
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
                    interface.status_win.refresh()
                    interface.stdscr.refresh()
                    time.sleep(0.3)  # Update animation every 300ms
                    animation_counter += 1
                
                # Wait for thread to complete
                generation_thread.join()
                
                # Handle results
                if generation_error:
                    raise generation_error
                
                initial_hypotheses = []
                if generated_hypothesis and not generated_hypothesis[0].get("error"):
                    # Only take the first hypothesis to be consistent with multi-hypothesis case
                    initial_hypotheses.append(generated_hypothesis[0])
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
                        interface.status_win.refresh()
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
                        # Only take the first hypothesis from the list to avoid duplicates
                        initial_hypotheses.append(single_hypothesis[0])
                        # Show completion for this hypothesis
                        completed_msg = f"Hypothesis {i+1}/{num_initial_hypotheses} completed! [{bar}]"
                        interface.draw_status_bar(completed_msg)
                        interface.stdscr.refresh()
                        time.sleep(0.5)  # Brief pause to show completion
                    elif single_hypothesis:
                        # Log error but continue with other hypotheses
                        error_msg = f"Error in hypothesis {i+1}: {single_hypothesis[0].get('error', 'Unknown error')}"
                        interface.draw_status_bar(error_msg)
                        interface.status_win.refresh()
                        interface.stdscr.refresh()
                        time.sleep(1)
                    else:
                        # Show error but continue with others
                        error_msg = f"Error generating hypothesis {i+1}, continuing..."
                        interface.draw_status_bar(error_msg)
                        interface.status_win.refresh()
                        interface.stdscr.refresh()
                        time.sleep(1)  # Brief pause to show error
                        
                except Exception as e:
                    # Show error but continue with others
                    error_msg = f"Error on hypothesis {i+1}: {str(e)[:30]}"
                    interface.draw_status_bar(error_msg)
                    interface.status_win.refresh()
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
        
        # Debug: verify hypothesis count
        interface.draw_status_bar(f"Processing {len(initial_hypotheses)} generated hypotheses...")
        interface.stdscr.refresh()
        time.sleep(0.5)
        
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
    
    # Main curses loop - improved for performance
    # Use longer timeout to reduce busy waiting and improve responsiveness
    stdscr.timeout(200)  # 200ms timeout for better responsiveness
    
    waiting_for_feedback = False
    feedback_input = ""
    
    # Force initial draw
    interface.mark_dirty("all")
    
    # Get current hypothesis for initial display
    current_hypothesis = None
    if all_hypotheses:
        # Simple approach: just get the first hypothesis for initial display
        current_hypothesis = all_hypotheses[0] if all_hypotheses else None
        # Ensure focus is on list pane and cursor on first hypothesis
        interface.current_hypothesis_idx = 0
        interface.focus_pane = "list"
    
    # Draw the complete interface immediately after generation
    try:
        # Force all components to be marked as dirty so they will actually draw
        interface.dirty_header = True
        interface.dirty_list = True
        interface.dirty_details = True
        interface.dirty_status = True
        
        # Draw all components
        interface.draw_header(research_goal, model_config['model_name'])
        interface.draw_hypothesis_list(all_hypotheses)
        interface.draw_hypothesis_details(current_hypothesis)
        interface.draw_status_bar("Ready to explore - press any key for commands")
        
        # Refresh all windows
        interface.header_win.refresh()
        interface.list_win.refresh()
        interface.detail_win.refresh()
        interface.status_win.refresh()
        stdscr.refresh()
        
    except Exception as e:
        # If initial draw fails, show error but continue
        interface.draw_status_bar(f"Display error: {str(e)[:50]}")
        interface.status_win.refresh()
        stdscr.refresh()
        time.sleep(3)  # Give time to see the error
    
    while True:
        try:
            # Handle terminal resize
            new_height, new_width = stdscr.getmaxyx()
            if new_height != interface.height or new_width != interface.width:
                interface.handle_resize()
                interface.mark_dirty("all")
            
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
            
            # Check for changes and mark dirty components
            interface.check_changes(all_hypotheses, interface.current_hypothesis_idx, current_hypothesis)
            
            # Draw interface only if needed
            if waiting_for_feedback:
                interface.draw_interface_selective(research_goal, model_config['model_name'], 
                                                 all_hypotheses, current_hypothesis, 
                                                 f"Enter feedback: {feedback_input}")
            else:
                interface.draw_interface_selective(research_goal, model_config['model_name'], 
                                                 all_hypotheses, current_hypothesis)
            
            # Single refresh for all windows
            stdscr.refresh()
            
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
                                
                                # Process improvement using TaskQueue
                                def improve_task():
                                    return improve_hypothesis(
                                        research_goal, current_hypothesis, feedback_input.strip(), model_config, interface.strategy_manager
                                    )
                                
                                def improve_callback(task):
                                    try:
                                        if task.status == TaskStatus.COMPLETED:
                                            improved_hypothesis = task.result
                                            
                                            if improved_hypothesis.get("error"):
                                                interface.draw_status_bar("Error improving hypothesis")
                                                interface.status_win.refresh()
                                                stdscr.refresh()
                                            else:
                                                # Add improved hypothesis
                                                nonlocal hypothesis_counter, version_tracker
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
                                                
                                                # Copy notes from current hypothesis
                                                improved_hypothesis["notes"] = current_hypothesis.get("notes", "")
                                                
                                                improved_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                                                all_hypotheses.append(improved_hypothesis)
                                                interface.draw_status_bar("Hypothesis improved!")
                                                interface.status_win.refresh()
                                                # Force refresh of all panes to show updated hypothesis
                                                interface.dirty_list = True
                                                interface.dirty_details = True
                                                interface.draw_hypothesis_list(all_hypotheses)
                                                interface.draw_hypothesis_details(improved_hypothesis)
                                                interface.list_win.refresh()
                                                interface.detail_win.refresh()
                                                stdscr.refresh()
                                        else:
                                            # Task failed
                                            error_msg = str(task.error)[:50] if task.error else "Unknown error"
                                            interface.draw_status_bar(f"Error: {error_msg}")
                                            interface.status_win.refresh()
                                            stdscr.refresh()
                                    except Exception as e:
                                        interface.draw_status_bar(f"Error: {str(e)[:50]}")
                                        interface.status_win.refresh()
                                        stdscr.refresh()
                                
                                # Submit task to queue
                                interface.task_queue.submit_task(
                                    "Improve Hypothesis",
                                    improve_task,
                                    priority=TaskPriority.HIGH,
                                    callback=improve_callback
                                )
                                
                                feedback_input = ""
                            else:
                                waiting_for_feedback = False
                                interface.draw_status_bar("Feedback cancelled")
                                interface.status_win.refresh()
                                stdscr.refresh()
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
                            # Debug: confirm q command is reached
                            interface.draw_status_bar("Quitting application...")
                            interface.status_win.refresh()
                            stdscr.refresh()
                            time.sleep(1)
                            break
                        elif key == curses.KEY_HOME or key == ord('g') or key == ord('G'):
                            # Home key - return to main display and reset view
                            interface.clear_status_on_action()
                            interface.focus_pane = "list"
                            interface.list_scroll_offset = 0
                            interface.detail_scroll_offset = 0
                            interface.current_hypothesis_idx = 0
                            interface.show_hallmarks = True
                            interface.show_references = True
                            interface.mark_dirty("all")
                            interface.set_status("Returned to main display (Home)")
                            stdscr.refresh()
                        elif key == ord('f') or key == ord('F'):
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                waiting_for_feedback = True
                                feedback_input = ""
                                interface.draw_status_bar("Enter feedback (Enter to submit, ESC to cancel)")
                                interface.status_win.refresh()
                                stdscr.refresh()
                            else:
                                interface.draw_status_bar("No hypothesis selected")
                                interface.status_win.refresh()
                                stdscr.refresh()
                        elif key == ord('n') or key == ord('N'):
                            interface.clear_status_on_action()
                            
                            # Generate new hypothesis using TaskQueue
                            def generate_task():
                                return generate_new_hypothesis(research_goal, all_hypotheses, model_config, interface.strategy_manager)
                            
                            def generate_callback(task):
                                try:
                                    if task.status == TaskStatus.COMPLETED:
                                        new_hypothesis = task.result
                                        
                                        if new_hypothesis.get("error"):
                                            interface.draw_status_bar("Error generating new hypothesis")
                                            interface.status_win.refresh()
                                            stdscr.refresh()
                                        else:
                                            nonlocal hypothesis_counter, version_tracker
                                            hypothesis_counter += 1
                                            version_tracker[hypothesis_counter] = 0
                                            new_hypothesis["hypothesis_number"] = hypothesis_counter
                                            new_hypothesis["version"] = "1.0"
                                            new_hypothesis["type"] = "new_alternative"
                                            new_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                                            all_hypotheses.append(new_hypothesis)
                                            interface.current_hypothesis_idx = hypothesis_counter - 1
                                            
                                            interface.draw_status_bar("New hypothesis generated!")
                                            interface.status_win.refresh()
                                            # Force refresh of list and details panes to show new hypothesis
                                            interface.dirty_list = True
                                            interface.dirty_details = True
                                            interface.draw_hypothesis_list(all_hypotheses)
                                            interface.draw_hypothesis_details(new_hypothesis)
                                            interface.list_win.refresh()
                                            interface.detail_win.refresh()
                                            stdscr.refresh()
                                    else:
                                        # Task failed
                                        error_msg = str(task.error)[:50] if task.error else "Unknown error"
                                        interface.draw_status_bar(f"Error: {error_msg}")
                                        interface.status_win.refresh()
                                        stdscr.refresh()
                                except Exception as e:
                                    interface.draw_status_bar(f"Error: {str(e)[:50]}")
                                    interface.status_win.refresh()
                                    stdscr.refresh()
                            
                            # Submit task to queue
                            interface.task_queue.submit_task(
                                "Generate New Hypothesis",
                                generate_task,
                                priority=TaskPriority.MEDIUM,
                                callback=generate_callback
                            )
                                
                        elif key == ord('h') or key == ord('H'):
                            interface.clear_status_on_action()
                            interface.show_hallmarks = not interface.show_hallmarks
                            status = "enabled" if interface.show_hallmarks else "disabled"
                            interface.draw_status_bar(f"Hallmarks display {status}")
                            interface.status_win.refresh()
                            # Force redraw of details pane to show/hide hallmarks
                            interface.dirty_details = True
                            interface.draw_hypothesis_details(current_hypothesis)
                            interface.detail_win.refresh()
                            stdscr.refresh()
                            
                        elif key == ord('r') or key == ord('R'):
                            interface.clear_status_on_action()
                            interface.show_references = not interface.show_references
                            status = "enabled" if interface.show_references else "disabled"
                            interface.draw_status_bar(f"References display {status}")
                            interface.status_win.refresh()
                            # Force redraw of details pane to show/hide references
                            interface.dirty_details = True
                            interface.draw_hypothesis_details(current_hypothesis)
                            interface.detail_win.refresh()
                            stdscr.refresh()
                            
                        elif key == ord('u') or key == ord('U'):
                            # Update hypothesis with abstracts
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                # Update hypothesis using TaskQueue
                                def update_task():
                                    return update_hypothesis_with_abstracts(current_hypothesis, model_config)
                                
                                def update_callback(task):
                                    try:
                                        if task.status == TaskStatus.COMPLETED:
                                            updated_hypothesis = task.result
                                            
                                            if "error" in updated_hypothesis:
                                                interface.set_status(f"Update error: {updated_hypothesis['error']}")
                                            else:
                                                # Add updated hypothesis to the list
                                                nonlocal hypothesis_counter, version_tracker
                                                hypothesis_number = current_hypothesis["hypothesis_number"]
                                                
                                                # The update function already increments the version
                                                all_hypotheses.append(updated_hypothesis)
                                                
                                                # Update version tracker
                                                current_version = updated_hypothesis.get('version', '1.1')
                                                try:
                                                    version_parts = current_version.split('.')
                                                    if len(version_parts) >= 2:
                                                        minor_version = int(version_parts[1])
                                                        version_tracker[hypothesis_number] = minor_version
                                                except:
                                                    pass
                                                
                                                # Set update metadata
                                                updated_hypothesis["hypothesis_number"] = hypothesis_number
                                                updated_hypothesis["type"] = "improvement"
                                                updated_hypothesis["original_hypothesis_id"] = hypothesis_number
                                                
                                                interface.set_status(f"Hypothesis updated with {updated_hypothesis.get('abstracts_used', 0)} abstracts!")
                                                
                                                # Force refresh of all panes
                                                interface.dirty_list = True
                                                interface.dirty_details = True
                                                interface.draw_hypothesis_list(all_hypotheses)
                                                interface.draw_hypothesis_details(updated_hypothesis)
                                                interface.list_win.refresh()
                                                interface.detail_win.refresh()
                                                stdscr.refresh()
                                        else:
                                            # Task failed
                                            error_msg = str(task.error)[:50] if task.error else "Unknown error"
                                            interface.set_status(f"Update error: {error_msg}")
                                    except Exception as e:
                                        interface.set_status(f"Update error: {str(e)[:50]}")
                                
                                # Submit task to queue
                                interface.task_queue.submit_task(
                                    "Update with Abstracts",
                                    update_task,
                                    priority=TaskPriority.HIGH,
                                    callback=update_callback
                                )
                            else:
                                interface.set_status("No hypothesis selected for updating")
                            
                        elif key == ord('c') or key == ord('C'):
                            # Score hypothesis hallmarks
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                # Score hypothesis using TaskQueue
                                def score_task():
                                    return score_hypothesis_hallmarks(current_hypothesis, model_config)
                                
                                def score_callback(task):
                                    try:
                                        if task.status == TaskStatus.COMPLETED:
                                            scoring_result = task.result
                                            
                                            if "error" in scoring_result:
                                                interface.set_status(f"Scoring error: {scoring_result['error']}")
                                            else:
                                                # Store scoring results in the hypothesis
                                                hyp_num = current_hypothesis.get("hypothesis_number", 0)
                                                total_score = scoring_result.get('total_score', 0)
                                                
                                                # Update all versions of this hypothesis with the scoring
                                                for hyp in all_hypotheses:
                                                    if hyp.get("hypothesis_number") == hyp_num:
                                                        hyp["hallmark_scores"] = scoring_result
                                                
                                                # Display the results briefly
                                                interface.set_status(f"Hallmarks scored! Total: {total_score}/25")
                                                
                                                # Force refresh of all panes to show updated scoring
                                                interface.dirty_list = True
                                                interface.dirty_details = True
                                                interface.draw_hypothesis_list(all_hypotheses)
                                                interface.draw_hypothesis_details(current_hypothesis)
                                                interface.list_win.refresh()
                                                interface.detail_win.refresh()
                                                stdscr.refresh()
                                        else:
                                            # Task failed
                                            error_msg = str(task.error)[:50] if task.error else "Unknown error"
                                            interface.set_status(f"Scoring error: {error_msg}")
                                    except Exception as e:
                                        interface.set_status(f"Scoring error: {str(e)[:50]}")
                                
                                # Submit task to queue
                                interface.task_queue.submit_task(
                                    "Score Hypothesis",
                                    score_task,
                                    priority=TaskPriority.MEDIUM,
                                    callback=score_callback
                                )
                            else:
                                interface.set_status("No hypothesis selected for scoring")
                            
                        elif key == ord('z') or key == ord('Z'):
                            # Batch score all hypotheses
                            interface.clear_status_on_action()
                            if not all_hypotheses:
                                interface.set_status("No hypotheses available for batch scoring")
                            else:
                                # Get unique hypothesis numbers
                                hypothesis_groups = {}
                                for hyp in all_hypotheses:
                                    hyp_num = hyp.get("hypothesis_number", 0)
                                    if hyp_num not in hypothesis_groups:
                                        hypothesis_groups[hyp_num] = []
                                    hypothesis_groups[hyp_num].append(hyp)
                                
                                # Get latest version of each hypothesis for scoring
                                hypotheses_to_score = []
                                for hyp_num, hyp_versions in hypothesis_groups.items():
                                    latest_version = max(hyp_versions, key=lambda h: h.get("version", "1.0"))
                                    hypotheses_to_score.append(latest_version)
                                
                                # Show progress operation
                                operation_id = f"batch_score_{time.time()}"
                                interface.add_progress_operation(operation_id, "scoring", len(hypotheses_to_score), "Batch scoring all hypotheses")
                                stdscr.refresh()
                                
                                # Score hypotheses in background thread
                                def batch_score_thread():
                                    try:
                                        scored_count = 0
                                        total_count = len(hypotheses_to_score)
                                        
                                        for i, hyp_to_score in enumerate(hypotheses_to_score):
                                            # Update progress
                                            interface.update_progress_operation(operation_id, i + 1, f"Scoring hypothesis {i+1}/{total_count}")
                                            
                                            scoring_result = score_hypothesis_hallmarks(hyp_to_score, model_config)
                                            
                                            if "error" not in scoring_result:
                                                # Store scoring results in all versions of this hypothesis
                                                hyp_num = hyp_to_score.get("hypothesis_number", 0)
                                                for hyp in all_hypotheses:
                                                    if hyp.get("hypothesis_number") == hyp_num:
                                                        hyp["hallmark_scores"] = scoring_result
                                                scored_count += 1
                                        
                                        interface.remove_progress_operation(operation_id)
                                        interface.set_status(f"Batch scoring complete! Scored {scored_count}/{total_count} hypotheses")
                                        
                                        # Force refresh of all panes to show updated scoring
                                        interface.dirty_list = True
                                        interface.dirty_details = True
                                        interface.draw_hypothesis_list(all_hypotheses)
                                        if current_hypothesis:
                                            interface.draw_hypothesis_details(current_hypothesis)
                                        interface.list_win.refresh()
                                        interface.detail_win.refresh()
                                        stdscr.refresh()
                                        
                                    except Exception as e:
                                        interface.remove_progress_operation(operation_id)
                                        interface.set_status(f"Batch scoring error: {str(e)[:50]}")
                                
                                # Start batch scoring in background
                                score_thread = threading.Thread(target=batch_score_thread)
                                score_thread.daemon = True
                                score_thread.start()
                            
                        elif key == ord('b') or key == ord('B'):
                            # Browse and view downloaded abstracts
                            interface.clear_status_on_action()
                            browse_abstracts_interface(stdscr, interface)
                            # Force full redraw after returning from abstract browser
                            interface.mark_dirty("all")
                            
                        elif key == ord('w') or key == ord('W'):
                            # Hypothesis generation strategies selection
                            interface.clear_status_on_action()
                            strategy_selection_interface(stdscr, interface)
                            # Force full redraw after returning from strategy selection
                            interface.mark_dirty("all")
                            
                        elif key == ord('a') or key == ord('A'):
                            # Fetch abstracts and papers for current hypothesis
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                # Generate session name based on current time and model
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                model_name = model_config.get('model_name', 'unknown_model')
                                session_name = f"papers_{model_name}_{timestamp}"
                                
                                # Fetch papers using TaskQueue
                                def fetch_task():
                                    return fetch_papers_for_hypothesis(current_hypothesis, session_name, interface)
                                
                                def fetch_callback(task):
                                    try:
                                        if task.status == TaskStatus.COMPLETED:
                                            results = task.result
                                            
                                            if results["status"] == "no_references":
                                                interface.set_status("No references found in current hypothesis")
                                            elif results["status"] == "success":
                                                fetched_count = len(results["fetched"])
                                                failed_count = len(results["failed"])
                                                if fetched_count > 0:
                                                    # Show brief directory name instead of full path
                                                    dir_name = os.path.basename(results['papers_dir'])
                                                    interface.set_status(f"✓ Papers fetched: {fetched_count} succeeded, {failed_count} failed → papers/{dir_name}/")
                                                else:
                                                    interface.set_status(f"Papers fetch completed: 0 succeeded, {failed_count} failed")
                                            else:
                                                interface.set_status(f"Papers fetch error: {results.get('message', 'Unknown error')}")
                                        else:
                                            # Task failed
                                            error_msg = str(task.error)[:50] if task.error else "Unknown error"
                                            interface.set_status(f"Papers fetch error: {error_msg}")
                                        
                                        # Force a refresh to show the result
                                        interface.draw_status_bar()
                                        interface.status_win.refresh()
                                        stdscr.refresh()
                                    except Exception as e:
                                        interface.set_status(f"Error: {str(e)[:50]}")
                                        interface.draw_status_bar()
                                        interface.status_win.refresh()
                                        stdscr.refresh()
                                
                                # Submit task to queue
                                interface.task_queue.submit_task(
                                    "Fetch Papers",
                                    fetch_task,
                                    priority=TaskPriority.LOW,
                                    callback=fetch_callback
                                )
                            else:
                                interface.draw_status_bar("No hypothesis selected")
                                interface.status_win.refresh()
                                stdscr.refresh()
                            
                        elif key == ord('l') or key == ord('L'):
                            # Load session - prompt for filename
                            interface.draw_status_bar("Enter filename to load (ESC to cancel):")
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
                            
                        elif key == ord('x') or key == ord('X'):
                            # Save session - prompt for filename
                            interface.draw_status_bar("Enter filename to save (ESC to cancel):")
                            stdscr.refresh()
                            
                            # Get filename input
                            filename_input = ""
                            saving_mode = True
                            
                            while saving_mode:
                                key_save = stdscr.getch()
                                if key_save == 27:  # ESC
                                    interface.set_status("Save cancelled")
                                    saving_mode = False
                                elif key_save == ord('\n') or key_save == curses.KEY_ENTER or key_save == 10:
                                    if filename_input.strip():
                                        # Try to save the session
                                        interface.set_status("Saving session...")
                                        interface.draw_status_bar()
                                        stdscr.refresh()
                                        
                                        save_filename = filename_input.strip()
                                        # Add .json extension if not present
                                        if not save_filename.endswith('.json'):
                                            save_filename += '.json'
                                        
                                        try:
                                            # Construct metadata for save
                                            unique_hypothesis_numbers = set()
                                            for hyp in all_hypotheses:
                                                unique_hypothesis_numbers.add(hyp.get("hypothesis_number", 0))
                                            
                                            metadata = {
                                                "session_type": "interactive",
                                                "research_goal": research_goal,
                                                "model": model_config.get('model_name', 'unknown'),
                                                "model_name": model_config.get('model_name', 'unknown'),
                                                "num_unique_hypotheses": len(unique_hypothesis_numbers),
                                                "total_hypothesis_versions": len(all_hypotheses),
                                                "timestamp": datetime.now().isoformat(),
                                                "hypothesis_types": {
                                                    "original": len([h for h in all_hypotheses if h.get("type") == "original"]),
                                                    "improvements": len([h for h in all_hypotheses if h.get("type") == "improvement"]),
                                                    "new_alternatives": len([h for h in all_hypotheses if h.get("type") == "new_alternative"])
                                                }
                                            }
                                            
                                            save_hypotheses_to_json(all_hypotheses, save_filename, metadata)
                                            interface.set_status(f"Session saved successfully to {save_filename}")
                                        except Exception as e:
                                            interface.set_status(f"Save error: {str(e)[:50]}")
                                            import traceback
                                            traceback.print_exc()  # For debugging
                                    else:
                                        interface.set_status("Save cancelled - no filename provided")
                                    saving_mode = False
                                elif key_save == curses.KEY_BACKSPACE or key_save == 127 or key_save == 8:
                                    if filename_input:
                                        filename_input = filename_input[:-1]
                                        interface.draw_status_bar(f"Enter filename: {filename_input}")
                                        stdscr.refresh()
                                elif 32 <= key_save <= 126:  # Printable characters
                                    filename_input += chr(key_save)
                                    interface.draw_status_bar(f"Enter filename: {filename_input}")
                                    stdscr.refresh()
                            
                        elif key == ord('t') or key == ord('T'):
                            # Notes - simple single-line editor in status bar
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                current_notes = current_hypothesis.get("notes", "")
                                interface.draw_status_bar("Enter notes (Enter to save, ESC to cancel):")
                                stdscr.refresh()
                                
                                # Get notes input
                                notes_input = current_notes
                                notes_editing = True
                                
                                while notes_editing:
                                    # Show current input
                                    display_input = notes_input if len(notes_input) <= 60 else "..." + notes_input[-57:]
                                    interface.draw_status_bar(f"Notes: {display_input}")
                                    interface.status_win.refresh()
                                    stdscr.refresh()
                                    
                                    key_notes = stdscr.getch()
                                    if key_notes == 27:  # ESC
                                        interface.set_status("Notes editing cancelled")
                                        notes_editing = False
                                    elif key_notes == ord('\n') or key_notes == curses.KEY_ENTER or key_notes == 10:
                                        # Save notes to current hypothesis and all versions with same number
                                        hyp_num = current_hypothesis["hypothesis_number"]
                                        for hyp in all_hypotheses:
                                            if hyp.get("hypothesis_number") == hyp_num:
                                                hyp["notes"] = notes_input.strip()
                                        
                                        interface.draw_status_bar(f"Notes saved for hypothesis #{hyp_num}")
                                        interface.status_win.refresh()
                                        stdscr.refresh()
                                        notes_editing = False
                                    elif key_notes == curses.KEY_BACKSPACE or key_notes == 127 or key_notes == 8:
                                        if notes_input:
                                            notes_input = notes_input[:-1]
                                    elif 32 <= key_notes <= 126:  # Printable characters
                                        notes_input += chr(key_notes)
                            else:
                                interface.draw_status_bar("No hypothesis selected for notes")
                                interface.status_win.refresh()
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
                                
                                interface.draw_status_bar(f"Enter hypothesis number ({min(available_numbers)}-{max(available_numbers)}, ESC to cancel):")
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
                                        
                        elif key == ord('o') or key == ord('O'):
                            # Sort hypothesis list by score
                            interface.clear_status_on_action()
                            interface.sort_mode = "score"
                            interface.set_status("Sorted by score (highest first)")
                            # Force refresh of hypothesis list
                            interface.dirty_list = True
                            interface.draw_hypothesis_list(all_hypotheses)
                            interface.list_win.refresh()
                            stdscr.refresh()
                            
                        elif key == ord('1'):
                            # Sort hypothesis list by numerical order (default)
                            interface.clear_status_on_action()
                            interface.sort_mode = "numerical"
                            interface.set_status("Sorted by numerical order")
                            # Force refresh of hypothesis list
                            interface.dirty_list = True
                            interface.draw_hypothesis_list(all_hypotheses)
                            interface.list_win.refresh()
                            stdscr.refresh()
                            
                        elif key == ord('g') or key == ord('G'):
                            # Generate revised hypothesis version from current one
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                # Show progress operation
                                operation_id = f"revise_{time.time()}"
                                interface.add_progress_operation(operation_id, "revising", 1, "Generating revised hypothesis version")
                                stdscr.refresh()
                                
                                # Revise hypothesis in background thread
                                def revise_thread():
                                    try:
                                        revised_hypothesis = revise_hypothesis(
                                            research_goal, current_hypothesis, model_config
                                        )
                                        
                                        interface.remove_progress_operation(operation_id)
                                        
                                        if revised_hypothesis.get("error"):
                                            interface.set_status("Error generating revised hypothesis")
                                        else:
                                            # Add revised hypothesis
                                            nonlocal hypothesis_counter, version_tracker
                                            hypothesis_number = current_hypothesis["hypothesis_number"]
                                            version_tracker[hypothesis_number] += 1
                                            revised_hypothesis["hypothesis_number"] = hypothesis_number
                                            revised_hypothesis["version"] = f"1.{version_tracker[hypothesis_number]}"
                                            revised_hypothesis["type"] = "revision"
                                            revised_hypothesis["original_hypothesis_id"] = current_hypothesis.get("hypothesis_number")
                                            revised_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                                            
                                            # Initialize or copy feedback history
                                            feedback_history = current_hypothesis.get("feedback_history", [])
                                            revision_entry = {
                                                "revision_type": "automated_improvement",
                                                "timestamp": datetime.now().isoformat(),
                                                "version_before": current_hypothesis.get("version", "1.0"),
                                                "version_after": f"1.{version_tracker[hypothesis_number]}",
                                                "improvements": revised_hypothesis.get("revision_improvements", "General revision and improvement")
                                            }
                                            feedback_history.append(revision_entry)
                                            revised_hypothesis["feedback_history"] = feedback_history
                                            
                                            # Copy notes from current hypothesis
                                            revised_hypothesis["notes"] = current_hypothesis.get("notes", "")
                                            
                                            all_hypotheses.append(revised_hypothesis)
                                            interface.set_status("Revised hypothesis generated!")
                                            
                                            # Force refresh of all panes to show revised hypothesis
                                            interface.dirty_list = True
                                            interface.dirty_details = True
                                            interface.draw_hypothesis_list(all_hypotheses)
                                            interface.draw_hypothesis_details(revised_hypothesis)
                                            interface.list_win.refresh()
                                            interface.detail_win.refresh()
                                            stdscr.refresh()
                                            
                                    except Exception as e:
                                        interface.remove_progress_operation(operation_id)
                                        interface.set_status(f"Error: {str(e)[:50]}")
                                
                                # Start revision in background
                                revise_thread = threading.Thread(target=revise_thread)
                                revise_thread.daemon = True
                                revise_thread.start()
                            else:
                                interface.set_status("No hypothesis selected for revision")
                            
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
                                            interface.safe_addstr(stdscr, y_pos, 2, line_text, attr)
                                        y_pos += 1
                                        line_count += 1
                                    
                                    # Footer
                                    if y_pos < interface.height - 1:
                                        total_hypotheses = len(hypothesis_groups)
                                        footer = f"Showing {min(line_count, max_display_lines)} of {total_hypotheses} hypotheses"
                                        interface.safe_addstr(stdscr, interface.height - 2, 2, footer)
                                    
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
                            interface.mark_dirty("list")
                            interface.mark_dirty("details")
                            
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
                            interface.mark_dirty("list")
                            interface.mark_dirty("details")
                            
                        elif key == curses.KEY_LEFT:  # Switch focus to list pane
                            interface.clear_status_on_action()
                            if interface.focus_pane != "list":
                                interface.focus_pane = "list"
                                interface.draw_status_bar("Focus: Hypothesis List (↑↓ to navigate, j/k to scroll)")
                                interface.status_win.refresh()
                                interface.mark_dirty("list")
                                interface.mark_dirty("details")
                                stdscr.refresh()
                            
                        elif key == curses.KEY_RIGHT:  # Switch focus to details pane
                            interface.clear_status_on_action()
                            if interface.focus_pane != "details":
                                interface.focus_pane = "details"
                                interface.draw_status_bar("Focus: Hypothesis Details (j/k/d/u to scroll)")
                                interface.status_win.refresh()
                                interface.mark_dirty("list")
                                interface.mark_dirty("details")
                                stdscr.refresh()
                            
                        elif key == curses.KEY_PPAGE:  # Page Up - scroll focused pane up
                            if interface.focus_pane == "list":
                                interface.scroll_list(-5)
                            else:
                                interface.scroll_detail(-5)
                            
                        elif key == curses.KEY_NPAGE:  # Page Down - scroll focused pane down
                            if interface.focus_pane == "list":
                                interface.scroll_list(5)
                            else:
                                interface.scroll_detail(5)
                            
                        # Mac-friendly scrolling alternatives
                        elif key == ord('j') or key == ord('J'):  # j = scroll down (vim-style)
                            if interface.focus_pane == "list":
                                interface.scroll_list(1)
                            else:
                                interface.scroll_detail(1)
                            
                        elif key == ord('k') or key == ord('K'):  # k = scroll up (vim-style)
                            if interface.focus_pane == "list":
                                interface.scroll_list(-1)
                            else:
                                interface.scroll_detail(-1)
                            
                        elif key == ord('d') or key == ord('D'):  # d = scroll down faster
                            if interface.focus_pane == "list":
                                interface.scroll_list(5)
                            else:
                                interface.scroll_detail(5)
                            
                        elif key == ord('u') or key == ord('U'):  # u = scroll up faster
                            if interface.focus_pane == "list":
                                interface.scroll_list(-5)
                            else:
                                interface.scroll_detail(-5)
                            
                        elif key == ord('p') or key == ord('P'):  # p = print to PDF
                            interface.clear_status_on_action()
                            if current_hypothesis:
                                if PDF_AVAILABLE:
                                    interface.draw_status_bar("Generating PDF...")
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
    
    # Cleanup TaskQueue and threads
    interface.cleanup()
    
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
    
    research_goal = "Test the feedback tracking and PDF generation functionality in Wisteria v6.0"
    
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
    model_config = load_model_config(args.model, args.config)
    
    print(f"Wisteria Research Hypothesis Generator v6.0 - Curses Multi-Pane Interface")
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