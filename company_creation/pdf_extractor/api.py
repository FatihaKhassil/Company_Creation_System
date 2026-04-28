import frappe
import os
import tempfile
import json
import traceback
from frappe import _
# OpenAI importé dans extractor
try:
    from .extractor import extract_any_pdf
except ImportError:
    try:
        from company_creation.pdf_extractor.extractor import extract_any_pdf
    except ImportError:
        def extract_any_pdf(pdf_path, openai_key, targets=None):
            return {'success': False, 'error': 'Module extractor non trouvé'}

# ----------------------------
# API principale : upload + extraction (multi)
# ----------------------------
@frappe.whitelist()
def upload_and_extract_any_pdf():
    """API pour upload et extraction universelle PDF (multi-fichiers supportés)"""
    try:
        frappe.logger().info("=== DEBUT EXTRACTION PDF (multi) ===")
        files = frappe.request.files or {}
        form = frappe.form_dict or {}

        # cibles éventuelles (optionnelles)
        target_doctype = form.get("target_doctype")
        target_fields_raw = form.get("target_fields_json")
        target_fields = []
        if target_fields_raw:
            try:
                target_fields = json.loads(target_fields_raw)
            except Exception:
                target_fields = []

        # Collecte fichiers
        upload_items = []
        if 'files' in files:
            try:
                upload_items = files.getlist('files')
            except Exception:
                upload_items = [files['files']]
        elif 'file' in files:
            upload_items = [files['file']]

        if not upload_items:
            return {'success': False, 'error': 'Aucun fichier uploadé'}
        if len(upload_items) > 10:
            return {'success': False, 'error': 'Maximum 10 fichiers autorisés'}

        settings = _get_extraction_settings()
        openai_key = settings["api_key"]
        frappe.logger().info(f"[Multi] OpenAI configurée: {'Oui' if openai_key else 'Non'}")

        # Résultats cumulés
        detected_types, confidences, raw_text_samples = [], [], []
        temp_paths = []
        per_file = []
        file_errors = []   # collecte des erreurs par fichier

        # 1) Sauvegarde temporaire
        for file_storage in upload_items:
            if not file_storage.filename.lower().endswith('.pdf'):
                return {'success': False, 'error': f"'{file_storage.filename}' n'est pas un PDF"}
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            file_storage.save(tmp.name)
            temp_paths.append((tmp.name, file_storage.filename))

        try:
            # 2) Extraction fichier par fichier
            for tmp_path, orig_name in temp_paths:
                # targets = None si pas de doctype/champs → mode large
                targets = target_fields if target_fields else None
                result = extract_any_pdf(tmp_path, openai_key, targets=target_fields if target_fields else None, settings=settings)

                # Fallback large si ciblé vide/échec
                if targets and (not result.get('success') or not result.get('table_data')):
                    frappe.logger().info(f"[Fallback] Relance extraction large pour {orig_name}")
                    result = extract_any_pdf(tmp_path, openai_key, targets=None)

                if not result.get('success'):
                    err = result.get('error') or 'Extraction échouée'
                    file_errors.append({"filename": orig_name, "error": err})
                    frappe.logger().warning(f"Extraction échouée pour {orig_name}: {err}")
                    continue

                file_entry = {
                    "filename": orig_name,
                    "document_type": result.get("document_type") or "Document",
                    "confidence": result.get("confidence") or 0.9,
                    "table": []
                }
                for row in (result.get('table_data') or []):
                    file_entry["table"].append({
                        "category": row.get("category") or "Données clés",
                        "field": row.get("field") or "",
                        "value": row.get("value") or "",
                        "type": row.get("type") or "text",
                        "page": row.get("page"),
                        "field_confidence": row.get("confidence"),
                        "label": row.get("label"),
                    })

                per_file.append(file_entry)

                if result.get('document_type'):
                    detected_types.append(result['document_type'])
                if result.get('confidence') is not None:
                    confidences.append(result['confidence'])
                if result.get('raw_text'):
                    raw_text_samples.append(result['raw_text'])

            if not per_file:
                return {
                    'success': False,
                    'error': "Impossible d'extraire des données des fichiers fournis",
                    'file_errors': file_errors
                }
                        # --- MODE CIBLE (Doctype choisi) ---
            if target_fields:
                exact_table = _build_exact_target_view(per_file, target_fields)
                final_type = detected_types[0] if not detected_types else max(set(detected_types), key=detected_types.count)
                avg_conf = round(sum(confidences)/len(confidences), 3) if confidences else 0.9

                return {
                    "success": True,
                    "mode": "targeted",
                    "target_doctype": target_doctype,
                    "document_type": final_type or "Document",
                    "confidence": avg_conf,
                    "table_data": exact_table
                }


            # 3) Vues fusionnées et résumé
            merged = build_merged_view(per_file)
            final_type = detected_types[0] if not detected_types else max(set(detected_types), key=detected_types.count)
            avg_conf = round(sum(confidences)/len(confidences), 3) if confidences else 0.9

            payload = {
                'success': True,
                'document_type': final_type or 'Document',
                'confidence': avg_conf,
                'raw_text': ' \n---\n'.join(raw_text_samples[:2])[:1000],
                'files': per_file,
                'merged': merged
            }
            if file_errors:
                payload['file_errors'] = file_errors

            # (facultatif) renvoyer le doctype choisi
            if target_doctype:
                payload['target_doctype'] = target_doctype

            return payload

        finally:
            for tmp_path, _ in temp_paths:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    except Exception as e:
        frappe.logger().error(f"Erreur globale upload PDF (multi): {str(e)}\n{traceback.format_exc()}")
        return {'success': False, 'error': f'Erreur serveur: {str(e)}'}


