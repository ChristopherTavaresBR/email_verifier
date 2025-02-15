# Email Verification Service
This project is a Flask-based web service designed to verify the availability of email addresses on Google's Gmail platform. It uses Selenium to automate the process of checking if an email address is already registered on Gmail. The service is modular, scalable, and ready for production deployment.

## Structure

email_verifier/
│
├── application/
│   ├── __init__.py
│   ├── base_verifier.py
│   ├── driver_manager.py
│   ├── queue_manager.py
│   └── api_factory.py
│
├── libs/
|   google_gmail/
│   ├── __init__.py
│   ├── google_verifier.py
│   └── conf.py
│
├── main.py
└── requirements.txt

## Purpose
The primary purpose of this service is to provide an API endpoint that allows users to check if a specific email address (username) is available for registration on Gmail. It automates the process of filling out Google's account creation form and checks for error messages indicating whether the email is already in use.

## How to Use

### Install Dependencies:
Ensure you have Python installed, then install the required dependencies by running:

```
pip install -r requirements.txt
```

## Run the Application:

### Start the Flask application by running:

```
python main.py
```

### Send Verification Requests:

Use the /verify-email endpoint to check if an email is available. For example:

```
curl -X POST http://localhost:5000/google/verify-email -H "Content-Type: application/json" -d '{"email": "teste"}'
```

The service will return a JSON response indicating whether the email is available:

```
json
{
    "email": "teste",
    "available": false,
    "verified_at": "2023-10-10T12:34:56.789Z"
}
```

## Start/Stop the Selenium Driver:

To start the Selenium driver manually:

```
curl -X POST http://localhost:5000/google/start-driver
```

To stop the Selenium driver:

```
curl -X POST http://localhost:5000/google/shutdown-driver
```

## Running in Production
To deploy this service in a production environment, follow these steps:

### Use a Production WSGI Server:

Replace Flask's built-in development server with a production-ready WSGI server like Gunicorn:

```
pip install gunicorn
```

run
```
gunicorn -w 4 -b 0.0.0.0:5000 main:create_app()
```

### Set Up a Reverse Proxy:

Use a reverse proxy like Nginx or Apache to handle incoming HTTP requests and forward them to the WSGI server. This improves performance, security, and scalability.

### Run as a Service:

Use a process manager like systemd (Linux) or Supervisor to ensure the service runs continuously and restarts automatically if it crashes.

Example systemd service file (/etc/systemd/system/email_verifier.service):

```
[Unit]
Description=Email Verification Service
After=network.target

[Service]
User=your_user
WorkingDirectory=/path/to/your/project
ExecStart=/path/to/your/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 main:create_app()
Restart=always

[Install]
WantedBy=multi-user.target
Enable and start the service:
```

```
sudo systemctl enable email_verifier
sudo systemctl start email_verifier
```

### Environment Variables:

Use environment variables to manage sensitive configurations (e.g., API keys, database credentials). You can load them using a .env file or directly in the systemd service file.

### Logging:
Ensure logs are properly configured and rotated. Use tools like logrotate to manage log files.

## Documentation

### API Endpoints

Verify Email Availability:

Endpoint: POST /google/verify-email

Request Body:

```
{
    "email": "teste"
}
```

Response:

```
{
    "email": "teste",
    "available": false,
    "verified_at": "2023-10-10T12:34:56.789Z"
}
```

### Start Selenium Driver:

Endpoint: POST /google/start-driver

Response:

```
{
    "message": "Driver started successfully"
}
```

Stop Selenium Driver:

Endpoint: POST /google/shutdown-driver

Response:

```
{
    "message": "Driver shut down successfully"
}
```

## Key Features

### Modular Design:

The application is divided into modules (driver_manager, queue_manager, api_factory, etc.), making it easy to maintain and extend.

### Headless Mode:

The Selenium driver runs in headless mode, making it suitable for server environments.

### Queue-Based Processing:

Email verification requests are processed asynchronously using a queue system.

### Automatic Driver Management:

The Selenium driver is automatically started and stopped based on activity.

### Production-Ready:

The service is designed to be deployed in production environments using tools like Gunicorn, Nginx, and systemd.

Future Improvements

### Support for Other Email Providers:

Extend the service to support verification for other email providers like Yahoo or Outlook.

### Rate Limiting:

Implement rate limiting to prevent abuse of the API.

### Captcha Handling:

Integrate captcha-solving services to handle cases where Google presents a captcha.

### Database Integration:

Store verification results in a database for analytics and reporting.