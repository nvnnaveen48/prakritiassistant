# Prakriti Assistant

A Django-based AI assistant application.

## Production Deployment Guide

### Prerequisites
- Python 3.8+
- PostgreSQL
- Redis
- Nginx
- Systemd

### Installation Steps

1. Clone the repository:
```bash
git clone <repository-url>
cd ai_project
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your actual values
```

5. Set up PostgreSQL:
```bash
sudo -u postgres psql
CREATE DATABASE prakriti_db;
CREATE USER prakriti_user WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE prakriti_db TO prakriti_user;
```

6. Set up Redis:
```bash
sudo apt-get install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

7. Configure Nginx:
```bash
sudo nano /etc/nginx/sites-available/prakriti
```

Add the following configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /home/myntra/ai_project;
    }

    location /media/ {
        root /home/myntra/ai_project;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/prakriti /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

8. Set up Gunicorn:
```bash
sudo cp gunicorn.service /etc/systemd/system/
sudo cp gunicorn.socket /etc/systemd/system/
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
```

9. Run deployment script:
```bash
chmod +x deploy.sh
./deploy.sh
```

10. Set up SSL with Let's Encrypt:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Maintenance

- To restart the application:
```bash
sudo systemctl restart gunicorn
```

- To check logs:
```bash
sudo journalctl -u gunicorn
tail -f logs/django.log
```

### Backup

1. Database backup:
```bash
pg_dump -U prakriti_user prakriti_db > backup.sql
```

2. Media files backup:
```bash
tar -czf media_backup.tar.gz media/
```

### Security Notes

- Keep your `.env` file secure and never commit it to version control
- Regularly update dependencies
- Monitor logs for suspicious activity
- Keep SSL certificates up to date
- Regularly backup your database and media files

### Troubleshooting

1. Check Gunicorn status:
```bash
sudo systemctl status gunicorn
```

2. Check Nginx status:
```bash
sudo systemctl status nginx
```

3. Check logs:
```bash
sudo journalctl -u gunicorn
sudo journalctl -u nginx
tail -f logs/django.log
```