# ----------------------------
# Utilitaires / autres endpoints
# ----------------------------
@frappe.whitelist()
def test_api():
    try:
        frappe.logger().info("Test API appelé")
        return {'success': True, 'message': 'API fonctionne correctement', 'timestamp': frappe.utils.now()}
    except Exception as e:
        frappe.logger().error(f"Erreur test API: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def check_dependencies():
    try:
        deps = {'pdfplumber': False, 'openai': False, 'tempfile': True}
        try:
            import pdfplumber  # noqa
            deps['pdfplumber'] = True
        except ImportError:
            pass
        try:
            import openai  # noqa
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
    """Sauvegarder les données extraites dans votre DocType 'Document Analysis'."""
    try:
        if not frappe.has_permission("Document Analysis", ptype="create"):
            return {"success": False, "error": _("Not permitted to create Document Analysis")}

        if isinstance(data, str):
            data = json.loads(data)

        doc = frappe.get_doc({
            "doctype": "Document Analysis",
            "document_name": filename or "Document PDF",
            "document_type": document_type,
            "analysis_date": frappe.utils.now(),
            "status": "Completed",
            "confidence_score": 0.9
        })

        for item in (data or []):
            doc.append("extracted_fields", {
                "field_name": item.get('field', '') or '',
                "field_value": item.get('value', '') or '',
                "field_type": item.get('type', 'text'),
                "category": item.get('category', ''),
                "confidence": 0.9
            })

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
def save_extracted_table_data(table_data, document_info=None):
    try:
        if isinstance(table_data, str):
            table_data = json.loads(table_data)
        if not isinstance(table_data, list):
            return {"success": False, "error": "table_data invalide"}

        if document_info is None:
            document_info = {}
        elif isinstance(document_info, str):
            document_info = json.loads(document_info)
        elif not isinstance(document_info, dict):
            document_info = {}

        document_type = document_info.get("document_type", "Document")
        filename = document_info.get("filename") or document_info.get("document_name") or ""

        result = save_extracted_data(
            data=table_data,
            document_type=document_type,
            filename=filename,
        )
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Sauvegarde échouée")}

        return {
            "success": True,
            "message": result.get("message", "Données sauvegardées"),
            "doc_name": result.get("doc_name"),
            "items_count": result.get("items_count", 0),
        }
    except json.JSONDecodeError:
        return {"success": False, "error": "JSON invalide pour table_data ou document_info"}
    except Exception as e:
        frappe.log_error(f"save_extracted_table_data: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_document_analyses():
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
def get_saved_extractions():
    try:
        result = get_document_analyses()
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Erreur récupération analyses"),
                "extractions": [],
            }
        return {"success": True, "extractions": result.get("records", [])}
    except Exception as e:
        frappe.log_error(f"get_saved_extractions: {str(e)}")
        return {"success": False, "error": str(e), "extractions": []}


@frappe.whitelist()
def get_extraction_details(extraction_name):
    """Récupérer les détails d'une extraction."""
    try:
        doc = frappe.get_doc("Document Analysis", extraction_name)  # <-- corrige doc_name -> extraction_name
        analysis_dict = doc.as_dict()
        return {
            'success': True,
            'analysis': analysis_dict,
            'items': analysis_dict.get('extracted_fields', [])
        }
    except Exception as e:
        frappe.log_error(f"Erreur get_extraction_details: {str(e)}")
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def load_extraction_data(analysis_name):
    try:
        if not analysis_name:
            return {"success": False, "error": "analysis_name manquant"}

        result = get_extraction_details(extraction_name=analysis_name)
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Extraction introuvable")}

        analysis = result.get("analysis") or {}
        items = result.get("items") or []

        table_data = []
        for item in items:
            table_data.append(
                {
                    "category": item.get("category") or "Données clés",
                    "field": item.get("field_name") or "",
                    "value": item.get("field_value") or "",
                    "type": item.get("field_type") or "text",
                }
            )

        return {
            "success": True,
            "document_type": analysis.get("document_type") or "Document",
            "confidence": analysis.get("confidence_score") or 0.9,
            "table_data": table_data,
            "raw_text": analysis.get("raw_text") or "",
            "analysis_name": analysis_name,
        }
    except Exception as e:
        frappe.log_error(f"load_extraction_data: {str(e)}")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def delete_extraction_item(item_name):
    try:
        if not frappe.has_permission("Extracted Data Item", ptype="delete"):
            return {"success": False, "error": _("Not permitted to delete Extracted Data Item")}
        frappe.delete_doc("Extracted Data Item", item_name)
        frappe.db.commit()
        return {'success': True, 'message': 'Champ supprimé'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@frappe.whitelist()
def update_extraction_item(item_name, field_value):
    try:
        doc = frappe.get_doc("Extracted Data Item", item_name)
        if not doc.has_permission("write"):
            return {"success": False, "error": _("Not permitted to modify this Extracted Data Item")}
        doc.field_value = field_value
        doc.save()
        frappe.db.commit()
        return {'success': True, 'message': 'Champ modifié'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# --------- Fusion (garde provenance) ---------
@frappe.whitelist()
def build_merged_view(per_file):
    rows = []
    index = {}
    for f in per_file:
        fname = f.get("filename")
        for r in f.get("table", []):
            key = f"{r.get('category') or ''}|{r.get('field') or ''}|{r.get('value') or ''}"
            if key in index:
                rows[index[key]]["sources"].append({"file": fname, "page": r.get("page")})
                fc = r.get("field_confidence")
                if fc is not None:
                    existing = rows[index[key]].get("_conf_list", [])
                    existing.append(fc)
                    rows[index[key]]["_conf_list"] = existing
                    rows[index[key]]["field_confidence"] = round(sum(existing)/len(existing), 3)
            else:
                new_row = {
                    "category": r.get("category") or "Données clés",
                    "field": r.get("field") or "",
                    "value": r.get("value") or "",
                    "type": r.get("type") or "text",
                    "sources": [{"file": fname, "page": r.get("page")}],
                }
                fc = r.get("field_confidence")
                if fc is not None:
                    new_row["_conf_list"] = [fc]
                    new_row["field_confidence"] = fc
                rows.append(new_row)
                index[key] = len(rows) - 1
    return {"table": rows}

#Récupérer la liste des Doctypes autorisés
@frappe.whitelist()
def get_available_doctypes():
    """Retourne la liste configurée dans PDF Extraction Settings."""
    try:
        settings = frappe.get_single("PDF Extraction Settings")
        rows = settings.get("doctypes_autorises") or []
        allowed = [r.doctype_name for r in rows if getattr(r, "active", 1)]
        return {"success": True, "doctypes": allowed}
    except Exception as e:
        frappe.log_error(f"get_available_doctypes: {str(e)}")
        return {"success": False, "error": str(e)}

@frappe.whitelist()
def get_doctype_fields(doctype):
    try:
        meta = frappe.get_meta(doctype)
        fields = []
        for df in meta.fields:
            if df.fieldtype in ("Section Break", "Column Break", "HTML", "Button", "Table", "Table MultiSelect"):
                continue
            fields.append({
                "label": df.label,
                "fieldname": df.fieldname,
                "fieldtype": df.fieldtype,
                "reqd": 1 if getattr(df, "reqd", 0) else 0,
            })
        return {"success": True, "doctype": doctype, "fields": fields}
    except Exception as e:
        frappe.log_error(f"get_doctype_fields: {str(e)}")
        return {"success": False, "error": str(e)}


# --------- Création du document cible ---------
@frappe.whitelist()
def create_doctype_record(target_doctype, data):
    """Créer un enregistrement dans le Doctype choisi à partir des données extraites."""
    if isinstance(data, str):
        data = json.loads(data)

    if not target_doctype:
        return {"success": False, "error": "target_doctype manquant"}
    if not frappe.has_permission(target_doctype, ptype="create"):
        return {"success": False, "error": _("Not permitted to create records in this DocType")}

    doc = frappe.get_doc({"doctype": target_doctype})

    for row in (data or []):
        fieldname = row.get("field") or row.get("fieldname")
        value = row.get("value")
        if fieldname and value not in (None, "", []):
            try:
                doc.set(fieldname, value)
            except Exception as e:
                frappe.logger().warning(f"Impossible de setter {fieldname}: {e}")

    doc.insert()
    frappe.db.commit()
    return {"success": True, "name": doc.name}


def _build_exact_target_view(per_file, target_fields):
    """
    Construit un tableau EXACT des champs du Doctype (dans le même ordre que target_fields),
    en prenant la première valeur non vide trouvée à travers les PDF.
    per_file: liste de dicts {"filename":..., "table":[{"field":..., "label":..., "value":...}, ...]}
    target_fields: liste de dicts {"fieldname":..., "label":...}
    """
    # index label par fieldname (pour l'affichage)
    label_by_field = { (f.get("fieldname") or ""): (f.get("label") or "") for f in (target_fields or []) }

    # valeurs collectées (vide par défaut)
    values_by_field = { (f.get("fieldname") or ""): "" for f in (target_fields or []) }

    # balayer les fichiers et remplir la 1ère valeur non vide
    for f in (per_file or []):
        for r in (f.get("table") or []):
            fn = r.get("field") or ""
            if fn in values_by_field and not values_by_field[fn]:
                v = (r.get("value") or "").strip()
                if v:
                    values_by_field[fn] = v

    # reconstruire la table finale dans l’ordre exact des target_fields
    out = []
    for f in (target_fields or []):
        fn = f.get("fieldname") or ""
        out.append({
            "category": "Doctype Fields",
            "field": fn,                          # fieldname technique (pour sauvegarde/création)
            "label": label_by_field.get(fn, ""),  # label humain (pour UI)
            "value": values_by_field.get(fn, ""), # valeur trouvée (ou vide)
            "type": "text"
        })
    return out
#Lire les paramètres OpenAI depuis les Settings
def _get_extraction_settings():
    """Lit la config unique. Fallback sur site_config si la clé n'est pas renseignée."""
    s = frappe.get_single("PDF Extraction Settings")
    key = s.openai_api_key or frappe.conf.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    return {
        "api_key": key,
        "model": s.openai_model or "gpt-4o-mini",
        "temperature": float(s.temperature or 0.1),
        "max_tokens": int(s.max_tokens or 1500),
        "prompt_general": (s.custom_prompt_general or "").strip(),
        "prompt_targeted": (s.custom_prompt_targeted or "").strip(),
    }


