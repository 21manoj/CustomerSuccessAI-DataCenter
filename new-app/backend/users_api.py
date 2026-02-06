from flask import Blueprint, request, jsonify
from extensions import db
from models import User

users_api = Blueprint('users', __name__, url_prefix='/api/users')

@users_api.route('/', methods=['GET'])
def get_users():
    """Get all users (for testing - should add auth in production)."""
    try:
        customer_id = request.headers.get('X-Customer-ID', type=int)
        if customer_id:
            users = User.query.filter_by(customer_id=customer_id).all()
        else:
            users = User.query.all()
        
        return jsonify({
            'users': [user.to_dict() for user in users],
            'count': len(users)
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch users: {str(e)}'}), 500

@users_api.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID."""
    try:
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict()), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch user: {str(e)}'}), 500

@users_api.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user."""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        if 'user_name' in data:
            user.user_name = data['user_name']
        if 'email' in data:
            user.email = data['email']
        
        db.session.commit()
        return jsonify({
            'message': 'User updated successfully',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update user: {str(e)}'}), 500

@users_api.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user."""
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to delete user: {str(e)}'}), 500

