"""
Module d'initialisation de l'application Flask
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    """
    Factory pattern pour créer l'application Flask
    """
    app = Flask(__name__, instance_relative_config=True)
    
    # Configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')
    
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Assurez-vous que le dossier d'instance existe
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Assurez-vous que le dossier de missions existe
    missions_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(missions_folder):
        os.makedirs(missions_folder)
    
    # Initialisation des extensions avec l'application
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Enregistrement des blueprints
    from app.routes import mission_routes, api_routes
    app.register_blueprint(mission_routes.bp)
    app.register_blueprint(api_routes.bp, url_prefix='/api')
    
    # Route de base pour le tableau de bord
    @app.route('/')
    def index():
        return mission_routes.index()
    
    # Ajouter des variables globales aux templates
    @app.context_processor
    def inject_now():
        from datetime import datetime
        return {'now': datetime.utcnow()}
    
    return app
