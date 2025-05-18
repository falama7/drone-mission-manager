"""
Service de gestion des fichiers pour les missions drone
"""
import os
import csv
import shutil
import zipfile
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
from app.models import File, Mission, MissionMetadata

def allowed_file(filename, file_type=None):
    """
    Vérifie si le fichier est autorisé en fonction de son extension
    
    Args:
        filename (str): Nom du fichier à vérifier
        file_type (str, optional): Type de fichier spécifique à vérifier
        
    Returns:
        bool: True si le fichier est autorisé, False sinon
    """
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if not extension:
        return False
        
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    
    if file_type:
        # Si un type spécifique est demandé
        return extension in allowed_extensions.get(file_type, set())
    else:
        # Vérifier dans tous les types
        for extensions in allowed_extensions.values():
            if extension in extensions:
                return True
        return False

def get_file_type(filename):
    """
    Détermine le type de fichier en fonction de son extension
    
    Args:
        filename (str): Nom du fichier
        
    Returns:
        str: Type du fichier (images, logs, geopos, ppk, rapport)
    """
    extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    if not extension:
        return 'autres'
        
    allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    
    for file_type, extensions in allowed_extensions.items():
        if extension in extensions:
            return file_type
            
    return 'autres'

def save_file(file, mission_name):
    """
    Sauvegarde un fichier dans la structure de dossiers appropriée
    
    Args:
        file: Objet fichier à sauvegarder
        mission_name (str): Nom de la mission
        
    Returns:
        tuple: (chemin du fichier, type de fichier)
    """
    filename = secure_filename(file.filename)
    file_type = get_file_type(filename)
    
    # Créer les dossiers de la mission s'ils n'existent pas
    mission_path = os.path.join(current_app.config['UPLOAD_FOLDER'], mission_name)
    if not os.path.exists(mission_path):
        os.makedirs(mission_path)
    
    # Créer le sous-dossier pour le type de fichier s'il n'existe pas
    type_folder = os.path.join(mission_path, file_type)
    if not os.path.exists(type_folder):
        os.makedirs(type_folder)
    
    # Chemin complet du fichier
    file_path = os.path.join(type_folder, filename)
    
    # Sauvegarder le fichier
    file.save(file_path)
    
    return file_path, file_type

def register_file_in_db(mission_id, filename, file_path, file_type):
    """
    Enregistre un fichier dans la base de données
    
    Args:
        mission_id (int): ID de la mission
        filename (str): Nom du fichier
        file_path (str): Chemin du fichier
        file_type (str): Type du fichier
        
    Returns:
        File: Objet File créé
    """
    file_size = os.path.getsize(file_path)
    
    file_record = File(
        mission_id=mission_id,
        filename=filename,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size
    )
    
    db.session.add(file_record)
    db.session.commit()
    
    # Si c'est un fichier de géoréférencement CSV, extraire les métadonnées
    if file_type == 'geopos' and filename.lower().endswith('.csv'):
        extract_metadata_from_csv(file_path, mission_id)
    
    return file_record

