release: python manage.py migrate --noinput && python manage.py ensure_superuser
web: gunicorn safety_mvp.wsgi:application --bind 0.0.0.0:$PORT
