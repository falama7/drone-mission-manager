"""
Service de gestion des missions de vol drone
"""
import os
import shutil
from datetime import datetime
from flask import current_app
from app import db
from app.models import Mission, MissionMetadata, File
from app.services.file_service import delete_mission_files

def create_mission(name, flight_date=None, description=None):
    """
    Crée une nouvelle mission
    
    Args:
        name (str): Nom de la mission
        flight_date (str, optional): Date du vol au format YYYY-MM-DD
        description (str, optional): Description de la mission
        
    Returns:
        Mission: Objet Mission créé
    """
    # Formatage de la date si fournie
    formatted_date = None
    if flight_date:
        try:
            formatted_date = datetime.strptime(flight_date, '%Y-%m-%d').date()
        except ValueError:
            current_app.logger.warning(f"Format de date invalide: {flight_date}")
    
    # Création de la mission
    mission = Mission(
        name=name,
        flight_date=formatted_date,
        description=description
    )
    
    db.session.add(mission)
    db.session.commit()
    
    # Création du dossier de la mission
    mission_path = os.path.join(current_app.config['UPLOAD_FOLDER'], name)
    if not os.path.exists(mission_path):
        os.makedirs(mission_path)
        
        # Création des sous-dossiers par type
        for file_type in current_app.config['ALLOWED_EXTENSIONS'].keys():
            os.makedirs(os.path.join(mission_path, file_type))
    
    # Création des métadonnées vides
    metadata = MissionMetadata(mission_id=mission.id)
    db.session.add(metadata)
    db.session.commit()
    
    return mission

def get_all_missions():
    """
    Récupère toutes les missions
    
    Returns:
        list: Liste des objets Mission
    """
    return Mission.query.order_by(Mission.date_created.desc()).all()

def get_mission_by_id(mission_id):
    """
    Récupère une mission par son ID
    
    Args:
        mission_id (int): ID de la mission
        
    Returns:
        Mission: Objet Mission ou None
    """
    return Mission.query.get(mission_id)

def get_mission_by_name(mission_name):
    """
    Récupère une mission par son nom
    
    Args:
        mission_name (str): Nom de la mission
        
    Returns:
        Mission: Objet Mission ou None
    """
    return Mission.query.filter_by(name=mission_name).first()

def update_mission(mission_id, name=None, flight_date=None, description=None):
    """
    Met à jour les informations d'une mission
    
    Args:
        mission_id (int): ID de la mission
        name (str, optional): Nouveau nom de la mission
        flight_date (str, optional): Nouvelle date du vol au format YYYY-MM-DD
        description (str, optional): Nouvelle description de la mission
        
    Returns:
        Mission: Objet Mission mis à jour
    """
    mission = Mission.query.get_or_404(mission_id)
    old_name = mission.name
    
    # Mise à jour des champs si fournis
    if name and name != old_name:
        # Renommer le dossier de la mission
        old_path = mission.mission_path
        mission.name = name
        new_path = mission.mission_path
        
        if os.path.exists(old_path):
            try:
                os.rename(old_path, new_path)
                
                # Mettre à jour les chemins des fichiers dans la base de données
                files = File.query.filter_by(mission_id=mission_id).all()
                for file in files:
                    file.file_path = file.file_path.replace(old_path, new_path)
            except OSError as e:
                current_app.logger.error(f"Erreur lors du renommage du dossier de mission: {str(e)}")
                # Restaurer l'ancien nom
                mission.name = old_name
    
    if flight_date:
        try:
            mission.flight_date = datetime.strptime(flight_date, '%Y-%m-%d').date()
        except ValueError:
            current_app.logger.warning(f"Format de date invalide: {flight_date}")
    
    if description is not None:
        mission.description = description
    
    db.session.commit()
    return mission

def delete_mission(mission_id):
    """
    Supprime une mission et tous ses fichiers
    
    Args:
        mission_id (int): ID de la mission
        
    Returns:
        bool: True si la suppression est réussie
    """
    mission = Mission.query.get_or_404(mission_id)
    
    try:
        # Supprimer les fichiers physiques
        mission_path = mission.mission_path
        if os.path.exists(mission_path):
            shutil.rmtree(mission_path)
        
        # Supprimer les métadonnées
        MissionMetadata.query.filter_by(mission_id=mission_id).delete()
        
        # Supprimer les fichiers de la base de données
        File.query.filter_by(mission_id=mission_id).delete()
        
        # Supprimer la mission
        db.session.delete(mission)
        db.session.commit()
        
        return True
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la suppression de la mission: {str(e)}")
        db.session.rollback()
        return False

def get_mission_files_by_type(mission_id, file_type=None):
    """
    Récupère les fichiers d'une mission, éventuellement filtrés par type
    
    Args:
        mission_id (int): ID de la mission
        file_type (str, optional): Type de fichier à filtrer
        
    Returns:
        list: Liste des objets File
    """
    if file_type:
        return File.query.filter_by(mission_id=mission_id, file_type=file_type).all()
    else:
        return File.query.filter_by(mission_id=mission_id).all()

def search_missions(query=None, start_date=None, end_date=None, file_type=None):
    """
    Recherche des missions selon différents critères
    
    Args:
        query (str, optional): Texte de recherche pour le nom ou la description
        start_date (str, optional): Date de début au format YYYY-MM-DD
        end_date (str, optional): Date de fin au format YYYY-MM-DD
        file_type (str, optional): Type de fichier que doit contenir la mission
        
    Returns:
        list: Liste des objets Mission correspondant aux critères
    """
    missions_query = Mission.query
    
    # Filtrage par nom ou description
    if query:
        missions_query = missions_query.filter(
            (Mission.name.ilike(f'%{query}%')) | 
            (Mission.description.ilike(f'%{query}%'))
        )
    
    # Filtrage par date de vol
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d').date()
            missions_query = missions_query.filter(Mission.flight_date >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d').date()
            missions_query = missions_query.filter(Mission.flight_date <= end)
        except ValueError:
            pass
    
    # Appliquer les filtres et récupérer les résultats
    missions = missions_query.order_by(Mission.date_created.desc()).all()
    
    # Filtrage par type de fichier (nécessite de vérifier chaque mission)
    if file_type:
        filtered_missions = []
        for mission in missions:
            # Vérifier si la mission contient au moins un fichier du type spécifié
            has_file_type = File.query.filter_by(mission_id=mission.id, file_type=file_type).first() is not None
            if has_file_type:
                filtered_missions.append(mission)
        return filtered_missions
    
    return missions