web: gunicorn --chdir /var/app/current kickit.wsgi:application --bind 0.0.0.0:8000
worker: celery -A kickit worker --loglevel=info