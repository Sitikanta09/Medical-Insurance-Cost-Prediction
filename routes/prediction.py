from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, g
from routes import login_required
from models.user import UserModel
from models.prediction import PredictionModel
from services.ml_service import MLService
import sqlite3

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/predict-form', methods=['GET'])
@prediction_bp.route('/predict', methods=['GET'])
@login_required
def predict_form():
    """Renders the professional prediction input form."""
    return render_template('predict.html')

@prediction_bp.route('/predict', methods=['POST'])
@login_required
def predict():
    """
    Handles form submission, validates 6 inputs, performs ML inference,
    records prediction in persistent database, and redirects to result page.
    """
    user_id = session.get('user_id')
    raw_data = request.form.to_dict()

    # Step 1: Verify user exists in database to prevent foreign key errors
    user = UserModel.get_by_id(user_id)
    if not user:
        session.clear()
        flash('User account not found or session has expired. Please sign in or create an account.', 'warning')
        return redirect(url_for('auth.login'))

    # Step 2: Validate inputs
    cleaned_data, error_msg = MLService.validate_inputs(raw_data)
    if error_msg:
        flash(error_msg, 'danger')
        return render_template('predict.html', form_data=raw_data)

    try:
        # Step 3: Run inference through MLService (preserves 6-feature LinearRegression contract)
        predicted_cost, formatted_text = MLService.predict(cleaned_data)

        # Step 4: Persist prediction to database
        saved_prediction = PredictionModel.create(
            user_id=user_id,
            age=cleaned_data['age'],
            sex=cleaned_data['sex'],
            bmi=cleaned_data['bmi'],
            children=cleaned_data['children'],
            smoker=cleaned_data['smoker'],
            region=cleaned_data['region'],
            predicted_cost=predicted_cost
        )

        flash('Prediction calculated successfully!', 'success')
        return redirect(url_for('prediction.result', prediction_id=saved_prediction['id']))

    except (ValueError, sqlite3.IntegrityError) as e:
        flash(f"Database error: {str(e)}", 'danger')
        return render_template('predict.html', form_data=raw_data)
    except Exception as e:
        flash(f"An unexpected error occurred during prediction: {str(e)}", 'danger')
        return render_template('predict.html', form_data=raw_data)

@prediction_bp.route('/result/<int:prediction_id>', methods=['GET'])
@login_required
def result(prediction_id):
    """
    Renders professional prediction result dashboard with non-medical ML estimate disclaimer.
    Strictly prevents cross-user access.
    """
    user_id = session.get('user_id')
    prediction_record = PredictionModel.get_by_id(prediction_id, user_id)
    if not prediction_record:
        flash('Prediction record not found or access denied.', 'warning')
        return redirect(url_for('prediction.history'))

    # Format output text for backwards-compatibility and display
    prediction_text = f"Estimated Insurance Cost: Rs.{prediction_record['predicted_cost']:,.2f}"

    return render_template(
        'result.html',
        prediction=prediction_record,
        prediction_text=prediction_text
    )

@prediction_bp.route('/history', methods=['GET'])
@login_required
def history():
    """Paginated, filterable, and searchable prediction history."""
    user_id = session.get('user_id')
    search = request.args.get('search', '').strip()
    region_filter = request.args.get('region', '').strip()
    smoker_filter = request.args.get('smoker', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()
    page = request.args.get('page', 1, type=int)

    history_data = PredictionModel.get_user_history(
        user_id=user_id,
        search=search,
        region_filter=region_filter,
        smoker_filter=smoker_filter,
        sort_by=sort_by,
        page=page,
        per_page=8
    )

    return render_template(
        'history.html',
        history=history_data,
        search=search,
        region_filter=region_filter,
        smoker_filter=smoker_filter,
        sort_by=sort_by
    )

@prediction_bp.route('/history/delete/<int:prediction_id>', methods=['POST'])
@login_required
def delete_history(prediction_id):
    """Delete a prediction record owned by the current user."""
    user_id = session.get('user_id')
    success = PredictionModel.delete(prediction_id, user_id)
    if success:
        flash('Prediction record deleted successfully.', 'info')
    else:
        flash('Failed to delete record or record not found.', 'danger')
    return redirect(url_for('prediction.history'))
