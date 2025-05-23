from models.database import db
from models.admin import  admin_bp, create_super_admin
from models.user import User
from models.subscription import (
    Subscription, SubscribedUser, subscription_required, 
    has_active_subscription, increment_qr_usage, design_access_required,
    has_design_access
)
from flask import g  # For storing subscription info during request
from datetime import datetime, UTC
from models.payment import Payment
from flask import Flask, render_template, request, redirect, send_file, url_for, flash, jsonify, session, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, case, or_, func
from sqlalchemy.orm import relationship, joinedload
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import ImageChops, Image  
import qrcode
from io import BytesIO
import base64
import os
import re
from flask_migrate import Migrate
import razorpay
from decimal import Decimal, ROUND_HALF_UP
from flask_caching import Cache
import uuid
import logging
from datetime import datetime, UTC, timedelta
from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect
import json
from PIL import Image, ImageDraw, ImageFont
import math
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer,
    RoundedModuleDrawer, 
    CircleModuleDrawer,
    VerticalBarsDrawer,
    GappedSquareModuleDrawer,
    HorizontalBarsDrawer
)
from flask_wtf.csrf import CSRFError
from qrcode.image.styles.colormasks import SolidFillColorMask
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask_wtf.csrf import CSRFProtect
from flask import request, flash, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from flask import Flask, session
from flask import request, flash, redirect, url_for
from models.subscription import subscription_bp
# Create the Flask instance at module level
app = Flask(__name__)

# Initialize Flask-Mail and Flask-Login
mail = Mail()
login_manager = LoginManager()

def format_amount(value):
    """Format amount with 2 decimal places"""
    try:
        return "{:.2f}".format(float(value))
    except (ValueError, TypeError):
        return "0.00"

app = Flask(__name__)

# Register custom filters and globals
app.jinja_env.filters['format_amount'] = format_amount
app.jinja_env.globals['hasattr'] = hasattr  # Add hasattr as a global



def create_app():
    # Configure the app
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Devi%401234@localhost:5432/qr_codes'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/uploads'

    # Initialize the shared SQLAlchemy instance with this app
    db.init_app(app)

    # Create tables within app context
    with app.app_context():
        db.create_all()

    # Register blueprints with proper URL prefixes
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(subscription_bp, url_prefix='/subscription')

    app.config['DEFAULT_TIMEZONE'] = os.environ.get('DEFAULT_TIMEZONE', 'Asia/Calcutta')
    #----------------------
    # CSRF Protection
    #----------------------
    # Use a consistent secret key - don't override the one set above
    # app.config['SECRET_KEY'] = os.urandom(24)  # REMOVED - don't override the key
    app.config['WTF_CSRF_ENABLED'] = True  # Enable CSRF protection
    app.config['WTF_CSRF_SECRET_KEY'] = os.urandom(24)  # Generate a random CSRF secret key

    app.config['WTF_CSRF_ENABLED'] = False  # Disable global CSRF protection
    csrf = CSRFProtect(app)
    # Configure token expiration
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # Token valid for 1 hour

    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Strict site origin control
    
    #Selective Route Protection
    @app.before_request
    def csrf_protect():
        """
        Conditionally apply CSRF protection only to authentication routes
        
        Mental Model: 
        - Like a selective security checkpoint
        - Only validates tokens for specific, sensitive routes
        """
        if request.method == "POST":
            # List of routes that require CSRF protection
            protected_routes = [
                'login', 
                'signup', 
                'reset_token', 
                'reset_request', 
                'resend_verification'
            ]
            
            # Check if current route needs protection
            if request.endpoint in protected_routes:
                csrf.protect()
              
    def init_app():
        with app.app_context():
            db.create_all()
            create_super_admin()


    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """
        Provide clear, user-friendly error handling for CSRF token failures
        
        Key Principles:
        - Log the security event
        - Inform user without revealing sensitive details
        - Redirect to a safe page
        """
        # Log the security event for monitoring
        app.logger.warning(
            f"CSRF Token Validation Failed: "
            f"Route: {request.endpoint}, "
            f"Method: {request.method}"
        )
        
        # User-friendly error message
        flash(
            'Your form submission was invalid. Please try again. '
            'If the problem persists, clear your browser cookies and reload the page.', 
            'danger'
        )
        
        # Context-aware redirection
        if request.endpoint == 'login':
            return redirect(url_for('login'))
        elif request.endpoint == 'signup':
            return redirect(url_for('signup'))
        
        return redirect(url_for('index'))
        
    #----------------------
    # Logging configuration
    #----------------------
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flask_app.log')
    logging.basicConfig(
        filename=log_path, 
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.info("Flask app started successfully")

    # Ensure download directory exists
    download_dir = "download_files"
    os.makedirs(download_dir, exist_ok=True)


    # Configure Flask-Caching (simple in-memory)
    app.config['CACHE_TYPE'] = 'simple'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300
    cache = Cache(app)


    # Add Razorpay configuration in your app config section
    app.config['RAZORPAY_KEY_ID'] = 'rzp_test_omIBrvMFqrjDyN'
    app.config['RAZORPAY_KEY_SECRET'] = 'XThGZMtibOTjFjG4wGsuXFD7'
    app.config['RAZORPAY_WEBHOOK_SECRET'] = 'your_webhook_secret'  # Add this if you have webhook integration

    # Initialize Razorpay client
    razorpay_client = razorpay.Client(auth=(app.config['RAZORPAY_KEY_ID'], app.config['RAZORPAY_KEY_SECRET']))
    app.config['RAZORPAY_CLIENT'] = razorpay_client


    # Flask-Mail configuration
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'callincegoodsonmarialouis@gmail.com'
    app.config['MAIL_PASSWORD'] = 'zfol bflm xqsf wtuq'

    mail = Mail(app)

    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'You need to log in to access this page.'
    login_manager.login_message_category = 'info'
    migrate = Migrate(app, db)
    
# QR code style templates - Updated with gradient flag
QR_TEMPLATES = {
    "modern": {
        "shape": "rounded",
        "color": "#3366CC",
        "background_color": "#FFFFFF",
        "custom_eyes": True,
        "inner_eye_style": "circle",
        "outer_eye_style": "rounded",
        "inner_eye_color": "#3366CC",
        "outer_eye_color": "#3366CC",
        "gradient": False  # Not a gradient template
    },
    "corporate": {
        "shape": "square",
        "color": "#000000",
        "background_color": "#FFFFFF",
        "frame_type": "square",
        "frame_color": "#000000",
        "custom_eyes": True,
        "inner_eye_style": "square",
        "outer_eye_style": "square",
        "inner_eye_color": "#000000",
        "outer_eye_color": "#000000",
        "gradient": False  # Not a gradient template
    },
    "playful": {
        "shape": "circle",
        "export_type": "gradient",
        "gradient_start": "#FF5500",
        "gradient_end": "#FFAA00",
        "background_color": "#FFFFFF",
        "custom_eyes": True,
        "inner_eye_style": "circle",
        "outer_eye_style": "circle",
        "inner_eye_color": "#FF5500",
        "outer_eye_color": "#FFAA00",
        "gradient": True  # This IS a gradient template
    },
    "minimal": {
        "shape": "square",
        "color": "#333333",
        "background_color": "#FFFFFF",
        "custom_eyes": True,
        "inner_eye_style": "square",
        "outer_eye_style": "square",
        "inner_eye_color": "#333333",
        "outer_eye_color": "#333333",
        "gradient": False  # Not a gradient template
    },
    "high_contrast": {
        "shape": "square",
        "color": "#000000",
        "background_color": "#FFFFFF",
        "module_size": 20,
        "quiet_zone": 4,
        "custom_eyes": True,
        "inner_eye_style": "square",
        "outer_eye_style": "square",
        "inner_eye_color": "#000000",
        "outer_eye_color": "#000000",
        "gradient": False  # Not a gradient template
    }
}

@app.before_request
def load_subscription_data():
    """Load user's subscription data for the current request"""
    if 'user_id' in session:
        user_id = session.get('user_id')
        # Get active subscription
        active_subscription = (
            SubscribedUser.query
            .filter(SubscribedUser.U_ID == user_id)
            .filter(SubscribedUser.end_date > datetime.now(UTC))
            .filter(SubscribedUser._is_active == True)
            .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
            .first()
        )
        
        if active_subscription:
            # Store subscription info in g object for access during request
            g.subscription = active_subscription
            g.subscription_plan = active_subscription.subscription
            g.has_subscription = True
            g.qr_remaining = active_subscription.get_qr_remaining()
            g.analytics_remaining = active_subscription.get_analytics_remaining()
            g.subscription_tier = active_subscription.subscription.tier
            g.available_designs = active_subscription.subscription.get_designs()
        else:
            g.has_subscription = False
            g.qr_remaining = 0
            g.analytics_remaining = 0
            g.subscription_tier = 0
            g.available_designs = []

# Custom Module Drawer Classes
class DiamondModuleDrawer(SquareModuleDrawer):
    """Custom drawer that draws diamond shapes for modules"""
    
    def drawrect(self, box, is_active):
        """Draw a diamond shape for the module."""
        if not is_active:
            return
        
        x, y, w, h = box
        cx, cy = x + w/2, y + h/2
        size = min(w, h)
        d = size / 2
        
        # Create a diamond shape
        self.draw.polygon([
            (cx, cy - d),  # Top
            (cx + d, cy),  # Right
            (cx, cy + d),  # Bottom
            (cx - d, cy)   # Left
        ], fill=self.color)

class CrossModuleDrawer(SquareModuleDrawer):
    """Custom drawer that draws X/cross shapes for modules"""
    
    def drawrect(self, box, is_active):
        """Draw an X shape for the module."""
        if not is_active:
            return
        
        x, y, w, h = box
        thickness = min(w, h) / 4
        
        # Draw the X shape
        self.draw.polygon([
            (x, y), (x + thickness, y), 
            (x + w, y + h - thickness), (x + w, y + h),
            (x + w - thickness, y + h), (x, y + thickness)
        ], fill=self.color)
        
        self.draw.polygon([
            (x + w, y), (x + w, y + thickness),
            (x + thickness, y + h), (x, y + h),
            (x, y + h - thickness), (x + w - thickness, y)
        ], fill=self.color)

class QRCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unique_id = db.Column(db.String(36), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    qr_type = db.Column(db.String(50), nullable=False)
    is_dynamic = db.Column(db.Boolean, default=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Basic styling
    color = db.Column(db.String(20), default='#000000')
    background_color = db.Column(db.String(20), default='#FFFFFF')
    logo_path = db.Column(db.String(200), nullable=True)
    frame_type = db.Column(db.String(50), nullable=True)
    shape = db.Column(db.String(50), default='square')
    
    # Advanced styling options
    template = db.Column(db.String(50), nullable=True)
    custom_eyes = db.Column(db.Boolean, default=False)
    inner_eye_style = db.Column(db.String(50), nullable=True)
    outer_eye_style = db.Column(db.String(50), nullable=True)
    inner_eye_color = db.Column(db.String(20), nullable=True)
    outer_eye_color = db.Column(db.String(20), nullable=True)
    module_size = db.Column(db.Integer, default=10)
    quiet_zone = db.Column(db.Integer, default=4)
    error_correction = db.Column(db.String(1), default='H')
    
    # NEW GRADIENT COLUMN - Boolean to explicitly track gradient usage
    gradient = db.Column(db.Boolean, nullable=False, default=False)
    
    gradient_start = db.Column(db.String(20), nullable=True)
    gradient_end = db.Column(db.String(20), nullable=True)
    export_type = db.Column(db.String(20), default='png')
    watermark_text = db.Column(db.String(100), nullable=True)
    logo_size_percentage = db.Column(db.Integer, default=25)
    round_logo = db.Column(db.Boolean, default=False)
    frame_text = db.Column(db.String(100), nullable=True)
    
    # New gradient options
    gradient_type = db.Column(db.String(20), nullable=True)
    gradient_direction = db.Column(db.String(20), nullable=True)
    
    # Frame color
    frame_color = db.Column(db.String(20), nullable=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scans = db.relationship('Scan', backref='qr_code', lazy=True)
# Add these models after your existing QRCode class

class QREmail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255), nullable=True)
    body = db.Column(db.Text, nullable=True)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('email_detail', uselist=False))

class QRPhone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=False)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('phone_detail', uselist=False))

class QRSms(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=True)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('sms_detail', uselist=False))

class QRWhatsApp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    phone = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=True)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('whatsapp_detail', uselist=False))

# In your models section, update the QRVCard class:

class QRVCard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    company = db.Column(db.String(100), nullable=True)
    title = db.Column(db.String(100), nullable=True)
    address = db.Column(db.Text, nullable=True)
    website = db.Column(db.String(255), nullable=True)
    
    # New fields for enhanced vCard
    logo_path = db.Column(db.String(200), nullable=True)
    primary_color = db.Column(db.String(20), nullable=True, default='#3366CC')
    secondary_color = db.Column(db.String(20), nullable=True, default='#5588EE')
    social_media = db.Column(db.Text, nullable=True)  # JSON storing social media links
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('vcard_detail', uselist=False))

class QREvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    title = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    start_date = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    organizer = db.Column(db.String(100), nullable=True)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('event_detail', uselist=False))

class QRWifi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    ssid = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(100), nullable=True)
    encryption = db.Column(db.String(20), nullable=True, default='WPA')
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('wifi_detail', uselist=False))

class QRText(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    text = db.Column(db.Text, nullable=False)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('text_detail', uselist=False))

class QRLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False, unique=True)
    url = db.Column(db.String(2000), nullable=False)
    
    # Relationship to parent QR code
    qr_code = db.relationship('QRCode', backref=db.backref('link_detail', uselist=False))

class Scan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    qr_code_id = db.Column(db.Integer, db.ForeignKey('qr_code.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    os = db.Column(db.String(50), nullable=True)

# Add a new model for QR templates
class QRTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    qr_type = db.Column(db.String(50), nullable=False)
    html_content = db.Column(db.Text, nullable=False)
    css_content = db.Column(db.Text, nullable=True)
    js_content = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<QRTemplate {self.name}>"

def get_module_drawer(shape):
    """Get the appropriate module drawer based on shape name with improved support for round and circular shapes"""
    try:
        shapes = {
            'square': SquareModuleDrawer(),
            'rounded': RoundedModuleDrawer(radius_ratio=0.5),  # Increased radius ratio for better rounding
            'circle': CircleModuleDrawer(),
            'vertical_bars': VerticalBarsDrawer(),
            'horizontal_bars': HorizontalBarsDrawer(),
            'gapped_square': GappedSquareModuleDrawer()  # Removed the gap_width parameter
        }
        return shapes.get(shape, SquareModuleDrawer())
    except Exception as e:
        print(f"Error getting module drawer: {str(e)}")
        return SquareModuleDrawer()
# Enhanced Subscription Model
@app.template_filter('nl2br')
def nl2br(value):
    """Convert newlines to HTML line breaks."""
    if value:
        return value.replace('\n', '<br>')
    return value

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
                          error_code=404,
                          error_message="QR Code not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', 
                          error_code=500,
                          error_message="An unexpected error occurred"), 500

@app.template_filter('date')
def date_filter(value, format='%Y-%m-%d'):
    """
    Custom Jinja2 filter to format datetime objects with timezone support
    
    Args:
        value: datetime object or string
        format: desired output format string
    
    Returns:
        Formatted date string
    """
    if value is None:
        return ''
    
    # If it's a string, try to parse it
    if isinstance(value, str):
        try:
            # Try parsing with multiple possible formats
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',  # Most common datetime format
                '%Y-%m-%dT%H:%M:%S',  # ISO format
                '%Y-%m-%d',           # Date only
                '%Y-%m-%d %H:%M',     # Datetime without seconds
            ]
            
            for fmt in formats_to_try:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format matches, return original string
                return value
        except Exception:
            return value
    
    # If it's already a datetime object, localize and format it
    if isinstance(value, datetime):
        # Convert to local timezone
        localized = get_localized_datetime(value)
        return localized.strftime(format)
    
    return str(value)

# ----------------------
# Login Required Decorator
# ----------------------
from functools import wraps

def login_required(f):
    @wraps(f)  # Preserve function metadata
    def wrap(*args, **kwargs):
        if 'user_id' not in session:
            flash("You need to log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

# ----------------------
#custom email validation
# ----------------------
# Function to send email verification
def send_verification_email(user):
    token = user.get_email_confirm_token()
    msg = Message('Email Verification',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.company_email])
    msg.body = f'''To verify your email address, please click the following link:

{url_for('verify_email', token=token, _external=True)}

This link will expire in 24 hours.

If you did not create an account, please ignore this email.

Thanks,
Your Team
'''
    mail.send(msg)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[user.company_email])
    msg.body = f'''To reset your password, click the following link:

{url_for('reset_token', token=token, _external=True)}

If you did not request this, please ignore this email.

Thanks,
Your Team
'''
    mail.send(msg)

application = create_app()
# ---------------------------------------
# user login signup and reset password
# ---------------------------------------

@app.route('/')
def index():
        return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
        if request.method == 'POST':
            company_email = request.form.get('companyEmail')
            password = request.form.get('password')
            
            # Validate user using SQLAlchemy
            user = User.query.filter_by(company_email=company_email).first()
            
            if not user:
                flash("Invalid email or password.", "danger")
                return redirect(url_for('login'))
            
            if not user.email_confirmed:
                flash("Please verify your email before logging in. Check your inbox or request a new verification link.", "warning")
                return redirect(url_for('resend_verification'))
            
            if user.check_password(password):
                login_user(user)  # Using Flask-Login
                session['user_id'] = user.id
                session['user_name'] = user.name
                flash("Login successful!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password.", "danger")
                return redirect(url_for('login'))
                
        return render_template('login.html')
