import frappe
import os
import tempfile
import json
import traceback
from frappe import _
import openai
# Import avec gestion d'erreurs
try:
    from .extractor import extract_any_pdf
except ImportError:
    try:
        from company_creation.pdf_extractor.extractor import extract_any_pdf
    except ImportError:
        def extract_any_pdf(pdf_path, openai_key):
            return {'success': False, 'error': 'Module extractor non trouvé'}

@frappe.whitelist()
def upload_and_extract_any_pdf():
    """API pour upload et extraction universelle PDF"""
    try:
        frappe.logger().info("=== DEBUT EXTRACTION PDF ===")
        
        # Récupérer le fichier uploadé
        files = frappe.request.files
        frappe.logger().info(f"Files reçus: {list(files.keys()) if files else 'Aucun'}")
        
        if 'file' not in files:
            return {'success': False, 'error': 'Aucun fichier uploadé'}
        
        file = files['file']
        frappe.logger().info(f"Fichier: {file.filename}")
        
        if not file.filename.lower().endswith('.pdf'):
            return {'success': False, 'error': 'Seuls les PDF sont acceptés'}
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
            frappe.logger().info(f"Fichier sauvé temporairement: {tmp_path}")
        
        try:
            # Récupérer la clé API
            openai_key = frappe.conf.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
            frappe.logger().info(f"Clé OpenAI configurée: {'Oui' if openai_key else 'Non'}")
            
            # TEST SIMPLE D'ABORD
            if not openai_key:
                # Version de test sans OpenAI
                result = {
                    'success': True,
                    'document_type': 'Document de test',
                    'confidence': 0.85,
                    'raw_text': 'Texte de test extrait du PDF',
                    'table_data': [
                        {
                            'category': 'Test',
                            'field': 'Nom du fichier',
                            'value': file.filename,
                            'type': 'text'
                        },
                        {
                            'category': 'Test',
                            'field': 'Taille du fichier',
                            'value': f"{os.path.getsize(tmp_path)} bytes",
                            'type': 'text'
                        }
                    ]
                }
                frappe.logger().info("Version de test sans OpenAI utilisée")
            else:
                # Extraction réelle
                result = extract_any_pdf(tmp_path, openai_key)
                frappe.logger().info(f"Résultat extraction: {result.get('success', False)}")
            
            return result
            
        except Exception as e:
            frappe.logger().error(f"Erreur lors de l'extraction: {str(e)}")
            frappe.logger().error(f"Traceback: {traceback.format_exc()}")
            return {'success': False, 'error': f'Erreur extraction: {str(e)}'}
            
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                frappe.logger().info("Fichier temporaire supprimé")
        
    except Exception as e:
        frappe.logger().error(f"Erreur globale upload PDF: {str(e)}")
        frappe.logger().error(f"Traceback: {traceback.format_exc()}")
        return {'success': False, 'error': f'Erreur serveur: {str(e)}'}

@frappe.whitelist()
def test_api():
    """API de test simple"""
    try:
        frappe.logger().info("Test API appelé")
        return {
            'success': True, 
            'message': 'API fonctionne correctement',
            'timestamp': frappe.utils.now()
        }
    except Exception as e:
        frappe.logger().error(f"Erreur test API: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def check_dependencies():
    """Vérifier les dépendances installées"""
    try:
        deps = {
            'pdfplumber': False,
            'openai': False,
            'tempfile': True,
        }
        
        try:
            import pdfplumber
            deps['pdfplumber'] = True
        except ImportError:
            pass
            
        try:
            import openai
            deps['openai'] = True
        except ImportError:
            pass
        
        openai_key = frappe.conf.get('openai_api_key') or os.getenv('OPENAI_API_KEY')
        
        return {
            'success': True,
            'dependencies': deps,
            'openai_configured': bool(openai_key),
            'frappe_version': frappe.__version__
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def save_extracted_data(data, document_type="Document", filename=""):
    """Sauvegarder les données extraites dans vos DocTypes existants"""
    try:
        # Parser JSON si string
        if isinstance(data, str):
            import json
            data = json.loads(data)
        
        # Créer Document Analysis
        doc = frappe.get_doc({
            "doctype": "Document Analysis",
            "document_name": filename or "Document PDF",
            "document_type": document_type,
            "analysis_date": frappe.utils.now(),
            "status": "Completed",
            "confidence_score": 0.9
        })
        # Ajouter les lignes du child table
        for item in data:
            # Vérifier que les données existent
            field_name = item.get('field', '') or ''
            field_value = item.get('value', '') or ''

            doc.append("extracted_fields", {
                "field_name": field_name,
                "field_value": field_value,
                "field_type": item.get('type', 'text'),
                "category": item.get('category', ''),
                "confidence": 0.9

             })
 
         # Vérifier qu'il y a des lignes avant de sauvegarder
        if not doc.extracted_fields:
            return {'success': False, 'error': 'Aucune ligne ajoutée au tableau'}
        doc.insert()
        frappe.db.commit()
        
        return {
            'success': True, 
            'doc_name': doc.name,
            'items_count': len(doc.extracted_fields),
            'message': f'Document sauvegardé avec {len(doc.extracted_fields)} champs'
        }
        
    except Exception as e:
        frappe.log_error(f"Erreur sauvegarde child table: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def get_document_analyses():
    """Liste des analyses"""
    try:
        records = frappe.get_all(
            "Document Analysis",
            fields=["name", "document_name", "document_type", "creation", "status"],
            order_by="creation desc",
            limit=50
        )
        
        return {'success': True, 'records': records}
        
    except Exception as e:
        frappe.log_error(f"Erreur get_document_analyses: {str(e)}")
        return {'success': False, 'error': str(e)}
@frappe.whitelist()
def get_extraction_details(extraction_name):
    """Récupérer les détails d'une extraction"""
    try:
        # Récupérer l'enregistrement principal
        doc = frappe.get_doc("Document Analysis", doc_name)
        # Convertir en dict et inclure les child items
        analysis_dict = doc.as_dict()
        # Récupérer tous les items extraits
        
        return {
            'success': True,
            'analysis': analysis_dict,
            'items': analysis_dict.get('extracted_fields', [])
        }
        
    except Exception as e:
        frappe.log_error(f"Erreur get_analysis_details: {str(e)}")
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def delete_extraction_item(item_name):
    """Supprimer un item extrait"""
    try:
        frappe.delete_doc("Extracted Data Item", item_name)
        frappe.db.commit()
        return {'success': True, 'message': 'Champ supprimé'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

@frappe.whitelist()
def update_extraction_item(item_name, field_value):
    """Modifier la valeur d'un item"""
    try:
        doc = frappe.get_doc("Extracted Data Item", item_name)
        doc.field_value = field_value
        doc.save()
        frappe.db.commit()
        return {'success': True, 'message': 'Champ modifié'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
