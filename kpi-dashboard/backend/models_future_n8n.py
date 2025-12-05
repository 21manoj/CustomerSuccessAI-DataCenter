"""
FUTURE IMPLEMENTATION: n8n Playbook Mapping Model

This model will be added when n8n workflow integration is needed.
Keep this separate from core PlaybookExecution to avoid schema conflicts.

To implement:
1. Add this model to backend/models.py
2. Create migration: alembic revision --autogenerate -m "add_n8n_playbook_mappings"
3. Run migration: alembic upgrade head
"""

# FUTURE: Uncomment and add to models.py when implementing n8n workflow mappings
"""
class N8NPlaybookMapping(db.Model):
    \"\"\"Maps playbooks to n8n workflows - separate from core playbook execution\"\"\"
    __tablename__ = 'n8n_playbook_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False, index=True)
    playbook_id = db.Column(db.String(50), nullable=False)  # 'voc-sprint', 'activation-blitz', etc.
    
    # n8n configuration
    enabled = db.Column(db.Boolean, default=False, nullable=False)
    n8n_workflow_url = db.Column(db.String(500))  # Full webhook URL
    n8n_workflow_id = db.Column(db.String(100))  # n8n workflow execution ID (set after handoff)
    auto_trigger = db.Column(db.Boolean, default=False)  # Auto-trigger on playbook start
    
    # Metadata
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    
    # Relationships
    customer = db.relationship('Customer', backref=db.backref('n8n_mappings', lazy='dynamic'))
    
    # Unique constraint: one mapping per customer+playbook
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'playbook_id', name='uq_customer_playbook_n8n'),
        db.Index('idx_customer_playbook_n8n', 'customer_id', 'playbook_id'),
    )
    
    def __repr__(self):
        return f'<N8NPlaybookMapping {self.customer_id}:{self.playbook_id} enabled={self.enabled}>'
"""









