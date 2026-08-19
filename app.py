import os
from flask import Flask, render_template
from config import Config
from database import close_db, init_db
from services.ml_service import MLService

def create_app(config_class=Config):
    """Application factory for Medical Insurance Cost Prediction platform."""
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(config_class)

    # Initialize SQLite database schema
    init_db(app)

    # Preload Machine Learning model (LinearRegression from model.pkl)
    try:
        MLService.load_model(app.config.get('MODEL_PATH'))
        app.logger.info("ML Model (model.pkl) successfully loaded into memory.")
    except Exception as e:
        app.logger.error(f"Error loading model.pkl: {e}")

    # Register request teardown
    app.teardown_appcontext(close_db)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.prediction import prediction_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(prediction_bp)

    # Custom User-friendly Error Handlers
    @app.errorhandler(400)
    def bad_request_error(error):
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(401)
    def unauthorized_error(error):
        return render_template('errors/401.html', error=error), 401

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template('errors/500.html', error=error), 500

    return app

# Application entry point
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    app.run(host=host, port=port, debug=debug)