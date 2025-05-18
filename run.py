#!/usr/bin/env python3
"""
Point d'entrée principal de l'application Flask pour la gestion des missions drones
"""
from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
