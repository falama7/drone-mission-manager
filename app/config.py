"""
Configuration de l'application Flask pour différents environnements
"""
import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Configuration de base partagée par tous les environnements"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
    # Configuration du dossier d'upload
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(os.path.dirname(basedir), 'missions')
    
    # Taille maximale de fichier (500MB)
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024
    
    # Types de fichiers autorisés
    ALLOWED_EXTENSIONS = {
        'images': {'jpg', 'jpeg', 'png', 'tif', 'tiff'},
        'logs': {'tlog', 'log', 'txt'},
        'geopos': {'csv', 'txt', 'gpx', 'kml'},
        'ppk': {'obs', 'nav', 'sp3', 'rinex'},
        'rapport': {'pdf', 'docx', 'xlsx', 'zip'}
    }
    
    # Configuration pour SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    @staticmethod
    def init_app(app):
        """Initialisation de la configuration de l'application"""
        # Création des dossiers nécessaires
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])

class DevelopmentConfig(Config):
    """Configuration pour le développement"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(basedir), 'instance', 'drone_missions_dev.sqlite')

class TestingConfig(Config):
    """Configuration pour les tests"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(basedir), 'instance', 'drone_missions_test.sqlite')
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    """Configuration pour la production"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Configuration de logging pour la production
        import logging
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler('logs/drone_missions.log', 
                                     maxBytes=10485760, 
                                     backupCount=10)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Drone Mission Manager startup')

class DockerDevConfig(DevelopmentConfig):
    """Configuration pour Docker en développement"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join('/app', 'instance', 'drone_missions_dev.sqlite')

class DockerProdConfig(ProductionConfig):
    """Configuration pour Docker en production"""
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)
        
        # Configuration spécifique pour Docker
        app.logger.info('Running in Docker Production mode')

# Dictionnaire de configuration disponible
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'docker-dev': DockerDevConfig,
    'docker-prod': DockerProdConfig,
    'default': DevelopmentConfig
}
