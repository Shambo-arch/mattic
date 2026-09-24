FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN SECRET_KEY=build-only-collectstatic python manage.py collectstatic --noinput
RUN useradd --create-home app && mkdir -p /app/media /app/private_media && chown -R app:app /app
USER app
EXPOSE 8000
CMD gunicorn mattic_project.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-3} --timeout 60 --access-logfile -
