from backend.app import app
from backend.extensions import db
from backend.models import Customer, User

def add_default_data():
    with app.app_context():
        # Add default customer if it doesn't exist
        customer = Customer.query.filter_by(customer_id=1).first()
        if not customer:
            customer = Customer(customer_id=1, customer_name="Default Customer")
            db.session.add(customer)
            print("Added default customer")
        
        # Add default user if it doesn't exist
        user = User.query.filter_by(user_id=1).first()
        if not user:
            user = User(user_id=1, user_name="Default User", customer_id=1)
            db.session.add(user)
            print("Added default user")
        
        db.session.commit()
        print("Default data added successfully!")

if __name__ == '__main__':
    add_default_data() 