from functools import wraps
from flask import session, redirect, url_for, flash, request

def login_required(f):
    """Decorator to enforce user authentication on protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function
