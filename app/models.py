"""
Modèles de données pour l'application de gestion des missions drone
"""
import os
from datetime import datetime
from app import db

class Mission(db.Model):
    """Modèle pour une mission de vol drone"""
    __tablename__ = 'missions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    flight_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    
    # Relations
    files = db.relationship('File', backref='mission', lazy='dynamic', cascade='all, delete-orphan')
    mission_metadata = db.relationship('MissionMetadata', backref='mission', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Mission {self.name}>'
    
    @property
    def mission_path(self):
        """Retourne le chemin du dossier de la mission"""
        from flask import current_app
        return os.path.join(current_app.config['UPLOAD_FOLDER'], self.name)
    
    @property
    def file_count(self):
        """Retourne le nombre total de fichiers dans la mission"""
        return self.files.count()
    
    @property
    def file_types(self):
        """Retourne les types de fichiers disponibles dans cette mission"""
        return set([file.file_type for file in self.files])
    
    @property
    def has_images(self):
        """Vérifie si la mission contient des images"""
        return self.files.filter_by(file_type='images').count() > 0
    
    @property
    def image_count(self):
        """Retourne le nombre d'images dans la mission"""
        return self.files.filter_by(file_type='images').count()
    
    def to_dict(self):
        """Convertit l'objet Mission en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'name': self.name,
            'flight_date': self.flight_date.isoformat() if self.flight_date else None,
            'date_created': self.date_created.isoformat(),
            'description': self.description,
            'file_count': self.file_count,
            'image_count': self.image_count,
            'file_types': list(self.file_types),
            'metadata': self.mission_metadata.to_dict() if self.mission_metadata else None
        }


class File(db.Model):
    """Modèle pour un fichier appartenant à une mission"""
    __tablename__ = 'files'
    
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('missions.id'), nullable=False)
    filename = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(64), nullable=False)  # images, logs, geopos, ppk, rapport
    file_size = db.Column(db.Integer, nullable=False)  # taille en octets
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<File {self.filename}>'
    
    @property
    def file_extension(self):
        """Retourne l'extension du fichier"""
        return os.path.splitext(self.filename)[1].lower()[1:]
    
    @property
    def full_path(self):
        """Retourne le chemin complet du fichier"""
        return self.file_path
    
    def to_dict(self):
        """Convertit l'objet File en dictionnaire pour l'API"""
        return {
            'id': self.id,
            'mission_id': self.mission_id,
            'filename': self.filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'file_extension': self.file_extension,
            'uploaded_at': self.uploaded_at.isoformat()
        }


class MissionMetadata(db.Model):
    """Modèle pour les métadonnées d'une mission"""
    __tablename__ = 'mission_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    mission_id = db.Column(db.Integer, db.ForeignKey('missions.id'), nullable=False)
    
    # Métadonnées extraites des fichiers CSV de géoréférencement
    area_covered = db.Column(db.Float, nullable=True)  # en m²
    center_latitude = db.Column(db.Float, nullable=True)
    center_longitude = db.Column(db.Float, nullable=True)
    min_altitude = db.Column(db.Float, nullable=True)
    max_altitude = db.Column(db.Float, nullable=True)
    
    # Autres métadonnées utiles
    drone_model = db.Column(db.String(64), default="Trinity F90+")
    camera_model = db.Column(db.String(64), nullable=True)
    flight_duration = db.Column(db.Integer, nullable=True)  # en secondes
    
    def __repr__(self):
        return f'<MissionMetadata for Mission {self.mission_id}>'
    
    def to_dict(self):
        """Convertit l'objet MissionMetadata en dictionnaire pour l'API"""
        return {
            'area_covered': self.area_covered,
            'center_coordinates': {
                'latitude': self.center_latitude,
                'longitude': self.center_longitude
            } if self.center_latitude and self.center_longitude else None,
            'altitude_range': {
                'min': self.min_altitude,
                'max': self.max_altitude
            } if self.min_altitude and self.max_altitude else None,
            'drone_model': self.drone_model,
            'camera_model': self.camera_model,
            'flight_duration': self.flight_duration
        }
