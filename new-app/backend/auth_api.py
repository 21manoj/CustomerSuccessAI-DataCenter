from flask import Blueprint, request, jsonify
from extensions import db
from models import Customer, User
from werkzeug.security import generate_password_hash, check_password_hash

auth_api = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_api.route('/register', methods=['POST'])
def register():
    """Register a new customer and user account."""
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    
    if not all([name, email, password]):
        return jsonify({'message': 'Name, email, and password are required'}), 400
    
    # Check if email already exists
    if Customer.query.filter_by(email=email).first() or User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 400
    
    try:
        # Create customer
        customer = Customer(customer_name=name, email=email, phone=phone)
        db.session.add(customer)
        db.session.flush()  # Get customer_id
        
        # Create user
        user = User(
            customer_id=customer.customer_id,
            user_name=name,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'customer_id': customer.customer_id,
            'user_id': user.user_id,
            'user_name': user.user_name,
            'email': user.email,
            'message': 'Registration successful'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@auth_api.route('/login', methods=['POST'])
def login():
    """Authenticate a user and return session info."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'message': 'Invalid email or password'}), 401
    
    return jsonify({
        'customer_id': user.customer_id,
        'user_id': user.user_id,
        'user_name': user.user_name,
        'email': user.email,
        'message': 'Login successful'
    }), 200

@auth_api.route('/logout', methods=['POST'])
def logout():
    """Logout user."""
    return jsonify({'message': 'Logout successful'}), 200

