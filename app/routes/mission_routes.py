"""
Routes pour la gestion des missions via l'interface web
"""
import os
import json
from datetime import datetime
from flask import (
    Blueprint, flash, redirect, render_template, request, url_for, 
    current_app, send_file, abort, jsonify
)
from werkzeug.utils import secure_filename
from app import db
from app.models import Mission, File
from app.services import mission_service, file_service

bp = Blueprint('missions', __name__)

@bp.route('/')
def index():
    """Page d'accueil avec la liste des missions"""
    missions = mission_service.get_all_missions()
    return render_template('index.html', missions=missions)

@bp.route('/missions')
def list_missions():
    """Liste toutes les missions avec filtres optionnels"""
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
    
    return render_template('missions/list.html', missions=missions)

@bp.route('/missions/<int:mission_id>')
def mission_detail(mission_id):
    """Affiche les détails d'une mission"""
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        abort(404)
    
    # Récupérer les fichiers par type
    files_by_type = {}
    for file_type in current_app.config['ALLOWED_EXTENSIONS'].keys():
        files_by_type[file_type] = mission_service.get_mission_files_by_type(mission_id, file_type)
    
    return render_template('missions/detail.html', mission=mission, files_by_type=files_by_type)

@bp.route('/missions/create', methods=['GET', 'POST'])
def create_mission():
    """Crée une nouvelle mission"""
    if request.method == 'POST':
        name = request.form.get('name')
        flight_date = request.form.get('flight_date')
        description = request.form.get('description')
        
        if not name:
            flash('Le nom de la mission est requis.', 'error')
            return render_template('missions/create.html')
        
        # Vérifier si une mission avec ce nom existe déjà
        existing_mission = mission_service.get_mission_by_name(name)
        if existing_mission:
            flash(f'Une mission avec le nom "{name}" existe déjà.', 'error')
            return render_template('missions/create.html')
        
        # Créer la mission
        mission = mission_service.create_mission(name, flight_date, description)
        
        flash(f'Mission "{name}" créée avec succès.', 'success')
        return redirect(url_for('missions.mission_detail', mission_id=mission.id))
    
    return render_template('missions/create.html')

@bp.route('/missions/<int:mission_id>/edit', methods=['GET', 'POST'])
def edit_mission(mission_id):
    """Édite une mission existante"""
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        abort(404)
    
    if request.method == 'POST':
        name = request.form.get('name')
        flight_date = request.form.get('flight_date')
        description = request.form.get('description')
        
        if not name:
            flash('Le nom de la mission est requis.', 'error')
            return render_template('missions/edit.html', mission=mission)
        
        # Vérifier si le nouveau nom existe déjà (si le nom est modifié)
        if name != mission.name:
            existing_mission = mission_service.get_mission_by_name(name)
            if existing_mission:
                flash(f'Une mission avec le nom "{name}" existe déjà.', 'error')
                return render_template('missions/edit.html', mission=mission)
        
        # Mettre à jour la mission
        updated_mission = mission_service.update_mission(
            mission_id=mission_id,
            name=name,
            flight_date=flight_date,
            description=description
        )
        
        flash(f'Mission "{name}" mise à jour avec succès.', 'success')
        return redirect(url_for('missions.mission_detail', mission_id=mission_id))
    
    return render_template('missions/edit.html', mission=mission)

@bp.route('/missions/<int:mission_id>/delete', methods=['POST'])
def delete_mission(mission_id):
    """Supprime une mission"""
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        abort(404)
    
    mission_name = mission.name
    success = mission_service.delete_mission(mission_id)
    
    if success:
        flash(f'Mission "{mission_name}" supprimée avec succès.', 'success')
    else:
        flash(f'Erreur lors de la suppression de la mission "{mission_name}".', 'error')
    
    return redirect(url_for('missions.list_missions'))

