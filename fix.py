from app import app, db
from models import Calculation
from datetime import datetime

with app.app_context():
    # Delete calculations from May and June 2026
    result = Calculation.query.filter(
        (Calculation.year == 2026) & 
        ((Calculation.month == 5) | (Calculation.month == 6))
    ).delete()
    
    db.session.commit()
    print(f"Deleted {result} sample calculation(s)")