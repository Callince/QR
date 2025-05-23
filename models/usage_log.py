from .database import db
from .user import User
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import relationship

class UsageLog(db.Model):
    __tablename__ = 'usage_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscribed_users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(UTC))
    operation_type = db.Column(db.String(100), nullable=False)  # e.g., 'url_analysis', 'keyword_search', etc.
    details = db.Column(db.Text, nullable=True)  # Additional details in JSON format
    
    # Relationships
    user = relationship('User', backref=db.backref('usage_logs', lazy=True))
    subscription = relationship('SubscribedUser', backref=db.backref('usage_logs', lazy=True))
    
    def __repr__(self):
        return f"<UsageLog id={self.id}, user_id={self.user_id}, operation={self.operation_type}>"

