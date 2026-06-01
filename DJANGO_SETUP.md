# Django admin for RunPro Bot

This Django project uses the same PostgreSQL database as the bot.

Existing bot tables are mapped with `managed = False`, so Django will not create,
drop, or migrate these tables:

- `drivers`
- `dispatchers`
- `driver_dispatcher`
- `loads`
- `chats`

Django migrations only create Django's own tables, such as users, sessions, and
permissions. Migrations are explicitly disabled for the `botdata` app.

## Environment

Use the same database variables as the bot:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

Or:

```env
DB_HOST=...
DB_PORT=5432
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
```

Also set these for production:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=your-domain.com,.railway.app
DJANGO_SECURE_SSL_REDIRECT=1
DJANGO_SESSION_COOKIE_SECURE=1
DJANGO_CSRF_COOKIE_SECURE=1
```

Set `DJANGO_SECURE_HSTS_SECONDS` only after HTTPS is confirmed working. A safe
first production value is `3600`; later it can be increased.

## First run

Install dependencies:

```bash
pip install -r requirements.txt
```

Create only Django system tables:

```bash
python manage.py migrate
```

Create an admin user:

```bash
python manage.py createsuperuser
```

Run locally:

```bash
python manage.py collectstatic --noinput
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/admin/
```

## Deployment

The `Procfile` now has both processes:

```text
worker: python main.py
web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn runpro_admin.wsgi:application --bind 0.0.0.0:$PORT
```

Run the bot as the `worker` process and Django as the `web` process. Both use the
same `DATABASE_URL`.
