from flask import Flask
from application.driver_manager import EnhancedDriverManager
from libs.google_gmail.google_verifier import GoogleEmailVerifier
from application.api_factory import APIFactory
from libs.google_gmail import google_config, google_email_text, google_queues

HOST = '0.0.0.0'
PORT = 5000


def create_app():
    """
    This function creates and configures a Flask application for email verification.

    Returns:
    app: A Flask application instance with the necessary blueprints registered.

    The function initializes a Flask application, creates a driver manager for Google,
    starts monitoring, creates a blueprint for Google, and registers the blueprint with Flask.
    """
    app = Flask(__name__)

    # Create driver manager for Google
    google_driver_manager = EnhancedDriverManager(
        verifier_class=GoogleEmailVerifier,
        config=google_config,
        email_text=google_email_text,
        queues=google_queues
    )

    # Start monitoring
    google_driver_manager.start_monitoring()

    # Create blueprint for Google
    google_blueprint = APIFactory.create_verifier_blueprint(
        'google', 
        google_driver_manager,
    )

    # Register blueprint with Flask
    app.register_blueprint(google_blueprint, url_prefix='/google')

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host=HOST, port=PORT)
