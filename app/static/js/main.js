/**
 * Script principal pour le gestionnaire de missions drone
 */

document.addEventListener('DOMContentLoaded', function() {
    // Fermeture automatique des alertes après 5 secondes
    const alerts = document.querySelectorAll('.alert:not(.alert-danger)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Activation des tooltips Bootstrap
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Confirmation pour les actions de suppression qui n'utilisent pas de modal
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            if (!confirm('Êtes-vous sûr de vouloir supprimer cet élément ?')) {
                event.preventDefault();
            }
        });
    });
    
    // Ajout de la date actuelle dans les champs de date vides
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(input => {
        if (input.value === '' && input.id === 'flight_date' && !input.hasAttribute('data-no-default')) {
            const today = new Date();
            const year = today.getFullYear();
            const month = String(today.getMonth() + 1).padStart(2, '0');
            const day = String(today.getDate()).padStart(2, '0');
            input.value = `${year}-${month}-${day}`;
        }
    });
    
    // Gestion des tabs avec persistance dans l'URL
    const tabLinks = document.querySelectorAll('a[data-bs-toggle="tab"]');
    
    // Activer l'onglet stocké ou celui dans l'URL
    const hash = window.location.hash;
    if (hash) {
        const tab = document.querySelector(`a[href="${hash}"]`);
        if (tab) {
            const bsTab = new bootstrap.Tab(tab);
            bsTab.show();
        }
    }
    
    // Mettre à jour l'URL lorsqu'un onglet est cliqué
    tabLinks.forEach(tabLink => {
        tabLink.addEventListener('shown.bs.tab', function (event) {
            window.location.hash = event.target.getAttribute('href');
        });
    });
    
    // Formatage des champs numériques
    const formatNumberElements = document.querySelectorAll('.format-number');
    formatNumberElements.forEach(element => {
        const value = parseFloat(element.textContent);
        if (!isNaN(value)) {
            element.textContent = value.toLocaleString();
        }
    });
    
    // Prévisualisation d'image
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    imageInputs.forEach(input => {
        input.addEventListener('change', function(event) {
            const previewContainer = document.querySelector(`#${input.id}-preview`);
            if (previewContainer) {
                previewContainer.innerHTML = '';
                
                const files = event.target.files;
                for (let i = 0; i < files.length; i++) {
                    const file = files[i];
                    if (file.type.match('image.*')) {
                        const reader = new FileReader();
                        
                        reader.onload = function(e) {
                            const img = document.createElement('img');
                            img.src = e.target.result;
                            img.className = 'img-thumbnail';
                            img.style.maxHeight = '150px';
                            img.style.marginRight = '10px';
                            img.style.marginBottom = '10px';
                            previewContainer.appendChild(img);
                        };
                        
                        reader.readAsDataURL(file);
                    }
                }
            }
        });
    });
    
    // Actualisation de l'heure dans le footer
    function updateFooterTime() {
        const footerTime = document.getElementById('footer-time');
        if (footerTime) {
            const now = new Date();
            footerTime.textContent = now.toLocaleTimeString();
        }
    }
    
    // Mise à jour initiale et toutes les minutes
    updateFooterTime();
    setInterval(updateFooterTime, 60000);
});
