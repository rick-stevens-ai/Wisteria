#!/usr/bin/env python3

"""
Wisteria Research Hypothesis Generator v1.0

Usage:
    python wisteria_v1.py <research_goal_file.txt> --model <model_shortname> [--num_hypotheses <number>] [--output <output_file.json>]
    python wisteria_v1.py --goal "<research_goal_text>" --model <model_shortname> [--num_hypotheses <number>] [--output <output_file.json>]

Where:
    - research_goal_file.txt: A text file containing the research goal/question
    - --goal: Specify the research goal directly as a command line argument
    - model_shortname: The shortname of the model to use from model_servers.yaml
    - num_hypotheses: Number of hypotheses to generate (default: 5)
    - output: Output JSON file for the hypotheses (default: hypotheses_<timestamp>.json)

Examples:
    python wisteria_v1.py research_goal.txt --model gpt41 --num_hypotheses 8
    python wisteria_v1.py --goal "How can we improve renewable energy storage efficiency?" --model scout
    python wisteria_v1.py --goal "What causes neurodegenerative diseases?" --model gpt41 --output my_hypotheses.json

The script:
1) Reads a research goal from a text file OR accepts it directly via --goal argument
2) Uses the specified MODEL to generate creative and novel hypotheses
3) Each hypothesis includes:
   - An overarching title
   - A paragraph description
   - Analysis against five scientific hypothesis hallmarks
4) Outputs results to console and JSON file
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

# ---------------------------------------------------------------------
# Helper functions (from argonium_score_parallel_v9.py)
# ---------------------------------------------------------------------

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
                hypotheses = json.loads(json_text)
                return hypotheses
            else:
                # Fallback: try to parse the entire response as JSON
                hypotheses = json.loads(generated_text)
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
            
        print(f"\nHYPOTHESIS {i}")
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

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Wisteria Research Hypothesis Generator')
    
    # Create mutually exclusive group for goal input
    goal_group = parser.add_mutually_exclusive_group(required=True)
    goal_group.add_argument('research_goal_file', nargs='?', help='Text file containing the research goal')
    goal_group.add_argument('--goal', help='Research goal specified directly as text')
    
    parser.add_argument('--model', required=True, help='Model shortname from model_servers.yaml')
    parser.add_argument('--num_hypotheses', type=int, default=5, help='Number of hypotheses to generate (default: 5)')
    parser.add_argument('--output', help='Output JSON file (default: hypotheses_<timestamp>.json)')
    return parser.parse_args()

# ---------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------

def main():
    args = parse_arguments()
    
    # Load model config
    model_config = load_model_config(args.model)
    
    print(f"Wisteria Research Hypothesis Generator v1.0")
    print(f"Using model: {args.model} ({model_config['model_name']})")
    print(f"Generating {args.num_hypotheses} hypotheses")
    
    # Get research goal from file or command line argument
    if args.goal:
        research_goal = args.goal.strip()
        goal_source = "command line argument"
    else:
        try:
            with open(args.research_goal_file, "r", encoding="utf-8") as f:
                research_goal = f.read().strip()
            goal_source = f"file: {args.research_goal_file}"
        except Exception as e:
            print(f"Error reading research goal file: {e}")
            sys.exit(1)
    
    if not research_goal:
        print("Error: Research goal is empty")
        sys.exit(1)
    
    print(f"\nResearch Goal:")
    print(f"{research_goal}")
    print("\nGenerating hypotheses...")
    
    # Generate hypotheses
    start_time = time.time()
    try:
        hypotheses = generate_hypotheses(research_goal, model_config, args.num_hypotheses)
    except Exception as e:
        print(f"Failed to generate hypotheses: {e}")
        sys.exit(1)
    
    generation_time = time.time() - start_time
    
    # Display hypotheses to console
    display_hypotheses(hypotheses)
    
    # Prepare output file
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"hypotheses_{args.model}_{timestamp}.json"
    else:
        output_file = args.output
    
    # Prepare metadata
    metadata = {
        "research_goal_source": goal_source,
        "research_goal": research_goal,
        "model": args.model,
        "model_name": model_config['model_name'],
        "num_hypotheses_requested": args.num_hypotheses,
        "num_hypotheses_generated": len(hypotheses),
        "timestamp": datetime.now().isoformat(),
        "generation_time_seconds": generation_time
    }
    
    # Save to JSON file
    save_hypotheses_to_json(hypotheses, output_file, metadata)
    
    print(f"\nGeneration completed in {generation_time:.2f} seconds")
    print(f"Hypotheses saved to: {output_file}")

if __name__ == "__main__":
    main()