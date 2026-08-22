from functools import wraps
from flask import session, redirect, url_for, flash, request, g
from models.user import UserModel

def login_required(f):
    """
    Decorator to enforce user authentication on protected routes.
    Validates that session contains a user_id AND that the user actually exists in the database.
    If the database was reset or the user was deleted, clears stale session and redirects to login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.path))

        # Verify user exists in the database
        user = UserModel.get_by_id(user_id)
        if not user:
            session.clear()
            flash('Your session is invalid or the user account was not found. Please sign in or register.', 'warning')
            return redirect(url_for('auth.login', next=request.path))

        g.current_user = user
        return f(*args, **kwargs)
    return decorated_function
