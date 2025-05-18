FROM python:3.10-slim

# Définir les variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py
ENV FLASK_CONFIG=docker-dev

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    netcat-openbsd \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer le dossier de stockage des missions et les autres dossiers nécessaires
RUN mkdir -p /app/missions /app/instance /app/logs

# Définir les permissions
RUN chmod +x /app/entrypoint.sh

# Exposer le port
EXPOSE 5000

# Exécuter l'application
ENTRYPOINT ["/app/entrypoint.sh"]