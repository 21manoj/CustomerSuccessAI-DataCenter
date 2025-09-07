from flask_sqlalchemy import SQLAlchemy
from flask import request

db = SQLAlchemy()

def get_customer_id():
    """Get customer ID from request headers"""
    return int(request.headers.get('X-Customer-ID', 1)) 