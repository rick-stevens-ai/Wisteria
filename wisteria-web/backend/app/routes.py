from flask import Blueprint, request, jsonify, send_file
from app.models import Session, Hypothesis, db
from app.services import HypothesisService, load_model_config
import yaml
import os
import io
from datetime import datetime

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

def generate_hypothesis_pdf(hypothesis, research_goal, output_filename=None):
    """
    Generate a nicely formatted PDF document for a hypothesis.
    
    Args:
        hypothesis (dict): The hypothesis data
        research_goal (str): The research goal
        output_filename (str, optional): Custom output filename
        
    Returns:
        bytes: PDF file content, or None if failed
    """
    if not PDF_AVAILABLE:
        return None
        
    try:
        # Create PDF in memory
        buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(buffer, pagesize=letter,
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
        hyp_type = hypothesis.get("hypothesis_type", "original")
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
        
        # Improvements (if any)
        if hypothesis.get("user_feedback") and hypothesis.get("hypothesis_type") == "improvement":
            story.append(Paragraph("Improvements Made", heading_style))
            improvements = hypothesis.get("user_feedback", "")
            story.append(Paragraph(improvements, body_style))
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
        story.append(Paragraph("Generated by Wisteria Research Hypothesis Generator", footer_style))
        story.append(Paragraph(f"Document created on {datetime.now().strftime('%B %d, %Y')}", footer_style))
        
        # Build the PDF
        doc.build(story)
        
        # Get the PDF content
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None

@api.route('/sessions/<session_id>/hypotheses/<hypothesis_id>/pdf', methods=['GET'])
def download_hypothesis_pdf(session_id, hypothesis_id):
    """Download a hypothesis as a PDF"""
    try:
        # Verify session and hypothesis exist
        session = Session.query.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        hypothesis = Hypothesis.query.get(hypothesis_id)
        if not hypothesis or hypothesis.session_id != session_id:
            return jsonify({'error': 'Hypothesis not found'}), 404
        
        if not PDF_AVAILABLE:
            return jsonify({'error': 'PDF generation not available. Please install reportlab.'}), 500
        
        # Generate PDF
        pdf_content = generate_hypothesis_pdf(
            hypothesis.to_dict(), 
            session.research_goal
        )
        
        if not pdf_content:
            return jsonify({'error': 'Failed to generate PDF'}), 500
        
        # Create filename
        safe_title = "".join(c for c in hypothesis.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
        filename = f"hypothesis_{safe_title}_v{hypothesis.version}.pdf"
        
        # Return PDF file
        buffer = io.BytesIO(pdf_content)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 