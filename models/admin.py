from flask import Blueprint, current_app, render_template, request, redirect
from flask import url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, case, or_
from datetime import datetime, timedelta, UTC
from functools import wraps
import uuid
import time
import string
import random
import logging
from io import BytesIO
from .database import db
from .user import User
from .subscription import Subscription, SubscribedUser, SubscriptionHistory, generate_invoice_pdf
from .payment import Payment, InvoiceAddress

from flask import current_app

from razorpay import Client

# Create the blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ----------------------
# Admin Model Definition
# ----------------------

class Admin(db.Model):
    __tablename__ = 'admin'

    id = db.Column(db.Integer, primary_key=True)
    email_id = db.Column(db.String(120), nullable=False, unique=True)
    NAME = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(15), nullable=True)
    assigned_by = db.Column(db.String(50), nullable=False)
    permission = db.Column(db.ARRAY(db.String(50))) 
    password_hash = db.Column(db.String(256), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, onupdate=datetime.now(UTC))
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        """Set the password hash."""
        if password and password.strip():
            try:
                self.password_hash = generate_password_hash(password)
                return True
            except Exception as e:
                current_app.logger.error(f"Password hashing error: {str(e)}")
                return False
        return False

    def check_password(self, password):
        """Check the password against the stored hash."""
        if not self.password_hash or not password:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except Exception as e:
            current_app.logger.error(f"Password check error: {str(e)}")
            return False

    def admin_permissions(self, required_permission):
        """Check if admin has the specified permission"""
        if request.method == 'POST':
            email_id = request.form.get('email_id')
            permissions = request.form.getlist('permissions[]')
            
            if self.email_id == email_id:
                return required_permission in permissions
            
        return required_permission in self.permission if self.permission else False

    @staticmethod
    def check_permission(email_id, required_permission):
        """Static method to check permissions by email"""
        admin = Admin.query.filter_by(email_id=email_id).first()
        if not admin:
            return False
            
        if request.method == 'POST':
            form_email = request.form.get('email_id')
            if form_email == email_id:
                permissions = request.form.getlist('permissions[]')
                return required_permission in permissions
                
        return admin.admin_permissions(required_permission)

    def __repr__(self):
        return f"<Admin {self.NAME} - {self.role}>"
    

