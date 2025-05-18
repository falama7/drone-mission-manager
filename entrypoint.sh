#!/bin/sh

# Attendre que la base de données PostgreSQL soit prête (si configurée)
if [ "$DATABASE_URL" != "" ]; then
    echo "Waiting for PostgreSQL..."
    
    POSTGRES_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\(.*\):.*/\1/p')
    POSTGRES_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ "$POSTGRES_HOST" != "" ] && [ "$POSTGRES_PORT" != "" ]; then
        while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
            sleep 0.1
        done
        echo "PostgreSQL started"
    fi
fi

# Initialiser la base de données
echo "Initializing the database..."
flask db init || true
flask db migrate
flask db upgrade

# Démarrer l'application Flask
if [ "$FLASK_ENV" = "development" ] || [ "$FLASK_CONFIG" = "docker-dev" ]; then
    echo "Starting Flask development server..."
    python run.py
else
    echo "Starting Gunicorn production server..."
    gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 run:app
fi
