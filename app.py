from portalflask.AI_firebase import techzone_app
import os

# Configure the app for production
techzone_app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'techzone_secret')
techzone_app.config['DEBUG'] = False

# Set upload folder path for production
techzone_app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'portalflask', 'static', 'uploads')

# Create the Flask app instance for gunicorn
app = techzone_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    techzone_app.run(host="0.0.0.0", port=port)
