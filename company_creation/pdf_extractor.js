frappe.pages['pdf-extractor'].on_page_load = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Extracteur PDF Universel',
        single_column: true
    });
    
    make_universal_extractor(page);
}

function make_universal_extractor(page) {
    let $wrapper = $(page.body);
    
    $wrapper.html(`
        <div class="pdf-extractor-container" style="padding: 20px;">
            <h3>Extraction universelle de données PDF</h3>
            <p>Uploadez n'importe quel PDF pour extraire toutes les informations importantes</p>
            
            <div class="upload-section" style="margin-bottom: 30px;">
                <input type="file" id="pdf-file" accept=".pdf" style="margin-bottom: 10px;">
                <button class="btn btn-primary" id="extract-btn">Analyser le document</button>
                <button class="btn btn-secondary" id="load-previous-btn" style="margin-left: 10px;">Charger une analyse précédente</button>
                <div id="loading" style="display: none; margin-top: 10px;">
                    <i class="fa fa-spinner fa-spin"></i> Analyse en cours...
                </div>
            </div>
            
            <div id="document-info" style="display: none; margin-bottom: 20px;">
                <div class="alert alert-info">
                    <strong>Document détecté:</strong> <span id="doc-type"></span><br>
                    <strong>Confiance:</strong> <span id="confidence"></span>%
                </div>
            </div>
            
            <div id="results-section" style="display: none;">
                <h4>Informations extraites (modifiables)</h4>
                <div id="data-table"></div>
                <div style="margin-top: 15px;">
                    <button class="btn btn-success" id="save-btn">Sauvegarder les données</button>
                    <button class="btn btn-info" id="export-btn" style="margin-left: 10px;">Exporter en JSON</button>
                </div>
            </div>
            
            <!-- Modal pour charger les analyses précédentes -->
            <div class="modal fade" id="previous-modal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h4 class="modal-title">Analyses précédentes</h4>
                            <button type="button" class="close" data-dismiss="modal">&times;</button>
                        </div>
                        <div class="modal-body">
                            <div id="previous-list"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);
    
    // Event listeners
    $('#extract-btn').click(function() {
        let fileInput = document.getElementById('pdf-file');
        if (!fileInput.files.length) {
            frappe.msgprint('Veuillez sélectionner un fichier PDF');
            return;
        }
        
        extractAnyPDF(fileInput.files[0]);
    });
    
    $('#save-btn').click(function() {
        saveTableData();
    });
    
    $('#export-btn').click(function() {
        exportData();
    });
    
    $('#load-previous-btn').click(function() {
        loadPreviousAnalyses();
    });
}

let currentExtraction = null;

function extractAnyPDF(file) {
    $('#loading').show();
    $('#results-section').hide();
    $('#document-info').hide();
    
    let formData = new FormData();
    formData.append('file', file);
    
    $.ajax({
        url: '/api/method/company_creation.pdf_extractor.api.upload_and_extract_any_pdf',
        type: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            $('#loading').hide();
            
            if (response.message && response.message.success) {
                currentExtraction = response.message;
                displayUniversalResults(response.message);
            } else {
                frappe.msgprint('Erreur: ' + (response.message.error || 'Extraction échouée'));
            }
        },
        error: function() {
            $('#loading').hide();
            frappe.msgprint('Erreur de communication avec le serveur');
        }
    });
}

function displayUniversalResults(data) {
    // Afficher les infos du document
    $('#doc-type').text(data.document_type || 'Document');
    $('#confidence').text(Math.round((data.confidence || 0) * 100));
    $('#document-info').show();
    
    // Créer le tableau modifiable
    let html = '<div class="table-responsive">';
    html += '<table class="table table-bordered" id="extraction-table">';
    html += '<thead><tr><th>Catégorie</th><th>Champ</th><th>Valeur</th><th>Actions</th></tr></thead>';
    html += '<tbody>';
    
    data.table_data.forEach(function(row, index) {
        html += '<tr data-index="' + index + '">';
        html += '<td><span class="category-label">' + (row.category || '') + '</span></td>';
        html += '<td><input type="text" class="form-control field-name" value="' + (row.field || '') + '"></td>';
        html += '<td>' + renderFieldInput(row) + '</td>';
        html += '<td><button class="btn btn-sm btn-danger remove-row">Supprimer</button></td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    html += '<button class="btn btn-sm btn-secondary" id="add-row-btn">Ajouter une ligne</button>';
    html += '</div>';
    
    $('#data-table').html(html);
    $('#results-section').show();
    
    // Event listeners pour le tableau
    $('.remove-row').click(function() {
        $(this).closest('tr').remove();
    });
    
    $('#add-row-btn').click(function() {
        addNewRow();
    });
}

function renderFieldInput(row) {
    let value = row.value || '';
    let type = row.type || 'text';
    
    switch(type) {
        case 'textarea':
            return '<textarea class="form-control field-value" rows="3">' + value + '</textarea>';
        case 'date':
            return '<input type="date" class="form-control field-value" value="' + value + '">';
        case 'number':
            return '<input type="number" class="form-control field-value" value="' + value + '">';
        case 'email':
            return '<input type="email" class="form-control field-value" value="' + value + '">';
        default:
            return '<input type="text" class="form-control field-value" value="' + value + '">';
    }
}

function addNewRow() {
    let newRow = `
        <tr>
            <td><span class="category-label">Personnalisé</span></td>
            <td><input type="text" class="form-control field-name" placeholder="Nom du champ"></td>
            <td><input type="text" class="form-control field-value" placeholder="Valeur"></td>
            <td><button class="btn btn-sm btn-danger remove-row">Supprimer</button></td>
        </tr>
    `;
    $('#extraction-table tbody').append(newRow);
    
    // Re-bind event
    $('.remove-row').off('click').click(function() {
        $(this).closest('tr').remove();
    });
}

function saveTableData() {
    let tableData = [];
    
    $('#extraction-table tbody tr').each(function() {
        let row = $(this);
        let category = row.find('.category-label').text();
        let field = row.find('.field-name').val();
        let value = row.find('.field-value').val();
        
        if (field && value) {
            tableData.push({
                category: category,
                field: field,
                value: value,
                type: 'text'
            });
        }
    });
    
    let documentInfo = {
        document_type: currentExtraction.document_type,
        confidence: currentExtraction.confidence,
        raw_text: currentExtraction.raw_text
    };
    
    frappe.call({
        method: 'company_creation.pdf_extractor.api.save_extracted_table_data',
        args: {
            table_data: JSON.stringify(tableData),
            document_info: JSON.stringify(documentInfo)
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                frappe.msgprint({
                    message: r.message.message,
                    indicator: 'green'
                });
            } else {
                frappe.msgprint('Erreur: ' + (r.message.error || 'Sauvegarde échouée'));
            }
        }
    });
}

function exportData() {
    let tableData = [];
    
    $('#extraction-table tbody tr').each(function() {
        let row = $(this);
        tableData.push({
            category: row.find('.category-label').text(),
            field: row.find('.field-name').val(),
            value: row.find('.field-value').val()
        });
    });
    
    let exportData = {
        document_type: currentExtraction.document_type,
        confidence: currentExtraction.confidence,
        extracted_data: tableData,
        export_date: new Date().toISOString()
    };
    
    // Télécharger le JSON
    let dataStr = JSON.stringify(exportData, null, 2);
    let dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    let exportFileDefaultName = 'extraction_' + new Date().toISOString().split('T')[0] + '.json';
    
    let linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
}

function loadPreviousAnalyses() {
    frappe.call({
        method: 'company_creation.pdf_extractor.api.get_saved_extractions',
        callback: function(r) {
            if (r.message && r.message.success) {
                displayPreviousAnalyses(r.message.extractions);
                $('#previous-modal').modal('show');
            }
        }
    });
}

function displayPreviousAnalyses(extractions) {
    let html = '<table class="table table-striped">';
    html += '<thead><tr><th>Document</th><th>Type</th><th>Confiance</th><th>Date</th><th>Action</th></tr></thead>';
    html += '<tbody>';
    
    extractions.forEach(function(ext) {
        html += '<tr>';
        html += '<td>' + ext.name + '</td>';
        html += '<td>' + ext.document_type + '</td>';
        html += '<td>' + Math.round(ext.confidence_score * 100) + '%</td>';
        html += '<td>' + ext.analysis_date + '</td>';
        html += '<td><button class="btn btn-sm btn-primary load-extraction" data-name="' + ext.name + '">Charger</button></td>';
        html += '</tr>';
    });
    
    html += '</tbody></table>';
    $('#previous-list').html(html);
    
    $('.load-extraction').click(function() {
        let analysisName = $(this).data('name');
        loadExtractionData(analysisName);
        $('#previous-modal').modal('hide');
    });
}

function loadExtractionData(analysisName) {
    frappe.call({
        method: 'company_creation.pdf_extractor.api.load_extraction_data',
        args: {
            analysis_name: analysisName
        },
        callback: function(r) {
            if (r.message && r.message.success) {
                currentExtraction = r.message;
                displayUniversalResults(r.message);
            }
        }
    });
}
