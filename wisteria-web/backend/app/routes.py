from flask import Blueprint, request, jsonify
from app.models import Session, Hypothesis, db
from app.services import HypothesisService, load_model_config
import yaml
import os

api = Blueprint('api', __name__)

@api.route('/models', methods=['GET'])
def get_available_models():
    """Get list of available models from model_servers.yaml"""
    try:
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "shared", "model_servers.yaml")
        
        with open(yaml_path, 'r') as yaml_file:
            config = yaml.safe_load(yaml_file)
        
        models = []
        for server in config['servers']:
            models.append({
                'shortname': server['shortname'],
                'model_name': server['openai_model'],
                'server': server['server']
            })
        
        return jsonify({'models': models})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions', methods=['GET'])
def get_sessions():
    """Get all sessions"""
    try:
        sessions = Session.query.order_by(Session.created_at.desc()).all()
        return jsonify({
            'sessions': [session.to_dict() for session in sessions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions', methods=['POST'])
def create_session():
    """Create a new research session"""
    try:
        data = request.get_json()
        
        if not data or 'research_goal' not in data or 'model_shortname' not in data:
            return jsonify({'error': 'research_goal and model_shortname are required'}), 400
        
        research_goal = data['research_goal'].strip()
        model_shortname = data['model_shortname'].strip()
        
        if not research_goal:
            return jsonify({'error': 'research_goal cannot be empty'}), 400
        
        # Validate model exists
        try:
            load_model_config(model_shortname)
        except Exception as e:
            return jsonify({'error': f'Invalid model: {str(e)}'}), 400
        
        session = HypothesisService.create_session(research_goal, model_shortname)
        
        return jsonify({
            'message': 'Session created successfully',
            'session': session.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get a specific session with its hypotheses"""
    try:
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Get all hypotheses for this session
        hypotheses = Hypothesis.query.filter_by(session_id=session_id).order_by(
            Hypothesis.hypothesis_number, Hypothesis.version
        ).all()
        
        session_data = session.to_dict()
        session_data['hypotheses'] = [h.to_dict() for h in hypotheses]
        
        return jsonify({'session': session_data})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>/hypotheses', methods=['POST'])
def generate_hypothesis(session_id):
    """Generate initial hypothesis for a session"""
    try:
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        # Check if session already has hypotheses
        existing_hypotheses = Hypothesis.query.filter_by(session_id=session_id).first()
        if existing_hypotheses:
            return jsonify({'error': 'Session already has hypotheses. Use /improve or /new endpoint.'}), 400
        
        hypothesis = HypothesisService.generate_initial_hypothesis(session_id)
        
        return jsonify({
            'message': 'Hypothesis generated successfully',
            'hypothesis': hypothesis.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>/hypotheses/<hypothesis_id>/improve', methods=['POST'])
def improve_hypothesis_endpoint(session_id, hypothesis_id):
    """Improve an existing hypothesis based on feedback"""
    try:
        data = request.get_json()
        
        if not data or 'feedback' not in data:
            return jsonify({'error': 'feedback is required'}), 400
        
        feedback = data['feedback'].strip()
        if not feedback:
            return jsonify({'error': 'feedback cannot be empty'}), 400
        
        # Verify session and hypothesis exist
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        hypothesis = Hypothesis.query.get(hypothesis_id)
        if not hypothesis or hypothesis.session_id != session_id:
            return jsonify({'error': 'Hypothesis not found'}), 404
        
        improved_hypothesis = HypothesisService.improve_hypothesis(hypothesis_id, feedback)
        
        return jsonify({
            'message': 'Hypothesis improved successfully',
            'hypothesis': improved_hypothesis.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>/hypotheses/new', methods=['POST'])
def generate_new_hypothesis_endpoint(session_id):
    """Generate a new alternative hypothesis"""
    try:
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        hypothesis = HypothesisService.generate_new_hypothesis(session_id)
        
        return jsonify({
            'message': 'New hypothesis generated successfully',
            'hypothesis': hypothesis.to_dict()
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>/hypotheses', methods=['GET'])
def get_session_hypotheses(session_id):
    """Get all hypotheses for a session"""
    try:
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        hypotheses = Hypothesis.query.filter_by(session_id=session_id).order_by(
            Hypothesis.hypothesis_number, Hypothesis.version
        ).all()
        
        return jsonify({
            'hypotheses': [h.to_dict() for h in hypotheses]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>/hypotheses/<hypothesis_id>', methods=['GET'])
def get_hypothesis(session_id, hypothesis_id):
    """Get a specific hypothesis"""
    try:
        hypothesis = Hypothesis.query.get(hypothesis_id)
        if not hypothesis or hypothesis.session_id != session_id:
            return jsonify({'error': 'Hypothesis not found'}), 404
        
        return jsonify({
            'hypothesis': hypothesis.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a session and all its hypotheses"""
    try:
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        db.session.delete(session)
        db.session.commit()
        
        return jsonify({'message': 'Session deleted successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Wisteria API is running'
    }) 