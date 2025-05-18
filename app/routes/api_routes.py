"""
Routes API REST pour la gestion des missions drone
"""
import os
from flask import (
    Blueprint, request, jsonify, current_app, send_file, abort
)
from werkzeug.utils import secure_filename
from app import db
from app.models import Mission, File
from app.services import mission_service, file_service

bp = Blueprint('api', __name__)

@bp.route('/missions', methods=['GET'])
def get_missions():
    """
    Récupère la liste des missions
    
    Query params:
        query (str, optional): Texte de recherche pour le nom ou la description
        start_date (str, optional): Date de début au format YYYY-MM-DD
        end_date (str, optional): Date de fin au format YYYY-MM-DD
        file_type (str, optional): Type de fichier que doit contenir la mission
    
    Returns:
        JSON: Liste des missions
    """
    query = request.args.get('query')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    file_type = request.args.get('file_type')
    
    missions = mission_service.search_missions(
        query=query, 
        start_date=start_date, 
        end_date=end_date, 
        file_type=file_type
    )
    
    return jsonify({
        'success': True,
        'count': len(missions),
        'missions': [mission.to_dict() for mission in missions]
    })

@bp.route('/missions/<int:mission_id>', methods=['GET'])
def get_mission(mission_id):
    """
    Récupère les détails d'une mission
    
    Args:
        mission_id (int): ID de la mission
    
    Returns:
        JSON: Détails de la mission
    """
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    # Récupérer les fichiers et les organiser par type
    files_by_type = {}
    for file_type in current_app.config['ALLOWED_EXTENSIONS'].keys():
        files = mission_service.get_mission_files_by_type(mission_id, file_type)
        files_by_type[file_type] = [file.to_dict() for file in files]
    
    mission_data = mission.to_dict()
    mission_data['files_by_type'] = files_by_type
    
    return jsonify({
        'success': True,
        'mission': mission_data
    })

@bp.route('/missions', methods=['POST'])
def create_mission():
    """
    Crée une nouvelle mission
    
    JSON Body:
        name (str): Nom de la mission
        flight_date (str, optional): Date du vol au format YYYY-MM-DD
        description (str, optional): Description de la mission
    
    Returns:
        JSON: Détails de la mission créée
    """
    data = request.json
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'Données JSON requises'
        }), 400
    
    name = data.get('name')
    if not name:
        return jsonify({
            'success': False,
            'message': 'Le nom de la mission est requis'
        }), 400
    
    # Vérifier si une mission avec ce nom existe déjà
    existing_mission = mission_service.get_mission_by_name(name)
    if existing_mission:
        return jsonify({
            'success': False,
            'message': f'Une mission avec le nom "{name}" existe déjà'
        }), 409
    
    flight_date = data.get('flight_date')
    description = data.get('description')
    
    # Créer la mission
    mission = mission_service.create_mission(name, flight_date, description)
    
    return jsonify({
        'success': True,
        'message': f'Mission "{name}" créée avec succès',
        'mission': mission.to_dict()
    }), 201

@bp.route('/missions/<int:mission_id>', methods=['PUT'])
def update_mission(mission_id):
    """
    Met à jour une mission existante
    
    Args:
        mission_id (int): ID de la mission
    
    JSON Body:
        name (str, optional): Nouveau nom de la mission
        flight_date (str, optional): Nouvelle date du vol au format YYYY-MM-DD
        description (str, optional): Nouvelle description de la mission
    
    Returns:
        JSON: Détails de la mission mise à jour
    """
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    data = request.json
    if not data:
        return jsonify({
            'success': False,
            'message': 'Données JSON requises'
        }), 400
    
    name = data.get('name')
    flight_date = data.get('flight_date')
    description = data.get('description')
    
    # Vérifier si le nouveau nom existe déjà (si un nouveau nom est fourni)
    if name and name != mission.name:
        existing_mission = mission_service.get_mission_by_name(name)
        if existing_mission:
            return jsonify({
                'success': False,
                'message': f'Une mission avec le nom "{name}" existe déjà'
            }), 409
    
    # Mettre à jour la mission
    updated_mission = mission_service.update_mission(
        mission_id=mission_id,
        name=name,
        flight_date=flight_date,
        description=description
    )
    
    return jsonify({
        'success': True,
        'message': f'Mission mise à jour avec succès',
        'mission': updated_mission.to_dict()
    })

