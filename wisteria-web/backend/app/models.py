from app import db
from datetime import datetime
import uuid
import json

class Session(db.Model):
    """Research session model"""
    __tablename__ = 'sessions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    research_goal = db.Column(db.Text, nullable=False)
    model_name = db.Column(db.String(100), nullable=False)
    model_shortname = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    hypotheses = db.relationship('Hypothesis', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert session to dictionary"""
        return {
            'id': self.id,
            'research_goal': self.research_goal,
            'model_name': self.model_name,
            'model_shortname': self.model_shortname,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'hypothesis_count': len(self.hypotheses)
        }

class Hypothesis(db.Model):
    """Hypothesis model"""
    __tablename__ = 'hypotheses'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.String(36), db.ForeignKey('sessions.id'), nullable=False)
    hypothesis_number = db.Column(db.Integer, nullable=False)
    version = db.Column(db.String(10), nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    hallmarks = db.Column(db.JSON, nullable=False)
    references = db.Column(db.JSON, nullable=False)
    hypothesis_type = db.Column(db.String(20), nullable=False)  # original, improvement, new_alternative
    user_feedback = db.Column(db.Text)
    original_hypothesis_id = db.Column(db.String(36), db.ForeignKey('hypotheses.id'))
    generation_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    improvements = db.relationship('Hypothesis', backref=db.backref('original', remote_side=[id]))
    
    def to_dict(self):
        """Convert hypothesis to dictionary"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'hypothesis_number': self.hypothesis_number,
            'version': self.version,
            'title': self.title,
            'description': self.description,
            'hallmarks': self.hallmarks,
            'references': self.references,
            'hypothesis_type': self.hypothesis_type,
            'user_feedback': self.user_feedback,
            'original_hypothesis_id': self.original_hypothesis_id,
            'generation_timestamp': self.generation_timestamp.isoformat(),
            'improvements_count': len(self.improvements)
        } 