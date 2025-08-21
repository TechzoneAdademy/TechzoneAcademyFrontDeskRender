# Email Configuration for TechZone Academy Student Management System

import os

# IMPORTANT: Before using the email functionality, you need to:
# 1. Enable 2-factor authentication on your Gmail account
# 2. Generate an App Password for this application
# 3. Update the EMAIL_CONFIG below with your credentials

# Gmail Configuration - Use environment variables in production
EMAIL_CONFIG = {
    'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.environ.get('SMTP_PORT', '587')),
    'email': os.environ.get('EMAIL_ADDRESS', 'tzacademy.hyd@gmail.com'),
    'password': os.environ.get('EMAIL_PASSWORD', 'ahghvzehagywhyaz')
}

# Example configuration (replace with your actual details):
# EMAIL_CONFIG = {
#     'smtp_server': 'smtp.gmail.com',
#     'smtp_port': 587,
#     'email': 'john.doe@gmail.com',
#     'password': 'abcd efgh ijkl mnop'  # Your 16-character app password
# }

# Instructions for setting up Gmail App Password:
# 1. Go to your Google Account settings
# 2. Navigate to Security -> 2-Step Verification
# 3. Enable 2-Step Verification if not already enabled
# 4. Go to Security -> App passwords
# 5. Select "Mail" and your device
# 6. Copy the generated 16-character password
# 7. Replace 'your_app_password' above with this generated password

# Alternative Email Providers (uncomment and modify if not using Gmail):

# Outlook/Hotmail Configuration
# EMAIL_CONFIG = {
#     'smtp_server': 'smtp-mail.outlook.com',
#     'smtp_port': 587,
#     'email': 'your_email@outlook.com',
#     'password': 'your_password'
# }

# Yahoo Configuration
# EMAIL_CONFIG = {
#     'smtp_server': 'smtp.mail.yahoo.com',
#     'smtp_port': 587,
#     'email': 'your_email@yahoo.com',
#     'password': 'your_app_password'
# }

# Custom SMTP Configuration
# EMAIL_CONFIG = {
#     'smtp_server': 'your_smtp_server.com',
#     'smtp_port': 587,
#     'email': 'your_email@yourdomain.com',
#     'password': 'your_password'
# }
