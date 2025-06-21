import os
import yaml
import json
import time
import random
import openai
import backoff
from datetime import datetime
from app.models import Session, Hypothesis, db
from app import socketio

def load_model_config(model_shortname):
    """
    Load model configuration from the model_servers.yaml file.
    Returns a dictionary with api_key, api_base, and model_name.
    """
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "shared", "model_servers.yaml")
    
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
                        raise ValueError(f"Environment variable {env_var} not set")
                
                return {
                    'api_key': api_key,
                    'api_base': server['openai_api_base'],
                    'model_name': server['openai_model'],
                    'shortname': model_shortname
                }
                
        # If not found
        raise ValueError(f"Model '{model_shortname}' not found in model_servers.yaml")
        
    except FileNotFoundError:
        raise FileNotFoundError(f"model_servers.yaml not found at {yaml_path}")
    except Exception as e:
        raise Exception(f"Error loading model configuration: {e}")

def clean_json_string(text):
    """Clean control characters from JSON string to prevent parsing errors."""
    if not text:
        return text
    # Remove ASCII control characters (0x00-0x1F and 0x7F) except for whitespace
    # Keep: \t (0x09), \n (0x0A), \r (0x0D)
    import re
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    return text

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def generate_hypotheses(research_goal, config, num_hypotheses=1, session_id=None):
    """
    Generate scientific hypotheses based on a research goal.
    Returns a list of hypothesis objects.
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
4. REFERENCES: Include relevant scientific references that support or relate to the hypothesis (3-5 references minimum)

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
        # Emit progress update if session_id provided
        if session_id:
            socketio.emit('generation_progress', {
                'session_id': session_id,
                'status': 'starting',
                'message': 'Initializing model...'
            }, room=session_id)
        
        # Add a small random delay to avoid overloading the API
        jitter = random.uniform(0.1, 1.0)
        time.sleep(jitter)
        
        if session_id:
            socketio.emit('generation_progress', {
                'session_id': session_id,
                'status': 'generating',
                'message': 'Generating hypothesis...'
            }, room=session_id)
        
        # Create a new client instance
        try:
            client = openai.OpenAI(
                api_key=api_key
            )
            # Set the base URL after creation if needed
            if api_base != "https://api.openai.com/v1":
                client.base_url = api_base
        except TypeError as e:
            if "proxies" in str(e):
                # If proxies parameter is causing issues, create client without it
                client = openai.OpenAI(
                    api_key=api_key
                )
                if api_base != "https://api.openai.com/v1":
                    client.base_url = api_base
            else:
                raise
        
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
        
        if session_id:
            socketio.emit('generation_progress', {
                'session_id': session_id,
                'status': 'processing',
                'message': 'Processing response...'
            }, room=session_id)
        
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
        if session_id:
            socketio.emit('generation_error', {
                'session_id': session_id,
                'error': str(e)
            }, room=session_id)
        raise

@backoff.on_exception(
    backoff.expo,
    (Exception),
    max_tries=5,
    giveup=lambda e: "Invalid authentication" in str(e),
    max_time=300
)
def improve_hypothesis(research_goal, current_hypothesis, user_feedback, config, session_id=None):
    """
    Improve a hypothesis based on user feedback.
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
5. Includes relevant scientific references that support the improved hypothesis (3-5 references minimum)

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
        if session_id:
            socketio.emit('generation_progress', {
                'session_id': session_id,
                'status': 'improving',
                'message': 'Improving hypothesis based on feedback...'
            }, room=session_id)
        
        # Add a small random delay to avoid overloading the API
        jitter = random.uniform(0.1, 1.0)
        time.sleep(jitter)
        
        # Create a new client instance
        try:
            client = openai.OpenAI(
                api_key=api_key
            )
            # Set the base URL after creation if needed
            if api_base != "https://api.openai.com/v1":
                client.base_url = api_base
        except TypeError as e:
            if "proxies" in str(e):
                # If proxies parameter is causing issues, create client without it
                client = openai.OpenAI(
                    api_key=api_key
                )
                if api_base != "https://api.openai.com/v1":
                    client.base_url = api_base
            else:
                raise
        
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
                "references": [],
                "improvements_made": "N/A",
                "error": True,
                "raw_response": generated_text
            }
            
    except Exception as e:
        # Propagate the exception to trigger backoff
        print(f"Error in improve_hypothesis (will retry): {str(e)}")
        if session_id:
            socketio.emit('generation_error', {
                'session_id': session_id,
                'error': str(e)
            }, room=session_id)
        raise

