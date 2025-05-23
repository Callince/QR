from .database import db
from datetime import datetime, UTC
import logging
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

# Models
class User(UserMixin, db.Model):
    # __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    company_email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    email_confirmed = db.Column(db.Boolean, default=False)
    email_confirm_token = db.Column(db.String(500), nullable=True)  # Increased length to safely store token
    email_token_created_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))  
    qr_codes = db.relationship('QRCode', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Updated Token Generation
    def get_reset_token(self, expires_sec=1800):
        """Generate a secure token for password reset (30 minute expiry)"""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id, 'email': self.company_email, 'purpose': 'reset_password'}, 
                      salt='password-reset-salt')

    # Updated Token Verification
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        """Verify a password reset token"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
            user_id = data.get('user_id')
            purpose = data.get('purpose')
            if user_id and purpose == 'reset_password':
                return User.query.get(user_id)
            return None
        except Exception as e:
            logging.error(f"Token verification error: {str(e)}")
            return None
        
    # Updated Email Confirmation Token
    def get_email_confirm_token(self):
        """Generate a secure token for email confirmation"""
        try:
            s = Serializer(current_app.config['SECRET_KEY'])
            token = s.dumps({
                'user_id': self.id, 
                'email': self.company_email, 
                'purpose': 'email_confirm',
                'timestamp': datetime.now(UTC).timestamp()  # Add timestamp for uniqueness
            }, salt='email-confirm-salt')
            
            # Store token in the user model
            self.email_confirm_token = token
            self.email_token_created_at = datetime.now(UTC)
            
            # Return the token - committing will be done by calling function
            return token
        except Exception as e:
            logging.error(f"Error generating token: {str(e)}")
            return None
        
    # Updated Email Token Verification
    @staticmethod
    def verify_email_token(token, expires_sec=86400):  # 24 hours
        """Verify an email confirmation token"""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='email-confirm-salt', max_age=expires_sec)
            user_id = data.get('user_id')
            purpose = data.get('purpose')
            
            logging.info(f"Verifying email token: user_id={user_id}, purpose={purpose}")
            
            if user_id and purpose == 'email_confirm':
                user = User.query.get(user_id)
                
                # Additional check to make sure token matches stored token
                if user and user.email_confirm_token == token:
                    return user
                elif user:
                    logging.warning(f"Token mismatch for user {user_id}: Stored token doesn't match provided token")
                else:
                    logging.warning(f"User {user_id} not found")
                    
                return user
            return None
        except Exception as e:
            logging.error(f"Email token verification error: {str(e)}")
            return None