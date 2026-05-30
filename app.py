from flask import Flask, render_template, request, redirect, url_for, flash, session
from models import db, Calculation, ForeignFund, LentFund, AppSetting
from datetime import datetime, date
from calendar import monthrange
from decimal import Decimal
from sqlalchemy import func
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 86400

db.init_app(app)

APP_PIN = "1234"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_month_days():
    today = date.today()
    return monthrange(today.year, today.month)[1]

def get_current_day():
    return date.today().day

def get_latest_setting(key):
    setting = AppSetting.query.filter_by(key=key).order_by(AppSetting.updated_at.desc()).first()
    return Decimal(setting.value) if setting else Decimal('0')

def save_setting(key, value):
    existing_setting = AppSetting.query.filter_by(key=key).first()
    if existing_setting:
        existing_setting.value = value
        existing_setting.updated_at = datetime.utcnow()
    else:
        existing_setting = AppSetting(key=key, value=value)
        db.session.add(existing_setting)
    db.session.commit()

def calculate_profit(equity, total_usdt, rate, ecash, hard_cash, 
                    cashin_commission, cashout_commission, foreign_funds, lent_funds,
                    locked_asset, ref_rate):
    locked_asset_value_current = locked_asset * rate
    locked_asset_value_ref = locked_asset * ref_rate
    locked_asset_gain_loss = locked_asset_value_current - locked_asset_value_ref
    
    usdt_value = total_usdt * rate
    total_assets = usdt_value + ecash + hard_cash + cashin_commission + cashout_commission + lent_funds
    total_liabilities = equity + foreign_funds
    operating_profit = total_assets - total_liabilities
    
    total_profit = operating_profit + locked_asset_gain_loss
    
    return {
        'operating_profit': operating_profit,
        'locked_asset_gain_loss': locked_asset_gain_loss,
        'total_profit': total_profit,
        'locked_asset_value_current': locked_asset_value_current,
        'locked_asset_value_ref': locked_asset_value_ref
    }

def get_total_foreign_funds():
    total = db.session.query(db.func.sum(ForeignFund.amount)).filter_by(status='active').scalar()
    return total if total else Decimal('0')

def get_total_lent_funds():
    total = db.session.query(db.func.sum(LentFund.amount)).filter_by(status='active').scalar()
    return total if total else Decimal('0')

# ==================== ROUTES ====================

