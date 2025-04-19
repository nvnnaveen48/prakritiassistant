#!/bin/bash

# Exit on error
set -e

echo "Starting deployment process..."

# Create necessary directories
mkdir -p logs
mkdir -p media
mkdir -p staticfiles

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if not exists
echo "Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
"

# Set proper permissions
echo "Setting permissions..."
chmod -R 755 staticfiles
chmod -R 755 media
chmod -R 755 logs

# Restart Gunicorn
echo "Restarting Gunicorn..."
sudo systemctl restart gunicorn

echo "Deployment completed successfully!" 