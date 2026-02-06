from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    phone = db.Column(db.String)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            'customer_id': self.customer_id,
            'customer_name': self.customer_name,
            'email': self.email,
            'phone': self.phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'), nullable=False)
    user_name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    customer = db.relationship('Customer', backref='users')

    def check_password(self, password):
        """Check if provided password matches the hash"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'customer_id': self.customer_id,
            'user_name': self.user_name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