@app.route('/', methods=['GET', 'POST'])
def index():
    if session.get('authenticated'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == APP_PIN:
            session['authenticated'] = True
            session.permanent = True
            flash('Welcome back! Access granted.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid PIN. Please try again.', 'error')
            return render_template('index.html')
    return render_template('index.html')

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    latest_calc = Calculation.query.filter_by(
        year=today.year, 
        month=today.month
    ).order_by(Calculation.created_at.desc()).first()
    
    # Get LIVE totals first (always current)
    foreign_funds_total = get_total_foreign_funds()
    lent_funds_total = get_total_lent_funds()
    equity_setting = get_latest_setting('equity')
    locked_asset = get_latest_setting('locked_asset')
    ref_rate = get_latest_setting('ref_rate')
    
    # Total Funds Value = LIVE equity + LIVE foreign funds
    total_funds_value = equity_setting + foreign_funds_total
    
    # Calculate Available Funds (Liquid)
    # Available = (Equity + Foreign) - (Locked Asset + Lent Funds)
    available_funds = (equity_setting + foreign_funds_total) - ((locked_asset * ref_rate) + lent_funds_total)
    
    if latest_calc:
        current_profit = latest_calc.profit
        operating_profit = latest_calc.operating_profit
        locked_asset_gain_loss = latest_calc.locked_asset_gain_loss
        equity = latest_calc.equity
        
        total_commission = latest_calc.cashin_commission + latest_calc.cashout_commission
        earn_from_rate = float(current_profit) - float(total_commission)
        
        current_day = get_current_day()
        if current_day > 0:
            daily_average = current_profit / Decimal(current_day)
        else:
            daily_average = Decimal('0')
        total_days = get_current_month_days()
        projected_profit = daily_average * Decimal(total_days)
    else:
        current_profit = Decimal('0')
        operating_profit = Decimal('0')
        locked_asset_gain_loss = Decimal('0')
        equity = equity_setting
        total_commission = Decimal('0')
        earn_from_rate = Decimal('0')
        daily_average = Decimal('0')
        projected_profit = Decimal('0')
    
    return render_template('dashboard.html',
                         current_profit=current_profit,
                         operating_profit=operating_profit,
                         locked_asset_gain_loss=locked_asset_gain_loss,
                         equity=equity,
                         total_funds_value=total_funds_value,
                         foreign_funds_total=foreign_funds_total,
                         lent_funds_total=lent_funds_total,
                         daily_average=daily_average,
                         projected_profit=projected_profit,
                         locked_asset=locked_asset,
                         ref_rate=ref_rate,
                         equity_setting=equity_setting,
                         total_commission=total_commission,
                         earn_from_rate=earn_from_rate,
                         available_funds=available_funds)  # ← ADD THIS

@app.route('/calculation', methods=['GET', 'POST'])
@login_required
def calculation():
    if request.method == 'POST':
        try:
            equity = Decimal(request.form['equity'])
            total_usdt = Decimal(request.form['total_usdt'])
            rate = Decimal(request.form['rate'])
            ecash = Decimal(request.form['ecash'])
            hard_cash = Decimal(request.form['hard_cash'])
            cashin_commission = Decimal(request.form['cashin_commission'])
            cashout_commission = Decimal(request.form['cashout_commission'])
            foreign_funds = Decimal(request.form['foreign_funds'])
            lent_funds = Decimal(request.form['lent_funds'])
            
            locked_asset = get_latest_setting('locked_asset')
            ref_rate = get_latest_setting('ref_rate')
            
            if any(v < 0 for v in [equity, total_usdt, rate, ecash, hard_cash, 
                                   cashin_commission, cashout_commission]):
                flash('Most values cannot be negative. Please check your inputs.', 'error')
                return redirect(url_for('calculation'))
            
            profit_data = calculate_profit(equity, total_usdt, rate, ecash, hard_cash,
                                          cashin_commission, cashout_commission, foreign_funds, lent_funds,
                                          locked_asset, ref_rate)
            
            current_day = get_current_day()
            daily_average = profit_data['total_profit'] / Decimal(current_day) if current_day > 0 else Decimal('0')
            total_days = get_current_month_days()
            projected_profit = daily_average * Decimal(total_days)
            
            today = date.today()
            calculation = Calculation(
                equity=equity,
                total_usdt=total_usdt,
                rate=rate,
                ecash=ecash,
                hard_cash=hard_cash,
                cashin_commission=cashin_commission,
                cashout_commission=cashout_commission,
                foreign_funds=foreign_funds,
                lent_funds=lent_funds,
                profit=profit_data['total_profit'],
                operating_profit=profit_data['operating_profit'],
                locked_asset_gain_loss=profit_data['locked_asset_gain_loss'],
                locked_asset_value_current=profit_data['locked_asset_value_current'],
                locked_asset_value_ref=profit_data['locked_asset_value_ref'],
                daily_average=daily_average,
                projected_profit=projected_profit,
                year=today.year,
                month=today.month,
                day=today.day
            )
            
            db.session.add(calculation)
            db.session.commit()
            flash(f'Calculation saved! Total Profit: GHS {profit_data["total_profit"]:,.2f}', 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error saving calculation: {str(e)}', 'error')
            return redirect(url_for('calculation'))
    
    foreign_funds_total = get_total_foreign_funds()
    lent_funds_total = get_total_lent_funds()
    latest_calc = Calculation.query.order_by(Calculation.created_at.desc()).first()
    locked_asset = get_latest_setting('locked_asset')
    ref_rate = get_latest_setting('ref_rate')
    equity_setting = get_latest_setting('equity')
    
    return render_template('calculation_form.html',
                         foreign_funds_total=foreign_funds_total,
                         lent_funds_total=lent_funds_total,
                         latest_calc=latest_calc,
                         locked_asset=locked_asset,
                         ref_rate=ref_rate,
                         equity_setting=equity_setting)

@app.route('/foreign-funds')
@login_required
def foreign_funds():
    active_funds = ForeignFund.query.filter_by(status='active').order_by(ForeignFund.date_added.desc()).all()
    settled_funds = ForeignFund.query.filter_by(status='settled').order_by(ForeignFund.date_added.desc()).all()
    foreign_total = get_total_foreign_funds()  # Add this line
    return render_template('foreign_funds.html', active_funds=active_funds, settled_funds=settled_funds, foreign_total=foreign_total)


@app.route('/foreign-funds/add', methods=['POST'])
@login_required
def add_foreign_fund():
    try:
        person_name = request.form['person_name']
        amount = Decimal(request.form['amount'])
        note = request.form.get('note', '')
        if amount < 0:
            flash('Amount cannot be negative.', 'error')
            return redirect(url_for('foreign_funds'))
        fund = ForeignFund(person_name=person_name, amount=amount, note=note)
        db.session.add(fund)
        db.session.commit()
        flash('Foreign fund added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding fund: {str(e)}', 'error')
    return redirect(url_for('foreign_funds'))

@app.route('/foreign-funds/edit', methods=['POST'])
@login_required
def edit_foreign_fund():
    try:
        fund_id = request.form.get('fund_id')
        fund = ForeignFund.query.get_or_404(fund_id)
        
        person_name = request.form['person_name']
        amount = Decimal(request.form['amount'])
        note = request.form.get('note', '')
        
        if amount < 0:
            flash('Amount cannot be negative.', 'error')
            return redirect(url_for('foreign_funds'))
        
        fund.person_name = person_name
        fund.amount = amount
        fund.note = note
        
        db.session.commit()
        flash('Foreign fund updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating fund: {str(e)}', 'error')
    return redirect(url_for('foreign_funds'))

@app.route('/foreign-funds/settle/<int:id>')
@login_required
def settle_foreign_fund(id):
    fund = ForeignFund.query.get_or_404(id)
    fund.status = 'settled'
    db.session.commit()
    flash('Fund marked as settled!', 'success')
    return redirect(url_for('foreign_funds'))

@app.route('/foreign-funds/delete/<int:id>')
@login_required
def delete_foreign_fund(id):
    fund = ForeignFund.query.get_or_404(id)
    db.session.delete(fund)
    db.session.commit()
    flash('Foreign fund deleted!', 'success')
    return redirect(url_for('foreign_funds'))

@app.route('/lent-funds')
@login_required
def lent_funds():
    active_funds = LentFund.query.filter_by(status='active').order_by(LentFund.date_lent.desc()).all()
    paid_funds = LentFund.query.filter_by(status='paid').order_by(LentFund.date_lent.desc()).all()
    lent_total = get_total_lent_funds()  # Add this line
    return render_template('lent_funds.html', active_funds=active_funds, paid_funds=paid_funds, lent_total=lent_total)

@app.route('/lent-funds/add', methods=['POST'])
@login_required
def add_lent_fund():
    try:
        borrower_name = request.form['borrower_name']
        amount = Decimal(request.form['amount'])
        note = request.form.get('note', '')
        if amount < 0:
            flash('Amount cannot be negative.', 'error')
            return redirect(url_for('lent_funds'))
        fund = LentFund(borrower_name=borrower_name, amount=amount, note=note)
        db.session.add(fund)
        db.session.commit()
        flash('Lent fund added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding fund: {str(e)}', 'error')
    return redirect(url_for('lent_funds'))

@app.route('/lent-funds/edit', methods=['POST'])
@login_required
def edit_lent_fund():
    try:
        fund_id = request.form.get('fund_id')
        fund = LentFund.query.get_or_404(fund_id)
        
        borrower_name = request.form['borrower_name']
        amount = Decimal(request.form['amount'])
        note = request.form.get('note', '')
        
        if amount < 0:
            flash('Amount cannot be negative.', 'error')
            return redirect(url_for('lent_funds'))
        
        fund.borrower_name = borrower_name
        fund.amount = amount
        fund.note = note
        
        db.session.commit()
        flash('Lent fund updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating fund: {str(e)}', 'error')
    return redirect(url_for('lent_funds'))

@app.route('/lent-funds/pay/<int:id>')
@login_required
def pay_lent_fund(id):
    fund = LentFund.query.get_or_404(id)
    fund.status = 'paid'
    db.session.commit()
    flash('Lent fund marked as paid!', 'success')
    return redirect(url_for('lent_funds'))

@app.route('/lent-funds/delete/<int:id>')
@login_required
def delete_lent_fund(id):
    fund = LentFund.query.get_or_404(id)
    db.session.delete(fund)
    db.session.commit()
    flash('Lent fund deleted!', 'success')
    return redirect(url_for('lent_funds'))

@app.route('/locked-asset-settings', methods=['GET', 'POST'])
@login_required
def locked_asset_settings():
    if request.method == 'POST':
        try:
            equity = Decimal(request.form['equity'])
            locked_asset = Decimal(request.form['locked_asset'])
            ref_rate = Decimal(request.form['ref_rate'])
            if equity < 0 or locked_asset < 0 or ref_rate < 0:
                flash('Values cannot be negative.', 'error')
                return redirect(url_for('locked_asset_settings'))
            save_setting('equity', equity)
            save_setting('locked_asset', locked_asset)
            save_setting('ref_rate', ref_rate)
            flash('Settings saved successfully!', 'success')
        except Exception as e:
            flash(f'Error saving settings: {str(e)}', 'error')
        return redirect(url_for('locked_asset_settings'))
    
    equity = get_latest_setting('equity')
    locked_asset = get_latest_setting('locked_asset')
    ref_rate = get_latest_setting('ref_rate')
    return render_template('locked_asset_settings.html', 
                         equity=equity, 
                         locked_asset=locked_asset, 
                         ref_rate=ref_rate)

@app.route('/reports')
@login_required
def reports():
    today = date.today()
    current_month_calc = Calculation.query.filter_by(
        year=today.year, 
        month=today.month
    ).order_by(Calculation.created_at.desc()).first()
    current_month_profit = current_month_calc.profit if current_month_calc else Decimal('0')
    
    subquery = db.session.query(
        Calculation.year,
        Calculation.month,
        func.max(Calculation.created_at).label('max_created')
    ).group_by(Calculation.year, Calculation.month).subquery()
    
    monthly_profits = db.session.query(Calculation).join(
        subquery,
        (Calculation.year == subquery.c.year) &
        (Calculation.month == subquery.c.month) &
        (Calculation.created_at == subquery.c.max_created)
    ).order_by(Calculation.year.desc(), Calculation.month.desc()).all()
    
    annual_summary = {}
    for calc in monthly_profits:
        key = calc.year
        if key not in annual_summary:
            annual_summary[key] = {
                'year': key,
                'total_profit': Decimal('0'),
                'months_count': 0
            }
        annual_summary[key]['total_profit'] += calc.profit
        annual_summary[key]['months_count'] += 1
    
    if current_month_calc and get_current_day() > 0:
        avg_daily = current_month_calc.profit / Decimal(get_current_day())
    else:
        avg_daily = Decimal('0')
    
    if current_month_calc:
        projected = avg_daily * Decimal(get_current_month_days())
    else:
        projected = Decimal('0')
    
    return render_template('reports.html',
                         current_month_profit=current_month_profit,
                         monthly_profits=monthly_profits,
                         annual_summary=annual_summary,
                         avg_daily_profit=avg_daily,
                         projected_profit=projected)

@app.route('/growth-trend')
@login_required
def growth_trend():
    subquery = db.session.query(
        Calculation.year,
        Calculation.month,
        func.max(Calculation.created_at).label('max_created')
    ).group_by(Calculation.year, Calculation.month).subquery()
    
    monthly_calcs = db.session.query(Calculation).join(
        subquery,
        (Calculation.year == subquery.c.year) &
        (Calculation.month == subquery.c.month) &
        (Calculation.created_at == subquery.c.max_created)
    ).order_by(Calculation.year, Calculation.month).all()
    
    chart_data = []
    table_data = []
    previous_profit = None
    
    for calc in monthly_calcs:
        month_name = date(calc.year, calc.month, 1).strftime('%B')
        profit_value = float(calc.profit)
        
        growth = None
        growth_percentage = None
        
        if previous_profit is not None:
            growth = profit_value - previous_profit
            if previous_profit != 0:
                growth_percentage = (growth / previous_profit) * 100
            else:
                growth_percentage = None
        
        chart_data.append({
            'month': f"{month_name} {calc.year}",
            'profit': profit_value
        })
        
        table_data.append({
            'year': calc.year,
            'month': calc.month,
            'month_name': month_name,
            'profit': calc.profit,
            'growth': growth,
            'growth_percentage': growth_percentage
        })
        
        previous_profit = profit_value
    
    return render_template('growth_trend.html', chart_data=chart_data, table_data=table_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5000))
    
    # Use debug=False in production
    app.run(host='0.0.0.0', port=port, debug=False)