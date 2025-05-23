from .database import db
from datetime import datetime, UTC, timedelta  # Update datetime import to include timedelta
from sqlalchemy.orm import relationship
from decimal import Decimal, ROUND_HALF_UP
import uuid
import decimal 
class Payment(db.Model):
    __tablename__ = 'payments'
    
    iid = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.S_ID', ondelete='SET NULL'), nullable=False)
    razorpay_order_id = db.Column(db.String(100), nullable=False)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    
    # Invoice-specific Details
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    invoice_date = db.Column(db.DateTime, default=datetime.now(UTC))
    
    # Extended Payment Information
    order_number = db.Column(db.String(50), nullable=True)
    customer_number = db.Column(db.String(50), nullable=True)
    purchase_order = db.Column(db.String(50), nullable=True)
    payment_terms = db.Column(db.String(100), default='Credit Card')
    
    # Base amount and tax calculations
    base_amount = db.Column(db.Float, nullable=False)
    gst_rate = db.Column(db.Float, default=0.18)  # Default 18% GST
    gst_amount = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Additional tax-related information
    hsn_code = db.Column(db.String(20), nullable=True)
    cin_number = db.Column(db.String(50), nullable=True)
    
    currency = db.Column(db.String(10), default='INR')
    status = db.Column(db.String(20), default='created')
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    payment_type = db.Column(db.String(20), default='new')
    previous_subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.S_ID'), nullable=True)
    credit_applied = db.Column(db.Float, default=0.0)
    
    # Additional notes or special instructions
    notes = db.Column(db.Text, nullable=True)
    
    # Relationships
    user = relationship("User", backref="payments")
    subscription = relationship("Subscription", foreign_keys=[subscription_id], backref="payments")
    previous_subscription = relationship("Subscription", foreign_keys=[previous_subscription_id])
    invoice_address = relationship("InvoiceAddress", back_populates="payment", uselist=False)
    
    def __init__(self, *args, **kwargs):
        # Get the base_amount from kwargs with a default value of 0
        base_amount = kwargs.pop('base_amount', 0)
        gst_rate = kwargs.pop('gst_rate', 0.18)
        
        # Validate inputs more robustly
        try:
            base_amount = float(base_amount)
            if base_amount < 0:
                raise ValueError("Base amount must be a non-negative number")
        except (TypeError, ValueError):
            raise ValueError("Invalid base amount provided")
        
        super().__init__(*args, **kwargs)
        
        self.base_amount = base_amount
        self.gst_rate = gst_rate
        
        self._generate_invoice_details()
        self._calculate_total_amount()
    
    def _generate_invoice_details(self):
        """
        Generate unique invoice details with more robust generation
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d")
        unique_id = str(uuid.uuid4().hex)[:6].upper()
        self.invoice_number = f"INV-{timestamp}-{unique_id}"
        self.invoice_date = datetime.now(UTC)
    
    def _calculate_total_amount(self):
        """
        Enhanced total amount calculation with comprehensive error handling
        """
        try:
            base = Decimal(str(self.base_amount)).quantize(Decimal('0.01'))
            gst_rate = Decimal(str(self.gst_rate)).quantize(Decimal('0.01'))
            
            gst_amount = base * gst_rate
            gst_amount = gst_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            total_amount = base + gst_amount
            total_amount = total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            self.gst_amount = float(gst_amount)
            self.total_amount = float(total_amount)
        except (TypeError, ValueError, decimal.InvalidOperation) as e:
            # Log the error and set default values
            print(f"Error in amount calculation: {e}")
            self.gst_amount = 0
            self.total_amount = self.base_amount
    
    def generate_invoice_pdf(self):
        """
        Placeholder method for generating invoice PDF
        Can be implemented with a library like ReportLab
        """
        # Future implementation for PDF generation
        pass
    
    def get_invoice_summary(self):
        """
        Return a comprehensive invoice summary
        
        :return: Dictionary with invoice details
        """
        return {
            'invoice_number': self.invoice_number,
            'invoice_date': self.invoice_date,
            'order_number': self.order_number,
            'customer_number': self.customer_number,
            'base_amount': self.base_amount,
            'gst_rate': self.gst_rate * 100,
            'gst_amount': self.gst_amount,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'status': self.status
        }
    
    def __repr__(self):
        return f"<Payment {self.invoice_number} - {self.total_amount}>"

class InvoiceAddress(db.Model):
    __tablename__ = 'invoice_addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.iid'), nullable=False)
    company_name = db.Column(db.String(255), nullable=True)
    full_name = db.Column(db.String(255), nullable=False)
    street_address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), default='India')
    email = db.Column(db.String(255), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    gst_number = db.Column(db.String(20), nullable=True)
    pan_number = db.Column(db.String(20), nullable=True)
    
    payment = relationship("Payment", back_populates="invoice_address")