@app.route('/register', methods=['GET', 'POST'])
def register():
    return signup()  

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        company_email = request.form.get('companyEmail')
        password = request.form.get('password')
        retype_password = request.form.get('retypePassword')
        
        # Enhanced input validation
        errors = []
        
        # Name validation
        if not name or len(name.strip()) < 2:
            errors.append("Name should be at least 2 characters long.")
        
        # Email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not company_email or not re.match(email_pattern, company_email):
            errors.append("Please enter a valid email address.")
        
        # Password validation
        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        elif not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter.")
        elif not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter.")
        elif not re.search(r'[0-9]', password):
            errors.append("Password must contain at least one number.")
        elif not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character.")
        
        # Password confirmation validation
        if password != retype_password:
            errors.append("Passwords do not match.")
        
        # Check if email already exists
        existing_user = User.query.filter_by(company_email=company_email).first()
        if existing_user:
            errors.append("This email is already registered.")
        
        # If there are any errors, flash them and redirect back to signup
        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template('signup.html', name=name, company_email=company_email)
        
       
        # Create new user with email verification required
        new_user = User(name=name, company_email=company_email, email_confirmed=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
            
            # Send verification email
        try:
            send_verification_email(new_user)
            flash("Signup successful! Please check your email to verify your account.", "success")
        except Exception as e:
            logging.error(f"Error sending verification email: {str(e)}")
            flash("Signup successful but there was an issue sending the verification email. Please contact support.", "warning")
        
        return redirect(url_for('verify_account'))
    return render_template('signup.html')

@app.route("/verify_account")
def verify_account():
    email = request.args.get('email')
    return render_template('verify_account.html', email=email)

@app.route('/verify_email/<token>')
def verify_email(token):
    user = User.verify_email_token(token)
    if user is None:
        flash('Invalid or expired verification link. Please request a new one.', 'danger')
        return redirect(url_for('resend_verification'))
    
    user.email_confirmed = True
    user.email_confirm_token = None
    user.email_token_created_at = None
    db.session.commit()
    
    flash('Your email has been verified! You can now log in.', 'success')
    return redirect(url_for('login'))

@app.route('/resend_verification', methods=['GET', 'POST'])
def resend_verification():
    if request.method == 'POST':
        email = request.form.get('companyEmail')
        user = User.query.filter_by(company_email=email).first()
        
        if user and not user.email_confirmed:
            try:
                send_verification_email(user)
                flash('A new verification email has been sent.', 'success')
            except Exception as e:
                logging.error(f"Error resending verification email: {str(e)}")
                flash('There was an issue sending the verification email. Please try again later.', 'danger')
        elif user and user.email_confirmed:
            flash('This email is already verified. You can log in.', 'info')
        else:
            flash('Email not found. Please sign up first.', 'warning')
            
        return redirect(url_for('login'))
    
    return render_template('resend_verification.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('companyEmail')
        user = User.query.filter_by(company_email=email).first()
        if user:
            send_reset_email(user)
            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('login'))
        else:
            flash('Email not found. Please register first.', 'warning')
    return render_template('reset_request.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    try:
        # Try to verify the token
        user = User.verify_reset_token(token)
        if not user:
            flash('Invalid or expired token. Please request a new password reset link.', 'danger')
            return redirect(url_for('reset_request'))

        if request.method == 'POST':
            # Handle password reset logic here
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate passwords
            if not password or not confirm_password:
                flash('Both password fields are required', 'danger')
                return render_template('reset_token.html', token=token)
            
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('reset_token.html', token=token)
            
            if len(password) < 8:
                flash('Password must be at least 8 characters long', 'danger')
                return render_template('reset_token.html', token=token)

            # Update password
            user.set_password(password)
            user.password_reset_at = datetime.now(UTC)
            db.session.commit()

            flash('Your password has been updated! You can now log in with your new password.', 'success')
            return redirect(url_for('login'))

    except Exception as e:
        # Log any errors
        logging.error(f"Error during password reset: {str(e)}")
        flash('An error occurred during the password reset process. Please try again.', 'danger')
        return redirect(url_for('reset_request'))

    # If method is GET, render the reset password page
    return render_template('reset_token.html', token=token)


@app.route('/logout')
@login_required
def logout():
    logout_user()  # Flask-Login function
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('index'))

# ---------------------------------------
# Profile Management Routes
# ---------------------------------------

@app.route('/profile')
@login_required
def profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    # Get user's active subscription if any
    subscription = (
        db.session.query(SubscribedUser)
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
        .first()
    )
    
    # Get recent payments
    payments = (
        Payment.query
        .filter_by(user_id=user_id)
        .order_by(Payment.created_at.desc())
        .limit(10)
        .all()
    )
    
    # Count total QR codes for the user
    qr_count = QRCode.query.filter_by(user_id=user_id).count()
    
    # Calculate today's date range
    today = datetime.now(UTC).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)
    
    # Count QR codes created today
    qr_created_today = QRCode.query.filter_by(user_id=user_id).filter(
        QRCode.created_at >= today_start,
        QRCode.created_at <= today_end
    ).count()
    
    return render_template(
        'profile.html',
        user=user,
        subscription=subscription,
        payments=payments,
        qr_count=qr_count,
        scans_today=qr_created_today  # Using the created_today count
    )

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('profile'))
    
    update_type = request.form.get('update_type', 'account')
    
    if update_type == 'account':
        # Update name
        name = request.form.get('name')
        if name and name.strip():
            user.name = name.strip()
            session['user_name'] = name.strip()  # Update session data too
            
        db.session.commit()
        flash('Profile information updated successfully', 'success')
        return redirect(url_for('profile') + '#account')
        
    elif update_type == 'security':
        # Process password change
        current_password = request.form.get('currentPassword')
        new_password = request.form.get('newPassword')
        confirm_password = request.form.get('confirmPassword')
        
        # Validate input fields
        if not all([current_password, new_password, confirm_password]):
            flash('All password fields are required', 'danger')
            return redirect(url_for('profile') + '#security')
        
        # Verify current password
        if not user.check_password(current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('profile') + '#security')
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('profile') + '#security')
        
        # Password complexity validation
        password_errors = []
        if len(new_password) < 8:
            password_errors.append('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', new_password):
            password_errors.append('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', new_password):
            password_errors.append('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', new_password):
            password_errors.append('Password must contain at least one number')
        if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', new_password):
            password_errors.append('Password must contain at least one special character')
        
        if password_errors:
            for error in password_errors:
                flash(error, 'danger')
            return redirect(url_for('profile') + '#security')
        
        # Check if new password is different from current
        if user.check_password(new_password):
            flash('New password must be different from current password', 'warning')
            return redirect(url_for('profile') + '#security')
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        # Log the password change (optional)
        logging.info(f"Password changed for user ID {user_id}")
        
        flash('Password updated successfully. Please use your new password next time you log in.', 'success')
        return redirect(url_for('profile') + '#security')
    
    # If we get here, something went wrong
    flash('Invalid update request', 'danger')
    return redirect(url_for('profile'))

# Generate a downloadable payment receipt
@app.route('/receipt/<payment_id>')
@login_required
def download_receipt(payment_id):
    user_id = session.get('user_id')
    
    # Get payment details
    payment = Payment.query.filter_by(id=payment_id, user_id=user_id).first_or_404()
    
    # TODO: Generate and return PDF receipt
    # This would typically use a PDF generation library like ReportLab or WeasyPrint
    
    flash('Receipt download feature coming soon!', 'info')
    return redirect(url_for('profile') + '#activity')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = current_user.id
    
    # Get user's QR codes
    qr_codes = QRCode.query.filter_by(user_id=user_id).all()
    
    # Get active subscription data
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
        .first()
    )
    
    # Prepare subscription data for template
    subscription_data = {
        'has_subscription': False,
        'plan_name': 'No Subscription',
        'days_remaining': 0,
        'qr_remaining': 0,
        'qr_limit': 0,
        'qr_percent': 0,
        'expires_on': None,
        'is_auto_renew': False,
        'subscription_id': None,
        'analytics_used': 0,
        'analytics_limit': 0,
        'analytics_percent': 0
    }
    
    if active_subscription:
        subscription_data.update({
            'has_subscription': True,
            'plan_name': active_subscription.subscription.plan,
            'days_remaining': active_subscription.days_remaining,
            'qr_remaining': active_subscription.get_qr_remaining(),
            'qr_limit': active_subscription.subscription.qr_count,
            'qr_percent': active_subscription.qr_percent,
            'expires_on': active_subscription.end_date,
            'is_auto_renew': active_subscription.is_auto_renew,
            'subscription_id': active_subscription.id,
            'analytics_used': active_subscription.analytics_used,
            'analytics_limit': active_subscription.subscription.analytics,
            'analytics_percent': active_subscription.analytics_percent
        })
    
    # Count total QR codes
    total_qr_codes = len(qr_codes)
    
    # Count QR codes created today
    today = datetime.now(UTC).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)
    
    qr_created_today = QRCode.query.filter_by(user_id=user_id).filter(
        QRCode.created_at >= today_start,
        QRCode.created_at <= today_end
    ).count()
    
    return render_template('dashboard.html', 
                          qr_codes=qr_codes,
                          subscription=subscription_data,
                          total_qr_codes=total_qr_codes,
                          qr_created_today=qr_created_today)

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_qr():
    user_id = session.get('user_id')
    
    # Check if user has an active subscription
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .first()
    )
    
    if not active_subscription:
        flash('You need an active subscription to create QR codes.', 'warning')
        return redirect(url_for('subscription.user_subscriptions'))
    
    # Check if user has reached QR generation limit
    if active_subscription.qr_generated >= active_subscription.subscription.qr_count:
        flash('You have reached your QR code generation limit for this subscription plan.', 'warning')
        return redirect(url_for('subscription.user_subscriptions'))
    
    if request.method == 'POST':
        try:
            # Extract basic QR code information
            qr_type = request.form.get('qr_type')
            name = request.form.get('name')
            is_dynamic = 'is_dynamic' in request.form and request.form.get('is_dynamic') == 'true'
            
            # Check if dynamic QR is allowed for this subscription
            if is_dynamic and active_subscription.subscription.tier < 2:
                flash('Your subscription plan does not include dynamic QR codes.', 'warning')
                return redirect(url_for('create_qr'))
            
            # Check if selected design is allowed for user's subscription
            selected_template = request.form.get('template', '')
            if selected_template and not active_subscription.is_design_allowed(selected_template):
                flash(f'Your subscription plan does not include access to the {selected_template} design.', 'warning')
                return redirect(url_for('create_qr'))
            
            # Validate required fields
            if not name or not qr_type:
                missing = []
                if not name:
                    missing.append("QR code name")
                if not qr_type:
                    missing.append("QR type")
                flash(f'Required fields missing: {", ".join(missing)}', 'error')
                return redirect(url_for('create_qr'))
            
            # Create empty content JSON for backward compatibility
            content = {}
            
            # Basic QR code styling options
            template = request.form.get('template', '')
            color = request.form.get('color', '#000000')
            if not color or color.strip() == '' or color == 'undefined' or color == 'null':
                color = '#000000'
            
            background_color = request.form.get('background_color', '#FFFFFF')
            if not background_color or background_color.strip() == '' or background_color == 'undefined':
                background_color = '#FFFFFF'
                
            shape = request.form.get('shape', 'square')
            frame_type = request.form.get('frame_type', '')
            frame_text = request.form.get('frame_text', '')
            
            # Get frame color if a frame is selected
            frame_color = None
            if frame_type:
                frame_color = request.form.get('frame_color', color)
            
            # IMPROVED GRADIENT DETECTION - Check explicit gradient selection
            using_gradient = False
            gradient_start = ''
            gradient_end = ''
            
            # Check if user explicitly selected gradient
            export_type = request.form.get('export_type', 'png')
            if export_type == 'gradient':
                using_gradient = True
            
            # Check if gradient is enabled via checkbox or form field
            if 'using_gradient' in request.form and request.form.get('using_gradient') == 'true':
                using_gradient = True
            
            # Check if template has gradient and user didn't override
            if template and template in QR_TEMPLATES:
                template_config = QR_TEMPLATES[template]
                if template_config.get('export_type') == 'gradient':
                    using_gradient = True
                    # Use template gradient colors if not provided by user
                    gradient_start = request.form.get('gradient_start', template_config.get('gradient_start', '#FF5500'))
                    gradient_end = request.form.get('gradient_end', template_config.get('gradient_end', '#FFAA00'))
            
            # Get gradient colors from form if using gradient
            if using_gradient:
                gradient_start = request.form.get('gradient_start', gradient_start or '#FF5500')
                gradient_end = request.form.get('gradient_end', gradient_end or '#FFAA00')
                export_type = 'gradient'  # Force export type to gradient
            
            print(f"Gradient settings - Using: {using_gradient}, Start: {gradient_start}, End: {gradient_end}")
            
            # Check if using custom eyes
            custom_eyes = 'custom_eyes' in request.form and request.form.get('custom_eyes') == 'true'
            if 'using_custom_eyes' in request.form and request.form.get('using_custom_eyes') == 'true':
                custom_eyes = True
            
            # Inner and outer eye styles and colors
            inner_eye_style = request.form.get('inner_eye_style', 'circle' if custom_eyes else '')
            outer_eye_style = request.form.get('outer_eye_style', 'rounded' if custom_eyes else '')
            
            # Handle eye colors
            inner_eye_color = request.form.get('inner_eye_color', '')
            outer_eye_color = request.form.get('outer_eye_color', '')
            
            if not inner_eye_color or inner_eye_color == 'undefined':
                inner_eye_color = gradient_start if using_gradient and gradient_start else color
            if not outer_eye_color or outer_eye_color == 'undefined':
                outer_eye_color = gradient_end if using_gradient and gradient_end else color
            
            # Other advanced settings
            module_size = int(request.form.get('module_size', 10))
            quiet_zone = int(request.form.get('quiet_zone', 4))
            error_correction = request.form.get('error_correction', 'H')
            watermark_text = request.form.get('watermark_text', '')
            
            # Gradient settings
            gradient_type = request.form.get('gradient_type', 'linear')
            gradient_direction = request.form.get('gradient_direction', 'to-right')
            
            # Logo settings
            logo_size_percentage = int(request.form.get('logo_size_percentage', 25))
            round_logo = 'round_logo' in request.form and request.form.get('round_logo') == 'true'
            
            # Create base QR code record with the new gradient column
            new_qr = QRCode(
                unique_id=str(uuid.uuid4()),
                name=name,
                qr_type=qr_type,
                is_dynamic=is_dynamic,
                content=json.dumps(content),
                color=color,
                background_color=background_color,
                frame_type=frame_type,
                frame_color=frame_color,
                shape=shape,
                template=template,
                custom_eyes=custom_eyes,
                inner_eye_style=inner_eye_style,
                outer_eye_style=outer_eye_style,
                inner_eye_color=inner_eye_color,
                outer_eye_color=outer_eye_color,
                module_size=module_size,
                quiet_zone=quiet_zone,
                error_correction=error_correction,
                export_type=export_type,
                watermark_text=watermark_text,
                
                # NEW GRADIENT COLUMN - Set based on user selection
                gradient=using_gradient,
                
                gradient_start=gradient_start if using_gradient else None,
                gradient_end=gradient_end if using_gradient else None,
                gradient_type=gradient_type if using_gradient else None,
                gradient_direction=gradient_direction if using_gradient else None,
                logo_size_percentage=logo_size_percentage,
                round_logo=round_logo,
                frame_text=frame_text,
                user_id=current_user.id
            )
            
            # Handle logo upload with improved path handling
            logo_path = fix_logo_path_handling(request, new_qr)
            new_qr.logo_path = logo_path

            # Save the base QR record to get an ID
            db.session.add(new_qr)
            db.session.flush()  # Get ID without committing
            
            # Now create the specific QR type record based on the type
            # [Rest of the QR type specific code remains the same...]
            if qr_type == 'link':
                link_detail = QRLink(
                    qr_code_id=new_qr.id,
                    url=request.form.get('url', 'https://example.com')
                )
                db.session.add(link_detail)
                
            elif qr_type == 'email':
                email_detail = QREmail(
                    qr_code_id=new_qr.id,
                    email=request.form.get('email', ''),
                    subject=request.form.get('subject', ''),
                    body=request.form.get('body', '')
                )
                db.session.add(email_detail)
                
            elif qr_type == 'text':
                text_detail = QRText(
                    qr_code_id=new_qr.id,
                    text=request.form.get('text', '')
                )
                db.session.add(text_detail)
                
            elif qr_type == 'call':
                phone_detail = QRPhone(
                    qr_code_id=new_qr.id,
                    phone=request.form.get('phone', '')
                )
                db.session.add(phone_detail)
                
            elif qr_type == 'sms':
                sms_detail = QRSms(
                    qr_code_id=new_qr.id,
                    phone=request.form.get('sms-phone') or request.form.get('phone', ''),
                    message=request.form.get('message', '')
                )
                db.session.add(sms_detail)
                
            elif qr_type == 'whatsapp':
                whatsapp_detail = QRWhatsApp(
                    qr_code_id=new_qr.id,
                    phone=request.form.get('whatsapp-phone') or request.form.get('phone', ''),
                    message=request.form.get('whatsapp-message') or request.form.get('message', '')
                )
                db.session.add(whatsapp_detail)
                
            elif qr_type == 'wifi':
                wifi_detail = QRWifi(
                    qr_code_id=new_qr.id,
                    ssid=request.form.get('ssid', ''),
                    password=request.form.get('password', ''),
                    encryption=request.form.get('encryption', 'WPA')
                )
                db.session.add(wifi_detail)
                
            # [Continue with other QR types as in original code...]
            
            # Increment QR usage for the subscription
            active_subscription.qr_generated += 1
            
            # Commit all changes
            db.session.commit()
            
            flash('QR Code created successfully!', 'success')
            return redirect(url_for('view_qr', qr_id=new_qr.unique_id))
            
        except Exception as e:
            import traceback
            app.logger.error(f"Error creating QR code: {str(e)}")
            app.logger.error(traceback.format_exc())
            db.session.rollback()
            flash(f'Error creating QR code: {str(e)}', 'error')
            return redirect(url_for('create_qr'))
    
    # For GET request, show the form
    available_templates = []
    if active_subscription and active_subscription.subscription.design:
        available_templates = active_subscription.subscription.get_designs()
    
    qr_limit = 0
    qr_used = 0
    qr_remaining = 0
    
    if active_subscription:
        qr_limit = active_subscription.subscription.qr_count
        qr_used = active_subscription.qr_generated
        qr_remaining = max(0, qr_limit - qr_used)
    
    can_create_dynamic = active_subscription.subscription.tier >= 2 if active_subscription else False
    
    return render_template('create_qr.html', 
                          qr_templates=QR_TEMPLATES,
                          available_templates=available_templates,
                          qr_limit=qr_limit,
                          qr_used=qr_used,
                          qr_remaining=qr_remaining,
                          can_create_dynamic=can_create_dynamic)

