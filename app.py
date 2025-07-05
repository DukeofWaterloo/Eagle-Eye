from flask import Flask, render_template, request, redirect, url_for, flash, g
from services.db_service import DBService
from services.scraper import scrape_google_reviews
from services.ai_service import generate_ai_response
from config import Config
import threading
import time
import os
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from services.alert_service import send_sms_alert
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
import logging
from celery_worker import process_reviews
from flask_mail import Mail

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)
db_service = DBService()

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

mail = Mail(app)
from services import alert_service
alert_service.mail = mail

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    user = db_service.get_user_by_id(user_id)
    if user:
        return User(user[0], user[1])
    return None

# Forms for input validation
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=150)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BusinessSettingsForm(FlaskForm):
    name = StringField('Business Name', validators=[DataRequired()])
    gmb_id = StringField('GMB ID', validators=[DataRequired()])
    phone = StringField('Phone', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    tone = StringField('Tone')
    submit = SubmitField('Save')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        if db_service.get_user_by_username(username):
            flash('Username already exists', 'danger')
            return render_template('register.html', form=form)
        db_service.create_user(username, password)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = db_service.verify_user(username, password)
        if user:
            login_user(User(user[0], user[1]))
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    business_id = request.args.get('business_id', type=int)
    status = request.args.get('status', default='pending')
    search = request.args.get('search')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', default=1, type=int)
    limit = 10
    offset = (page - 1) * limit
    reviews = db_service.get_pending_reviews(
        business_id=business_id,
        status=status,
        search=search,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    businesses = db_service.get_all_businesses()
    return render_template('dashboard.html', reviews=reviews, page=page, limit=limit, search=search, status=status, business_id=business_id, start_date=start_date, end_date=end_date, businesses=businesses)

@app.route('/review/<int:review_id>', methods=['GET', 'POST'])
@login_required
def review_detail(review_id):
    review = db_service.get_review_details(review_id)
    if not review:
        flash('Review not found', 'danger')
        return redirect(url_for('dashboard'))
    feedback_rating = db_service.get_response_feedback(review_id)
    if request.method == 'POST' and 'rating' in request.form:
        rating = int(request.form.get('rating'))
        if 1 <= rating <= 5:
            db_service.save_response_feedback(review_id, rating)
            flash('Thank you for your feedback!', 'success')
        return redirect(url_for('review_detail', review_id=review_id) + '#feedback')
    return render_template('review_detail.html', review=review, feedback_rating=feedback_rating)

@app.route('/respond/<int:review_id>', methods=['POST'])
@login_required
def respond_to_review(review_id):
    response_text = request.form.get('response')
    if not response_text:
        flash('No response provided', 'danger')
        return redirect(url_for('review_detail', review_id=review_id))
    
    if db_service.save_response(review_id, response_text):
        flash('Response saved successfully!', 'success')
    else:
        flash('Failed to save response', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def business_settings():
    business_id = request.args.get('business_id', type=int)
    business = db_service.get_business_by_id(business_id) if business_id else None
    form = BusinessSettingsForm(obj=business) if business else BusinessSettingsForm()
    if form.validate_on_submit():
        name = form.name.data
        gmb_id = form.gmb_id.data
        phone = form.phone.data
        email = form.email.data
        tone = form.tone.data
        if not all([name, gmb_id, phone, email]):
            flash('All fields are required', 'danger')
            return render_template('settings.html', form=form)
        db_service.save_business(name, gmb_id, phone, email, tone, business_id=business_id)
        flash(f'Business "{name}" settings saved!', 'success')
        return redirect(url_for('dashboard'))
    if business:
        form.name.data = business[1]
        form.gmb_id.data = business[2]
        form.phone.data = business[3]
        form.email.data = business[4]
        form.tone.data = business[5]
    return render_template('settings.html', form=form)

@app.before_request
def set_demo_mode_flag():
    g.demo_mode = Config.DEMO_MODE

@app.route('/demo', methods=['GET'])
def demo_mode():
    if not Config.DEMO_MODE:
        flash('Demo mode is not enabled.', 'danger')
        return redirect(url_for('dashboard'))
    # Reset and load demo data
    db_service.conn.rollback()
    with db_service.conn.cursor() as cur:
        cur.execute('TRUNCATE reviews, ai_responses, response_feedback RESTART IDENTITY CASCADE;')
        cur.execute('TRUNCATE businesses RESTART IDENTITY CASCADE;')
        cur.execute("""
            INSERT INTO businesses (name, gmb_account_id, owner_phone, owner_email, response_tone)
            VALUES ('Demo Restaurant', 'demo_place_id', '+1234567890', 'demo@example.com', 'friendly')
            RETURNING id
        """)
        business_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO reviews (business_id, review_text, rating, source, response_status, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'America/Toronto') RETURNING id
        """, (business_id, "The food was absolutely amazing! Best meal I've had in years.", 5, 'google', 'pending'))
        review_id = cur.fetchone()[0]
    db_service.conn.commit()
    # Generate AI responses for the demo review
    responses = generate_ai_response("The food was absolutely amazing! Best meal I've had in years.", "restaurant", "friendly")
    db_service.save_ai_responses(review_id, responses)
    flash('Demo data loaded! You are now in demo mode.', 'info')
    return redirect(url_for('dashboard'))

@app.route('/run-tasks')
@login_required
def run_tasks():
    process_reviews.delay()
    flash('Background review processing started!', 'info')
    return redirect(url_for('dashboard'))

@app.route('/generate-ai-responses')
@login_required
def generate_ai_responses():
    """Manually generate AI responses for reviews that don't have them"""
    try:
        # Get reviews without AI responses
        with db_service.conn.cursor() as cur:
            cur.execute("""
                SELECT r.id, r.review_text, r.rating, b.name, b.response_tone
                FROM reviews r
                JOIN businesses b ON r.business_id = b.id
                LEFT JOIN ai_responses ar ON r.id = ar.review_id
                WHERE ar.review_id IS NULL
                ORDER BY r.created_at DESC
            """)
            reviews_without_ai = cur.fetchall()
        
        if not reviews_without_ai:
            flash('All reviews already have AI responses!', 'info')
            return redirect(url_for('dashboard'))
        
        generated_count = 0
        for review in reviews_without_ai:
            review_id, review_text, rating, business_name, tone = review
            
            try:
                # Generate AI responses
                responses = generate_ai_response(review_text, "restaurant", tone or "professional")
                
                if responses and len(responses) == 3:
                    # Save AI responses
                    db_service.save_ai_responses(review_id, responses)
                    generated_count += 1
                    print(f"Generated AI responses for review {review_id}: {responses}")
                else:
                    print(f"Failed to generate responses for review {review_id}: {responses}")
                    
            except Exception as e:
                print(f"Error generating AI responses for review {review_id}: {e}")
                continue
        
        if generated_count > 0:
            flash(f'Successfully generated AI responses for {generated_count} reviews!', 'success')
        else:
            flash('Failed to generate AI responses. Check the logs for details.', 'danger')
            
    except Exception as e:
        print(f"Error in generate_ai_responses: {e}")
        flash('Error generating AI responses. Check the logs for details.', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/reset-demo', methods=['POST'])
@login_required
def reset_demo():
    if not Config.DEMO_MODE:
        flash('Demo mode is not enabled.', 'danger')
        return redirect(url_for('dashboard'))
    # Reset and load demo data (same as /demo route)
    db_service.conn.rollback()
    with db_service.conn.cursor() as cur:
        cur.execute('TRUNCATE reviews, ai_responses, response_feedback RESTART IDENTITY CASCADE;')
        cur.execute('TRUNCATE businesses RESTART IDENTITY CASCADE;')
        cur.execute("""
            INSERT INTO businesses (name, gmb_account_id, owner_phone, owner_email, response_tone)
            VALUES ('Demo Restaurant', 'demo_place_id', '+1234567890', 'demo@example.com', 'friendly')
            RETURNING id
        """)
        business_id = cur.fetchone()[0]
        cur.execute("""
            INSERT INTO reviews (business_id, review_text, rating, source, response_status, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP AT TIME ZONE 'America/Toronto') RETURNING id
        """, (business_id, "The food was absolutely amazing! Best meal I've had in years.", 5, 'google', 'pending'))
        review_id = cur.fetchone()[0]
    db_service.conn.commit()
    responses = generate_ai_response("The food was absolutely amazing! Best meal I've had in years.", "restaurant", "friendly")
    db_service.save_ai_responses(review_id, responses)
    flash('Demo data has been reset!', 'info')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
