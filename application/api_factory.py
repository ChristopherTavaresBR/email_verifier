# api_factory.py
from flask import Blueprint, request, jsonify, current_app
import re
import uuid
from datetime import datetime
from functools import wraps
from typing import Callable, Any
import logging

from application.driver_manager import EnhancedDriverManager

def validate_email(email: str) -> bool:
    """
    Validates the format of an email address.

    Args:
        email (str): The email address to validate.

    Returns:
        bool: True if the email format is valid, False otherwise.
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def error_handler(f: Callable) -> Callable:
    """
    Decorator for consistent error handling in API endpoints.

    Args:
        f (Callable): The function to wrap with error handling.

    Returns:
        Callable: The wrapped function with error handling.
    """
    @wraps(f)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500
    return wrapper

class APIFactory:
    @staticmethod
    def create_verifier_blueprint(
        service_name: str,
        driver_manager: EnhancedDriverManager
    ) -> Blueprint:
        """
        Creates a Flask Blueprint for an email verification service.

        Args:
            service_name (str): The name of the service.
            driver_manager (EnhancedDriverManager): The driver manager instance.

        Returns:
            Blueprint: A Flask Blueprint with email verification endpoints.
        """
        bp = Blueprint(service_name, __name__)
        
        @bp.route('/verify-email', methods=['POST'])
        @error_handler
        def verify_email():
            """
            Endpoint to verify an email address.

            Returns:
                JSON response with verification details or an error message.
            """
            data = request.get_json()
            if not data or 'email' not in data:
                return jsonify({
                    "error": "Email not provided",
                    "timestamp": datetime.utcnow().isoformat()
                }), 400

            email = data['email']
            if not validate_email(email):
                return jsonify({
                    "error": "Invalid email format",
                    "timestamp": datetime.utcnow().isoformat()
                }), 400

            # Ensure the driver is running
            if not driver_manager.driver:
                success = driver_manager.start_driver()
                if not success:
                    return jsonify({
                        "error": "Failed to start email verification service",
                        "timestamp": datetime.utcnow().isoformat()
                    }), 500

            driver_manager.update_activity()
            
            # Create a verification request
            queues = driver_manager.queues
            queue_item = queues.add_verification(email)
            
            return jsonify({
                "verification_id": queue_item.id,
                "status": "pending",
                "timestamp": datetime.utcnow().isoformat()
            }), 202

        @bp.route('/verification-status/<verification_id>', methods=['GET'])
        @error_handler
        def get_verification_status(verification_id: str):
            """
            Endpoint to check the status of an email verification.

            Args:
                verification_id (str): The ID of the verification request.

            Returns:
                JSON response with verification status or an error message.
            """
            queues = driver_manager.queues
            status = queues.get_verification_status(verification_id)
            
            if not status:
                return jsonify({
                    "error": "Verification not found",
                    "timestamp": datetime.utcnow().isoformat()
                }), 404

            return jsonify({
                "verification_id": verification_id,
                "status": status.status,
                "result": status.result,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

        @bp.route('/driver/status', methods=['GET'])
        @error_handler
        def get_driver_status():
            """
            Endpoint to check the status of the driver.

            Returns:
                JSON response with the driver's status and last activity time.
            """
            return jsonify({
                "status": "running" if driver_manager.driver else "stopped",
                "last_activity": driver_manager.last_activity,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

        @bp.route('/driver/start', methods=['POST'])
        @error_handler
        def start_driver():
            """
            Endpoint to start the driver.

            Returns:
                JSON response indicating success or failure.
            """
            success = driver_manager.start_driver()
            return jsonify({
                "success": success,
                "message": "Driver started successfully" if success else "Driver already running",
                "timestamp": datetime.utcnow().isoformat()
            }), 200 if success else 400

        @bp.route('/driver/stop', methods=['POST'])
        @error_handler
        def stop_driver():
            """
            Endpoint to stop the driver.

            Returns:
                JSON response indicating success or failure.
            """
            success = driver_manager.shutdown_driver()
            return jsonify({
                "success": success,
                "message": "Driver stopped successfully" if success else "Driver not running",
                "timestamp": datetime.utcnow().isoformat()
            }), 200 if success else 400

        return bp