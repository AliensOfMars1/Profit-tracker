from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal

db = SQLAlchemy()

class Calculation(db.Model):
    __tablename__ = 'calculations'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Input values
    equity = db.Column(db.Numeric(10, 2), nullable=False)
    total_usdt = db.Column(db.Numeric(10, 2), nullable=False)
    rate = db.Column(db.Numeric(10, 2), nullable=False)
    ecash = db.Column(db.Numeric(10, 2), nullable=False)
    hard_cash = db.Column(db.Numeric(10, 2), nullable=False)
    cashin_commission = db.Column(db.Numeric(10, 2), nullable=False)
    cashout_commission = db.Column(db.Numeric(10, 2), nullable=False)
    foreign_funds = db.Column(db.Numeric(10, 2), nullable=False)
    lent_funds = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Calculated values
    profit = db.Column(db.Numeric(10, 2), nullable=False)
    operating_profit = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    locked_asset_gain_loss = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    locked_asset_value_current = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    locked_asset_value_ref = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    daily_average = db.Column(db.Numeric(10, 2))
    projected_profit = db.Column(db.Numeric(10, 2))
    
    # Metadata
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    
    def __init__(self, *args, **kwargs):
        super(Calculation, self).__init__(*args, **kwargs)
        if self.created_at:
            self.year = self.created_at.year
            self.month = self.created_at.month
            self.day = self.created_at.day

class ForeignFund(db.Model):
    __tablename__ = 'foreign_funds'
    
    id = db.Column(db.Integer, primary_key=True)
    person_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    note = db.Column(db.Text)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')

class LentFund(db.Model):
    __tablename__ = 'lent_funds'
    
    id = db.Column(db.Integer, primary_key=True)
    borrower_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    note = db.Column(db.Text)
    date_lent = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')

class AppSetting(db.Model):
    __tablename__ = 'app_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.Numeric(10, 2))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)