class HypothesisService:
    """Service class for managing hypotheses"""
    
    @staticmethod
    def create_session(research_goal: str, model_shortname: str) -> Session:
        """Create a new research session"""
        try:
            # Load model configuration to validate
            model_config = load_model_config(model_shortname)
            
            session = Session(
                research_goal=research_goal,
                model_name=model_config['model_name'],
                model_shortname=model_shortname
            )
            
            db.session.add(session)
            db.session.commit()
            return session
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def generate_initial_hypothesis(session_id: str) -> Hypothesis:
        """Generate the first hypothesis for a session"""
        session = Session.query.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        model_config = load_model_config(session.model_shortname)
        
        # Generate hypothesis using existing logic
        hypotheses = generate_hypotheses(
            session.research_goal, 
            model_config, 
            num_hypotheses=1,
            session_id=session_id
        )
        
        if not hypotheses or hypotheses[0].get("error"):
            raise Exception("Failed to generate hypothesis")
        
        hypothesis_data = hypotheses[0]
        
        # Create hypothesis record
        hypothesis = Hypothesis(
            session_id=session_id,
            hypothesis_number=1,
            version="1.0",
            title=hypothesis_data['title'],
            description=hypothesis_data['description'],
            hallmarks=hypothesis_data['hallmarks'],
            references=hypothesis_data['references'],
            hypothesis_type="original"
        )
        
        db.session.add(hypothesis)
        db.session.commit()
        
        # Emit success event
        socketio.emit('hypothesis_generated', {
            'session_id': session_id,
            'hypothesis': hypothesis.to_dict(),
            'status': 'success'
        }, room=session_id)
        
        return hypothesis
    
    @staticmethod
    def improve_hypothesis(hypothesis_id: str, feedback: str) -> Hypothesis:
        """Improve an existing hypothesis based on feedback"""
        hypothesis = Hypothesis.query.get(hypothesis_id)
        if not hypothesis:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")
        
        session = hypothesis.session
        model_config = load_model_config(session.model_shortname)
        
        # Convert hypothesis to dict for improvement function
        hypothesis_dict = {
            'title': hypothesis.title,
            'description': hypothesis.description,
            'hallmarks': hypothesis.hallmarks,
            'references': hypothesis.references
        }
        
        # Improve hypothesis using existing logic
        improved_data = improve_hypothesis(
            session.research_goal,
            hypothesis_dict,
            feedback,
            model_config,
            session_id=session.id
        )
        
        if improved_data.get("error"):
            raise Exception("Failed to improve hypothesis")
        
        # Get next version number
        version_parts = hypothesis.version.split('.')
        minor_version = int(version_parts[1]) + 1
        new_version = f"{version_parts[0]}.{minor_version}"
        
        # Create improved hypothesis
        improved_hypothesis = Hypothesis(
            session_id=session.id,
            hypothesis_number=hypothesis.hypothesis_number,
            version=new_version,
            title=improved_data['title'],
            description=improved_data['description'],
            hallmarks=improved_data['hallmarks'],
            references=improved_data['references'],
            hypothesis_type="improvement",
            user_feedback=feedback,
            original_hypothesis_id=hypothesis.id
        )
        
        db.session.add(improved_hypothesis)
        db.session.commit()
        
        # Emit success event
        socketio.emit('hypothesis_improved', {
            'session_id': session.id,
            'hypothesis': improved_hypothesis.to_dict(),
            'status': 'success'
        }, room=session.id)
        
        return improved_hypothesis
    
    @staticmethod
    def generate_new_hypothesis(session_id: str) -> Hypothesis:
        """Generate a new alternative hypothesis"""
        session = Session.query.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get existing hypotheses to avoid duplication
        existing_hypotheses = session.hypotheses
        
        model_config = load_model_config(session.model_shortname)
        
        # For now, just generate a new hypothesis (we'll add duplication avoidance later)
        hypotheses = generate_hypotheses(
            session.research_goal, 
            model_config, 
            num_hypotheses=1,
            session_id=session_id
        )
        
        if not hypotheses or hypotheses[0].get("error"):
            raise Exception("Failed to generate new hypothesis")
        
        hypothesis_data = hypotheses[0]
        
        # Get next hypothesis number
        next_number = max([h.hypothesis_number for h in existing_hypotheses]) + 1 if existing_hypotheses else 1
        
        # Create new hypothesis
        hypothesis = Hypothesis(
            session_id=session_id,
            hypothesis_number=next_number,
            version="1.0",
            title=hypothesis_data['title'],
            description=hypothesis_data['description'],
            hallmarks=hypothesis_data['hallmarks'],
            references=hypothesis_data['references'],
            hypothesis_type="new_alternative"
        )
        
        db.session.add(hypothesis)
        db.session.commit()
        
        # Emit success event
        socketio.emit('hypothesis_generated', {
            'session_id': session_id,
            'hypothesis': hypothesis.to_dict(),
            'status': 'success'
        }, room=session_id)
        
        return hypothesis 