@bp.route('/missions/<int:mission_id>/upload', methods=['GET', 'POST'])
def upload_files(mission_id):
    """Interface pour l'upload de fichiers"""
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        abort(404)
    
    if request.method == 'POST':
        if 'files[]' not in request.files:
            flash('Aucun fichier sélectionné.', 'error')
            return redirect(request.url)
        
        files = request.files.getlist('files[]')
        
        uploaded_count = 0
        error_count = 0
        
        for file in files:
            if file.filename == '':
                continue
            
            if file and file_service.allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path, file_type = file_service.save_file(file, mission.name)
                
                # Enregistrer dans la base de données
                file_service.register_file_in_db(
                    mission_id=mission_id,
                    filename=filename,
                    file_path=file_path,
                    file_type=file_type
                )
                
                uploaded_count += 1
            else:
                error_count += 1
        
        if uploaded_count > 0:
            flash(f'{uploaded_count} fichier(s) téléversé(s) avec succès.', 'success')
        
        if error_count > 0:
            flash(f'{error_count} fichier(s) non téléversé(s) car le format n\'est pas autorisé.', 'error')
        
        return redirect(url_for('missions.mission_detail', mission_id=mission_id))
    
    return render_template('upload.html', mission=mission)

@bp.route('/missions/<int:mission_id>/download', methods=['GET'])
def download_files(mission_id):
    """Téléchargement de fichiers par catégorie"""
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        abort(404)
    
    file_type = request.args.get('type')
    
    if file_type and file_type not in current_app.config['ALLOWED_EXTENSIONS'].keys():
        abort(400, f"Type de fichier '{file_type}' non valide")
    
    # Créer le ZIP
    zip_path = file_service.create_mission_zip(mission_id, file_type)
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=os.path.basename(zip_path),
        mimetype='application/zip'
    )

@bp.route('/missions/<int:mission_id>/download-all', methods=['GET'])
def download_all_files(mission_id):
    """Téléchargement de tous les fichiers d'une mission"""
    mission = mission_service.get_mission_by_id(mission_id)
    if not mission:
        abort(404)
    
    # Créer le ZIP de toute la mission
    zip_path = file_service.create_mission_zip(mission_id)
    
    return send_file(
        zip_path,
        as_attachment=True,
        download_name=os.path.basename(zip_path),
        mimetype='application/zip'
    )

@bp.route('/file/<int:file_id>', methods=['GET'])
def view_file(file_id):
    """Visualisation d'un fichier individuel"""
    file = File.query.get_or_404(file_id)
    
    # Vérifier si le fichier existe
    if not os.path.exists(file.file_path):
        abort(404, "Le fichier n'existe pas sur le disque")
    
    # Déterminer le type MIME en fonction de l'extension
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'tif': 'image/tiff',
        'tiff': 'image/tiff',
        'pdf': 'application/pdf',
        'csv': 'text/csv',
        'txt': 'text/plain',
        'log': 'text/plain',
        'tlog': 'application/octet-stream',
        'gpx': 'application/gpx+xml',
        'kml': 'application/vnd.google-earth.kml+xml',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'zip': 'application/zip',
    }
    
    extension = file.file_extension
    mimetype = mime_types.get(extension, 'application/octet-stream')
    
    # Pour les images, les afficher dans le navigateur
    if extension in ['jpg', 'jpeg', 'png', 'tif', 'tiff']:
        return send_file(file.file_path, mimetype=mimetype)
    
    # Pour les autres types, proposer le téléchargement
    return send_file(
        file.file_path,
        as_attachment=True,
        download_name=file.filename,
        mimetype=mimetype
    )

@bp.route('/file/<int:file_id>/delete', methods=['POST'])
def delete_file(file_id):
    """Suppression d'un fichier"""
    file = File.query.get_or_404(file_id)
    mission_id = file.mission_id
    
    # Supprimer le fichier physique
    if os.path.exists(file.file_path):
        try:
            os.remove(file.file_path)
        except OSError as e:
            flash(f"Erreur lors de la suppression du fichier: {str(e)}", 'error')
            return redirect(url_for('missions.mission_detail', mission_id=mission_id))
    
    # Supprimer l'entrée de la base de données
    db.session.delete(file)
    db.session.commit()
    
    flash('Fichier supprimé avec succès.', 'success')
    return redirect(url_for('missions.mission_detail', mission_id=mission_id))
