worker: python main.py
web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn runpro_admin.wsgi:application --bind 0.0.0.0:$PORT