@bp.route('/missions/<int:mission_id>', methods=['DELETE'])
def delete_mission(mission_id):
    """
    Supprime une mission
    
    Args:
        mission_id (int): ID de la mission
    
    Returns:
        JSON: Résultat de la suppression
    """
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    success = mission_service.delete_mission(mission_id)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Mission supprimée avec succès'
        })
    else:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de la suppression de la mission'
        }), 500

@bp.route('/upload', methods=['POST'])
def upload_files():
    """
    Téléverse des fichiers pour une mission
    
    Form data:
        mission_id (str): ID de la mission
        files (list): Liste des fichiers à téléverser
    
    Returns:
        JSON: Résultat du téléversement
    """
    if 'mission_id' not in request.form:
        return jsonify({
            'success': False,
            'message': 'ID de mission requis'
        }), 400
    
    mission_id = request.form.get('mission_id')
    mission = mission_service.get_mission_by_id(mission_id)
    
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    if 'files' not in request.files:
        return jsonify({
            'success': False,
            'message': 'Aucun fichier téléversé'
        }), 400
    
    files = request.files.getlist('files')
    
    uploaded_files = []
    errors = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if file and file_service.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path, file_type = file_service.save_file(file, mission.name)
            
            # Enregistrer dans la base de données
            file_record = file_service.register_file_in_db(
                mission_id=mission_id,
                filename=filename,
                file_path=file_path,
                file_type=file_type
            )
            
            uploaded_files.append({
                'id': file_record.id,
                'filename': filename,
                'file_type': file_type
            })
        else:
            errors.append({
                'filename': file.filename,
                'error': 'Format de fichier non autorisé'
            })
    
    return jsonify({
        'success': len(errors) == 0,
        'message': f'{len(uploaded_files)} fichier(s) téléversé(s) avec succès, {len(errors)} erreur(s)',
        'uploaded_files': uploaded_files,
        'errors': errors
    })

@bp.route('/missions/<int:mission_id>/files', methods=['GET'])
def get_mission_files(mission_id):
    """
    Récupère les fichiers d'une mission
    
    Args:
        mission_id (int): ID de la mission
    
    Query params:
        type (str, optional): Type de fichier à filtrer
    
    Returns:
        JSON: Liste des fichiers
    """
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    file_type = request.args.get('type')
    
    files = mission_service.get_mission_files_by_type(mission_id, file_type)
    
    return jsonify({
        'success': True,
        'count': len(files),
        'files': [file.to_dict() for file in files]
    })

@bp.route('/missions/<int:mission_id>/download', methods=['GET'])
def download_files(mission_id):
    """
    Télécharge les fichiers d'une mission
    
    Args:
        mission_id (int): ID de la mission
    
    Query params:
        type (str, optional): Type de fichier à télécharger
    
    Returns:
        File: Fichier ZIP
    """
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    file_type = request.args.get('type')
    
    if file_type and file_type not in current_app.config['ALLOWED_EXTENSIONS'].keys():
        return jsonify({
            'success': False,
            'message': f'Type de fichier "{file_type}" non valide'
        }), 400
    
    # Créer le ZIP
    try:
        zip_path = file_service.create_mission_zip(mission_id, file_type)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=os.path.basename(zip_path),
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de la création du ZIP: {str(e)}'
        }), 500

@bp.route('/missions/<int:mission_id>/download-all', methods=['GET'])
def download_all_files(mission_id):
    """
    Télécharge tous les fichiers d'une mission
    
    Args:
        mission_id (int): ID de la mission
    
    Returns:
        File: Fichier ZIP
    """
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        return jsonify({
            'success': False,
            'message': f'Mission avec ID {mission_id} non trouvée'
        }), 404
    
    # Créer le ZIP
    try:
        zip_path = file_service.create_mission_zip(mission_id)
        
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=os.path.basename(zip_path),
            mimetype='application/zip'
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Erreur lors de la création du ZIP: {str(e)}'
        }), 500

@bp.route('/files/<int:file_id>', methods=['DELETE'])
def delete_file(file_id):
    """
    Supprime un fichier
    
    Args:
        file_id (int): ID du fichier
    
    Returns:
        JSON: Résultat de la suppression
    """
    file = File.query.get(file_id)
    if not file:
        return jsonify({
            'success': False,
            'message': f'Fichier avec ID {file_id} non trouvé'
        }), 404
    
    # Supprimer le fichier physique
    if os.path.exists(file.file_path):
        try:
            os.remove(file.file_path)
        except OSError as e:
            return jsonify({
                'success': False,
                'message': f'Erreur lors de la suppression du fichier: {str(e)}'
            }), 500
    
    # Supprimer l'entrée de la base de données
    db.session.delete(file)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Fichier supprimé avec succès'
    })