# Helper decorator for admin authentication
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in as admin first.', 'warning')
            return redirect(url_for('admin.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper functions
def generate_unique_invoice_number():
    """Generate a unique invoice number"""
    timestamp = datetime.now(UTC).strftime("%y%m%d")
    unique_id = str(uuid.uuid4().hex)[:8]
    return f"INV-{timestamp}-{unique_id}"

def create_or_update_subscription(payment):
    """Create or update subscription based on payment"""
    # Check if subscription already exists
    existing_sub = SubscribedUser.query.filter_by(
        U_ID=payment.user_id,
        S_ID=payment.subscription_id
    ).first()
    
    if not existing_sub:
        subscription = db.session.get(Subscription, payment.subscription_id)
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=subscription.days)
        
        new_subscription = SubscribedUser(
            U_ID=payment.user_id,
            S_ID=payment.subscription_id,
            start_date=start_date,
            end_date=end_date,
            current_usage=0,
            is_auto_renew=True
        )
        
        # Record subscription history
        history_entry = SubscriptionHistory(
            U_ID=payment.user_id,
            S_ID=payment.subscription_id,
            action=payment.payment_type,
            previous_S_ID=payment.previous_subscription_id
        )
        
        db.session.add(new_subscription)
        db.session.add(history_entry)

def create_invoice_address_for_payment(payment):
    """Create invoice address for payment if not exists"""
    existing_address = InvoiceAddress.query.filter_by(payment_id=payment.iid).first()
    
    if not existing_address:
        # Try to get user details
        user = User.query.get(payment.user_id)
        
        new_address = InvoiceAddress(
            payment_id=payment.iid,
            full_name=user.name,
            email=user.company_email,
            company_name=user.company_name if hasattr(user, 'company_name') else None,
            street_address=user.address if hasattr(user, 'address') else 'N/A',
            city=user.city if hasattr(user, 'city') else 'N/A',
            state=user.state if hasattr(user, 'state') else 'N/A',
            postal_code=user.postal_code if hasattr(user, 'postal_code') else 'N/A',
            gst_number=user.gst_number if hasattr(user, 'gst_number') else None
        )
        
        db.session.add(new_address)

def create_super_admin():
    """Create super admin user if it doesn't exist"""
    try:
        # Check if super admin already exists
        super_admin_email = "goodson@fourdm.digital.com"
        existing_admin = Admin.query.filter_by(email_id=super_admin_email).first()
        
        if existing_admin:
            print("Super admin already exists")
            return

        # Create super admin with all permissions
        super_admin = Admin(
            email_id=super_admin_email,
            NAME="Super Admin",
            role="Super Admin",
            phone_number="8122156835",
            assigned_by="System",
            permission=[
                "dashboard",
                "manage_roles",
                "subscription_management",
                "subscribed_users_view",
                "user_management",
                "payments"
            ],
            is_active=True,
            created_at=datetime.now(UTC)
        )

        # Set password explicitly
        super_admin.set_password("Good@1234")
        
        # Add and commit
        db.session.add(super_admin)
        db.session.commit()
        
        print("Super admin created successfully!")
        print(f"Email: {super_admin_email}")
        print(f"Password: Good@1234")
        
        return super_admin

    except Exception as e:
        print(f"Error creating super admin: {str(e)}")
        db.session.rollback()
        return None 

# ----------------------
# Admin Routes
# ----------------------

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    try:
        now = datetime.now(UTC)
        
        # Create a custom RecentPayment class to match template expectations
        class RecentPayment:
            def _init_(self, user, subscription, payment):
                self.user = user
                self.subscription = subscription
                self.payment = payment
            
            def format_amount(self):
                try:
                    if hasattr(self.payment, 'total_amount') and self.payment.total_amount:
                        return "{:,.2f}".format(float(self.payment.total_amount))
                    elif hasattr(self.payment, 'base_amount') and self.payment.base_amount:
                        return "{:,.2f}".format(float(self.payment.base_amount))
                    elif hasattr(self.payment, 'amount') and self.payment.amount:
                        return "{:,.2f}".format(float(self.payment.amount))
                    else:
                        return "0.00"
                except (AttributeError, TypeError, ValueError):
                    return "0.00"

        # Get basic statistics
        total_users = User.query.count() or 0
        active_users = User.query.filter_by(email_confirmed=True).count() or 0
        unconfirmed_users = total_users - active_users
        
        # Calculate active and expired subscriptions
        active_subscriptions = SubscribedUser.query.filter(SubscribedUser.end_date > now).count() or 0
        expired_subscriptions = SubscribedUser.query.filter(SubscribedUser.end_date <= now).count() or 0
        
        # Calculate revenue metrics
        try:
            total_revenue_query = db.session.query(func.sum(Payment.total_amount)).filter(Payment.status == 'completed').scalar()
            total_revenue = float(total_revenue_query) if total_revenue_query else 0.0
            
            monthly_revenue_query = db.session.query(func.sum(Payment.total_amount)).filter(
                Payment.status == 'completed',
                Payment.created_at >= (now - timedelta(days=30))
            ).scalar()
            monthly_revenue = float(monthly_revenue_query) if monthly_revenue_query else 0.0
        except Exception as e:
            current_app.logger.error(f"Revenue calculation error: {str(e)}")
            total_revenue = 0.0
            monthly_revenue = 0.0
        
        # Get recent payments
        try:
            recent_payments_query = (
                db.session.query(Payment, User, Subscription)
                .join(User, Payment.user_id == User.id)
                .join(Subscription, Payment.subscription_id == Subscription.S_ID)
                .filter(Payment.status == 'completed')
                .order_by(Payment.created_at.desc())
                .limit(10)
                .all()
            )
            
            recent_payments = []
            for payment, user, subscription in recent_payments_query:
                recent_payments.append(RecentPayment(user=user, subscription=subscription, payment=payment))
        except Exception as e:
            current_app.logger.error(f"Recent payments query error: {str(e)}")
            recent_payments = []
        
        # Get popular subscription plans
        try:
            popular_plans_query = (
                db.session.query(
                    Subscription.plan,
                    func.count(SubscribedUser.id).label('subscribers')
                )
                .join(SubscribedUser, Subscription.S_ID == SubscribedUser.S_ID)
                .filter(SubscribedUser.end_date > now)  # Only active subscriptions
                .group_by(Subscription.plan)
                .order_by(func.count(SubscribedUser.id).desc())
                .limit(5)
                .all()
            )
            
            popular_plans = []
            for plan_name, subscriber_count in popular_plans_query:
                popular_plans.append({
                    'plan': str(plan_name) if plan_name else 'Unknown',
                    'subscribers': int(subscriber_count) if subscriber_count else 0
                })
        except Exception as e:
            current_app.logger.error(f"Popular plans query error: {str(e)}")
            popular_plans = []
        
        # Get subscriptions expiring soon
        try:
            expiring_soon_query = (
                db.session.query(User, Subscription, SubscribedUser)
                .join(SubscribedUser, User.id == SubscribedUser.U_ID)
                .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
                .filter(
                    SubscribedUser.end_date > now,
                    SubscribedUser.end_date <= now + timedelta(days=7)
                )
                .order_by(SubscribedUser.end_date.asc())
                .all()
            )
            
            expiring_soon = []
            for user, subscription, subscribed_user in expiring_soon_query:
                # Ensure timezone consistency
                if subscribed_user.end_date.tzinfo is None:
                    subscribed_user.end_date = subscribed_user.end_date.replace(tzinfo=UTC)
                if subscribed_user.start_date.tzinfo is None:
                    subscribed_user.start_date = subscribed_user.start_date.replace(tzinfo=UTC)
                
                expiring_soon.append((user, subscription, subscribed_user))
        except Exception as e:
            current_app.logger.error(f"Expiring subscriptions query error: {str(e)}")
            expiring_soon = []
        
        # Get subscription activities/actions
        try:
            subscription_actions_query = (
                db.session.query(
                    SubscriptionHistory.action,
                    func.count(SubscriptionHistory.id).label('count')
                )
                .filter(SubscriptionHistory.created_at >= (now - timedelta(days=30)))
                .group_by(SubscriptionHistory.action)
                .order_by(func.count(SubscriptionHistory.id).desc())
                .all()
            )
            
            subscription_actions = []
            for action_name, action_count in subscription_actions_query:
                subscription_actions.append({
                    'action': str(action_name) if action_name else 'Unknown',
                    'count': int(action_count) if action_count else 0
                })
        except Exception as e:
            current_app.logger.error(f"Subscription actions query error: {str(e)}")
            subscription_actions = []
        
        # Auto-renewal statistics
        try:
            auto_renewal_count = SubscribedUser.query.filter(
                SubscribedUser.is_auto_renew == True,
                SubscribedUser.end_date > now
            ).count() or 0
            
            non_renewal_count = SubscribedUser.query.filter(
                or_(SubscribedUser.is_auto_renew == False, SubscribedUser.is_auto_renew.is_(None)),
                SubscribedUser.end_date > now
            ).count() or 0
        except Exception as e:
            current_app.logger.error(f"Auto-renewal stats query error: {str(e)}")
            auto_renewal_count = 0
            non_renewal_count = 0
        
        # Payment types distribution
        try:
            payment_types_query = (
                db.session.query(
                    Payment.payment_type,
                    func.count(Payment.iid).label('count')
                )
                .filter(Payment.status == 'completed')
                .group_by(Payment.payment_type)
                .order_by(func.count(Payment.iid).desc())
                .all()
            )
            
            payment_types = []
            for payment_type_name, payment_count in payment_types_query:
                payment_types.append({
                    'payment_type': str(payment_type_name) if payment_type_name else 'Unknown',
                    'count': int(payment_count) if payment_count else 0
                })
        except Exception as e:
            current_app.logger.error(f"Payment types query error: {str(e)}")
            payment_types = []
        
        # Debug logging
        current_app.logger.info(f"Dashboard data prepared successfully")
        current_app.logger.debug(f"Popular plans: {popular_plans}")
        current_app.logger.debug(f"Payment types: {payment_types}")
        current_app.logger.debug(f"Subscription actions: {subscription_actions}")
        current_app.logger.debug(f"Auto renewal: {auto_renewal_count}, Manual: {non_renewal_count}")
        
        return render_template('admin/dashboard.html', 
                              now=now,
                              total_users=total_users,
                              active_users=active_users,
                              unconfirmed_users=unconfirmed_users,
                              active_subscriptions=active_subscriptions,
                              expired_subscriptions=expired_subscriptions,
                              recent_payments=recent_payments,
                              total_revenue=total_revenue,
                              monthly_revenue=monthly_revenue,
                              popular_plans=popular_plans,
                              expiring_soon=expiring_soon,
                              subscription_actions=subscription_actions,
                              auto_renewal_count=auto_renewal_count,
                              non_renewal_count=non_renewal_count,
                              payment_types=payment_types)
                              
    except Exception as e:
        current_app.logger.error(f"Dashboard error: {str(e)}")
        # Return a minimal dashboard with empty data in case of error
        return render_template('admin/dashboard.html', 
                              now=datetime.now(UTC),
                              total_users=0,
                              active_users=0,
                              unconfirmed_users=0,
                              active_subscriptions=0,
                              expired_subscriptions=0,
                              recent_payments=[],
                              total_revenue=0.0,
                              monthly_revenue=0.0,
                              popular_plans=[],
                              expiring_soon=[],
                              subscription_actions=[],
                              auto_renewal_count=0,
                              non_renewal_count=0,
                              payment_types=[])

#-------------------------
# Admin login and logout
#-------------------------

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        print(f"Login attempt for email: {email}")  # Debug print

        # Input validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('admin/login.html')

        # Get admin user
        admin = Admin.query.filter_by(email_id=email).first()
        
        if not admin:
            print(f"No admin found with email: {email}")  # Debug print
            flash('Invalid email or password.', 'danger')
            return render_template('admin/login.html')

        # Verify password
        if admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin_name'] = admin.NAME
            session['email_id'] = admin.email_id
            session['admin_permissions'] = admin.permission if isinstance(admin.permission, list) else []
            
            print(f"Admin login successful: {email}")  # Debug print
            flash('Login successful!', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            print(f"Invalid password for admin: {email}")  # Debug print
            flash('Invalid email or password.', 'danger')

    return render_template('admin/login.html')
@admin_bp.route('/logout')
@admin_required
def admin_logout():
    session.pop('admin_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('admin.admin_login'))


# Route to add and display roles
@admin_bp.route('/roles', methods=['GET', 'POST'])
@admin_required
def manage_roles():
    # Check if the user has permission to manage roles
    email_id = session.get('email_id')
    if not Admin.check_permission(email_id, 'manage_roles'):
        flash("You don't have permission to manage roles.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

        
    if request.method == 'POST':
        try:
            # Get form data
            name = request.form.get('NAME')
            email_id = request.form.get('email_id')
            role = request.form.get('role')
            phone_number = request.form.get('phone_number')
            password = request.form.get('password')
            permissions = request.form.getlist('permissions[]')
            # Validate required fields
            if not all([name, email_id, role]):
                flash('Name, email and role are required fields.', 'danger')
                return redirect(url_for('admin.manage_roles'))

            admin_role = Admin.query.filter_by(email_id=email_id).first()

            if admin_role:
                # Update existing admin
                admin_role.NAME = name
                admin_role.role = role
                admin_role.phone_number = phone_number
                admin_role.permission = permissions
                admin_role.updated_at = datetime.now(UTC)
                
                 # Only update password if provided
                if password and password.strip():
                    if not admin_role.set_password(password):
                        flash('Error setting password.', 'danger')
                        return redirect(url_for('admin.manage_roles'))
                
                flash(f'Role updated successfully for {name}!', 'success')
            else:
                # Create new admin
                if not password:
                    flash('Password is required for new admin roles.', 'danger')
                    return redirect(url_for('admin.manage_roles'))

                new_role = Admin(
                    NAME=name,
                    email_id=email_id,
                    role=role,
                    phone_number=phone_number,
                    permission=permissions,
                    assigned_by=session.get('admin_name', 'System'),
                    is_active=True
                )

                # Set password for new admin
                if not new_role.set_password(password):
                    flash('Error setting password.', 'danger')
                    return redirect(url_for('admin.manage_roles'))

                db.session.add(new_role)
                flash(f'New role created successfully for {name}!', 'success')

            db.session.commit()
            return redirect(url_for('admin.manage_roles'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Role management error: {str(e)}")
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('admin.manage_roles'))

    roles = Admin.query.all()
    return render_template('admin/roles.html', roles=roles)

@admin_bp.route('/roles/edit/<int:role_id>', methods=['GET', 'POST'])
@admin_required
def edit_role(role_id):
    role = Admin.query.get_or_404(role_id)

    if request.method == 'POST':
        try:
            # Get form data
            role.NAME = request.form.get('NAME')
            role.email_id = request.form.get('email_id')
            role.role = request.form.get('role')
            role.phone_number = request.form.get('phone_number')
            permissions = request.form.getlist('permissions[]')
            password = request.form.get('password')

            # Validate required fields
            if not all([role.NAME, role.email_id, role.role]):
                flash('Name, email and role are required fields.', 'danger')
                return redirect(url_for('admin.edit_role', role_id=role_id))

            # Update password if provided
            if password and password.strip():
                if not role.set_password(password):
                    flash('Error updating password.', 'danger')
                    return redirect(url_for('admin.edit_role', role_id=role_id))

            # Update other fields
            role.permission = permissions
            role.updated_at = datetime.now(UTC)

            db.session.commit()
            flash(f'Role updated successfully for {role.NAME}!', 'success')
            return redirect(url_for('admin.manage_roles'))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Role update error: {str(e)}")
            flash(f'Error updating role: {str(e)}', 'danger')
            return redirect(url_for('admin.edit_role', role_id=role_id))

    return render_template('admin/edit_role.html', 
                         role=role, 
                         role_permissions=role.permission if role.permission else [])

#------------------------------
# admin Subscription Management
#------------------------------
@admin_bp.route('/subscriptions')
def admin_subscriptions():
    email_id = session.get('email_id')
    
    if not Admin.check_permission(email_id, 'subscription_management'):
        flash("You don't have permission to access this page.", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    # Get all subscription plans with subscriber counts
    subscriptions = (
        db.session.query(
            Subscription,
            func.count(SubscribedUser.id).label('active_subscribers'),
            func.sum(case(
                (SubscribedUser.end_date > datetime.now(UTC), 1),
                else_=0
            )).label('active_count')
        )
        .outerjoin(SubscribedUser, Subscription.S_ID == SubscribedUser.S_ID)
        .group_by(Subscription.S_ID)
        .all()
    )
    
    # Extract the Subscription object and other data into a list of dictionaries
    subscription_data = [
        {
            "subscription": row[0],  # Subscription object
            "active_subscribers": row[1],
            "active_count": row[2]
        }
        for row in subscriptions
    ]
    
    return render_template('admin/subscriptions.html', subscriptions=subscription_data)

@admin_bp.route('/subscriptions/new', methods=['GET', 'POST'])
def admin_new_subscription():
    if request.method == 'POST':
        plan = request.form.get('plan')
        price = float(request.form.get('price'))
        days = int(request.form.get('days'))
        tier = int(request.form.get('tier', 1))
        features = request.form.get('features', '')
        plan_type = request.form.get('plan_type', 'Normal')
        
        # New fields
        design = request.form.get('design', '')
        analytics = int(request.form.get('analytics', 0))
        qr_count = int(request.form.get('qr_count', 0))
        
        # Validate inputs
        if not plan or price <= 0 or days <= 0 or tier <= 0:
            flash('Invalid subscription details. Please check your input.', 'danger')
            return redirect(url_for('admin.admin_new_subscription'))
        
        # Check if plan name already exists
        existing_plan = Subscription.query.filter_by(plan=plan).first()
        if existing_plan:
            flash('A subscription plan with this name already exists.', 'danger')
            return redirect(url_for('admin.admin_new_subscription'))
        
        new_subscription = Subscription(
            plan=plan,
            price=price,
            days=days, # Use analytics value for backward compatibility
            tier=tier,
            features=features,
            plan_type=plan_type,
            design=design,
            analytics=analytics,
            qr_count=qr_count
        )
        
        db.session.add(new_subscription)
        db.session.commit()
        
        flash('Subscription plan created successfully!', 'success')
        return redirect(url_for('admin.admin_subscriptions'))
    
    return render_template('admin/new_subscription.html')

@admin_bp.route('/subscriptions/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_subscription(id):
    subscription = db.session.get(Subscription, id)
    
    # Get active subscribers count
    active_subscribers = SubscribedUser.query.filter(
        SubscribedUser.S_ID == id,
        SubscribedUser.end_date > datetime.now(UTC)
    ).count()
    
    if request.method == 'POST':
        plan = request.form.get('plan')
        price = float(request.form.get('price'))
        days = int(request.form.get('days'))
        tier = int(request.form.get('tier', subscription.tier))
        features = request.form.get('features', subscription.features)
        plan_type = request.form.get('plan_type', subscription.plan_type)
        
        # New fields
        design = request.form.get('design', '')
        analytics = int(request.form.get('analytics', 0))
        qr_count = int(request.form.get('qr_count', 0))
        
        # Validate inputs
        if not plan or price <= 0 or days <= 0 or tier <= 0:
            flash('Invalid subscription details. Please check your input.', 'danger')
            return redirect(url_for('admin.admin_edit_subscription', id=id))
        
        # Check if plan name already exists with a different ID
        existing_plan = Subscription.query.filter(
            Subscription.plan == plan,
            Subscription.plan_type == plan_type,
            Subscription.S_ID != id
        ).first()
        
        if existing_plan:
            flash('A subscription plan with this name already exists.', 'danger')
            return redirect(url_for('admin.admin_edit_subscription', id=id))
        
        subscription.plan = plan
        subscription.price = price
        subscription.days = days
        subscription.tier = tier
        subscription.features = features
        subscription.plan_type = plan_type
        subscription.design = design
        subscription.analytics = analytics
        subscription.qr_count = qr_count

        db.session.commit()
        
        flash('Subscription plan updated successfully!', 'success')
        return redirect(url_for('admin.admin_subscriptions'))
    
    return render_template('admin/edit_subscription.html', 
                          subscription=subscription,
                          active_subscribers=active_subscribers)
# Add these routes to your Flask application

@admin_bp.route('/subscriptions/archive/<int:id>', methods=['POST'])
def admin_archive_subscription(id):
    subscription = db.session.get(Subscription, id)
    
    # Check if already archived
    if subscription.archived_at:
        flash('This subscription plan is already archived.', 'warning')
        return redirect(url_for('admin.admin_subscriptions'))
    
    # Archive the subscription plan
    subscription.is_active = False
    subscription.archived_at = datetime.now(UTC)
    db.session.commit()
    
    flash('Subscription plan has been archived successfully.', 'success')
    return redirect(url_for('admin.admin_subscriptions'))


@admin_bp.route('/subscriptions/restore/<int:id>', methods=['POST'])
def admin_restore_subscription(id):
    subscription = db.session.get(Subscription, id)
    
    # Check if not archived
    if not subscription.archived_at:
        flash('This subscription plan is not archived.', 'warning')
        return redirect(url_for('admin.admin_subscriptions'))
    
    # Restore the subscription plan
    subscription.is_active = True
    subscription.archived_at = None
    db.session.commit()
    
    flash('Subscription plan has been restored successfully.', 'success')
    return redirect(url_for('admin.admin_subscriptions'))

@admin_bp.route('/subscriptions/delete/<int:id>', methods=['POST'])
def admin_delete_subscription(id):
    subscription = db.session.get(Subscription, id)
    
    # Check if there are any users subscribed to this plan (active or inactive)
    if subscription.subscribed_users:
        flash('Cannot delete subscription plan as it has users associated with it. Please remove the user subscriptions first.', 'danger')
        return redirect(url_for('admin.admin_subscriptions'))
    
    # Check if there are any payments or history records associated with this plan
    payment_count = Payment.query.filter_by(subscription_id=id).count()
    history_count = SubscriptionHistory.query.filter(
        (SubscriptionHistory.S_ID == id) | 
        (SubscriptionHistory.previous_S_ID == id)
    ).count()
    
    if payment_count > 0 or history_count > 0:
        # Instead of blocking, mark as archived
        subscription.is_active = False
        subscription.archived_at = datetime.now(UTC)
        db.session.commit()
        
        flash('Subscription plan has been archived as it has payment or history records associated with it.', 'warning')
        return redirect(url_for('admin.admin_subscriptions'))
    
    # If no constraints, perform actual deletion
    db.session.delete(subscription)
    db.session.commit()
    
    flash('Subscription plan deleted successfully!', 'success')
    return redirect(url_for('admin.admin_subscriptions'))
    
@admin_bp.route('/subscribed-users')
def admin_subscribed_users():

    email_id = session.get('email_id')
    
    if not Admin.check_permission(email_id, 'subscribed_users_view'):
        flash("You don't have permission to access this page.", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    plan_filter = request.args.get('plan', 'all')
    
    # Get current time - use naive datetime to match database storage
    now = datetime.now(UTC)
    
    # Base query with joins
    query = (
        db.session.query(
            SubscribedUser, 
            User, 
            Subscription
        )
        .join(User, SubscribedUser.U_ID == User.id)
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
    )
    
    # Apply filters
    if status_filter == 'active':
        query = query.filter(SubscribedUser.end_date > now)
    elif status_filter == 'expired':
        query = query.filter(SubscribedUser.end_date <= now)
    
    if plan_filter != 'all':
        query = query.filter(Subscription.S_ID == plan_filter)
    
    # Get all subscription plans for the filter dropdown
    all_plans = Subscription.query.all()
    
    # Execute the query
    subscribed_users = query.order_by(SubscribedUser.end_date.desc()).all()
     # Make all datetime objects timezone-aware
    for sub, _, _ in subscribed_users:
        if sub.start_date.tzinfo is None:
            sub.start_date = sub.start_date.replace(tzinfo=UTC)
        if sub.end_date.tzinfo is None:
            sub.end_date = sub.end_date.replace(tzinfo=UTC)
    # Define a function to check if a subscription is active
    def is_active(sub_user):
        if sub_user.end_date.tzinfo is None:
            end_date = sub_user.end_date.replace(tzinfo=UTC)
        else:
            end_date = sub_user.end_date
        return end_date > now
    return render_template('admin/subscribed_users.html', 
                        subscribed_users=subscribed_users,
                        all_plans=all_plans,
                        status_filter=status_filter,
                        plan_filter=plan_filter,
                        now=now,
                        is_active=is_active,
                        hasattr=hasattr)  # Add hasattr to the template context

@admin_bp.route('/subscribed-users/new', methods=['GET', 'POST'])
def admin_new_subscribed_user():
    if request.method == 'POST':
        user_id = int(request.form.get('user_id'))
        subscription_id = int(request.form.get('subscription_id'))
        auto_renew = request.form.get('auto_renew', 'off') == 'on'  # Added auto-renewal field
        
        # Check if user exists
        user = db.session.get(User, user_id)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('admin.admin_new_subscribed_user'))
        
        # Check if subscription exists
        subscription = db.session.get(Subscription, subscription_id)
        if not subscription:
            flash('Subscription plan not found.', 'danger')
            return redirect(url_for('admin.admin_new_subscribed_user'))
        now = datetime.now(UTC)
        
        # Check if user already has this subscription
        existing_sub = SubscribedUser.query.filter(
            SubscribedUser.U_ID == user_id,
            SubscribedUser.S_ID == subscription_id,
            SubscribedUser.end_date > now
        ).first()
        
        if existing_sub:
            flash('User already has an active subscription to this plan.', 'warning')
            return redirect(url_for('admin.admin_subscribed_users'))
        
        # Calculate dates
        start_date = now
        end_date = start_date + timedelta(days=subscription.days)
        
        new_subscribed_user = SubscribedUser(
            U_ID=user_id,
            S_ID=subscription_id,
            start_date=start_date,
            end_date=end_date,
            current_usage=0,
            is_auto_renew=auto_renew  # Added auto-renewal
        )
        
        new_payment = Payment(
            base_amount=subscription.price,  # Changed from 'amount' to 'base_amount'
            user_id=user_id,
            subscription_id=subscription_id,
            razorpay_order_id=f"manual_admin_{int(time.time())}",
            razorpay_payment_id=f"manual_admin_{int(time.time())}",
            currency='INR',
            status='completed',
            payment_type='new',
            created_at= now
        )
        
        # Add subscription history record
        new_history = SubscriptionHistory(
            U_ID=user_id,
            S_ID=subscription_id,
            action='new',
            created_at=now
        )
        
        db.session.add(new_subscribed_user)
        db.session.add(new_payment)
        db.session.add(new_history)
        db.session.commit()
        
        flash('User subscription added successfully with payment record!', 'success')
        return redirect(url_for('admin.admin_subscribed_users'))
    
    # Get all active users (email confirmed)
    users = User.query.filter_by(email_confirmed=True).all()
    
    # Get all subscription plans
    subscriptions = Subscription.query.all()
    
    return render_template('admin/new_subscribed_user.html', 
                          users=users, 
                          subscriptions=subscriptions)

@admin_bp.route('/subscribed-users/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_subscribed_user(id):
    # Fetch the subscribed user and related data
    subscribed_user = SubscribedUser.query.get_or_404(id)
    user = User.query.get(subscribed_user.U_ID)

    if request.method == 'POST':
        # Extract form data
        subscription_id = int(request.form.get('subscription_id'))
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        current_usage = int(request.form.get('current_usage', 0))
        auto_renew = request.form.get('auto_renew', 'off') == 'on'  # Auto-renewal field

        # Validate the subscription plan exists
        subscription = Subscription.query.get(subscription_id)
        if not subscription:
            flash('Subscription plan not found.', 'danger')
            return redirect(url_for('admin.admin_edit_subscribed_user', id=id))

        # Check if start_date and end_date are provided
        if not start_date_str or not end_date_str:
            flash('Start date and End date are required.', 'danger')
            return redirect(url_for('admin.admin_edit_subscribed_user', id=id))

        # Parse dates
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            if end_date <= start_date:
                raise ValueError("End date must be after start date")
        except Exception as e:
            flash(f'Invalid date format: {str(e)}', 'danger')
            return redirect(url_for('admin.admin_edit_subscribed_user', id=id))

        # Validate current usage
        if current_usage < 0:
            flash('Current usage cannot be negative.', 'danger')
            return redirect(url_for('admin.admin_edit_subscribed_user', id=id))

        # Check if subscription has changed and record history
        old_subscription_id = subscribed_user.S_ID
        if old_subscription_id != subscription_id:
            action = 'upgrade' if subscription.tier > Subscription.query.get(old_subscription_id).tier else 'downgrade'

            # Create subscription history record
            history_record = SubscriptionHistory(
                U_ID=subscribed_user.U_ID,
                S_ID=subscription_id,
                action=action,
                previous_S_ID=old_subscription_id,
                created_at=datetime.now(UTC)
            )
            db.session.add(history_record)

        # Update the subscribed user's details
        subscribed_user.S_ID = subscription_id
        subscribed_user.start_date = start_date
        subscribed_user.end_date = end_date
        subscribed_user.current_usage = current_usage
        subscribed_user.is_auto_renew = auto_renew  # Update auto-renewal status

        db.session.commit()  # Commit the changes to the database

        flash('User subscription updated successfully!', 'success')
        return redirect(url_for('admin.admin_subscribed_users'))

    # Fetch all subscriptions for the dropdown
    subscriptions = Subscription.query.all()
    return render_template('admin/edit_subscribed_user.html', 
                           subscribed_user=subscribed_user,
                           user=user,
                           subscriptions=subscriptions)


@admin_bp.route('/subscribed-users/extend/<int:id>', methods=['POST'])
def admin_extend_subscription(id):
    subscribed_user = SubscribedUser.query.get_or_404(id)
    extension_days = int(request.form.get('extension_days', 0))
    
    if extension_days <= 0:
        flash('Extension days must be positive.', 'danger')
    else:
        # Extend the subscription
        current_end_date = subscribed_user.end_date
        new_end_date = current_end_date + timedelta(days=extension_days)
        subscribed_user.end_date = new_end_date
        
        # Create a history record for this extension
        history_record = SubscriptionHistory(
            U_ID=subscribed_user.U_ID,
            S_ID=subscribed_user.S_ID,
            action='extend',
            created_at=datetime.now(UTC)
        )
        
        db.session.add(history_record)
        db.session.commit()
        flash(f'Subscription extended by {extension_days} days successfully!', 'success')
    
    return redirect(url_for('admin.admin_subscribed_users'))

@admin_bp.route('/subscribed-users/delete/<int:id>', methods=['POST'])
def admin_delete_subscribed_user(id):
    subscribed_user = SubscribedUser.query.get_or_404(id)
    
    # Get user details for the flash message
    user = User.query.get(subscribed_user.U_ID)
    subscription = Subscription.query.get(subscribed_user.S_ID)
    
    # Create a history record for cancellation
    history_record = SubscriptionHistory(
        U_ID=subscribed_user.U_ID,
        S_ID=subscribed_user.S_ID,
        action='cancel',
        created_at=datetime.now(UTC)
    )
    
    db.session.add(history_record)
    db.session.delete(subscribed_user)
    db.session.commit()
    
    flash(f'Subscription for {user.name} to {subscription.plan} plan deleted successfully!', 'success')
    return redirect(url_for('admin.admin_subscribed_users'))

@admin_bp.route('/users')
def admin_users():
    email_id = session.get('email_id')
    
    if not Admin.check_permission(email_id, 'user_management'):
        flash("You don't have permission to access this page.", "danger")
        return redirect(url_for('admin.admin_dashboard'))

    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('search', '')
    
    # Start with base query
    query = User.query
    
    # Apply filters
    if status_filter == 'active':
        query = query.filter_by(email_confirmed=True)
    elif status_filter == 'unconfirmed':
        query = query.filter_by(email_confirmed=False)
    elif status_filter == 'admin':
        query = query.filter_by(is_admin=True)
    
    # Apply search if provided
    if search_query:
        query = query.filter(
            or_(
                User.name.ilike(f'%{search_query}%'),
                User.company_email.ilike(f'%{search_query}%')
            )
        )
    
    # Execute query and sort by creation date
    users = query.order_by(User.created_at.desc()).all()
    
    # Get subscription status for each user - improved to include plan data directly
    user_subscriptions = {}
    for user in users:
        active_sub = (
            db.session.query(SubscribedUser, Subscription)
            .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
            .filter(
                SubscribedUser.U_ID == user.id,
                SubscribedUser.end_date > datetime.now(UTC),
                SubscribedUser._is_active == True  # Use the actual DB column name
            )
            .first()
        )
        
        if active_sub:
            # Create a dictionary with subscription data
            subscribed_user, subscription = active_sub  # Unpack the tuple
            
            # Store both the subscription object and relevant data
            user_subscriptions[user.id] = {
                'subscription': subscription,
                'subscribed_user': subscribed_user,
                'plan_name': subscription.plan,
                'plan_type': subscription.plan_type or 'Normal'
            }
            
    # Add debug logging
    current_app.logger.debug(f"User subscriptions: {user_subscriptions}")
    
    return render_template('admin/users.html', 
                           users=users,
                           user_subscriptions=user_subscriptions,
                           status_filter=status_filter,
                           search_query=search_query)
@admin_bp.route('/users/<int:user_id>')
def admin_user_details(user_id):
    user = db.session.get(User, user_id)
    
    # Get user's subscription history
    subscriptions = (
        db.session.query(SubscribedUser, Subscription)
        .join(Subscription, SubscribedUser.S_ID == Subscription.S_ID)
        .filter(SubscribedUser.U_ID == user_id)
        .order_by(SubscribedUser.start_date.desc())
        .all()
    )
    
    # Get user's payment history
    payments = (
        db.session.query(Payment, Subscription)
        .join(Subscription, Payment.subscription_id == Subscription.S_ID)
        .filter(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
      # Make sure all datetime objects are timezone-aware
    for sub, _ in subscriptions:
        if sub.start_date.tzinfo is None:
            sub.start_date = sub.start_date.replace(tzinfo=UTC)
        if sub.end_date.tzinfo is None:
            sub.end_date = sub.end_date.replace(tzinfo=UTC)

    for payment, _ in payments:
        if payment.created_at.tzinfo is None:
            payment.created_at = payment.created_at.replace(tzinfo=UTC)
        if payment.invoice_date and payment.invoice_date.tzinfo is None:
            payment.invoice_date = payment.invoice_date.replace(tzinfo=UTC)
    # Calculate current date for checking subscription status
    now = datetime.now(UTC)
    
    return render_template('admin/user_details.html',
                          user=user,
                          subscriptions=subscriptions,
                          payments=payments,
                          now=now)

@admin_bp.route('/remove_user/<int:user_id>', methods=['POST'])
def remove_user(user_id):
    """
    Remove a user and all associated data from the system.
    This function carefully handles all foreign key relationships
    by deleting related records in the correct order.
    """
    # Fetch the user by ID
    user = db.session.get(User, user_id)
    
    # Check if the user has active subscriptions
    active_subscription = SubscribedUser.query.filter(
        SubscribedUser.U_ID == user_id,
        SubscribedUser.end_date > datetime.now(UTC)
    ).first()
    
    if active_subscription:
        flash('Cannot delete user with active subscriptions. Please remove their subscriptions first.', 'warning')
        return redirect(url_for('admin.admin_users'))
    
    # Check if user is an admin
    if user.is_admin:
        flash('Cannot delete an admin user.', 'danger')
        return redirect(url_for('admin.admin_users'))
    
    # Store user details for the success message
    user_email = user.company_email
    
    try:
        # Begin a transaction
        db.session.begin_nested()
        
        # Delete all related records in the correct order to avoid foreign key constraint violations
        
        # 1. First delete invoice addresses associated with the user's payments
        payment_ids = [p.iid for p in Payment.query.filter_by(user_id=user_id).all()]
        if payment_ids:
            InvoiceAddress.query.filter(InvoiceAddress.payment_id.in_(payment_ids)).delete(synchronize_session=False)
        
        # 2. Delete payments
        Payment.query.filter_by(user_id=user_id).delete(synchronize_session=False)
        
        # 3. Delete search history
        # SearchHistory.query.filter_by(u_id=user_id).delete(synchronize_session=False)
        
        # 4. Delete subscription history
        SubscriptionHistory.query.filter_by(U_ID=user_id).delete(synchronize_session=False)
        
        # 5. Delete subscribed users
        SubscribedUser.query.filter_by(U_ID=user_id).delete(synchronize_session=False)
        
        # 6. Finally, delete the user
        db.session.delete(user)
        
        # Commit the transaction
        db.session.commit()
        
        current_app.logger.info(f"User {user_id} ({user_email}) successfully deleted")
        flash(f'User {user_email} removed successfully.', 'success')
    except Exception as e:
        # Rollback in case of error
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id}: {str(e)}")
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin.admin_users'))

@admin_bp.route('/edit_user/<int:user_id>', methods=['POST'])
def admin_edit_user(user_id):
    user = db.session.get(User, user_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('company_email')
        is_active = 'email_confirmed' in request.form
        is_admin = 'is_admin' in request.form
        
        # Check if email is already taken by another user
        existing_email = User.query.filter(
            User.company_email == email, 
            User.id != user_id
        ).first()
        
        if existing_email:
            flash('Email already taken by another user.', 'danger')
            return redirect(url_for('admin.admin_users'))
        
        # Update user details
        user.name = name
        user.company_email = email
        user.email_confirmed = is_active
        
        # Only update admin status if current user is not modifying themselves
        if 'user_id' not in session:
            flash("You need to log in first.", "warning")
            return redirect(url_for('admin.login'))
        current_user_id = session['user_id']

        if user_id != current_user_id:
            user.is_admin = is_admin
        else:
            if not is_admin:
                flash('You cannot remove your own admin privileges.', 'warning')
        
        db.session.commit()
        flash('User updated successfully!', 'success')
    
    return redirect(url_for('admin.admin_user_details', user_id=user_id))

@admin_bp.route('/reset_user_password/<int:user_id>', methods=['POST'])
def admin_reset_user_password(user_id):
    user = db.session.get(User, user_id)
    
    # Generate a random password
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    # Update the user's password
    user.set_password(new_password)
    db.session.commit()
    
    # Here you would typically send an email to the user with their new password
    # For now, we'll just flash it (in production, you'd want to email it instead)
    flash(f'Password reset successfully! Temporary password: {new_password}', 'success')
    
    return redirect(url_for('admin.admin_user_details', user_id=user_id))

@admin_bp.route('/add_user', methods=['POST'])
def admin_add_user():
    if request.method == 'POST':
        name = request.form.get('name')
        company_email = request.form.get('company_email')
        password = request.form.get('password')
        email_confirmed = 'email_confirmed' in request.form
        
        # Print debug info to console
        print(f"Form data: name={name}, email={company_email}, password_length={len(password) if password else 0}")
        
        # Check if all required fields are provided
        if not name or not company_email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('admin.admin_users'))
        
        # Check if email already exists
        existing_user = User.query.filter_by(company_email=company_email).first()
        if existing_user:
            flash('A user with that email already exists.', 'danger')
            return redirect(url_for('admin.admin_users'))
        
        try:
            # Create new user
            new_user = User(
                name=name,
                company_email=company_email,
                email_confirmed=email_confirmed,
                created_at=datetime.now(UTC)
            )
            new_user.set_password(password)
            
            db.session.add(new_user)
            db.session.commit()
            flash(f'User {name} ({company_email}) created successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            print(f"Database error: {str(e)}")
        
        return redirect(url_for('admin.admin_users'))



@admin_bp.route('/payments')
def admin_payments():

    email_id = session.get('email_id')
    
    if not Admin.check_permission(email_id, 'payments'):
        flash("You don't have permission to access this page.", "danger")
        return redirect(url_for('admin.admin_dashboard'))
    
    # Get filter parameters
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date_range', '30')
    search_query = request.args.get('search', '')
    payment_type_filter = request.args.get('payment_type', 'all')
    
    # Base query with joins
    query = (
        db.session.query(
            Payment,
            User,
            Subscription,
            InvoiceAddress
        )
        .join(User, Payment.user_id == User.id)
        .join(Subscription, Payment.subscription_id == Subscription.S_ID)
        .outerjoin(InvoiceAddress, InvoiceAddress.payment_id == Payment.iid)
    )
    
    # Apply filters
    if status_filter != 'all':
        query = query.filter(Payment.status == status_filter)
    
    if payment_type_filter != 'all':
        query = query.filter(Payment.payment_type == payment_type_filter)
    
    # Date filter
    now = datetime.now(UTC)
    date_ranges = {
        '7': now - timedelta(days=7),
        '30': now - timedelta(days=30),
        '90': now - timedelta(days=90)
    }
    if date_filter in date_ranges:
        query = query.filter(Payment.created_at >= date_ranges[date_filter])
    
    # Search filter with expanded search capabilities
    if search_query:
        search_filter = or_(
            User.name.ilike(f'%{search_query}%'),
            User.company_email.ilike(f'%{search_query}%'),
            Payment.invoice_number.ilike(f'%{search_query}%'),
            Payment.razorpay_order_id.ilike(f'%{search_query}%'),
            Payment.customer_number.ilike(f'%{search_query}%')
        )
        query = query.filter(search_filter)
    
    # Order and pagination
    payments = (
        query.order_by(Payment.created_at.desc())
        .paginate(page=request.args.get('page', 1, type=int), per_page=50)
    )
    
    # Advanced statistics
    stats = {
        'total_payments': payments.total,
        'total_revenue': db.session.query(func.sum(Payment.total_amount))
                            .filter(Payment.status == 'completed')
                            .scalar() or 0,
        'completed_payments': db.session.query(func.count(Payment.iid))
                                .filter(Payment.status == 'completed')
                                .scalar() or 0,
        'payment_type_breakdown': dict(
            db.session.query(Payment.payment_type, func.count(Payment.iid))
            .group_by(Payment.payment_type)
            .all()
        )
    }
    
    # Revenue trend for chart
    revenue_trend = (
        db.session.query(
            func.date_trunc('day', Payment.created_at).label('day'),
            func.sum(Payment.total_amount).label('total_revenue')
        )
        .filter(Payment.status == 'completed')
        .group_by('day')
        .order_by('day')
        .limit(30)
        .all()
    )
    
    return render_template('admin/payments.html',
                           payments=payments,
                           stats=stats,
                           revenue_trend=revenue_trend,
                           filters={
                               'status': status_filter,
                               'date_range': date_filter,
                               'search': search_query,
                               'payment_type': payment_type_filter
                           })

@admin_bp.route('/payments/<string:order_id>')
def admin_payment_details(order_id):
    # Comprehensive payment details query
    payment_details = (
        db.session.query(
            Payment,
            User,
            Subscription,
            InvoiceAddress
        )
        .join(User, Payment.user_id == User.id)
        .join(Subscription, Payment.subscription_id == Subscription.S_ID)
        .outerjoin(InvoiceAddress, InvoiceAddress.payment_id == Payment.iid)
        .filter(Payment.invoice_number == order_id)
        .first_or_404()
    )
    
    # Unpack query results
    payment, user, subscription, invoice_address = payment_details
    
    # Fetch Razorpay details if applicable
    razorpay_details = None
    razorpay_details = None
    if payment.razorpay_payment_id and not payment.razorpay_payment_id.startswith('manual_'):
        try:
            
            razorpay_details = current_app.config['RAZORPAY_CLIENT'].payment.fetch(payment.razorpay_payment_id)
        except Exception as e:
            current_app.logger.warning(f"Razorpay fetch error: {str(e)}")
    razorpay_details = None
    
    # Related payments history
    related_payments = (
        Payment.query
        .filter(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc())
        .limit(5)
        .all()
    )
    
    return render_template('admin/payment_details.html', 
                           payment=payment, 
                           user=user, 
                           subscription=subscription,
                           invoice_address=invoice_address,
                           razorpay_details=razorpay_details,
                           related_payments=related_payments)

@admin_bp.route('/payments/update/<string:order_id>', methods=['POST'])
def admin_update_payment(order_id):
    payment = Payment.query.filter_by(invoice_number=order_id).first_or_404()
    
    # Validate and update payment status
    new_status = request.form.get('status')
    valid_statuses = ['created', 'completed', 'failed', 'cancelled']
    
    if new_status in valid_statuses:
        old_status = payment.status
        payment.status = new_status
        
        # Additional status change logic
        try:
            if new_status == 'completed' and old_status != 'completed':
                # Ensure invoice is generated
                if not payment.invoice_number:
                    payment.invoice_number = generate_unique_invoice_number()
                
                # Create or update subscription
                create_or_update_subscription(payment)
                
                # Generate invoice address if not exists
                create_invoice_address_for_payment(payment)
            
            db.session.commit()
            flash('Payment status updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Payment update error: {str(e)}")
            flash(f'Error updating payment: {str(e)}', 'danger')
    else:
        flash('Invalid status', 'danger')
    
    return redirect(url_for('admin.admin_payment_details', order_id=order_id))

@admin_bp.route('/payment/<order_id>/invoice')
@admin_required  
def admin_payment_invoice(order_id):
    """
    Generate and serve a PDF invoice for a specific payment order
    
    :param order_id: Razorpay order ID
    :return: PDF file response
    """
    # Find the payment by order_id
    payment = Payment.query.filter_by(razorpay_order_id=order_id).first_or_404()
    
    # Generate PDF invoice
    pdf_buffer = generate_invoice_pdf(payment)
    
    # Send the PDF as a download
    return send_file(
        pdf_buffer,
        download_name=f"invoice_{payment.invoice_number}.pdf",
        as_attachment=True,
        mimetype='application/pdf'
    )