def extract_metadata_from_csv(csv_path, mission_id):
    """
    Extrait les métadonnées d'un fichier CSV de géoréférencement
    
    Args:
        csv_path (str): Chemin du fichier CSV
        mission_id (int): ID de la mission
    """
    try:
        # Vérifier si des métadonnées existent déjà pour cette mission
        metadata = MissionMetadata.query.filter_by(mission_id=mission_id).first()
        if not metadata:
            metadata = MissionMetadata(mission_id=mission_id)
            db.session.add(metadata)
        
        # Lecture du fichier CSV
        latitudes = []
        longitudes = []
        altitudes = []
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # On s'adapte aux différents formats possibles
                lat = None
                lon = None
                alt = None
                
                # Essayer de trouver les colonnes de latitude/longitude
                for col in reader.fieldnames:
                    col_lower = col.lower()
                    if lat is None and ('lat' in col_lower or 'latitude' in col_lower):
                        lat = row[col]
                    if lon is None and ('lon' in col_lower or 'longitude' in col_lower or 'lng' in col_lower):
                        lon = row[col]
                    if alt is None and ('alt' in col_lower or 'altitude' in col_lower or 'elevation' in col_lower):
                        alt = row[col]
                
                # Si on a trouvé les coordonnées
                if lat and lon:
                    try:
                        lat_float = float(lat)
                        lon_float = float(lon)
                        latitudes.append(lat_float)
                        longitudes.append(lon_float)
                        
                        if alt:
                            try:
                                alt_float = float(alt)
                                altitudes.append(alt_float)
                            except ValueError:
                                pass
                    except ValueError:
                        continue
        
        # Calcul des métadonnées
        if latitudes and longitudes:
            metadata.center_latitude = sum(latitudes) / len(latitudes)
            metadata.center_longitude = sum(longitudes) / len(longitudes)
            
            if altitudes:
                metadata.min_altitude = min(altitudes)
                metadata.max_altitude = max(altitudes)
            
            # Calcul approximatif de la zone couverte
            if len(latitudes) > 3:  # Besoin d'au moins 3 points pour définir une zone
                # Simplification: utilisation d'un rectangle englobant
                lat_min, lat_max = min(latitudes), max(latitudes)
                lon_min, lon_max = min(longitudes), max(longitudes)
                
                # Conversion approximative degrés -> mètres (à l'équateur)
                # 1 degré de latitude ≈ 111 000 mètres
                # 1 degré de longitude ≈ 111 000 * cos(latitude) mètres
                import math
                lat_center_rad = math.radians((lat_min + lat_max) / 2)
                lat_distance = (lat_max - lat_min) * 111000
                lon_distance = (lon_max - lon_min) * 111000 * math.cos(lat_center_rad)
                
                metadata.area_covered = lat_distance * lon_distance
        
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Erreur lors de l'extraction des métadonnées: {str(e)}")
        db.session.rollback()

def create_mission_zip(mission_id, file_type=None):
    """
    Crée un fichier ZIP pour une mission
    
    Args:
        mission_id (int): ID de la mission
        file_type (str, optional): Type de fichier à inclure (tous si None)
        
    Returns:
        str: Chemin du fichier ZIP créé
    """
    mission = Mission.query.get_or_404(mission_id)
    
    # Nom du fichier ZIP
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if file_type:
        zip_filename = f"{mission.name}_{file_type}_{timestamp}.zip"
    else:
        zip_filename = f"{mission.name}_complete_{timestamp}.zip"
    
    # Chemin temporaire pour le ZIP
    temp_dir = os.path.join(current_app.instance_path, 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    zip_path = os.path.join(temp_dir, zip_filename)
    
    # Création du ZIP
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if file_type:
            # Ajouter seulement les fichiers du type spécifié
            files = File.query.filter_by(mission_id=mission_id, file_type=file_type).all()
            for file in files:
                arcname = os.path.join(file.file_type, file.filename)
                zipf.write(file.file_path, arcname=arcname)
        else:
            # Ajouter tous les fichiers
            files = File.query.filter_by(mission_id=mission_id).all()
            for file in files:
                arcname = os.path.join(file.file_type, file.filename)
                zipf.write(file.file_path, arcname=arcname)
    
    return zip_path

def delete_mission_files(mission_id):
    """
    Supprime tous les fichiers associés à une mission
    
    Args:
        mission_id (int): ID de la mission
    """
    mission = Mission.query.get_or_404(mission_id)
    
    # Supprimer le dossier de la mission
    if os.path.exists(mission.mission_path):
        shutil.rmtree(mission.mission_path)
    
    # Supprimer les enregistrements de fichiers
    File.query.filter_by(mission_id=mission_id).delete()
    db.session.commit()