@app.route('/preview-qr', methods=['GET', 'POST'])
def preview_qr():
    from flask import Response
    
    try:
        # Check for user authentication
        if not current_user.is_authenticated:
            # For preview, create a temporary response if not logged in
            temp_img = qrcode.make("Example QR Code").get_image()
            buffered = BytesIO()
            temp_img.save(buffered, format="PNG")
            img_data = buffered.getvalue()
            return Response(img_data, mimetype='image/png')
        
        # Extract parameters from either form data (POST) or query string (GET)
        if request.method == 'POST':
            qr_type = request.form.get('qr_type', 'link')
            name = request.form.get('name', 'Preview')
            is_dynamic = 'is_dynamic' in request.form and request.form.get('is_dynamic') == 'true'
            color = request.form.get('color', '#000000')
            if not color or color.strip() == '' or color == 'undefined':
                color = '#000000'
            background_color = request.form.get('background_color', '#FFFFFF')
            if not background_color or background_color.strip() == '' or background_color == 'undefined':
                background_color = '#FFFFFF'
            shape = request.form.get('shape', 'square')
            template = request.form.get('template', '')
            frame_type = request.form.get('frame_type', '')
            frame_text = request.form.get('frame_text', '')
            custom_eyes = 'custom_eyes' in request.form and request.form.get('custom_eyes') == 'true'
            inner_eye_style = request.form.get('inner_eye_style', '')
            outer_eye_style = request.form.get('outer_eye_style', '')
            inner_eye_color = request.form.get('inner_eye_color', '')
            outer_eye_color = request.form.get('outer_eye_color', '')
            module_size = int(request.form.get('module_size', 10))
            quiet_zone = int(request.form.get('quiet_zone', 4))
            error_correction = request.form.get('error_correction', 'H')
            export_type = request.form.get('export_type', 'png')
            gradient_start = request.form.get('gradient_start', '')
            gradient_end = request.form.get('gradient_end', '')
            watermark_text = request.form.get('watermark_text', '')
            logo_size_percentage = int(request.form.get('logo_size_percentage', 25))
            round_logo = 'round_logo' in request.form and request.form.get('round_logo') == 'true'
        else:  # GET request
            qr_type = request.args.get('qr_type', 'link')
            name = request.args.get('name', 'Preview')
            is_dynamic = 'is_dynamic' in request.args and request.args.get('is_dynamic') == 'true'
            color = request.args.get('color', '#000000')
            if not color or color.strip() == '' or color == 'undefined':
                color = '#000000'
            background_color = request.args.get('background_color', '#FFFFFF')
            if not background_color or background_color.strip() == '' or background_color == 'undefined':
                background_color = '#FFFFFF'
            shape = request.args.get('shape', 'square')
            template = request.args.get('template', '')
            frame_type = request.args.get('frame_type', '')
            frame_text = request.args.get('frame_text', '')
            custom_eyes = 'custom_eyes' in request.args and request.args.get('custom_eyes') == 'true'
            inner_eye_style = request.args.get('inner_eye_style', '')
            outer_eye_style = request.args.get('outer_eye_style', '')
            inner_eye_color = request.args.get('inner_eye_color', '')
            outer_eye_color = request.args.get('outer_eye_color', '')
            module_size = int(request.args.get('module_size', 10))
            quiet_zone = int(request.args.get('quiet_zone', 4))
            error_correction = request.args.get('error_correction', 'H')
            export_type = request.args.get('export_type', 'png')
            gradient_start = request.args.get('gradient_start', '')
            gradient_end = request.args.get('gradient_end', '')
            watermark_text = request.args.get('watermark_text', '')
            logo_size_percentage = int(request.args.get('logo_size_percentage', 25))
            round_logo = 'round_logo' in request.args and request.args.get('round_logo') == 'true'
        
        # Handle ID parameter for directly fetching QR content from database
        qr_id = request.form.get('id', '') if request.method == 'POST' else request.args.get('id', '')
        if qr_id:
            # Try to fetch the QR code from database
            qr_from_db = QRCode.query.filter_by(unique_id=qr_id).first()
            if qr_from_db:
                # Generate QR code image using the stored settings
                qr_image, _ = generate_qr_code(qr_from_db)
                
                # If base64 data URL, convert back to binary
                if qr_image.startswith('data:'):
                    header, encoded = qr_image.split(",", 1)
                    img_data = base64.b64decode(encoded)
                else:
                    img_data = base64.b64decode(qr_image)
                
                return Response(img_data, mimetype='image/png')
        
        # Build content based on QR type
        content = {}
        if qr_type == 'link':
            if request.method == 'POST':
                content['url'] = request.form.get('url', 'https://example.com')
            else:
                content['url'] = request.args.get('url', 'https://example.com')
        elif qr_type == 'email':
            if request.method == 'POST':
                content['email'] = request.form.get('email', '')
                content['subject'] = request.form.get('subject', '')
                content['body'] = request.form.get('body', '')
            else:
                content['email'] = request.args.get('email', '')
                content['subject'] = request.args.get('subject', '')
                content['body'] = request.args.get('body', '')
        elif qr_type == 'text':
            if request.method == 'POST':
                content['text'] = request.form.get('text', '')
            else:
                content['text'] = request.args.get('text', '')
        elif qr_type == 'call':
            if request.method == 'POST':
                content['phone'] = request.form.get('phone', '')
            else:
                content['phone'] = request.args.get('phone', '')
        elif qr_type == 'sms':
            if request.method == 'POST':
                content['phone'] = request.form.get('sms-phone') or request.form.get('phone', '')
                content['message'] = request.form.get('message', '')
            else:
                content['phone'] = request.args.get('sms-phone') or request.args.get('phone', '')
                content['message'] = request.args.get('message', '')
        elif qr_type == 'whatsapp':
            if request.method == 'POST':
                content['phone'] = request.form.get('whatsapp-phone') or request.form.get('phone', '')
                content['message'] = request.form.get('whatsapp-message') or request.form.get('message', '')
            else:
                content['phone'] = request.args.get('whatsapp-phone') or request.args.get('phone', '')
                content['message'] = request.args.get('whatsapp-message') or request.args.get('message', '')
        elif qr_type == 'wifi':
            if request.method == 'POST':
                content['ssid'] = request.form.get('ssid', '')
                content['password'] = request.form.get('password', '')
                content['encryption'] = request.form.get('encryption', 'WPA')
            else:
                content['ssid'] = request.args.get('ssid', '')
                content['password'] = request.args.get('password', '')
                content['encryption'] = request.args.get('encryption', 'WPA')
        elif qr_type == 'vcard':
            if request.method == 'POST':
                content['name'] = request.form.get('full_name', '')
                content['phone'] = request.form.get('vcard-phone') or request.form.get('phone', '')
                content['email'] = request.form.get('vcard-email') or request.form.get('email', '')
                content['company'] = request.form.get('company', '')
                content['title'] = request.form.get('title', '')
                content['address'] = request.form.get('address', '')
                content['website'] = request.form.get('website', '')
            else:
                content['name'] = request.args.get('full_name', '')
                content['phone'] = request.args.get('vcard-phone') or request.args.get('phone', '')
                content['email'] = request.args.get('vcard-email') or request.args.get('email', '')
                content['company'] = request.args.get('company', '')
                content['title'] = request.args.get('title', '')
                content['address'] = request.args.get('address', '')
                content['website'] = request.args.get('website', '')
        elif qr_type == 'event':
            if request.method == 'POST':
                content['title'] = request.form.get('event-title') or request.form.get('title', '')
                content['location'] = request.form.get('location', '')
                content['start_date'] = request.form.get('start_date', '')
                content['end_time'] = request.form.get('end_time', '')
                content['description'] = request.form.get('description', '')
                content['organizer'] = request.form.get('organizer', '')
            else:
                content['title'] = request.args.get('event-title') or request.args.get('title', '')
                content['location'] = request.args.get('location', '')
                content['start_date'] = request.args.get('start_date', '')
                content['end_time'] = request.args.get('end_time', '')
                content['description'] = request.args.get('description', '')
                content['organizer'] = request.args.get('organizer', '')
        
        # Handle logo preview
        logo_file = None
        if request.method == 'POST' and 'logo' in request.files and request.files['logo'].filename:
            logo_file = request.files['logo']
            
        # Create temporary QR code object
        temp_qr = QRCode(
            unique_id="preview",
            name=name,
            qr_type=qr_type,
            is_dynamic=is_dynamic,
            content=json.dumps(content),
            color=color,
            background_color=background_color,
            shape=shape,
            template=template,
            frame_type=frame_type,
            frame_text=frame_text,
            custom_eyes=custom_eyes,
            inner_eye_style=inner_eye_style,
            outer_eye_style=outer_eye_style,
            inner_eye_color=inner_eye_color,
            outer_eye_color=outer_eye_color,
            module_size=module_size,
            quiet_zone=quiet_zone,
            error_correction=error_correction,
            export_type=export_type,
            gradient_start=gradient_start,
            gradient_end=gradient_end,
            watermark_text=watermark_text,
            logo_size_percentage=logo_size_percentage,
            round_logo=round_logo,
            user_id=current_user.id if current_user.is_authenticated else 0
        )
        
        # Handle temp logo file if uploaded
        temp_logo_path = None
        if logo_file:
            # Create a temporary directory if it doesn't exist
            temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Save the logo temporarily
            temp_filename = f"temp_{uuid.uuid4()}.{logo_file.filename.split('.')[-1]}"
            temp_logo_path = os.path.join(temp_dir, temp_filename)
            logo_file.save(temp_logo_path)
            temp_qr.logo_path = temp_logo_path
        
        # Generate QR code image
        qr_image, _ = generate_qr_code(temp_qr)
        
        # Clean up temporary logo file if it was created
        if temp_logo_path and os.path.exists(temp_logo_path):
            try:
                os.remove(temp_logo_path)
            except:
                # Continue even if cleanup fails
                pass
        
        # If base64 data URL, convert back to binary
        if qr_image.startswith('data:'):
            header, encoded = qr_image.split(",", 1)
            img_data = base64.b64decode(encoded)
        else:
            img_data = base64.b64decode(qr_image)
        
        # Return the image
        return Response(img_data, mimetype='image/png')
    
    except Exception as e:
        app.logger.error(f"Error in preview_qr: {str(e)}")
        # Return a fallback/error image
        try:
            error_qr = qrcode.make("Error generating QR preview").get_image()
            buffered = BytesIO()
            error_qr.save(buffered, format="PNG")
            img_data = buffered.getvalue()
            return Response(img_data, mimetype='image/png')
        except:
            # If all else fails, return an empty response
            return Response(status=500)
        
# 4. Fixed preview_qr function logo handling
def preview_qr_logo_handling(logo_file, temp_qr):
    """Handle logo file for QR preview - extracted from preview_qr function"""
    temp_logo_path = None
    
    if logo_file and logo_file.filename:
        try:
            # Create a temporary directory if it doesn't exist
            temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Get file extension
            file_ext = os.path.splitext(logo_file.filename)[1].lower()
            if not file_ext or file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
                file_ext = '.png'  # Default to PNG
            
            # Save the logo temporarily with unique name
            temp_filename = f"temp_{uuid.uuid4()}{file_ext}"
            temp_logo_path = os.path.join(temp_dir, temp_filename)
            logo_file.save(temp_logo_path)
            
            # Verify file was saved
            if not os.path.exists(temp_logo_path):
                app.logger.error(f"Failed to save temp logo: {temp_logo_path}")
            elif os.path.getsize(temp_logo_path) == 0:
                app.logger.error(f"Temp logo file is empty: {temp_logo_path}")
                os.remove(temp_logo_path)
                temp_logo_path = None
            else:
                temp_qr.logo_path = temp_logo_path
                app.logger.info(f"Temp logo saved to: {temp_logo_path}")
        except Exception as e:
            app.logger.error(f"Error handling logo upload in preview: {str(e)}")
            import traceback
            app.logger.error(traceback.format_exc())
    
    return temp_logo_path

@app.route('/qr/<qr_id>')
@login_required
def view_qr(qr_id):
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    # Ensure the QR code belongs to the current user
    if qr_code.user_id != current_user.id:
        flash('You do not have permission to view this QR code.')
        return redirect(url_for('dashboard'))

    # Generate QR code image
    qr_image, qr_info = generate_qr_code(qr_code)

    # Get scan statistics if dynamic
    scans = []
    if qr_code.is_dynamic:
        scans = Scan.query.filter_by(qr_code_id=qr_code.id).all()

    # ✅ Fix logo_path safely
    if qr_code.logo_path:
        if not qr_code.logo_path.startswith('uploads/'):
            qr_code.logo_path = os.path.join('uploads', qr_code.logo_path).replace('\\', '/')
        else:
            qr_code.logo_path = qr_code.logo_path.replace('\\', '/')
    else:
        qr_code.logo_path = None  # Or set to a default image path if you want

    # Parse the JSON content
    content = json.loads(qr_code.content)

    return render_template('view_qr.html', qr_code=qr_code, qr_image=qr_image, 
                           qr_info=qr_info, scans=scans, content=content)


# In your edit_qr route, add this section where you handle styling updates:

