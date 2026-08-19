from flask import Blueprint, render_template, redirect, url_for, session, request, flash
from routes import login_required
from models.user import UserModel
from models.prediction import PredictionModel

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    username = session.get('username', 'User')
    stats = PredictionModel.get_user_stats(user_id)
    recent_predictions = PredictionModel.get_recent(user_id, limit=5)

    return render_template(
        'dashboard.html',
        username=username,
        stats=stats,
        recent_predictions=recent_predictions
    )

@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    user = UserModel.get_by_id(user_id)
    stats = PredictionModel.get_user_stats(user_id)

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        success, msg = UserModel.update_email(user_id, email)
        flash(msg, 'success' if success else 'danger')
        if success:
            user = UserModel.get_by_id(user_id)

    return render_template(
        'profile.html',
        user=user,
        stats=stats
    )
