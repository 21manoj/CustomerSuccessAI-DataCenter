"""
Wizard A Database Models
========================

Models for storing wizard runs, learnings, and results.

Add to your existing models.py file.
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import uuid

# Assuming you already have db = SQLAlchemy(app)
# from your existing models.py


class WizardRun(db.Model):
    """
    Tracks each wizard run (data generation + training session)
    """
    __tablename__ = 'wizard_runs'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Job tracking
    job_id = db.Column(db.String(100), index=True)  # Celery task ID
    status = db.Column(db.String(20), nullable=False, default='queued', index=True)
    # Status: queued, running, completed, failed, cancelled
    
    current_phase = db.Column(db.String(50))  # Phase 1, Phase 2, etc.
    progress = db.Column(db.JSON)  # {phase1: 100, phase2: 50, ...}
    
    # Configuration
    config = db.Column(db.JSON, nullable=False)  # Full wizard config
    
    # Results
    results = db.Column(db.JSON)  # Final results after completion
    error_message = db.Column(db.Text)  # Error details if failed
    
    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_by = db.Column(db.String(100))  # User who started it
    
    # Relationships
    learnings = db.relationship('WizardLearning', backref='source_run', lazy='dynamic')
    
    def __init__(self, **kwargs):
        super(WizardRun, self).__init__(**kwargs)
        if not self.run_id:
            self.run_id = f"wizard_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    def update_progress(self, phase, percent):
        """Update progress for a specific phase"""
        if not self.progress:
            self.progress = {}
        self.progress[phase] = percent
        self.current_phase = phase
        db.session.commit()
    
    def mark_started(self):
        """Mark run as started"""
        self.status = 'running'
        self.started_at = datetime.utcnow()
        db.session.commit()
    
    def mark_completed(self, results):
        """Mark run as completed with results"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
        self.results = results
        db.session.commit()
    
    def mark_failed(self, error_message):
        """Mark run as failed"""
        self.status = 'failed'
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        db.session.commit()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'run_id': self.run_id,
            'job_id': self.job_id,
            'status': self.status,
            'current_phase': self.current_phase,
            'progress': self.progress,
            'config': self.config,
            'results': self.results,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_by': self.created_by
        }


class WizardLearning(db.Model):
    """
    Stores extracted learnings from wizard runs
    These learnings are used to improve Wizard B defaults
    """
    __tablename__ = 'wizard_learnings'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), nullable=False, unique=True, index=True)
    # e.g., "v1.0", "v1.1", "v2.0"
    
    # Source information
    source_runs = db.Column(db.JSON)  # List of run_ids that contributed
    run_id = db.Column(db.String(50), db.ForeignKey('wizard_runs.run_id'))
    
    # Learnings
    learnings = db.Column(db.JSON, nullable=False)
    # {
    #   'optimal_weights': {...},
    #   'threshold_recommendations': {...},
    #   'event_severity_ranges': {...},
    #   'pattern_effectiveness': {...}
    # }
    
    industry_benchmarks = db.Column(db.JSON)
    # {
    #   'SaaS': {'weights': {...}, 'thresholds': {...}},
    #   'Hardware': {...}
    # }
    
    validation_rules = db.Column(db.JSON)
    # {
    #   'min_kpi_coverage': 0.71,
    #   'min_events_per_week': 3,
    #   'optimal_thresholds': {...}
    # }
    
    edge_cases = db.Column(db.JSON)
    # List of discovered edge cases and solutions
    
    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    is_active = db.Column(db.Boolean, default=True, index=True)
    # Only one version should be active at a time
    
    # Statistics
    total_accounts_tested = db.Column(db.Integer)
    avg_accuracy = db.Column(db.Float)
    
    def __init__(self, **kwargs):
        super(WizardLearning, self).__init__(**kwargs)
        # Auto-increment version
        if not self.version:
            latest = WizardLearning.query.order_by(
                WizardLearning.created_at.desc()
            ).first()
            if latest:
                # Parse version (e.g., "v1.5" -> 1.5)
                try:
                    current_version = float(latest.version.replace('v', ''))
                    new_version = current_version + 0.1
                    self.version = f"v{new_version:.1f}"
                except:
                    self.version = "v1.0"
            else:
                self.version = "v1.0"
    
    def activate(self):
        """Make this the active learning version"""
        # Deactivate all others
        WizardLearning.query.update({'is_active': False})
        self.is_active = True
        db.session.commit()
    
    @classmethod
    def get_active(cls):
        """Get the currently active learning version"""
        return cls.query.filter_by(is_active=True).first()
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'version': self.version,
            'source_runs': self.source_runs,
            'learnings': self.learnings,
            'industry_benchmarks': self.industry_benchmarks,
            'validation_rules': self.validation_rules,
            'edge_cases': self.edge_cases,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active,
            'total_accounts_tested': self.total_accounts_tested,
            'avg_accuracy': self.avg_accuracy
        }


class WizardFile(db.Model):
    """
    Tracks files generated by wizard runs
    """
    __tablename__ = 'wizard_files'
    
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(50), db.ForeignKey('wizard_runs.run_id'), nullable=False, index=True)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(50))  # html, png, json, csv
    file_size = db.Column(db.Integer)  # bytes
    
    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text)  # What this file contains
    
    def to_dict(self):
        return {
            'filename': self.filename,
            'filepath': self.filepath,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'created_at': self.created_at.isoformat(),
            'description': self.description
        }


# ============================================================================
# DATABASE MIGRATION SQL
# ============================================================================

"""
Run this SQL to create the tables:

CREATE TABLE wizard_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) UNIQUE NOT NULL,
    job_id VARCHAR(100),
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    current_phase VARCHAR(50),
    progress JSONB,
    config JSONB NOT NULL,
    results JSONB,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_by VARCHAR(100)
);

CREATE INDEX idx_wizard_runs_run_id ON wizard_runs(run_id);
CREATE INDEX idx_wizard_runs_status ON wizard_runs(status);
CREATE INDEX idx_wizard_runs_created_at ON wizard_runs(created_at);
CREATE INDEX idx_wizard_runs_job_id ON wizard_runs(job_id);


CREATE TABLE wizard_learnings (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    source_runs JSONB,
    run_id VARCHAR(50) REFERENCES wizard_runs(run_id),
    learnings JSONB NOT NULL,
    industry_benchmarks JSONB,
    validation_rules JSONB,
    edge_cases JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    total_accounts_tested INTEGER,
    avg_accuracy FLOAT
);

CREATE INDEX idx_wizard_learnings_version ON wizard_learnings(version);
CREATE INDEX idx_wizard_learnings_is_active ON wizard_learnings(is_active);
CREATE INDEX idx_wizard_learnings_created_at ON wizard_learnings(created_at);


CREATE TABLE wizard_files (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(50) REFERENCES wizard_runs(run_id) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    description TEXT
);

CREATE INDEX idx_wizard_files_run_id ON wizard_files(run_id);
"""