@app.route('/qr/<qr_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_qr(qr_id):
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    # Ensure the QR code belongs to the current user
    if qr_code.user_id != current_user.id:
        flash('You do not have permission to edit this QR code.')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # [Content update code remains the same...]
        
        # Update styling - including the new gradient column
        qr_code.template = request.form.get('template')
        
        # Get and validate color input
        color = request.form.get('color', '#000000')
        if not color or color.strip() == '' or color == 'undefined' or color == 'null':
            color = '#000000'
        qr_code.color = color
        
        background_color = request.form.get('background_color', '#FFFFFF')
        if not background_color or background_color.strip() == '' or background_color == 'undefined':
            background_color = '#FFFFFF'
        qr_code.background_color = background_color
        
        qr_code.shape = request.form.get('shape', 'square')
        qr_code.frame_type = request.form.get('frame_type')
        qr_code.frame_text = request.form.get('frame_text')
        
        # Get frame color if a frame is selected
        if request.form.get('frame_type'):
            qr_code.frame_color = request.form.get('frame_color', qr_code.color)
        
        # UPDATE GRADIENT HANDLING - Use the new gradient column
        using_gradient = False
        export_type = request.form.get('export_type', 'png')
        
        # Check if user explicitly selected gradient
        if export_type == 'gradient':
            using_gradient = True
        
        # Check if gradient is enabled via checkbox or form field
        if 'using_gradient' in request.form and request.form.get('using_gradient') == 'true':
            using_gradient = True
        
        # Check if template has gradient
        template = request.form.get('template', '')
        if template and template in QR_TEMPLATES:
            template_config = QR_TEMPLATES[template]
            if template_config.get('export_type') == 'gradient':
                using_gradient = True
        
        # UPDATE THE GRADIENT COLUMN
        qr_code.gradient = using_gradient
        print(f"Updated gradient column to: {using_gradient}")
        
        # Set gradient parameters if using gradient
        if using_gradient:
            qr_code.gradient_start = request.form.get('gradient_start', '#FF5500')
            qr_code.gradient_end = request.form.get('gradient_end', '#FFAA00')
            qr_code.gradient_type = request.form.get('gradient_type', 'linear')
            qr_code.gradient_direction = request.form.get('gradient_direction', 'to-right')
            qr_code.export_type = 'gradient'
        else:
            # Clear gradient parameters if not using gradient
            qr_code.gradient_start = None
            qr_code.gradient_end = None
            qr_code.gradient_type = None
            qr_code.gradient_direction = None
            qr_code.export_type = 'png'
        
        # Update advanced styling
        qr_code.custom_eyes = request.form.get('custom_eyes') == 'true'
        qr_code.inner_eye_style = request.form.get('inner_eye_style')
        qr_code.outer_eye_style = request.form.get('outer_eye_style')
        
        # Handle eye colors
        inner_eye_color = request.form.get('inner_eye_color')
        outer_eye_color = request.form.get('outer_eye_color')
        
        if inner_eye_color and inner_eye_color != 'undefined' and inner_eye_color.strip() != '':
            qr_code.inner_eye_color = inner_eye_color
        elif using_gradient and qr_code.gradient_start:
            qr_code.inner_eye_color = qr_code.gradient_start
        elif qr_code.custom_eyes:
            qr_code.inner_eye_color = qr_code.color
        else:
            qr_code.inner_eye_color = ''
        
        if outer_eye_color and outer_eye_color != 'undefined' and outer_eye_color.strip() != '':
            qr_code.outer_eye_color = outer_eye_color
        elif using_gradient and qr_code.gradient_end:
            qr_code.outer_eye_color = qr_code.gradient_end
        elif qr_code.custom_eyes:
            qr_code.outer_eye_color = qr_code.color
        else:
            qr_code.outer_eye_color = ''
        
        # [Rest of the update code remains the same...]
        qr_code.module_size = request.form.get('module_size', 10, type=int)
        qr_code.quiet_zone = request.form.get('quiet_zone', 4, type=int)
        qr_code.error_correction = request.form.get('error_correction', 'H')
        qr_code.watermark_text = request.form.get('watermark_text')
        qr_code.logo_size_percentage = request.form.get('logo_size_percentage', 25, type=int)
        qr_code.round_logo = request.form.get('round_logo') == 'true'
        
        # Handle logo update
        logo_path = fix_logo_path_handling(request, qr_code)
        qr_code.logo_path = logo_path
        
        qr_code.updated_at = datetime.utcnow()
        db.session.commit()
        
        flash('QR Code updated successfully!')
        return redirect(url_for('view_qr', qr_id=qr_id))
    
    # [GET request code remains the same...]
    content = json.loads(qr_code.content)
    scans = Scan.query.filter_by(qr_code_id=qr_code.id).all()
    max_scans = 1000
    qr_image, qr_info = generate_qr_code(qr_code)
    
    return render_template('edit_qr.html', 
                     qr_code=qr_code, 
                     content=content, 
                     qr_templates=QR_TEMPLATES,
                     scans=scans,
                     qr_image=qr_image,
                     max_scans=max_scans)

@app.route('/qr/<qr_id>/delete', methods=['POST'])
@login_required
def delete_qr(qr_id):
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    # Ensure the QR code belongs to the current user
    if qr_code.user_id != current_user.id:
        flash('You do not have permission to delete this QR code.')
        return redirect(url_for('dashboard'))
    
    try:
        # Delete type-specific detail records first
        qr_type = qr_code.qr_type
        if qr_type == 'link':
            QRLink.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'email':
            QREmail.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'text':
            QRText.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'call':
            QRPhone.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'sms':
            QRSms.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'whatsapp':
            QRWhatsApp.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'wifi':
            QRWifi.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'vcard':
            QRVCard.query.filter_by(qr_code_id=qr_code.id).delete()
        elif qr_type == 'event':
            QREvent.query.filter_by(qr_code_id=qr_code.id).delete()
            
        # Delete related scans
        Scan.query.filter_by(qr_code_id=qr_code.id).delete()
        
        # Remove logo file if it exists
        if qr_code.logo_path and os.path.exists(qr_code.logo_path):
            try:
                os.remove(qr_code.logo_path)
            except:
                pass
        
        # Delete the QR code
        db.session.delete(qr_code)
        db.session.commit()
        
        flash('QR Code deleted successfully!')
        return redirect(url_for('dashboard'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting QR code: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/qr/<qr_id>/download')
def download_qr(qr_id):
    """Fixed download function that properly handles gradients and all styling options"""
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    try:
        # Use the complete QR generation pipeline to ensure all styling is applied
        qr_image_data, qr_info = generate_qr_code(qr_code)
        
        # Convert base64 data URL to binary data
        if qr_image_data.startswith('data:image/png;base64,'):
            # Extract just the base64 part
            header, encoded = qr_image_data.split(",", 1)
            img_data = base64.b64decode(encoded)
        else:
            # If it's just base64 without data URL prefix
            img_data = base64.b64decode(qr_image_data)
        
        # Create BytesIO buffer for the image
        buffer = BytesIO(img_data)
        buffer.seek(0)
        
        # Determine filename based on QR code name and format
        safe_name = "".join(c for c in qr_code.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_name}.png"
        
        # Return the image file with proper headers
        return send_file(
            buffer, 
            mimetype='image/png',
            as_attachment=True, 
            download_name=filename
        )
        
    except Exception as e:
        app.logger.error(f"Error in download_qr: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        
        # Fallback: create a simple QR code if the full pipeline fails
        try:
            qr_data = generate_qr_data(qr_code)
            
            # Create basic QR code
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=qr_code.module_size or 10,
                border=qr_code.quiet_zone or 4
            )
            
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Use basic colors
            color = qr_code.color if qr_code.color else '#000000'
            bg_color = qr_code.background_color if qr_code.background_color else '#FFFFFF'
            
            qr_img = qr.make_image(fill_color=color, back_color=bg_color)
            
            # Convert to BytesIO for download
            buffered = BytesIO()
            qr_img.save(buffered, format="PNG")
            buffered.seek(0)
            
            safe_name = "".join(c for c in qr_code.name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_name}_basic.png"
            
            return send_file(
                buffered, 
                mimetype='image/png',
                as_attachment=True, 
                download_name=filename
            )
            
        except Exception as fallback_error:
            app.logger.error(f"Fallback download also failed: {str(fallback_error)}")
            flash('Error generating QR code for download. Please try again.', 'error')
            return redirect(url_for('view_qr', qr_id=qr_id))

@app.route('/debug-qr-color/<qr_id>')
def debug_qr_color(qr_id):
    """Debug endpoint to check color values"""
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    color_info = {
        'qr_id': qr_id,
        'color_in_db': qr_code.color,
        'color_in_db_stripped': qr_code.color.strip() if qr_code.color else None,
        'background_color': qr_code.background_color,
        'hex_to_rgb_conversion': hex_to_rgb(qr_code.color) if qr_code.color else None,
    }
    
    return jsonify(color_info)

@app.route('/qr/<qr_id>/analytics')
@login_required
def qr_analytics(qr_id):
    user_id = current_user.id
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    # Ensure the QR code belongs to the current user
    if qr_code.user_id != user_id:
        flash('You do not have permission to view analytics for this QR code.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if user has an active subscription
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .first()
    )
    
    if not active_subscription:
        flash('You need an active subscription to view analytics.', 'warning')
        return redirect(url_for('subscription.user_subscriptions'))
    
    # Check if user has analytics available
    if active_subscription.analytics_used >= active_subscription.subscription.analytics:
        flash('You have reached your analytics usage limit for this subscription plan.', 'warning')
        return redirect(url_for('subscription.user_subscriptions'))
    
    # Increment analytics usage
    active_subscription.analytics_used += 1
    db.session.commit()
    
    # Get all scans for this QR code
    scans = Scan.query.filter_by(qr_code_id=qr_code.id).order_by(Scan.timestamp.desc()).all()
    total_scans = len(scans)
    
    # Pagination for recent scans
    page = request.args.get('page', 1, type=int)
    page_size = 10
    total_pages = (total_scans + page_size - 1) // page_size if total_scans > 0 else 1
    page_num = min(max(page, 1), total_pages) if total_pages > 0 else 1
    
    # Get paginated scans
    start_index = (page_num - 1) * page_size
    end_index = min(start_index + page_size, total_scans)
    paginated_scans = scans[start_index:end_index] if total_scans > 0 else []
    
    # Process scan data for charts and analysis
    scan_dates = {}
    scan_devices = {}
    scan_locations = {}
    hourly_counts = [0] * 24
    os_data = {}
    
    for scan in scans:
        # Get timestamp and adjust for timezone
        timestamp = scan.timestamp
        localized_time = get_localized_datetime(timestamp)
        if localized_time:
            scan_date = localized_time.strftime('%Y-%m-%d')
            hour = localized_time.hour
        else:
            scan_date = timestamp.strftime('%Y-%m-%d') if timestamp else 'Unknown'
            hour = timestamp.hour if timestamp else 0
        
        # Group by date for timeline chart
        if scan_date != 'Unknown':
            scan_dates[scan_date] = scan_dates.get(scan_date, 0) + 1
        
        # Process hourly data
        if 0 <= hour < 24:
            hourly_counts[hour] += 1
        
        # Extract device info from user agent
        device = "Unknown"
        operating_system = "Unknown"
        
        if scan.user_agent:
            # Device detection
            if "Mobile" in scan.user_agent and "Tablet" not in scan.user_agent:
                device = "Mobile"
            elif "Tablet" in scan.user_agent:
                device = "Tablet"
            else:
                device = "Desktop"
                
            # OS detection
            if "Windows" in scan.user_agent:
                operating_system = "Windows"
            elif "Mac OS" in scan.user_agent or "MacOS" in scan.user_agent:
                operating_system = "macOS"
            elif "Android" in scan.user_agent:
                operating_system = "Android"
            elif "iPhone" in scan.user_agent or "iPad" in scan.user_agent or "iOS" in scan.user_agent:
                operating_system = "iOS"
            elif "Linux" in scan.user_agent and "Android" not in scan.user_agent:
                operating_system = "Linux"
                
        scan_devices[device] = scan_devices.get(device, 0) + 1
        os_data[operating_system] = os_data.get(operating_system, 0) + 1
        
        # Group by location
        location = scan.location or "Unknown"
        scan_locations[location] = scan_locations.get(location, 0) + 1
    
    # Transform data for charts - FIXED FORMAT
    # Timeline data - convert to sorted list of objects
    sorted_dates = sorted(scan_dates.items())
    timeline_data = [{"date": date, "scans": count} for date, count in sorted_dates]
    
    # Device data - list of objects
    device_data = [{"device": device, "scans": count} for device, count in scan_devices.items() if count > 0]
    
    # Location data - list of objects (top 10)
    sorted_locations = sorted(scan_locations.items(), key=lambda x: x[1], reverse=True)[:10]
    location_data = [{"location": loc, "scans": count} for loc, count in sorted_locations]
    
    # OS data - list of objects
    os_data_list = [{"os": os_name, "scans": count} for os_name, count in os_data.items() if count > 0]
    
    return render_template('analytics.html', 
                         qr_code=qr_code, 
                         scans=scans,
                         paginated_scans=paginated_scans,
                         total_scans=total_scans,
                         page_num=page_num,
                         total_pages=total_pages,
                         timeline_data=timeline_data, 
                         device_data=device_data,
                         scan_dates=scan_dates,
                         hourly_data=hourly_counts,
                         location_data=location_data,
                         os_data=os_data_list,  # Changed to list format
                         has_data=(total_scans > 0),
                         analytics_used=active_subscription.analytics_used,
                         analytics_limit=active_subscription.subscription.analytics,
                         analytics_remaining=max(0, active_subscription.subscription.analytics - active_subscription.analytics_used))


@app.route('/user/analytics')
@login_required
def user_analytics():
    # Get all QR codes for the current user
    qr_codes = QRCode.query.filter_by(user_id=current_user.id).all()
    
    # Initialize analytics data structures
    total_scans = 0
    scan_timeline = {}  # Date -> count
    qr_performance = {}  # QR ID -> scan count
    device_data = {"Mobile": 0, "Desktop": 0, "Tablet": 0, "Unknown": 0}
    os_data = {"Windows": 0, "Android": 0, "iOS": 0, "macOS": 0, "Linux": 0, "Unknown": 0}
    location_data = {}
    hourly_data = [0] * 24  # Hour -> count
    
    # Try to get user's timezone from session, or use default (UTC)
    user_timezone = session.get('user_timezone', 'UTC')
    try:
        import pytz
        tz = pytz.timezone(user_timezone)
    except (ImportError, pytz.exceptions.UnknownTimeZoneError):
        from datetime import timezone, timedelta
        # Default to UTC if pytz not available
        tz = timezone.utc
    
    # Process all scans
    for qr_code in qr_codes:
        qr_id = qr_code.unique_id
        qr_name = qr_code.name
        scan_count = 0
        
        # Get scans for this QR code
        scans = Scan.query.filter_by(qr_code_id=qr_code.id).all()
        for scan in scans:
            total_scans += 1
            scan_count += 1
            
            # Get timestamp and adjust for timezone if possible
            timestamp = scan.timestamp
            try:
                # Convert UTC timestamp to user's local time if pytz is available
                if hasattr(timestamp, 'replace') and timestamp is not None:
                    import pytz
                    local_time = timestamp.replace(tzinfo=pytz.UTC).astimezone(tz)
                    scan_date = local_time.strftime('%Y-%m-%d')
                    hour = local_time.hour
                else:
                    scan_date = timestamp.strftime('%Y-%m-%d') if timestamp else 'Unknown'
                    hour = timestamp.hour if timestamp else 0
            except (AttributeError, ValueError, TypeError):
                # Fallback if timestamp manipulation fails
                scan_date = 'Unknown'
                hour = 0
            
            # Process timeline data
            if scan_date != 'Unknown':
                scan_timeline[scan_date] = scan_timeline.get(scan_date, 0) + 1
            
            # Process hourly data
            hourly_data[hour] += 1
            
            # Process device data
            device = "Unknown"
            operating_system = "Unknown"
            
            if scan.user_agent:
                # Device detection
                if "Mobile" in scan.user_agent and "Tablet" not in scan.user_agent:
                    device = "Mobile"
                elif "Tablet" in scan.user_agent:
                    device = "Tablet"
                else:
                    device = "Desktop"
                    
                # OS detection
                if "Windows" in scan.user_agent:
                    operating_system = "Windows"
                elif "Mac OS" in scan.user_agent or "MacOS" in scan.user_agent:
                    operating_system = "macOS"
                elif "Android" in scan.user_agent:
                    operating_system = "Android"
                elif "iPhone" in scan.user_agent or "iPad" in scan.user_agent or "iOS" in scan.user_agent:
                    operating_system = "iOS"
                elif "Linux" in scan.user_agent and "Android" not in scan.user_agent:
                    operating_system = "Linux"
                    
            device_data[device] = device_data.get(device, 0) + 1
            os_data[operating_system] = os_data.get(operating_system, 0) + 1
            
            # Process location data
            location = scan.location or "Unknown"
            location_data[location] = location_data.get(location, 0) + 1
        
        # Add to QR performance data
        qr_performance[qr_id] = {
            "name": qr_name,
            "scans": scan_count,
            "type": qr_code.qr_type,
            "id": qr_id,
            "created": qr_code.created_at.strftime('%b %d, %Y') if qr_code.created_at else None
        }
    
    # Prepare data for charts
    device_chart_data = [{"device": device, "scans": count} for device, count in device_data.items() if count > 0]
    os_chart_data = [{"os": os, "scans": count} for os, count in os_data.items() if count > 0]
    sorted_locations = sorted(location_data.items(), key=lambda x: x[1], reverse=True)[:10]
    location_chart_data = [{"location": loc, "scans": count} for loc, count in sorted_locations]
    
    # Prepare QR performance data
    qr_chart_data = list(qr_performance.values())
    qr_chart_data.sort(key=lambda x: x["scans"], reverse=True)
    
    # Get top 5 QR codes for display
    top_qr_codes = qr_chart_data[:5] if qr_chart_data else []
    
    # Calculate peak hour in user-friendly format
    peak_hour_index = hourly_data.index(max(hourly_data)) if max(hourly_data) > 0 else 0
    hour_format = peak_hour_index % 12 or 12
    ampm = 'AM' if peak_hour_index < 12 else 'PM'
    peak_hour_formatted = f"{hour_format}{ampm}"
    
    # Make sure all variables used in the template are defined
    scan_timeline_keys = list(scan_timeline.keys())
    
    return render_template(
        'user_analytics.html',
        qr_codes=qr_codes,
        total_scans=total_scans,
        scan_timeline=scan_timeline,
        scan_timeline_keys=scan_timeline_keys,
        device_data=device_chart_data,
        os_data=os_chart_data,
        hourly_data=hourly_data,
        qr_performance=qr_chart_data,
        top_qr_codes=top_qr_codes,
        location_data=location_chart_data,
        user_timezone=user_timezone,
        peak_hour=peak_hour_formatted
    )


@app.route('/qr/<qr_id>/export/<format>')
@login_required
def export_qr(qr_id, format):
    qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
    
    # Ensure the QR code belongs to the current user
    if qr_code.user_id != current_user.id:
        flash('You do not have permission to export this QR code.')
        return redirect(url_for('dashboard'))
    
    # Only allow PNG format
    if format != 'png':
        flash('Only PNG format is supported for export.')
        return redirect(url_for('view_qr', qr_id=qr_id))
    
    # Temporarily set the export format
    original_format = qr_code.export_type
    qr_code.export_type = format
    
    # Generate QR code image
    qr_image, _ = generate_qr_code(qr_code)
    
    # Reset to original format
    qr_code.export_type = original_format
    
    # Determine mime type - only PNG is supported
    mime_type = 'image/png'
    
    # If base64 data URL, convert back to binary
    if qr_image.startswith('data:'):
        # Extract just the base64 part
        header, encoded = qr_image.split(",", 1)
        img_data = base64.b64decode(encoded)
        buffer = BytesIO(img_data)
    else:
        buffer = BytesIO(base64.b64decode(qr_image))
    
    # Return the image as a file download
    return send_file(buffer, mimetype=mime_type, as_attachment=True, download_name=f"{qr_code.name}.{format}")\
    
@app.route('/r/<qr_id>')
def redirect_qr(qr_id):
    from flask import render_template, jsonify
    import traceback
    
    try:
        # Step 1: Retrieve the QR code record
        qr_code = QRCode.query.filter_by(unique_id=qr_id).first_or_404()
        
        # Record scan if dynamic
        if qr_code.is_dynamic:
            scan = Scan(
                qr_code_id=qr_code.id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string,
                location=request.headers.get('X-Forwarded-For', request.remote_addr)
            )
            db.session.add(scan)
            db.session.commit()
        
        # Get QR type and prepare content
        qr_type = qr_code.qr_type
        content = json.loads(qr_code.content) if qr_code.content else {}
        
        # Step 2: Retrieve specific model data based on QR type
        # This is the key part - directly accessing the database relationship
        detail = None
        
        if qr_type == 'vcard':
            # Use the direct relationship from the QR code to its detail
            detail = qr_code.vcard_detail
            
            # Only fall back to JSON content if no database record exists
            if not detail and content:
                app.logger.info(f"No vCard detail found in database, creating from content: {content}")
                
                # Handle social_media field if it's a string in content
                social_media_data = content.get('social_media', None)
                if isinstance(social_media_data, str):
                    try:
                        social_media_data = json.loads(social_media_data)
                    except (json.JSONDecodeError, TypeError):
                        social_media_data = None
                
                detail = type('VCardDetail', (), {
                    'name': content.get('name', ''),
                    'phone': content.get('phone', ''),
                    'email': content.get('email', ''),
                    'company': content.get('company', ''),
                    'title': content.get('title', ''),
                    'address': content.get('address', ''),
                    'website': content.get('website', ''),
                    # Additional enhanced vCard fields
                    'logo_path': content.get('logo_path', ''),
                    'primary_color': content.get('primary_color', '#3366CC'),
                    'secondary_color': content.get('secondary_color', '#5588EE'),
                    'social_media': social_media_data if isinstance(social_media_data, dict) else json.dumps(social_media_data) if social_media_data else None
                })()
            
            return render_template('vcard_display.html', detail=detail)
            
        elif qr_type == 'event':
            # Use the direct relationship from the QR code to its detail
            detail = qr_code.event_detail
            # Only fall back to JSON content if no database record exists
            if not detail and content:
                app.logger.info(f"No event detail found in database, creating from content: {content}")
                detail = type('EventDetail', (), {
                    'title': content.get('title', ''),
                    'organizer': content.get('organizer', ''),
                    'start_date': content.get('start_date', ''),
                    'end_time': content.get('end_time', ''),
                    'location': content.get('location', ''),
                    'description': content.get('description', '')
                })()
            return render_template('event_display.html', detail=detail)
            
        elif qr_type == 'wifi':
            # Use the direct relationship from the QR code to its detail
            detail = qr_code.wifi_detail
            # Only fall back to JSON content if no database record exists
            if not detail and content:
                app.logger.info(f"No WiFi detail found in database, creating from content: {content}")
                detail = type('WifiDetail', (), {
                    'ssid': content.get('ssid', ''),
                    'password': content.get('password', ''),
                    'encryption': content.get('encryption', 'WPA')
                })()
            return render_template('wifi_display.html', detail=detail)
            
        elif qr_type == 'text':
            # Use the direct relationship from the QR code to its detail
            detail = qr_code.text_detail
            # Only fall back to JSON content if no database record exists
            if not detail and content:
                app.logger.info(f"No text detail found in database, creating from content: {content}")
                detail = type('TextDetail', (), {
                    'text': content.get('text', '')
                })()
            return render_template('text_display.html', detail=detail, now=datetime.now().strftime('%d %b %Y, %H:%M'))

            
        elif qr_type == 'link':
            # Link types redirect directly, no template needed
            url = None
            if hasattr(qr_code, 'link_detail') and qr_code.link_detail:
                url = qr_code.link_detail.url
            elif 'url' in content:
                url = content['url']
            
            if url:
                return redirect(url)
            else:
                return render_template('error.html', message="Link information not found")
                
        elif qr_type == 'email':
            # Email types redirect to mailto:
            if hasattr(qr_code, 'email_detail') and qr_code.email_detail:
                email = qr_code.email_detail.email
                subject = qr_code.email_detail.subject or ''
                body = qr_code.email_detail.body or ''
                return redirect(f"mailto:{email}?subject={subject}&body={body}")
            elif 'email' in content:
                return redirect(f"mailto:{content['email']}?subject={content.get('subject', '')}&body={content.get('body', '')}")
            else:
                return render_template('error.html', message="Email information not found")
                
        elif qr_type == 'call':
            # Call types redirect to tel:
            if hasattr(qr_code, 'phone_detail') and qr_code.phone_detail:
                return redirect(f"tel:{qr_code.phone_detail.phone}")
            elif 'phone' in content:
                return redirect(f"tel:{content['phone']}")
            else:
                return render_template('error.html', message="Phone information not found")
                
        elif qr_type == 'sms':
            # SMS types redirect to sms:
            if hasattr(qr_code, 'sms_detail') and qr_code.sms_detail:
                return redirect(f"sms:{qr_code.sms_detail.phone}?body={qr_code.sms_detail.message or ''}")
            elif 'phone' in content:
                return redirect(f"sms:{content['phone']}?body={content.get('message', '')}")
            else:
                return render_template('error.html', message="SMS information not found")
                
        elif qr_type == 'whatsapp':
            # WhatsApp types redirect to wa.me
            if hasattr(qr_code, 'whatsapp_detail') and qr_code.whatsapp_detail:
                # Clean phone number (remove non-digits)
                phone = ''.join(c for c in qr_code.whatsapp_detail.phone if c.isdigit())
                return redirect(f"https://wa.me/{phone}?text={qr_code.whatsapp_detail.message or ''}")
            elif 'phone' in content:
                phone = ''.join(c for c in content['phone'] if c.isdigit())
                return redirect(f"https://wa.me/{phone}?text={content.get('message', '')}")
            else:
                return render_template('error.html', message="WhatsApp information not found")
        
        # If no specific handling is found, show an error or default page
        return render_template('error.html', message="Unable to process QR code")
        
    except Exception as e:
        app.logger.error(f"Unhandled error: {e}")
        app.logger.error(traceback.format_exc())
        return render_template('error.html', message=f"An error occurred: {str(e)}")

@app.route('/batch-export', methods=['POST'])
@login_required
def batch_export():
    user_id = current_user.id
    
    # Check if user has an active subscription
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .first()
    )
    
    if not active_subscription:
        flash('You need an active subscription to export QR codes in batch.', 'warning')
        return redirect(url_for('subscription.user_subscriptions'))
    
    # Check if batch export is allowed for this subscription tier
    if active_subscription.subscription.tier < 2:  # Adjust tier requirement as needed
        flash('Batch export is only available for higher tier subscriptions.', 'warning')
        return redirect(url_for('dashboard'))
    
    qr_ids = request.form.getlist('qr_ids')
    format = request.form.get('format', 'zip')
    
    if not qr_ids:
        flash('No QR codes selected for export.')
        return redirect(url_for('dashboard'))
    
    # Get QR codes and ensure they belong to the current user
    data_list = []
    for qr_id in qr_ids:
        qr_code = QRCode.query.filter_by(unique_id=qr_id).first()
        if qr_code and qr_code.user_id == user_id:
            # Generate QR data
            qr_data = generate_qr_data(qr_code)
            
            # Get options for the QR code
            options = get_qr_options(qr_code)
            
            data_list.append({
                'data': qr_data,
                'options': options,
                'label': qr_code.name
            })
    
    if not data_list:
        flash('No valid QR codes selected for export.')
        return redirect(url_for('dashboard'))
    
    # Generate batch export
    result = batch_generate_qr(data_list, output_format=format)
    
    # Record usage
    if active_subscription:
        # Consider this a single analytics usage
        if active_subscription.analytics_used < active_subscription.subscription.analytics:
            active_subscription.analytics_used += 1
            db.session.commit()
    
    # Determine mime type
    mime_type = "application/zip" if format == "zip" else "application/pdf"
    
    # If base64 data URL, convert back to binary
    if result.startswith('data:'):
        # Extract just the base64 part
        header, encoded = result.split(",", 1)
        file_data = base64.b64decode(encoded)
        buffer = BytesIO(file_data)
    else:
        buffer = BytesIO(base64.b64decode(result))
    
    # Return the file as a download
    filename = f"qr_batch_export.{format}"
    return send_file(buffer, mimetype=mime_type, as_attachment=True, download_name=filename)

@app.route('/help')
def help_center():
    """Help center page with guides and tutorials for using QR Craft"""
    return render_template('help_center.html')

def apply_watermark(qr_img, text):
    """Apply text watermark to QR code"""
    # Create a transparent layer for watermark
    watermark = Image.new('RGBA', qr_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark)
    
    # Set watermark color and opacity
    watermark_color = (0, 0, 0, 60)  # Black with 60/255 opacity
    
    # Try to load font, fall back to default
    try:
        font_size = min(qr_img.size) // 15
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text position (bottom right corner)
    text_width = draw.textlength(text, font=font)
    text_position = (qr_img.size[0] - text_width - 10, qr_img.size[1] - font_size - 10)
    
    # Draw text
    draw.text(text_position, text, fill=watermark_color, font=font)
    
    # Composite watermark with QR code
    result = Image.alpha_composite(qr_img.convert('RGBA'), watermark)
    
    return result

def apply_frame(qr_img, frame_type, options):
    """Apply frame around QR code with black frame color only"""
    if not frame_type:  # Added check for empty frame_type
        return qr_img
        
    qr_width, qr_height = qr_img.size
    
    # Determine frame size
    frame_padding = qr_width // 10
    frame_width = qr_width + (frame_padding * 2)
    
    # Additional height for text
    text_height = 0
    if frame_type in ['scan_me', 'branded']:
        text_height = frame_padding * 2
    
    frame_height = qr_height + (frame_padding * 2) + text_height
    
    # Get background color from options
    background_color = options.get('background_color', '#FFFFFF')
    
    # Convert background color to RGB if needed - Add validation
    try:
        if isinstance(background_color, str) and background_color.startswith('#'):
            # Validate hex color format
            if not all(c in '0123456789ABCDEFabcdef' for c in background_color.lstrip('#')):
                background_color = '#FFFFFF'  # Default to white if invalid
            bg_color_rgb = tuple(int(background_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (255,)
        else:
            bg_color_rgb = background_color + (255,) if len(background_color) == 3 else background_color
    except Exception:
        # Fallback to white if there's any error
        bg_color_rgb = (255, 255, 255, 255)
    
    # FORCE frame color to be black, ignore any other settings
    frame_color_rgb = (0, 0, 0, 255)  # Black with full opacity
    
    # Debug output
    print(f"Applying frame with BLACK color: {frame_color_rgb}, ignoring other colors")
    
    # Special handling for circle frame
    if frame_type == 'circle':
        # For circle, ensure the circle is large enough to contain the QR code with proper padding
        # Use a larger padding for circular frames to ensure the QR code fits well
        circle_padding = int(frame_padding * 1.5)
        circle_diameter = max(qr_width, qr_height) + (circle_padding * 2)
        
        # Create a new image with the circle diameter
        circle_img = Image.new('RGBA', (circle_diameter, circle_diameter), bg_color_rgb)
        circle_draw = ImageDraw.Draw(circle_img)
        
        # Draw the circle frame - make the outline thicker for better visibility
        circle_line_width = max(2, circle_padding // 3)
        circle_draw.ellipse([0, 0, circle_diameter-1, circle_diameter-1], 
                           outline=frame_color_rgb, 
                           width=circle_line_width)
        
        # Position the QR code in the center of the circle
        qr_pos = ((circle_diameter - qr_width) // 2, (circle_diameter - qr_height) // 2)
        circle_img.paste(qr_img, qr_pos)
        
        return circle_img
    
    # For other frame types, create standard frame image
    frame_img = Image.new('RGBA', (frame_width, frame_height), bg_color_rgb)
    draw = ImageDraw.Draw(frame_img)
    
    # Draw other frame types
    if frame_type == 'square':
        draw.rectangle([0, 0, frame_width-1, frame_height-1], outline=frame_color_rgb, width=max(1, frame_padding // 2))
    elif frame_type == 'rounded':
        radius = frame_padding
        # Draw rounded rectangle manually since older Pillow versions might not have rounded_rectangle
        # Top and bottom horizontal lines
        draw.line([(radius, 0), (frame_width - radius - 1, 0)], fill=frame_color_rgb, width=max(1, frame_padding // 2))
        draw.line([(radius, frame_height - 1), (frame_width - radius - 1, frame_height - 1)], fill=frame_color_rgb, width=max(1, frame_padding // 2))
        # Left and right vertical lines
        draw.line([(0, radius), (0, frame_height - radius - 1)], fill=frame_color_rgb, width=max(1, frame_padding // 2))
        draw.line([(frame_width - 1, radius), (frame_width - 1, frame_height - radius - 1)], fill=frame_color_rgb, width=max(1, frame_padding // 2))
        # Four arc corners
        draw.arc([(0, 0), (radius * 2, radius * 2)], 180, 270, fill=frame_color_rgb, width=max(1, frame_padding // 2))
        draw.arc([(frame_width - radius * 2 - 1, 0), (frame_width - 1, radius * 2)], 270, 0, fill=frame_color_rgb, width=max(1, frame_padding // 2))
        draw.arc([(0, frame_height - radius * 2 - 1), (radius * 2, frame_height - 1)], 90, 180, fill=frame_color_rgb, width=max(1, frame_padding // 2))
        draw.arc([(frame_width - radius * 2 - 1, frame_height - radius * 2 - 1), (frame_width - 1, frame_height - 1)], 0, 90, fill=frame_color_rgb, width=max(1, frame_padding // 2))
    elif frame_type == 'scan_me':
        # Create a black bar at the top with text
        bar_height = text_height
        draw.rectangle([0, 0, frame_width, bar_height], fill=frame_color_rgb)
        
        # Draw rectangle frame
        draw.rectangle([0, 0, frame_width-1, frame_height-1], outline=frame_color_rgb, width=max(1, frame_padding // 2))
        
        # Add "Scan Me" text
        try:
            font = ImageFont.truetype("arial.ttf", frame_padding)
        except IOError:
            # Fallback to default font
            font = ImageFont.load_default()
        
        text = options.get('frame_text', 'SCAN ME')
        try:
            text_width = draw.textlength(text, font=font)
        except AttributeError:
            # Fallback for older Pillow versions
            text_width = font.getsize(text)[0]
            
        text_position = ((frame_width - text_width) // 2, (bar_height - frame_padding) // 2)
        draw.text(text_position, text, fill=(255, 255, 255, 255), font=font)  # White text
    elif frame_type == 'branded':
        # Create branded frame with company name
        # Black bar at the bottom with text
        bar_height = text_height
        draw.rectangle([0, 0, frame_width, bar_height], fill=frame_color_rgb)
        
        # Draw the outer frame
        draw.rectangle([0, 0, frame_width-1, frame_height-1], outline=frame_color_rgb, width=max(1, frame_padding // 2))
        
        # Add company name
        company_name = options.get('frame_text', 'COMPANY')
        try:
            font = ImageFont.truetype("arial.ttf", frame_padding)
        except IOError:
            font = ImageFont.load_default()
        
        try:
            text_width = draw.textlength(company_name, font=font)
        except AttributeError:
            # Fallback for older Pillow versions
            text_width = font.getsize(company_name)[0]
            
        text_position = ((frame_width - text_width) // 2, (bar_height - frame_padding) // 2)
        draw.text(text_position, company_name, fill=(255, 255, 255, 255), font=font)  # White text
    
    # Paste QR code onto frame
    qr_position = ((frame_width - qr_width) // 2, (frame_height - qr_height) // 2)
    if frame_type in ['scan_me', 'branded']:
        qr_position = ((frame_width - qr_width) // 2, text_height + frame_padding)
    
    frame_img.paste(qr_img, qr_position)
    
    return frame_img


def generate_qr_data(qr_code):
    """Generate QR data string based on QR code type and content from detailed tables"""
    try:
        qr_type = qr_code.qr_type
        
        # Generate QR data based on type
        qr_data = ""
        
        # For dynamic QR codes, always use the redirect URL regardless of type
        if qr_code.is_dynamic:
            qr_data = url_for('redirect_qr', qr_id=qr_code.unique_id, _external=True)
            return qr_data
            
        # For static QR codes, use the appropriate data format by type
        if qr_type == 'link':
            # Try to get data from link_detail table first
            if hasattr(qr_code, 'link_detail') and qr_code.link_detail:
                qr_data = qr_code.link_detail.url
            else:
                # Fallback to JSON content for backward compatibility
                content = json.loads(qr_code.content)
                qr_data = content.get('url', 'https://example.com')
                
        elif qr_type == 'email':
            # Try to get data from email_detail table first
            if hasattr(qr_code, 'email_detail') and qr_code.email_detail:
                email = qr_code.email_detail.email
                subject = qr_code.email_detail.subject or ''
                body = qr_code.email_detail.body or ''
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                email = content.get('email', '')
                subject = content.get('subject', '')
                body = content.get('body', '')
                
            # Format mailto URL
            qr_data = f"mailto:{email}?subject={subject}&body={body}"
            
        elif qr_type == 'text':
            # Try to get data from text_detail table first
            if hasattr(qr_code, 'text_detail') and qr_code.text_detail:
                qr_data = qr_code.text_detail.text
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                qr_data = content.get('text', '')
                
        elif qr_type == 'call':
            # Try to get data from phone_detail table first
            if hasattr(qr_code, 'phone_detail') and qr_code.phone_detail:
                qr_data = f"tel:{qr_code.phone_detail.phone}"
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                qr_data = f"tel:{content.get('phone', '')}"
                
        elif qr_type == 'sms':
            # Try to get data from sms_detail table first
            if hasattr(qr_code, 'sms_detail') and qr_code.sms_detail:
                phone = qr_code.sms_detail.phone
                message = qr_code.sms_detail.message or ''
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                phone = content.get('phone', '')
                message = content.get('message', '')
                
            # Format SMS URL
            qr_data = f"sms:{phone}?body={message}"
            
        elif qr_type == 'whatsapp':
            # Try to get data from whatsapp_detail table first
            if hasattr(qr_code, 'whatsapp_detail') and qr_code.whatsapp_detail:
                phone = qr_code.whatsapp_detail.phone
                # Remove any non-numeric characters from phone number
                phone = ''.join(c for c in phone if c.isdigit())
                message = qr_code.whatsapp_detail.message or ''
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                phone = content.get('phone', '')
                # Remove any non-numeric characters
                phone = ''.join(c for c in phone if c.isdigit())
                message = content.get('message', '')
                
            # Format WhatsApp URL
            qr_data = f"https://wa.me/{phone}?text={message}"
            
        elif qr_type == 'wifi':
            # Try to get data from wifi_detail table first
            if hasattr(qr_code, 'wifi_detail') and qr_code.wifi_detail:
                ssid = qr_code.wifi_detail.ssid
                password = qr_code.wifi_detail.password or ''
                encryption = qr_code.wifi_detail.encryption or 'WPA'
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                ssid = content.get('ssid', '')
                password = content.get('password', '')
                encryption = content.get('encryption', 'WPA')
                
            # Format WiFi URL
            qr_data = f"WIFI:S:{ssid};T:{encryption};P:{password};;"
            
        # In the generate_qr_data function, update the vcard section:
        elif qr_type == 'vcard':
            # Try to get data from vcard_detail table first
            if hasattr(qr_code, 'vcard_detail') and qr_code.vcard_detail:
                detail = qr_code.vcard_detail
                name = detail.name
                phone = detail.phone or ''
                email = detail.email or ''
                company = detail.company or ''
                title = detail.title or ''
                address = detail.address or ''
                website = detail.website or ''
                
                # New fields
                logo_url = ''
                if detail.logo_path:
                    logo_url = url_for('static', filename=f'uploads/{detail.logo_path}', _external=True)
                
                primary_color = detail.primary_color or '#3366CC'
                secondary_color = detail.secondary_color or '#5588EE'
                
                social_media = {}
                if detail.social_media:
                    try:
                        social_media = json.loads(detail.social_media)
                    except:
                        social_media = {}
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                name = content.get('name', '')
                phone = content.get('phone', '')
                email = content.get('email', '')
                company = content.get('company', '')
                title = content.get('title', '')
                address = content.get('address', '')
                website = content.get('website', '')
                logo_url = ''
                primary_color = '#3366CC'
                secondary_color = '#5588EE'
                social_media = {}
            
            # Create enhanced vCard data
            vcard = [
                "BEGIN:VCARD",
                "VERSION:4.0",  # Updated to version 4.0 for better feature support
                f"N:{name}",
                f"FN:{name}"
            ]
            
            if phone:
                vcard.append(f"TEL:{phone}")
                
            if email:
                vcard.append(f"EMAIL:{email}")
                
            if company:
                vcard.append(f"ORG:{company}")
                
            if title:
                vcard.append(f"TITLE:{title}")
                
            if address:
                vcard.append(f"ADR:{address}")
                
            if website:
                vcard.append(f"URL:{website}")
            
            # Add logo if available
            if logo_url:
                vcard.append(f"LOGO;TYPE=PNG:{logo_url}")
            
            # Add custom fields for colors (using X- prefix for custom fields)
            vcard.append(f"X-PRIMARY-COLOR:{primary_color}")
            vcard.append(f"X-SECONDARY-COLOR:{secondary_color}")
            
            # Add social media links
            for platform, link in social_media.items():
                vcard.append(f"X-SOCIALPROFILE;TYPE={platform.upper()}:{link}")
            
            vcard.append("END:VCARD")
            qr_data = "\n".join(vcard)
            
        elif qr_type == 'event':
            # Try to get data from event_detail table first
            if hasattr(qr_code, 'event_detail') and qr_code.event_detail:
                detail = qr_code.event_detail
                title = detail.title
                location = detail.location or ''
                start_date = detail.start_date
                end_time = detail.end_time
                description = detail.description or ''
                organizer = detail.organizer or ''
                
                # Format dates for iCalendar if available
                start_date_str = ''
                end_time_str = ''
                
                if start_date:
                    start_date_str = start_date.strftime('%Y%m%dT%H%M%S')
                    
                if end_time:
                    end_time_str = end_time.strftime('%Y%m%dT%H%M%S')
            else:
                # Fallback to JSON content
                content = json.loads(qr_code.content)
                title = content.get('title', '')
                location = content.get('location', '')
                start_date_str = content.get('start_date', '')
                end_time_str = content.get('end_time', '')
                description = content.get('description', '')
                organizer = content.get('organizer', '')
                
            # Create iCalendar event
            vevent = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "BEGIN:VEVENT"
            ]
            
            if title:
                vevent.append(f"SUMMARY:{title}")
                
            if location:
                vevent.append(f"LOCATION:{location}")
                
            if start_date_str:
                vevent.append(f"DTSTART:{start_date_str}")
                
            if end_time_str:
                vevent.append(f"DTEND:{end_time_str}")
                
            if description:
                vevent.append(f"DESCRIPTION:{description}")
                
            if organizer:
                vevent.append(f"ORGANIZER:{organizer}")
                
            vevent.extend([
                "END:VEVENT",
                "END:VCALENDAR"
            ])
            
            qr_data = "\n".join(vevent)
        
        return qr_data
    except Exception as e:
        app.logger.error(f"Error generating QR data: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        # Return a fallback string so something is displayed
        return "https://example.com/error"

def create_inner_eye_mask(img):
    """Create mask for inner eyes with improved accuracy and size scaling"""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Find eye positions with better scaling
    # QR code has 3 fixed position detection patterns in corners
    quiet_zone = int(img_size * 0.08)  # Estimate quiet zone (border)
    module_count = 25  # Typical for medium QR codes
    module_size = (img_size - 2 * quiet_zone) / module_count
    
    eye_size = int(module_size * 7)  # Position detection pattern is 7x7 modules
    inner_eye_size = int(module_size * 3)  # Inner eye is 3x3 modules
    
    # Position is based on the fixed positioning patterns of QR codes
    tl_x, tl_y = quiet_zone, quiet_zone  # Top left corner
    tr_x, tr_y = img_size - quiet_zone - eye_size, quiet_zone  # Top right corner
    bl_x, bl_y = quiet_zone, img_size - quiet_zone - eye_size  # Bottom left corner
    
    # Calculate inner eye offset (center point of each eye)
    inner_offset = (eye_size - inner_eye_size) // 2
    
    # Draw inner eye masks with additional border for better detection
    offset_adjust = int(module_size * 0.2)  # Small adjustment for better coverage
    
    # Top left inner eye
    draw.rectangle((
        tl_x + inner_offset - offset_adjust, 
        tl_y + inner_offset - offset_adjust, 
        tl_x + inner_offset + inner_eye_size + offset_adjust, 
        tl_y + inner_offset + inner_eye_size + offset_adjust
    ), fill=255)
    
    # Top right inner eye
    draw.rectangle((
        tr_x + inner_offset - offset_adjust, 
        tr_y + inner_offset - offset_adjust, 
        tr_x + inner_offset + inner_eye_size + offset_adjust, 
        tr_y + inner_offset + inner_eye_size + offset_adjust
    ), fill=255)
    
    # Bottom left inner eye
    draw.rectangle((
        bl_x + inner_offset - offset_adjust, 
        bl_y + inner_offset - offset_adjust, 
        bl_x + inner_offset + inner_eye_size + offset_adjust, 
        bl_y + inner_offset + inner_eye_size + offset_adjust
    ), fill=255)
    
    return mask

def create_outer_eye_mask(img):
    """Create mask for outer eyes with improved accuracy and size scaling"""
    img_size = img.size[0]
    mask = Image.new('L', img.size, 0)
    draw = ImageDraw.Draw(mask)
    
    # Find eye positions with better scaling
    quiet_zone = int(img_size * 0.08)  # Estimate quiet zone (border)
    module_count = 25  # Typical for medium QR codes
    module_size = (img_size - 2 * quiet_zone) / module_count
    
    eye_size = int(module_size * 7)  # Position detection pattern is 7x7 modules
    inner_eye_size = int(module_size * 3)  # Inner eye is 3x3 modules
    
    # Position is based on the fixed positioning patterns of QR codes
    tl_x, tl_y = quiet_zone, quiet_zone  # Top left corner
    tr_x, tr_y = img_size - quiet_zone - eye_size, quiet_zone  # Top right corner
    bl_x, bl_y = quiet_zone, img_size - quiet_zone - eye_size  # Bottom left corner
    
    inner_offset = (eye_size - inner_eye_size) // 2
    
    # Draw outer eye masks with small outward expansion for better detection
    offset_adjust = int(module_size * 0.2)  # Small adjustment for better coverage
    
    # Draw outer eye masks (complete eye areas)
    draw.rectangle((
        tl_x - offset_adjust, 
        tl_y - offset_adjust, 
        tl_x + eye_size + offset_adjust, 
        tl_y + eye_size + offset_adjust
    ), fill=255)  # top left
    
    draw.rectangle((
        tr_x - offset_adjust, 
        tr_y - offset_adjust, 
        tr_x + eye_size + offset_adjust, 
        tr_y + eye_size + offset_adjust
    ), fill=255)  # top right
    
    draw.rectangle((
        bl_x - offset_adjust, 
        bl_y - offset_adjust, 
        bl_x + eye_size + offset_adjust, 
        bl_y + eye_size + offset_adjust
    ), fill=255)  # bottom left
    
    # Cut out inner eyes with exact dimensions - no adjustment here
    draw.rectangle((
        tl_x + inner_offset, 
        tl_y + inner_offset, 
        tl_x + inner_offset + inner_eye_size, 
        tl_y + inner_offset + inner_eye_size
    ), fill=0)  # top left
    
    draw.rectangle((
        tr_x + inner_offset, 
        tr_y + inner_offset, 
        tr_x + inner_offset + inner_eye_size, 
        tr_y + inner_offset + inner_eye_size
    ), fill=0)  # top right
    
    draw.rectangle((
        bl_x + inner_offset, 
        bl_y + inner_offset, 
        bl_x + inner_offset + inner_eye_size, 
        bl_y + inner_offset + inner_eye_size
    ), fill=0)  # bottom left
    
    return mask

# Fix 2: Improved hex color validation and conversion
def hex_to_rgb(hex_color):
    """
    Convert hex color to RGB tuple with robust error handling.
    """
    try:
        # Remove the # symbol if present
        hex_color = hex_color.lstrip('#')
        
        # Check if the hex color is valid
        if not all(c in '0123456789ABCDEFabcdef' for c in hex_color):
            print(f"Invalid hex color: {hex_color}, defaulting to black")
            return (0, 0, 0)
            
        # Handle different hex formats
        if len(hex_color) == 3:
            # Expand 3-digit hex to 6-digit
            hex_color = ''.join(c + c for c in hex_color)
        
        # Convert hex to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        print(f"Converted {hex_color} to RGB: ({r}, {g}, {b})")
        return (r, g, b)
    except Exception as e:
        print(f"Error converting hex color {hex_color}: {str(e)}")
        return (0, 0, 0)  # Return black as fallback

    
def apply_gradient(img, options):
    """Apply gradient to QR code with improved implementation and eye color handling"""
    try:
        # Get gradient parameters
        start_color = hex_to_rgb(options.get('gradient_start', '#FF5500'))
        end_color = hex_to_rgb(options.get('gradient_end', '#FFAA00'))
        gradient_type = options.get('gradient_type', 'linear')
        gradient_direction = options.get('gradient_direction', 'to-right')
        
        # Get whether custom eyes will be applied later
        will_apply_custom_eyes = options.get('custom_eyes', False)
        
        # Print debug info
        print(f"Applying gradient with start color: {start_color}, end color: {end_color}")
        print(f"Gradient type: {gradient_type}, direction: {gradient_direction}")
        print(f"Will apply custom eyes later: {will_apply_custom_eyes}")
        
        width, height = img.size
        
        # Create a new image with the same size
        gradient_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
        
        # Get QR code mask (where the QR modules are)
        mask = Image.new('L', img.size, 0)
        
        # Use the original color to determine what's part of the QR code
        qr_color = hex_to_rgb(options.get('color', '#000000'))
        
        # Calculate eye dimensions for eye preservation
        img_size = img.size[0]
        quiet_zone = int(img_size * 0.08)  # Estimate quiet zone (border)
        module_count = 25  # Typical for medium QR codes
        module_size = (img_size - 2 * quiet_zone) / module_count
        eye_size = int(module_size * 7)  # Position detection pattern is 7x7 modules
        
        # Eye positions
        tl_x, tl_y = quiet_zone, quiet_zone  # Top left
        tr_x, tr_y = img_size - quiet_zone - eye_size, quiet_zone  # Top right
        bl_x, bl_y = quiet_zone, img_size - quiet_zone - eye_size  # Bottom left
        
        # Create eye mask
        eye_mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(eye_mask)
        
        # Draw eye areas - always create the eye mask regardless of custom eyes setting
        draw.rectangle([tl_x, tl_y, tl_x + eye_size, tl_y + eye_size], fill=255)
        draw.rectangle([tr_x, tr_y, tr_x + eye_size, tr_y + eye_size], fill=255)
        draw.rectangle([bl_x, bl_y, bl_x + eye_size, bl_y + eye_size], fill=255)
        
        # Create QR mask, identify all modules
        for y in range(height):
            for x in range(width):
                pixel = img.getpixel((x, y))
                # Check if the pixel matches the QR code color (with some tolerance)
                if (len(pixel) >= 3 and
                    abs(pixel[0] - qr_color[0]) < 30 and 
                    abs(pixel[1] - qr_color[1]) < 30 and 
                    abs(pixel[2] - qr_color[2]) < 30):
                    mask.putpixel((x, y), 255)
        
        # Apply different gradient types
        if gradient_type == 'radial':
            # Radial gradient
            center_x, center_y = width // 2, height // 2
            max_distance = math.sqrt(center_x**2 + center_y**2)
            
            for y in range(height):
                for x in range(width):
                    # Calculate distance from center (normalized 0-1)
                    distance = math.sqrt((x - center_x)**2 + (y - center_y)**2) / max_distance
                    
                    # Interpolate color
                    color = (
                        int(start_color[0] + (end_color[0] - start_color[0]) * distance),
                        int(start_color[1] + (end_color[1] - start_color[1]) * distance),
                        int(start_color[2] + (end_color[2] - start_color[2]) * distance),
                        255
                    )
                    
                    # If pixel is part of QR module but not an eye (when custom eyes will not be applied),
                    # apply gradient color
                    if mask.getpixel((x, y)) > 0:
                        if will_apply_custom_eyes or eye_mask.getpixel((x, y)) == 0:
                            gradient_img.putpixel((x, y), color)
                        
        else:  # Linear gradient (default)
            # Determine gradient direction
            if gradient_direction == 'to-bottom':
                # Vertical gradient (top to bottom)
                for y in range(height):
                    for x in range(width):
                        pos = y / (height - 1) if height > 1 else 0
                        
                        color = (
                            int(start_color[0] + (end_color[0] - start_color[0]) * pos),
                            int(start_color[1] + (end_color[1] - start_color[1]) * pos),
                            int(start_color[2] + (end_color[2] - start_color[2]) * pos),
                            255
                        )
                        
                        if mask.getpixel((x, y)) > 0:
                            if will_apply_custom_eyes or eye_mask.getpixel((x, y)) == 0:
                                gradient_img.putpixel((x, y), color)
                            
            elif gradient_direction == 'to-right-bottom':
                # Diagonal gradient (top-left to bottom-right)
                for y in range(height):
                    for x in range(width):
                        pos = (x / (width - 1) + y / (height - 1)) / 2 if (width > 1 and height > 1) else 0
                        
                        color = (
                            int(start_color[0] + (end_color[0] - start_color[0]) * pos),
                            int(start_color[1] + (end_color[1] - start_color[1]) * pos),
                            int(start_color[2] + (end_color[2] - start_color[2]) * pos),
                            255
                        )
                        
                        if mask.getpixel((x, y)) > 0:
                            if will_apply_custom_eyes or eye_mask.getpixel((x, y)) == 0:
                                gradient_img.putpixel((x, y), color)
            else:
                # Default: horizontal gradient (left to right)
                for y in range(height):
                    for x in range(width):
                        pos = x / (width - 1) if width > 1 else 0
                        
                        color = (
                            int(start_color[0] + (end_color[0] - start_color[0]) * pos),
                            int(start_color[1] + (end_color[1] - start_color[1]) * pos),
                            int(start_color[2] + (end_color[2] - start_color[2]) * pos),
                            255
                        )
                        
                        if mask.getpixel((x, y)) > 0:
                            if will_apply_custom_eyes or eye_mask.getpixel((x, y)) == 0:
                                gradient_img.putpixel((x, y), color)
        
        # Combine gradient with background
        bg_color = hex_to_rgb(options.get('background_color', '#FFFFFF'))
        bg_img = Image.new('RGBA', img.size, bg_color + (255,))
        
        # First composite the gradient onto the background
        result = Image.alpha_composite(bg_img, gradient_img)
        
        # Copy original eye patterns from original image if not using custom eyes
        if not will_apply_custom_eyes:
            # Convert original QR color to RGBA
            original_qr_color = hex_to_rgb(options.get('color', '#000000')) + (255,)
            
            # Create a new image for eyes with solid color
            eye_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
            
            # Copy eye patterns in solid color
            for y in range(height):
                for x in range(width):
                    if eye_mask.getpixel((x, y)) > 0 and mask.getpixel((x, y)) > 0:
                        eye_img.putpixel((x, y), original_qr_color)
            
            # Composite eyes over the result
            result = Image.alpha_composite(result, eye_img)
        
        return result
    except Exception as e:
        print(f"Error applying gradient: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return the original image if there's an error
        return img
    
def apply_custom_eyes(qr, qr_img, options):
    """Applies custom eye styling with improved inner/outer proportions and color management"""
    try:
        # Get dimensions and styling options
        img_width, img_height = qr_img.size
        
        # Determine QR code module count
        module_count = len(qr.modules) if qr else 25  # Default to 25 if no qr object
        quiet_zone = options.get('quiet_zone', 4)
        
        # Calculate module size for precise positioning
        module_size = (min(img_width, img_height)) / (module_count + (2 * quiet_zone))
        
        # Get color options with proper validation
        main_color = options.get('color', '#000000')
        inner_eye_color = options.get('inner_eye_color', main_color)
        outer_eye_color = options.get('outer_eye_color', main_color)
        background_color = options.get('background_color', '#FFFFFF')
        
        # Debug color values
        print(f"Custom eyes - Main color: {main_color}")
        print(f"Custom eyes - Inner eye color: {inner_eye_color}")
        print(f"Custom eyes - Outer eye color: {outer_eye_color}")
        
        # Convert colors to RGB tuples with validation
        inner_eye_rgb = hex_to_rgb(inner_eye_color)
        outer_eye_rgb = hex_to_rgb(outer_eye_color)
        bg_rgb = hex_to_rgb(background_color)
        
        # Get eye style options
        inner_eye_style = options.get('inner_eye_style', 'square')
        outer_eye_style = options.get('outer_eye_style', 'square')
        
        # Debug eye styles
        print(f"Custom eyes - Inner eye style: {inner_eye_style}")
        print(f"Custom eyes - Outer eye style: {outer_eye_style}")
        
        # Calculate eye dimensions - IMPROVED PROPORTIONS
        eye_size = int(7 * module_size)  # Standard size for positioning patterns
        inner_size = int(5 * module_size)  # Increased for better proportions
        
        # Print dimension info for debugging
        print(f"Eye dimensions - Total eye size: {eye_size}px, Inner size: {inner_size}px")
        
        # Create a copy of the QR code to work with
        result = qr_img.copy().convert('RGBA')
        
        # Calculate precise eye positions
        first_module_pos = int(quiet_zone * module_size)
        last_module_pos = int(img_width - quiet_zone * module_size - eye_size)
        
        # Define eye positions
        eye_positions = [
            # Top-left
            (first_module_pos, first_module_pos),
            # Top-right
            (last_module_pos, first_module_pos),
            # Bottom-left
            (first_module_pos, last_module_pos)
        ]
        
        # Process each eye position
        for eye_x, eye_y in eye_positions:
            # Completely clear the original eye area with background color plus 1px buffer
            result_draw = ImageDraw.Draw(result)
            result_draw.rectangle(
                [eye_x-2, eye_y-2, eye_x + eye_size+2, eye_y + eye_size+2],  # Added 2px buffer
                fill=bg_rgb + (255,),
                outline=None
            )
            
            # Draw outer eye pattern
            if outer_eye_style == 'square':
                # Square outer eye
                result_draw.rectangle(
                    [eye_x, eye_y, eye_x + eye_size, eye_y + eye_size],
                    fill=outer_eye_rgb + (255,),
                    outline=None
                )
                
                # Cut out middle for inner eye
                inner_margin = (eye_size - inner_size) // 2
                result_draw.rectangle(
                    [eye_x + inner_margin, eye_y + inner_margin, 
                     eye_x + inner_margin + inner_size, eye_y + inner_margin + inner_size],
                    fill=bg_rgb + (255,),
                    outline=None
                )
                
            elif outer_eye_style == 'circle':
                # Circle outer eye
                result_draw.ellipse(
                    [eye_x, eye_y, eye_x + eye_size, eye_y + eye_size],
                    fill=outer_eye_rgb + (255,),
                    outline=None
                )
                
                # Cut out middle for inner eye
                inner_margin = (eye_size - inner_size) // 2
                result_draw.ellipse(
                    [eye_x + inner_margin, eye_y + inner_margin, 
                     eye_x + inner_margin + inner_size, eye_y + inner_margin + inner_size],
                    fill=bg_rgb + (255,),
                    outline=None
                )
                
            elif outer_eye_style == 'rounded':
                # Rounded square outer eye
                corner_radius = eye_size // 5
                draw_rounded_rectangle(
                    result_draw,
                    [eye_x, eye_y, eye_x + eye_size, eye_y + eye_size],
                    radius=corner_radius,
                    fill=outer_eye_rgb + (255,)
                )
                
                # Cut out middle for inner eye
                inner_margin = (eye_size - inner_size) // 2
                inner_corner_radius = corner_radius // 2
                draw_rounded_rectangle(
                    result_draw,
                    [eye_x + inner_margin, eye_y + inner_margin, 
                     eye_x + inner_margin + inner_size, eye_y + inner_margin + inner_size],
                    radius=inner_corner_radius,
                    fill=bg_rgb + (255,)
                )
            
            # Calculate inner eye position and size
            inner_margin = (eye_size - inner_size) // 2
            inner_x = eye_x + inner_margin
            inner_y = eye_y + inner_margin
            
            # Calculate inner eye size (centered in the cut-out area)
            inner_eye_actual_size = int(inner_size * 0.6)  # Increased proportion
            inner_center_offset = (inner_size - inner_eye_actual_size) // 2
            
            inner_center_x = inner_x + inner_center_offset
            inner_center_y = inner_y + inner_center_offset
            
            # Draw inner eye
            if inner_eye_style == 'square':
                result_draw.rectangle(
                    [inner_center_x, inner_center_y, 
                     inner_center_x + inner_eye_actual_size, inner_center_y + inner_eye_actual_size],
                    fill=inner_eye_rgb + (255,),
                    outline=None
                )
                
            elif inner_eye_style == 'circle':
                result_draw.ellipse(
                    [inner_center_x, inner_center_y, 
                     inner_center_x + inner_eye_actual_size, inner_center_y + inner_eye_actual_size],
                    fill=inner_eye_rgb + (255,),
                    outline=None
                )
                
            elif inner_eye_style == 'rounded':
                inner_corner_radius = inner_eye_actual_size // 5
                draw_rounded_rectangle(
                    result_draw,
                    [inner_center_x, inner_center_y, 
                     inner_center_x + inner_eye_actual_size, inner_center_y + inner_eye_actual_size],
                    radius=inner_corner_radius,
                    fill=inner_eye_rgb + (255,)
                )
        
        return result
    except Exception as e:
        print(f"Error applying custom eyes: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return original image if there's an error
        return qr_img

def draw_rounded_rectangle(draw, coords, radius, fill=None):
    """Helper function to draw a rounded rectangle"""
    x1, y1, x2, y2 = coords
    
    # Draw the main rectangles
    draw.rectangle([x1 + radius, y1, x2 - radius, y2], fill=fill)
    draw.rectangle([x1, y1 + radius, x2, y2 - radius], fill=fill)
    
    # Draw the corner arcs
    draw.pieslice([x1, y1, x1 + radius * 2, y1 + radius * 2], 180, 270, fill=fill)
    draw.pieslice([x2 - radius * 2, y1, x2, y1 + radius * 2], 270, 360, fill=fill)
    draw.pieslice([x1, y2 - radius * 2, x1 + radius * 2, y2], 90, 180, fill=fill)
    draw.pieslice([x2 - radius * 2, y2 - radius * 2, x2, y2], 0, 90, fill=fill)

def generate_svg_qr(qr, options):
    """Generate SVG version of QR code"""
    qr_matrix = qr.get_matrix()
    shape = options.get('shape', 'square')
    
    # Convert colors
    fill_color = options.get('color', '#000000')
    bg_color = options.get('background_color', '#FFFFFF')
    
    # Calculate dimensions
    module_count = len(qr_matrix)
    box_size = options.get('module_size', 10)
    border = options.get('quiet_zone', 4)
    size = module_count * box_size + border * 2 * box_size
    
    # Prepare for gradient if requested
    has_gradient = options.get('gradient_start') and options.get('gradient_end')
    gradient_id = f"gradient-{uuid.uuid4()}"
    
    # Start SVG
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
    ]
    
    # Add gradient definition if needed
    if has_gradient:
        start_color = options.get('gradient_start')
        end_color = options.get('gradient_end')
        svg.append(f'<defs><linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="100%">')
        svg.append(f'<stop offset="0%" stop-color="{start_color}"/>')
        svg.append(f'<stop offset="100%" stop-color="{end_color}"/>')
        svg.append(f'</linearGradient></defs>')
        fill_color = f"url(#{gradient_id})"
    
    # Add background
    svg.append(f'<rect width="{size}" height="{size}" fill="{bg_color}"/>')
    
    # Draw modules
    for r, row in enumerate(qr_matrix):
        for c, val in enumerate(row):
            if val:
                x, y = c * box_size + border * box_size, r * box_size + border * box_size
                
                if shape == 'square':
                    svg.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" fill="{fill_color}"/>')
                elif shape == 'rounded':
                    radius = box_size / 4
                    svg.append(f'<rect x="{x}" y="{y}" width="{box_size}" height="{box_size}" rx="{radius}" ry="{radius}" fill="{fill_color}"/>')
                elif shape == 'circle':
                    cx, cy = x + box_size / 2, y + box_size / 2
                    radius = box_size / 2
                    svg.append(f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="{fill_color}"/>')
                elif shape == 'diamond':
                    cx, cy = x + box_size / 2, y + box_size / 2
                    points = f"{cx},{y} {x+box_size},{cy} {cx},{y+box_size} {x},{cy}"
                    svg.append(f'<polygon points="{points}" fill="{fill_color}"/>')
    
    # Apply custom eyes if requested
    if options.get('custom_eyes'):
        # This would require a more complex SVG generation approach
        # For simplicity, we'll skip custom eyes in SVG format
        pass
    
    # Add logo if provided
    logo_path = options.get('logo_path')
    if logo_path and os.path.exists(logo_path):
        try:
            # For SVG, we'll embed the logo as base64
            with open(logo_path, "rb") as image_file:
                logo_data = base64.b64encode(image_file.read()).decode()
            
            logo_mime = "image/png"  # Assume PNG, could detect from file extension
            logo_size = size // 4
            logo_x = (size - logo_size) // 2
            logo_y = (size - logo_size) // 2
            
            svg.append(f'<image x="{logo_x}" y="{logo_y}" width="{logo_size}" height="{logo_size}" '+
                      f'href="data:{logo_mime};base64,{logo_data}" />')
        except Exception as e:
            print(f"Error adding logo to SVG: {str(e)}")
    
    # Add watermark if specified
    watermark_text = options.get('watermark_text')
    if watermark_text:
        font_size = size // 30
        svg.append(f'<text x="{size - 10}" y="{size - 10}" font-size="{font_size}" '
                  f'fill="rgba(0,0,0,0.3)" text-anchor="end">{watermark_text}</text>')
    
    # Close SVG
    svg.append('</svg>')
    
    svg_str = ''.join(svg)
    return f"data:image/svg+xml;base64,{base64.b64encode(svg_str.encode()).decode()}"


def apply_logo(qr_img, logo_path, round_corners=False, size_percentage=25):
    """
    Apply logo to center of QR code without extra white space:
    - If logo has its own background, keep it as is
    - If logo is transparent, apply it directly without background
    - If rounded corners requested, round the corners without adding white background
    
    Parameters:
        qr_img (PIL.Image): The QR code image to apply the logo to
        logo_path (str): Path to the logo file
        round_corners (bool): Whether to apply rounded corners to the logo
        size_percentage (int): Logo size as percentage of QR code (10-30%)
    
    Returns:
        PIL.Image: QR code with logo applied
    """
    try:
        # Debug log for logo path
        print(f"Applying logo from path: {logo_path}")
        
        # Check if logo path exists and is valid
        if not logo_path:
            print("Logo path is empty or None")
            return qr_img
            
        # Handle relative paths correctly
        full_logo_path = ''
        if not os.path.isabs(logo_path):
            # Try multiple possible paths to find the logo
            possible_paths = [
                os.path.join(app.config['UPLOAD_FOLDER'], logo_path),
                logo_path,
                os.path.join('static', 'uploads', logo_path),
                os.path.join('static', logo_path),
                os.path.join(app.config['UPLOAD_FOLDER'], 'logos', os.path.basename(logo_path))
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    full_logo_path = path
                    print(f"Found logo at path: {full_logo_path}")
                    break
        else:
            full_logo_path = logo_path
            
        # Double-check file exists
        if not full_logo_path or not os.path.exists(full_logo_path):
            print(f"Logo file not found. Tried paths including: {full_logo_path}")
            return qr_img
        
        # Verify file is not empty
        if os.path.getsize(full_logo_path) == 0:
            print(f"Logo file exists but is empty: {full_logo_path}")
            return qr_img
            
        # Open and prepare logo image with error handling
        try:
            logo = Image.open(full_logo_path).convert('RGBA')
            print(f"Logo opened successfully. Size: {logo.size}, Mode: {logo.mode}")
        except Exception as img_error:
            print(f"Error opening logo image: {str(img_error)}")
            return qr_img
        
        # Calculate logo size (percentage of QR code)
        qr_width, qr_height = qr_img.size
        size_percentage = max(10, min(30, size_percentage))  # Limit to 10-30%
        logo_max_size = min(qr_width, qr_height) * size_percentage // 100
        print(f"QR size: {qr_width}x{qr_height}, Logo max size: {logo_max_size}px")
        
        # Resize logo maintaining aspect ratio
        logo_width, logo_height = logo.size
        scale_factor = min(logo_max_size / logo_width, logo_max_size / logo_height)
        new_logo_width = int(logo_width * scale_factor)
        new_logo_height = int(logo_height * scale_factor)
        logo = logo.resize((new_logo_width, new_logo_height), Image.LANCZOS)
        print(f"Logo resized to: {new_logo_width}x{new_logo_height}")
        
        # Check if logo has transparency (alpha channel)
        has_transparency = False
        if logo.mode == 'RGBA':
            # More robust transparency check
            alpha_channel = logo.getchannel('A')
            if alpha_channel.getextrema()[0] < 255:  # If minimum alpha is less than 255
                has_transparency = True
                print("Logo has transparency")
        
        # Create a working copy of the logo
        processed_logo = logo.copy()
        
        # Apply rounded corners if requested (WITHOUT white background)
        if round_corners:
            print("Applying rounded corners to logo")
            
            # Add rounded corners directly to the logo without background
            corner_radius = min(new_logo_width, new_logo_height) // 4
            
            # Create a rounded mask
            mask = Image.new('L', (new_logo_width, new_logo_height), 0)
            draw = ImageDraw.Draw(mask)
            
            # Draw a rounded rectangle mask
            draw.rounded_rectangle(
                [(0, 0), (new_logo_width, new_logo_height)], 
                radius=corner_radius, 
                fill=255
            )
            
            # Create new image with rounded corners and preserve transparency
            rounded_logo = Image.new('RGBA', (new_logo_width, new_logo_height), (0, 0, 0, 0))
            rounded_logo.paste(processed_logo, (0, 0), mask)
            processed_logo = rounded_logo
            
            # Set transparency flag since we've created rounded corners
            has_transparency = True
        
        # Create a copy of QR code to avoid modifying original
        result = qr_img.copy()
        
        # Calculate center position for logo
        x = (qr_width - new_logo_width) // 2
        y = (qr_height - new_logo_height) // 2
        print(f"Logo position: ({x}, {y})")
        
        # REMOVED: All the background/padding code that was adding white space
        # The logo will be applied directly without any background modification
        
        # Create mask for transparency handling
        mask = processed_logo if has_transparency else None
        
        # Paste logo directly onto QR code without any background modifications
        result.paste(processed_logo, (x, y), mask)
        print("Logo applied successfully without extra white space")
        
        return result
    except Exception as e:
        import traceback
        print(f"Error applying logo: {str(e)}")
        traceback.print_exc()
        # Return original QR code if logo application fails
        return qr_img


def add_corners(im, rad):
    """
    Adds rounded corners to a given PIL Image while preserving transparency.
    
    Args:
        im (PIL.Image.Image): The input image to which rounded corners will be applied.
        rad (int): The radius of the rounded corners.
    
    Returns:
        PIL.Image.Image: A new image with rounded corners and preserved transparency.
    """
    circle = Image.new('L', (rad * 2, rad * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
    
    alpha = Image.new('L', im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    
    # Preserve original alpha channel if it exists
    if im.mode == 'RGBA':
        original_alpha = im.getchannel('A')
        alpha = ImageChops.multiply(original_alpha, alpha)
    
    # Create a new image with the rounded alpha channel
    result = im.copy()
    result.putalpha(alpha)
    
    return result


def fix_logo_path_handling(request, qr_code):
    """Handle logo upload with robust path handling and validation"""
    logo_path = qr_code.logo_path  # Keep existing path by default
    
    # Handle logo upload
    if 'logo' in request.files and request.files['logo'].filename:
        # Remove old logo if it exists
        if qr_code.logo_path and os.path.exists(qr_code.logo_path):
            try:
                # Check if path is absolute or relative
                logo_file_path = qr_code.logo_path
                if not os.path.isabs(logo_file_path):
                    logo_file_path = os.path.join(app.config['UPLOAD_FOLDER'], logo_file_path)
                
                if os.path.exists(logo_file_path):
                    os.remove(logo_file_path)
                    print(f"Removed old logo: {logo_file_path}")
                else:
                    print(f"Old logo file not found: {logo_file_path}")
            except Exception as e:
                print(f"Error removing old logo: {e}")
                
        # Save new logo
        logo_file = request.files['logo']
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'logos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Create unique filename with original extension
        file_ext = os.path.splitext(logo_file.filename)[1].lower()
        if not file_ext or file_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
            file_ext = '.png'  # Default to PNG if no valid extension
            
        filename = f"{uuid.uuid4()}{file_ext}"
        full_path = os.path.join(upload_dir, filename)
        relative_path = os.path.join('logos', filename)  # Store relative path
        
        try:
            logo_file.save(full_path)
            logo_path = relative_path  # Update to the new path
            print(f"Logo saved to: {full_path}, storing as: {logo_path}")
        except Exception as e:
            print(f"Error saving logo: {e}")
            import traceback
            traceback.print_exc()
    
    return logo_path


def generate_qr_code(qr_code):
    """Generate QR code image with improved color handling and eye customization"""
    try:
        # Get QR data
        qr_data = generate_qr_data(qr_code)
        
        # Get QR options
        options = get_qr_options(qr_code)
        
        # Apply fixes to ensure template doesn't override user choices
        options = fix_template_override_issues(qr_code, options)
        
        # Set up QR code generator with proper quiet zone
        module_size = options.get('module_size', 10)
        quiet_zone = options.get('quiet_zone', 4)
        
        qr = qrcode.QRCode(
            version=None,
            error_correction={
                'L': qrcode.constants.ERROR_CORRECT_L,
                'M': qrcode.constants.ERROR_CORRECT_M,
                'Q': qrcode.constants.ERROR_CORRECT_Q,
                'H': qrcode.constants.ERROR_CORRECT_H
            }.get(options.get('error_correction', 'H'), qrcode.constants.ERROR_CORRECT_H),
            box_size=module_size,
            border=quiet_zone
        )
        
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Get shape and validated colors
        shape = options.get('shape', 'square')
        color = options.get('color', '#000000')
        background_color = options.get('background_color', '#FFFFFF')
        
        # Convert colors to RGB tuples
        color_rgb = hex_to_rgb(color)
        bg_color_rgb = hex_to_rgb(background_color)
        
        # Determine if we need gradient or custom eyes
        using_gradient = options.get('using_gradient', False)
        using_custom_eyes = options.get('custom_eyes', False)
        
        print(f"Generating QR code - Using gradient: {using_gradient}, Using custom eyes: {using_custom_eyes}")
        print(f"QR color: {color}, Background: {background_color}")
        
        # Generate the basic QR image
        try:
            module_drawer = get_module_drawer(shape)
            qr_img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=module_drawer,
                color_mask=SolidFillColorMask(
                    front_color=color_rgb,
                    back_color=bg_color_rgb
                )
            ).convert('RGBA')
            print(f"Generated basic QR with shape: {shape}")
        except Exception as style_error:
            print(f"Error with styled QR generation: {str(style_error)}")
            qr_img = qr.make_image(
                fill_color=color,
                back_color=background_color
            ).convert('RGBA')
            print("Fallback to basic QR generation")
        
        # Apply special effects in sequence - THE ORDER IS IMPORTANT
        
        # 1. First apply gradient if needed
        if using_gradient:
            # Set flag in options so gradient function knows if custom eyes will be applied later
            options['will_apply_custom_eyes'] = using_custom_eyes
            
            try:
                print("Applying gradient to QR code")
                qr_img = apply_gradient(qr_img, options)
                print("Gradient applied successfully")
            except Exception as gradient_error:
                print(f"Error applying gradient: {str(gradient_error)}")
                import traceback
                traceback.print_exc()
        
        # 2. Then apply custom eyes if needed
        if using_custom_eyes:
            try:
                print("Applying custom eyes")
                qr_img = apply_custom_eyes(qr, qr_img, options)
                print("Custom eyes applied successfully")
            except Exception as eye_error:
                print(f"Error applying custom eyes: {str(eye_error)}")
                import traceback
                traceback.print_exc()
        
        # 3. Apply logo if provided - FIXED LOGO HANDLING
        logo_path = options.get('logo_path')
        if logo_path:
            # Enhanced verification of logo path
            logo_exists = False
            
            # Check if path exists directly
            if os.path.exists(logo_path):
                logo_exists = True
            else:
                # Try alternative paths if direct path doesn't exist
                possible_paths = [
                    os.path.join(app.config['UPLOAD_FOLDER'], logo_path),
                    os.path.join('static', 'uploads', logo_path),
                    os.path.join('static', logo_path)
                ]
                
                for alt_path in possible_paths:
                    if os.path.exists(alt_path):
                        logo_path = alt_path
                        logo_exists = True
                        print(f"Found logo at alternative path: {alt_path}")
                        break
            
            if logo_exists:
                try:
                    # Now calling the external apply_logo function
                    qr_img = apply_logo(
                        qr_img, 
                        logo_path,
                        round_corners=options.get('round_logo', False),
                        size_percentage=options.get('logo_size_percentage', 25)
                    )
                    print("Logo applied successfully")
                except Exception as logo_error:
                    print(f"Error applying logo: {str(logo_error)}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"Logo file not found at any expected location: {logo_path}")
        
        # 4. Apply frame if specified
        if options.get('frame_type'):
            try:
                qr_img = apply_frame(qr_img, options.get('frame_type'), options)
                print(f"Frame applied: {options.get('frame_type')}")
            except Exception as frame_error:
                print(f"Error applying frame: {str(frame_error)}")
        
        # 5. Apply watermark if specified
        if options.get('watermark_text'):
            try:
                qr_img = apply_watermark(qr_img, options.get('watermark_text'))
                print("Watermark applied")
            except Exception as watermark_error:
                print(f"Error applying watermark: {str(watermark_error)}")
        
        # Convert to base64 string
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Return data URL and QR info
        qr_info = {
            'version': qr.version,
            'error_correction': options.get('error_correction', 'H'),
            'module_count': len(qr.modules),
            'format': 'png',
            'color': color,
            'eye_colors': {
                'inner': options.get('inner_eye_color', color),
                'outer': options.get('outer_eye_color', color)
            }
        }
        
        return f"data:image/png;base64,{img_str}", qr_info
        
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a fallback/error QR code
        try:
            error_qr = qrcode.make(f"Error generating QR code").get_image()
            buffered = BytesIO()
            error_qr.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            qr_info = {
                'version': 1,
                'error_correction': 'H',
                'module_count': 25,
                'format': 'png',
                'error': str(e)
            }
            
            return f"data:image/png;base64,{img_str}", qr_info
        except:
            # If all else fails, return a simple encoded string
            return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=", {'error': 'Failed to generate QR code', 'format': 'png'}

def batch_generate_qr(data_list, output_format="zip"):
    """
    Generate multiple QR codes at once
    
    Parameters:
    data_list (list): List of dictionaries containing:
        - data: QR code data
        - options: Individual QR code options (optional)
        - label: Name for the QR code file (optional)
    output_format (str): Output format: "zip" or "pdf"
    
    Returns:
    str: Base64 encoded zip or PDF file
    """
    try:
        # Generate multiple QR codes
        qr_images = []
        for item in data_list:
            data = item['data']
            item_options = item.get('options', {})
            
            # Create QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=item_options.get('module_size', 10),
                border=item_options.get('quiet_zone', 4),
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Generate image
            fill_color = item_options.get('color', '#000000')
            bg_color = item_options.get('background_color', '#FFFFFF')
            img = qr.make_image(fill_color=fill_color, back_color=bg_color).convert('RGBA')
            
            # Apply shape if specified
            shape = item_options.get('shape')
            if shape and shape != 'square':
                # Simplified shape application
                width, height = img.size
                mask = Image.new('L', (width, height), 0)
                draw = ImageDraw.Draw(mask)
                
                if shape == 'rounded':
                    radius = width // 10
                    draw.rectangle([radius, radius, width - radius, height - radius], fill=255)
                    draw.rectangle([0, radius, width, height - radius], fill=255)
                    draw.rectangle([radius, 0, width - radius, height], fill=255)
                    draw.pieslice([0, 0, radius * 2, radius * 2], 180, 270, fill=255)
                    draw.pieslice([width - radius * 2, 0, width, radius * 2], 270, 0, fill=255)
                    draw.pieslice([0, height - radius * 2, radius * 2, height], 90, 180, fill=255)
                    draw.pieslice([width - radius * 2, height - radius * 2, width, height], 0, 90, fill=255)
                elif shape == 'circle':
                    draw.ellipse([0, 0, width, height], fill=255)
                
                shaped_img = Image.new('RGBA', (width, height))
                shaped_img.paste(img, (0, 0), mask)
                img = shaped_img
            
            # Apply logo if specified
            logo_path = item_options.get('logo_path')
            if logo_path and os.path.exists(logo_path):
                img = apply_logo(
                    img, 
                    logo_path,
                    round_corners=item_options.get('round_logo', False),
                    size_percentage=item_options.get('logo_size_percentage', 25)
                )
            
            qr_images.append(img)
        
        # Output as requested format
        buffered = BytesIO()
        
        if output_format == "pdf":
            # Create a PDF with multiple QR codes
            try:
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                
                # Create PDF
                c = canvas.Canvas(buffered, pagesize=letter)
                width, height = letter
                
                # Calculate grid layout
                margin = 50
                max_per_row = 2
                qr_size = (width - margin*2) // max_per_row
                
                # Add QR codes to PDF
                for i, img in enumerate(qr_images):
                    row = i // max_per_row
                    col = i % max_per_row
                    
                    x = margin + col * qr_size
                    y = height - margin - (row + 1) * qr_size
                    
                    # Convert PIL image to temp file for PDF
                    temp_img = BytesIO()
                    img = img.resize((int(qr_size * 0.9), int(qr_size * 0.9)), Image.LANCZOS)
                    img.save(temp_img, format='PNG')
                    temp_img.seek(0)
                    
                    # Add to PDF
                    c.drawImage(temp_img, x, y, width=qr_size * 0.9, height=qr_size * 0.9)
                    
                    # Add label if available
                    if 'label' in data_list[i]:
                        c.setFont("Helvetica", 10)
                        c.drawString(x, y - 15, data_list[i]['label'])
                    
                    # Create new page if needed
                    if (i + 1) % (max_per_row * 4) == 0 and i < len(qr_images) - 1:
                        c.showPage()
                
                c.save()
                mime_type = "application/pdf"
            except ImportError:
                # Fallback to ZIP if ReportLab is not available
                output_format = "zip"
        
        if output_format == "zip":
            # Create a ZIP file with multiple QR codes
            import zipfile
         
            # Create ZIP file
            with zipfile.ZipFile(buffered, 'w') as zf:
                for i, img in enumerate(qr_images):
                    # Generate filename
                    filename = f"qrcode_{i+1}.png"
                    if 'label' in data_list[i]:
                        safe_label = data_list[i]['label'].replace(' ', '_').replace('/', '_')
                        filename = f"{safe_label}.png"
                    
                    # Save image to temporary buffer
                    temp_img = BytesIO()
                    img.save(temp_img, format='PNG')
                    temp_img.seek(0)
                    
                    # Add to ZIP
                    zf.writestr(filename, temp_img.getvalue())
            
            mime_type = "application/zip"
        
        # Convert to base64
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return f"data:{mime_type};base64,{img_str}"
    except Exception as e:
        print(f"Error in batch_generate_qr: {str(e)}")
        # Return a simple error message as base64
        error_msg = f"Error generating batch QR codes: {str(e)}"
        return f"data:text/plain;base64,{base64.b64encode(error_msg.encode()).decode()}"
    


def fix_template_override_issues(qr_code, options):
    """
    Enhanced function to fix issues with template colors overriding user selections.
    This ensures eye colors and QR colors are properly applied and
    provides perfect styling consistency.
    """
    # Start with a clean copy of options to avoid modifying the original
    fixed_options = options.copy()
    
    # Always prioritize user's explicitly chosen colors
    if qr_code.color and qr_code.color.strip() and qr_code.color != 'undefined' and qr_code.color != 'null':
        fixed_options['color'] = qr_code.color
        print(f"Using user's explicit color: {qr_code.color}")
    
    if qr_code.background_color and qr_code.background_color.strip() and qr_code.background_color != 'undefined' and qr_code.background_color != 'null':
        fixed_options['background_color'] = qr_code.background_color
        print(f"Using user's explicit background color: {qr_code.background_color}")
    
    # Enable custom eyes by default unless explicitly disabled
    fixed_options['custom_eyes'] = False if qr_code.custom_eyes is False else True
    
    # Determine if we're using gradient
    using_gradient = False
    gradient_start = None
    gradient_end = None
    
    if fixed_options.get('export_type') == 'gradient' or qr_code.export_type == 'gradient':
        using_gradient = True
        gradient_start = qr_code.gradient_start or fixed_options.get('gradient_start')
        gradient_end = qr_code.gradient_end or fixed_options.get('gradient_end')
    
    # Set eye styles and colors appropriately
    if fixed_options['custom_eyes']:
        print("Custom eyes are enabled, setting eye styles and colors")
        
        # Handle eye styles with user preferences first, then sensible defaults
        if qr_code.inner_eye_style:
            fixed_options['inner_eye_style'] = qr_code.inner_eye_style
        elif 'inner_eye_style' not in fixed_options:
            # Default eye style based on QR shape for harmony
            shape_eye_map = {
                'circle': 'circle',
                'rounded': 'rounded',
                'square': 'square',
                'vertical_bars': 'square',
                'horizontal_bars': 'square',
                'gapped_square': 'square'
            }
            qr_shape = fixed_options.get('shape', 'square')
            fixed_options['inner_eye_style'] = shape_eye_map.get(qr_shape, 'square')
        
        if qr_code.outer_eye_style:
            fixed_options['outer_eye_style'] = qr_code.outer_eye_style
        elif 'outer_eye_style' not in fixed_options:
            # Match outer style to inner by default, or based on QR shape
            if 'inner_eye_style' in fixed_options:
                fixed_options['outer_eye_style'] = fixed_options['inner_eye_style']
            else:
                shape_eye_map = {
                    'circle': 'circle',
                    'rounded': 'rounded',
                    'square': 'square'
                }
                qr_shape = fixed_options.get('shape', 'square')
                fixed_options['outer_eye_style'] = shape_eye_map.get(qr_shape, 'square')
        
        # Handle eye colors based on user choices, gradient, or main color
        main_color = fixed_options.get('color', '#000000')
        
        # Inner eye color
        if qr_code.inner_eye_color and qr_code.inner_eye_color.strip() != '' and qr_code.inner_eye_color != 'undefined' and qr_code.inner_eye_color != 'null':
            fixed_options['inner_eye_color'] = qr_code.inner_eye_color
            print(f"Using user's inner eye color: {qr_code.inner_eye_color}")
        elif using_gradient and gradient_start:
            # For gradient QRs, use first gradient color for inner eye
            fixed_options['inner_eye_color'] = gradient_start
            print(f"Using gradient start color for inner eye: {gradient_start}")
        else:
            # Default to main QR color
            fixed_options['inner_eye_color'] = main_color
            print(f"Using main color for inner eye: {main_color}")
        
        # Outer eye color
        if qr_code.outer_eye_color and qr_code.outer_eye_color.strip() != '' and qr_code.outer_eye_color != 'undefined' and qr_code.outer_eye_color != 'null':
            fixed_options['outer_eye_color'] = qr_code.outer_eye_color
            print(f"Using user's outer eye color: {qr_code.outer_eye_color}")
        elif using_gradient and gradient_end:
            # For gradient QRs, use second gradient color for outer eye
            fixed_options['outer_eye_color'] = gradient_end
            print(f"Using gradient end color for outer eye: {gradient_end}")
        else:
            # Default to main QR color
            fixed_options['outer_eye_color'] = main_color
            print(f"Using main color for outer eye: {main_color}")
    else:
        # If custom eyes disabled, REMOVE any eye styles to prevent conflicts
        print("Custom eyes are disabled, removing any eye style settings")
        
        for key in ['inner_eye_style', 'outer_eye_style', 'inner_eye_color', 'outer_eye_color']:
            if key in fixed_options:
                del fixed_options[key]
    
    # Handle frame color if present
    if qr_code.frame_type:
        if qr_code.frame_color and qr_code.frame_color.strip() != '' and qr_code.frame_color != 'undefined' and qr_code.frame_color != 'null':
            fixed_options['frame_color'] = qr_code.frame_color
            print(f"Using user's frame color: {qr_code.frame_color}")
        else:
            fixed_options['frame_color'] = '#000000'  # Default to black instead of QR color
            print("Setting default black color for frame")
    
    # IMPORTANT: Be very strict about when gradients should be used
    should_use_gradient = False
    
    # Check if export_type is explicitly set to gradient
    if fixed_options.get('export_type') == 'gradient':
        should_use_gradient = True
    
    # Also check if both gradient start and end colors are provided
    if using_gradient and gradient_start and gradient_end:
        should_use_gradient = True
        fixed_options['gradient_start'] = gradient_start
        fixed_options['gradient_end'] = gradient_end
        fixed_options['gradient_type'] = getattr(qr_code, 'gradient_type', 'linear')
        fixed_options['gradient_direction'] = getattr(qr_code, 'gradient_direction', 'to-right')
    
    # Set the flag clearly
    fixed_options['using_gradient'] = should_use_gradient
    
    # If not using gradient, REMOVE all gradient-related options to prevent interference
    if not should_use_gradient:
        for key in ['gradient_start', 'gradient_end', 'gradient_type', 'gradient_direction']:
            if key in fixed_options:
                del fixed_options[key]
                
        # Ensure export_type is not 'gradient'
        if fixed_options.get('export_type') == 'gradient':
            fixed_options['export_type'] = 'png'
    
    return fixed_options

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Add custom Jinja2 filter for JSON parsing
@app.template_filter('fromjson')
def fromjson_filter(value):
    """Convert a JSON string to a Python object"""
    if value:
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}

@app.route('/set_timezone', methods=['POST'])
def set_timezone():
    """Store user's timezone in session."""
    if request.is_json:
        timezone_data = request.get_json()
        timezone = timezone_data.get('timezone')
        
        # Validate timezone
        try:
            import pytz
            pytz.timezone(timezone)
            # Store valid timezone in session
            session['user_timezone'] = timezone
            return jsonify({'status': 'success'})
        except (ImportError, pytz.exceptions.UnknownTimeZoneError):
            # If timezone is invalid, set default based on request IP
            # This is a simplified approach - you might want to use a GeoIP service
            ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            # Simple check - you would want a proper GeoIP lookup in production
            if ip.startswith('103.') or ip.startswith('49.') or ip.startswith('122.'):  # Common Indian IP ranges
                session['user_timezone'] = 'Asia/Kolkata'
            else:  # Default to US Eastern
                session['user_timezone'] = 'America/New_York'
            return jsonify({'status': 'fallback', 'timezone': session['user_timezone']})
    
    return jsonify({'status': 'error'}), 400

def get_localized_datetime(utc_datetime, user_timezone=None):
    """
    Convert UTC datetime to user's local timezone.
    
    Args:
        utc_datetime: A datetime object in UTC
        user_timezone: Timezone string (e.g. 'America/New_York', 'Asia/Kolkata')
                      If None, uses session timezone or app default
    
    Returns:
        Datetime object converted to local timezone
    """
    if utc_datetime is None:
        return None
        
    # Ensure datetime has UTC timezone if not already set
    if utc_datetime.tzinfo is None:
        try:
            # For Python 3.11+
            from datetime import UTC
            utc_datetime = utc_datetime.replace(tzinfo=UTC)
        except ImportError:
            # For older Python versions
            from datetime import timezone
            utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    # Get target timezone
    if user_timezone is None:
        user_timezone = session.get('user_timezone', app.config['DEFAULT_TIMEZONE'])
    
    try:
        import pytz
        target_tz = pytz.timezone(user_timezone)
        return utc_datetime.astimezone(target_tz)
    except (ImportError, pytz.exceptions.UnknownTimeZoneError):
        # Fallback to simple offset for Indian Standard Time (+5:30)
        if user_timezone == 'Asia/Kolkata' or user_timezone == 'Asia/Calcutta':
            from datetime import timedelta
            offset = timedelta(hours=5, minutes=30)
            try:
                from datetime import timezone
                return utc_datetime.astimezone(timezone(offset))
            except (ImportError, AttributeError):
                # Very basic fallback
                return utc_datetime + offset
        return utc_datetime  # Return original as last resort
    
@app.template_filter('tojson')
def to_json(value):
    import json
    try:
        if isinstance(value, str):
            return value
        return json.dumps(value)
    except:
        return value
    

@app.context_processor
def inject_subscription_data():
    """Make subscription data available to all templates"""
    if not session.get('user_id'):
        # Not logged in
        return {
            'has_subscription': False,
            'qr_remaining': 0,
            'analytics_remaining': 0,
            'subscription_tier': 0,
            'can_create_dynamic': False,
            'available_designs': []
        }
    
    user_id = session.get('user_id')
    
    # Get active subscription data
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
        .first()
    )
    
    subscription_data = {
        'has_subscription': False,
        'qr_remaining': 0,
        'analytics_remaining': 0,
        'subscription_tier': 0,
        'can_create_dynamic': False,
        'available_designs': []
    }
    
    if active_subscription:
        # Calculate remaining QR codes
        qr_limit = active_subscription.subscription.qr_count
        qr_used = active_subscription.qr_generated
        qr_remaining = max(0, qr_limit - qr_used)
        
        # Calculate remaining analytics
        analytics_limit = active_subscription.subscription.analytics
        analytics_used = active_subscription.analytics_used
        analytics_remaining = max(0, analytics_limit - analytics_used)
        
        # Get subscription tier
        subscription_tier = active_subscription.subscription.tier
        
        # Check if user can create dynamic QR codes
        can_create_dynamic = subscription_tier >= 2
        
        # Get available designs
        available_designs = []
        if active_subscription.subscription.design:
            available_designs = active_subscription.subscription.get_designs()
        
        subscription_data.update({
            'has_subscription': True,
            'qr_remaining': qr_remaining,
            'analytics_remaining': analytics_remaining,
            'subscription_tier': subscription_tier,
            'can_create_dynamic': can_create_dynamic,
            'available_designs': available_designs,
            'plan_name': active_subscription.subscription.plan,
            'days_remaining': active_subscription.days_remaining,
            'expires_on': active_subscription.end_date.strftime('%Y-%m-%d') if active_subscription.end_date else None
        })
    
    return subscription_data
@app.route('/qr_limits')
@login_required
def qr_limits():
    """Show current QR code generation limits and usage"""
    user_id = session.get('user_id')
    
    # Get active subscription
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
        .first()
    )
    
    if not active_subscription:
        flash('You need an active subscription to view QR code limits.', 'warning')
        return redirect(url_for('subscription.user_subscriptions'))
    
    # Get QR code counts
    total_qr_codes = QRCode.query.filter_by(user_id=user_id).count()
    
    # Count QR codes created today and this month
    today = datetime.now(UTC).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)
    
    # First day of current month
    month_start = datetime(today.year, today.month, 1, tzinfo=UTC)
    
    qr_created_today = QRCode.query.filter_by(user_id=user_id).filter(
        QRCode.created_at >= today_start,
        QRCode.created_at <= today_end
    ).count()
    
    qr_created_month = QRCode.query.filter_by(user_id=user_id).filter(
        QRCode.created_at >= month_start,
        QRCode.created_at <= today_end
    ).count()
    
    # Get subscription details
    subscription_plan = active_subscription.subscription
    
    # Calculate QR usage stats
    qr_limit = subscription_plan.qr_count
    qr_used = active_subscription.qr_generated
    qr_remaining = max(0, qr_limit - qr_used)
    qr_percent = (qr_used / qr_limit * 100) if qr_limit > 0 else 0
    
    # Calculate analytics usage stats
    analytics_limit = subscription_plan.analytics
    analytics_used = active_subscription.analytics_used
    analytics_remaining = max(0, analytics_limit - analytics_used)
    analytics_percent = (analytics_used / analytics_limit * 100) if analytics_limit > 0 else 0
    
    # Get available designs
    available_designs = []
    if subscription_plan.design:
        available_designs = subscription_plan.get_designs()
    
    # Get QR types by count
    qr_types = db.session.query(
        QRCode.qr_type, 
        func.count(QRCode.id).label('count')
    ).filter_by(user_id=user_id).group_by(QRCode.qr_type).all()
    
    return render_template('qr_limits.html',
                          subscription=active_subscription,
                          subscription_plan=subscription_plan,
                          total_qr_codes=total_qr_codes,
                          qr_created_today=qr_created_today,
                          qr_created_month=qr_created_month,
                          qr_used=qr_used,
                          qr_limit=qr_limit,
                          qr_remaining=qr_remaining,
                          qr_percent=qr_percent,
                          analytics_used=analytics_used,
                          analytics_limit=analytics_limit,
                          analytics_remaining=analytics_remaining,
                          analytics_percent=analytics_percent,
                          available_designs=available_designs,
                          qr_types=qr_types)

def get_subscription_tier(user_id):
    """Get the subscription tier for a user"""
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
        .first()
    )
    
    if active_subscription:
        return active_subscription.subscription.tier
    return 0

def can_create_dynamic_qr(user_id):
    """Check if a user can create dynamic QR codes based on subscription"""
    tier = get_subscription_tier(user_id)
    return tier >= 2  # Assuming tier 2+ can create dynamic QR codes

def has_subscription_access(user_id, feature_type, tier_required=1):
    """
    Check if user has access to a specific feature based on subscription tier
    
    Args:
        user_id (int): User ID
        feature_type (str): Feature type ('dynamic', 'analytics', 'batch_export', etc.)
        tier_required (int): Minimum tier required for the feature
        
    Returns:
        bool: True if user has access, False otherwise
    """
    # Get user's subscription tier
    tier = get_subscription_tier(user_id)
    
    # Check tier requirement
    if tier < tier_required:
        return False
    
    # Get active subscription
    active_subscription = (
        SubscribedUser.query
        .filter(SubscribedUser.U_ID == user_id)
        .filter(SubscribedUser.end_date > datetime.now(UTC))
        .filter(SubscribedUser._is_active == True)
        .first()
    )
    
    if not active_subscription:
        return False
    
    # Check feature-specific limits
    if feature_type == 'analytics':
        # Check analytics limit
        return active_subscription.analytics_used < active_subscription.subscription.analytics
    elif feature_type == 'qr_code':
        # Check QR code limit
        return active_subscription.qr_generated < active_subscription.subscription.qr_count
    elif feature_type == 'dynamic':
        # Just check tier (already done above)
        return True
    elif feature_type == 'batch_export':
        # Check tier and analytics limit
        return (tier >= tier_required and
                active_subscription.analytics_used < active_subscription.subscription.analytics)
    
    # Default for unknown feature types
    return False

def check_subscription_access(route_function):
    """
    Decorator to redirect to subscription page when feature is unavailable
    
    Args:
        route_function (callable): Flask route function
        
    Returns:
        callable: Decorated function
    """
    @wraps(route_function)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash("You need to log in first.", "warning")
            return redirect(url_for('login'))
        
        # Check if user has an active subscription
        active_subscription = (
            SubscribedUser.query
            .filter(SubscribedUser.U_ID == user_id)
            .filter(SubscribedUser.end_date > datetime.now(UTC))
            .filter(SubscribedUser._is_active == True)
            .first()
        )
        
        if not active_subscription:
            flash("You need an active subscription to access this feature.", "warning")
            return redirect(url_for('subscription.user_subscriptions'))
            
        return route_function(*args, **kwargs)
        
    return decorated_function

def get_qr_options(qr_code):
    """Get QR code options from QR code model - SIMPLIFIED with gradient column"""
    options = {}
    
    # Apply template if specified but create a copy to avoid modifying original template
    if qr_code.template and qr_code.template in QR_TEMPLATES:
        options.update(QR_TEMPLATES[qr_code.template].copy())
        print(f"Applied template: {qr_code.template}")
    
    # Basic styling - always override with user's explicit choices
    if qr_code.color and qr_code.color.strip() and qr_code.color != 'undefined' and qr_code.color != 'null':
        options['color'] = qr_code.color
        print(f"Set color from user choice: {qr_code.color}")
    
    if qr_code.background_color and qr_code.background_color.strip() and qr_code.background_color != 'undefined' and qr_code.background_color != 'null':
        options['background_color'] = qr_code.background_color
        print(f"Set background color from user choice: {qr_code.background_color}")
    
    if qr_code.shape:
        options['shape'] = qr_code.shape
    
    # SIMPLIFIED GRADIENT HANDLING - Use the dedicated gradient column
    using_gradient = qr_code.gradient  # Direct from database column
    options['using_gradient'] = using_gradient
    print(f"Gradient from database column: {using_gradient}")
    
    # If gradient is enabled, include gradient parameters
    if using_gradient:
        options['export_type'] = 'gradient'
        if qr_code.gradient_start:
            options['gradient_start'] = qr_code.gradient_start
        if qr_code.gradient_end:
            options['gradient_end'] = qr_code.gradient_end
        if qr_code.gradient_type:
            options['gradient_type'] = qr_code.gradient_type
        if qr_code.gradient_direction:
            options['gradient_direction'] = qr_code.gradient_direction
        print(f"Gradient colors: {qr_code.gradient_start} -> {qr_code.gradient_end}")
    else:
        # If not using gradient, ensure export type is PNG
        options['export_type'] = 'png'
        # Remove any gradient settings that might be in template
        for key in ['gradient_start', 'gradient_end', 'gradient_type', 'gradient_direction']:
            if key in options:
                del options[key]
    
    # Custom eyes - enabled by default unless explicitly disabled
    options['custom_eyes'] = True if qr_code.custom_eyes is None else qr_code.custom_eyes
    
    # If custom eyes are enabled
    if options['custom_eyes']:
        # Set eye styles based on user choice or template
        if qr_code.inner_eye_style:
            options['inner_eye_style'] = qr_code.inner_eye_style
        elif 'inner_eye_style' not in options:
            # Default inner eye style based on shape
            shape_eye_map = {
                'circle': 'circle',
                'rounded': 'rounded', 
                'square': 'square',
                'vertical_bars': 'square',
                'horizontal_bars': 'square',
                'gapped_square': 'square'
            }
            qr_shape = options.get('shape', 'square')
            options['inner_eye_style'] = shape_eye_map.get(qr_shape, 'square')
            
        if qr_code.outer_eye_style:
            options['outer_eye_style'] = qr_code.outer_eye_style
        elif 'outer_eye_style' not in options:
            # Match outer style to inner if not specified
            if 'inner_eye_style' in options:
                options['outer_eye_style'] = options['inner_eye_style']
            else:
                shape_eye_map = {
                    'circle': 'circle',
                    'rounded': 'rounded',
                    'square': 'square'
                }
                qr_shape = options.get('shape', 'square')
                options['outer_eye_style'] = shape_eye_map.get(qr_shape, 'square')
        
        # Set eye colors based on user choices, gradient, or main color
        main_color = options.get('color', '#000000')
        
        # Set inner eye color
        if qr_code.inner_eye_color and qr_code.inner_eye_color.strip() and qr_code.inner_eye_color != 'undefined' and qr_code.inner_eye_color != 'null':
            options['inner_eye_color'] = qr_code.inner_eye_color
        elif using_gradient and qr_code.gradient_start:
            # For gradient QRs, use gradient start color for inner eye
            options['inner_eye_color'] = qr_code.gradient_start
        else:
            # Default to main QR color
            options['inner_eye_color'] = main_color
            
        # Set outer eye color
        if qr_code.outer_eye_color and qr_code.outer_eye_color.strip() and qr_code.outer_eye_color != 'undefined' and qr_code.outer_eye_color != 'null':
            options['outer_eye_color'] = qr_code.outer_eye_color
        elif using_gradient and qr_code.gradient_end:
            # For gradient QRs, use gradient end color for outer eye
            options['outer_eye_color'] = qr_code.gradient_end
        else:
            # Default to main QR color
            options['outer_eye_color'] = main_color
    
    # Logo settings
    if qr_code.logo_path:
        # Try multiple possible locations for the logo
        logo_locations = [
            qr_code.logo_path,  # As stored
            os.path.join(app.config['UPLOAD_FOLDER'], qr_code.logo_path),  # With upload folder
            os.path.join('static', 'uploads', qr_code.logo_path),  # With static/uploads
            os.path.join('static', qr_code.logo_path)  # With static
        ]
        
        # Find first existing location
        found_logo = False
        for location in logo_locations:
            if os.path.exists(location):
                options['logo_path'] = location
                found_logo = True
                print(f"Found logo at: {location}")
                break
        
        if not found_logo:
            print(f"Warning: Logo path {qr_code.logo_path} not found in any expected location")
            options['logo_path'] = os.path.join(app.config['UPLOAD_FOLDER'], qr_code.logo_path)
        
        options['round_logo'] = qr_code.round_logo
        options['logo_size_percentage'] = qr_code.logo_size_percentage
    
    # Frame settings
    if qr_code.frame_type:
        options['frame_type'] = qr_code.frame_type
        options['frame_text'] = qr_code.frame_text
        options['frame_color'] = getattr(qr_code, 'frame_color', '#000000')
    
    # Module settings
    options['module_size'] = qr_code.module_size
    options['quiet_zone'] = qr_code.quiet_zone
    options['error_correction'] = qr_code.error_correction
    
    # Watermark
    if qr_code.watermark_text:
        options['watermark_text'] = qr_code.watermark_text
    
    return options


# Execute application
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_super_admin()
    app.run(debug=True)
