from backend.app import app
from backend.models import db
from sqlalchemy import text
with app.app_context():
    db.session.execute(text("SELECT setval('customers_customer_id_seq', COALESCE((SELECT MAX(customer_id) FROM customers), 1), true);"))
    db.session.execute(text("SELECT setval('users_user_id_seq', COALESCE((SELECT MAX(user_id) FROM users), 1), true);"))
    db.session.commit()
    print('✅ Sequences for customers and users have been reset.')

