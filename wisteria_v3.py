#!/usr/bin/env python3

"""
Wisteria Research Hypothesis Generator v3.0 - Interactive Mode

Usage:
    python wisteria_v3.py <research_goal_file.txt> --model <model_shortname> [--output <output_file.json>]
    python wisteria_v3.py --goal "<research_goal_text>" --model <model_shortname> [--output <output_file.json>]
    python wisteria_v3.py --resume <session_file.json> --model <model_shortname> [--output <output_file.json>]

Where:
    - research_goal_file.txt: A text file containing the research goal/question
    - --goal: Specify the research goal directly as a command line argument
    - --resume: Resume from a previous session JSON file
    - model_shortname: The shortname of the model to use from model_servers.yaml
    - output: Output JSON file for the hypotheses (default: hypotheses_<timestamp>.json)

Examples:
    python wisteria_v3.py research_goal.txt --model gpt41
    python wisteria_v3.py --goal "How can we improve renewable energy storage efficiency?" --model scout
    python wisteria_v3.py --resume hypotheses_interactive_gpt41_20250531_165238.json --model gpt41
    python wisteria_v3.py --goal "What causes neurodegenerative diseases?" --model gpt41 --output my_hypotheses.json

The script:
1) Reads a research goal from a text file OR accepts it directly via --goal argument OR resumes from a previous session
2) Uses the specified MODEL to generate creative and novel hypotheses interactively
3) For each hypothesis:
   - Presents it to the user with title, description, and hallmarks analysis
   - Requests user feedback for improvement
   - Uses feedback to refine the hypothesis
   - Allows user to generate new hypotheses or quit
4) Interactive commands during session:
   - \\f - Provide feedback to improve the current hypothesis
   - \\n - Generate a new hypothesis different from previous ones
   - \\l - Load from a JSON file a previous session log
   - \\v - View the titles of hypotheses in current session
   - \\s - Select a hypothesis to continue to refine
   - \\q - Quit and save all hypotheses
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
# Color and Diff utilities
# ---------------------------------------------------------------------

class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'  # Added text
    RED = '\033[91m'    # Removed text
    YELLOW = '\033[93m' # Changed text
    BLUE = '\033[94m'   # Unchanged text
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
3. ANALYSIS: Evaluate the hypothesis against each of the five hallmarks of strong scientific hypotheses:

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
  "hallmarks": {{
    "testability": "Paragraph explaining how this hypothesis satisfies testability/falsifiability",
    "specificity": "Paragraph explaining how this hypothesis satisfies specificity and clarity",
    "grounded_knowledge": "Paragraph explaining how this hypothesis is grounded in prior knowledge",
    "predictive_power": "Paragraph explaining the predictive power and novel insights",
    "parsimony": "Paragraph explaining how this hypothesis follows the principle of simplicity"
  }}
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

def display_single_hypothesis(hypothesis, hypothesis_number, previous_hypothesis=None):
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
        print(f"{Colors.GREEN}Changes from feedback are highlighted in green{Colors.RESET}")
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
    print("\\q - Quit and save all hypotheses")
    print("-" * 60)
    
    while True:
        choice = input("\nEnter your choice (\\f, \\n, \\l, \\v, \\s, or \\q): ").strip()
        
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
            
        elif choice == "\\q":
            return "QUIT"
            
        else:
            print("Invalid choice. Please enter \\f, \\n, \\l, \\v, \\s, or \\q.")

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

USER FEEDBACK:
{user_feedback}

Please provide an improved version of this hypothesis that:
1. Addresses the specific concerns and suggestions in the user feedback
2. Maintains or enhances scientific rigor and testability
3. Keeps the core innovative insights while making requested improvements
4. Ensures the hypothesis remains relevant to the original research goal

Please format your response as a JSON object with the following structure:
{{
  "title": "Improved hypothesis title",
  "description": "Detailed paragraph description incorporating the feedback",
  "hallmarks": {{
    "testability": "Paragraph explaining how this improved hypothesis satisfies testability/falsifiability",
    "specificity": "Paragraph explaining how this improved hypothesis satisfies specificity and clarity", 
    "grounded_knowledge": "Paragraph explaining how this improved hypothesis is grounded in prior knowledge",
    "predictive_power": "Paragraph explaining the predictive power and novel insights",
    "parsimony": "Paragraph explaining how this improved hypothesis follows the principle of simplicity"
  }},
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
                return improved_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                improved_hypothesis = json.loads(cleaned_text)
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

Please format your response as a JSON object with the following structure:
{{
  "title": "Hypothesis title",
  "description": "Detailed paragraph explanation of the hypothesis, its key predictions, and potential mechanisms",
  "hallmarks": {{
    "testability": "Paragraph explaining how this hypothesis satisfies testability/falsifiability",
    "specificity": "Paragraph explaining how this hypothesis satisfies specificity and clarity",
    "grounded_knowledge": "Paragraph explaining how this hypothesis is grounded in prior knowledge",
    "predictive_power": "Paragraph explaining the predictive power and novel insights",
    "parsimony": "Paragraph explaining how this hypothesis follows the principle of simplicity"
  }}
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
                return new_hypothesis
            else:
                # Fallback: try to parse the entire response as JSON
                cleaned_text = clean_json_string(generated_text)
                new_hypothesis = json.loads(cleaned_text)
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
    parser = argparse.ArgumentParser(description='Wisteria Research Hypothesis Generator v3.0 - Interactive Mode')
    
    # Create mutually exclusive group for goal input
    goal_group = parser.add_mutually_exclusive_group(required=False)
    goal_group.add_argument('research_goal_file', nargs='?', help='Text file containing the research goal')
    goal_group.add_argument('--goal', help='Research goal specified directly as text')
    
    parser.add_argument('--model', required=True, help='Model shortname from model_servers.yaml')
    parser.add_argument('--output', help='Output JSON file (default: hypotheses_<timestamp>.json)')
    parser.add_argument('--resume', help='Resume from a previous session JSON file')
    return parser.parse_args()

def interactive_hypothesis_session(research_goal, model_config, initial_hypotheses=None):
    """
    Run an interactive hypothesis generation and refinement session.
    
    Args:
        research_goal (str): The research goal or question
        model_config (dict): Configuration for the model API
        initial_hypotheses (list, optional): Previously loaded hypotheses to continue from
        
    Returns:
        list: All hypotheses generated during the session (including refinements)
    """
    if initial_hypotheses:
        all_hypotheses = initial_hypotheses.copy()
        # Determine the highest hypothesis number to continue counting
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
        
        print(f"\nResumed session with {len(all_hypotheses)} existing hypothesis versions")
        print("You can now generate new hypotheses or refine existing ones.")
        
        # Start with the most recent hypothesis
        current_hypothesis = max(all_hypotheses, key=lambda h: h.get("generation_timestamp", ""))
        
    else:
        all_hypotheses = []
        hypothesis_counter = 0
        # Track version numbers: {hypothesis_number: current_minor_version}
        version_tracker = {}
        
        print("\n" + "=" * 80)
        print("INTERACTIVE HYPOTHESIS GENERATION SESSION")
        print("=" * 80)
        print("Starting interactive mode. Commands:")
        print("- \\f - Provide feedback to improve hypotheses")
        print("- \\n - Generate new hypotheses different from previous ones")
        print("- \\l - Load from a JSON file a previous session log")
        print("- \\v - View the titles of hypotheses in current session")
        print("- \\s - Select a hypothesis to continue to refine")
        print("- \\q - Quit at any time to save all hypotheses")
        print("=" * 80)
        
        # Generate the first hypothesis
        print("\nGenerating your first hypothesis...")
        try:
            first_hypothesis = generate_hypotheses(research_goal, model_config, num_hypotheses=1)[0]
            if first_hypothesis.get("error"):
                print("Error generating first hypothesis. Exiting.")
                return []
            
            hypothesis_counter += 1
            version_tracker[hypothesis_counter] = 0  # Start at version 1.0
            first_hypothesis["hypothesis_number"] = hypothesis_counter
            first_hypothesis["version"] = "1.0"
            first_hypothesis["type"] = "original"
            first_hypothesis["generation_timestamp"] = datetime.now().isoformat()
            all_hypotheses.append(first_hypothesis)
            
        except Exception as e:
            print(f"Error generating first hypothesis: {e}")
            return []
        
        current_hypothesis = first_hypothesis
    
    previous_hypothesis_for_display = None
    
    # Main interactive loop
    while True:
        # Display current hypothesis (with highlighting if this is an improvement)
        if current_hypothesis:
            display_single_hypothesis(current_hypothesis, current_hypothesis["hypothesis_number"], previous_hypothesis_for_display)
        
        # Reset previous hypothesis after display
        previous_hypothesis_for_display = None
        
        # Get user feedback
        feedback = get_user_feedback(all_hypotheses, current_hypothesis)
        
        if feedback == "QUIT":
            print("\nThank you for your session! Saving all hypotheses...")
            break
            
        elif feedback == "GENERATE_NEW":
            print("\nGenerating a new hypothesis that's different from previous ones...")
            try:
                new_hypothesis = generate_new_hypothesis(research_goal, all_hypotheses, model_config)
                if new_hypothesis.get("error"):
                    print("Error generating new hypothesis. Please try again.")
                    continue
                
                hypothesis_counter += 1
                version_tracker[hypothesis_counter] = 0  # Start at version 1.0
                new_hypothesis["hypothesis_number"] = hypothesis_counter
                new_hypothesis["version"] = "1.0"
                new_hypothesis["type"] = "new_alternative"
                new_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                all_hypotheses.append(new_hypothesis)
                current_hypothesis = new_hypothesis
                
            except Exception as e:
                print(f"Error generating new hypothesis: {e}")
                print("Please try again.")
                continue
                
        elif feedback.startswith("LOAD_SESSION:"):
            filename = feedback[13:]  # Remove "LOAD_SESSION:" prefix
            loaded_goal, loaded_hypotheses, loaded_metadata = load_session_from_json(filename)
            
            if loaded_hypotheses:
                # Merge loaded hypotheses into current session
                for hyp in loaded_hypotheses:
                    if hyp not in all_hypotheses:  # Avoid duplicates
                        all_hypotheses.append(hyp)
                
                # Update research goal if it was loaded
                if loaded_goal and loaded_goal.strip():
                    research_goal = loaded_goal
                    print(f"Updated research goal: {research_goal}")
                
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
                current_hypothesis = max(all_hypotheses, key=lambda h: h.get("generation_timestamp", ""))
                print("Session loaded successfully!")
            else:
                print("Failed to load session. Continuing with current session.")
            continue
            
        elif feedback.startswith("SELECT_HYPOTHESIS:"):
            try:
                selected_num = int(feedback[18:])  # Remove "SELECT_HYPOTHESIS:" prefix
                
                # Find the latest version of the selected hypothesis
                hypothesis_groups = {}
                for hyp in all_hypotheses:
                    hyp_num = hyp.get("hypothesis_number", 0)
                    if hyp_num not in hypothesis_groups:
                        hypothesis_groups[hyp_num] = []
                    hypothesis_groups[hyp_num].append(hyp)
                
                if selected_num in hypothesis_groups:
                    latest_version = max(hypothesis_groups[selected_num], key=lambda h: h.get("version", "1.0"))
                    current_hypothesis = latest_version
                    print(f"Selected hypothesis #{selected_num} for refinement.")
                else:
                    print(f"Hypothesis #{selected_num} not found.")
                    
            except ValueError:
                print("Invalid hypothesis selection.")
            continue
                
        else:
            # User provided feedback to improve current hypothesis
            if not current_hypothesis:
                print("No hypothesis selected. Please select a hypothesis first or generate a new one.")
                continue
                
            print(f"\nImproving hypothesis based on your feedback...")
            
            # Store the previous version for comparison
            previous_hypothesis = current_hypothesis.copy()
            
            try:
                improved_hypothesis = improve_hypothesis(research_goal, current_hypothesis, feedback, model_config)
                if improved_hypothesis.get("error"):
                    print("Error improving hypothesis. Please try again.")
                    continue
                
                # Keep the same hypothesis number but increment version
                hypothesis_number = current_hypothesis["hypothesis_number"]
                version_tracker[hypothesis_number] += 1  # Increment minor version
                improved_hypothesis["hypothesis_number"] = hypothesis_number
                improved_hypothesis["version"] = f"1.{version_tracker[hypothesis_number]}"
                improved_hypothesis["type"] = "improvement"
                improved_hypothesis["original_hypothesis_id"] = current_hypothesis.get("hypothesis_number")
                improved_hypothesis["user_feedback"] = feedback
                improved_hypothesis["generation_timestamp"] = datetime.now().isoformat()
                all_hypotheses.append(improved_hypothesis)
                
                # Set up for displaying the improvement with highlighting
                previous_hypothesis_for_display = previous_hypothesis
                current_hypothesis = improved_hypothesis
                
                print("\nHypothesis improved! Here's the updated version with changes highlighted:")
                
                # Continue to next iteration where the improved hypothesis will be displayed with highlighting
                continue
                
            except Exception as e:
                print(f"Error improving hypothesis: {e}")
                print("Please try again.")
                continue
    
    return all_hypotheses

# ---------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------

def main():
    args = parse_arguments()
    
    # Load model config
    model_config = load_model_config(args.model)
    
    print(f"Wisteria Research Hypothesis Generator v3.0 - Interactive Mode")
    print(f"Using model: {args.model} ({model_config['model_name']})")
    
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
    
    # Run interactive session
    start_time = time.time()
    try:
        all_hypotheses = interactive_hypothesis_session(research_goal, model_config, initial_hypotheses)
    except KeyboardInterrupt:
        print("\n\nSession interrupted by user. Saving current hypotheses...")
        all_hypotheses = []
    except Exception as e:
        print(f"Failed to run interactive session: {e}")
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