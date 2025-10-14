import frappe
import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from datetime import datetime
from reportlab.lib.units import mm 
#Fonctions qui prend en parametre les chiffres et les inserer dans des cases specifique
def insert_date_digits(c, date_str, positions):
    """
    c          : canvas ReportLab
    date_str   : date en format string (ex: '05/07/2025')
    positions  : liste des coordonnées [(x1,y1), (x2,y2), ...] pour chaque chiffre
    """

    # ✅ Nettoyage : garder seulement les chiffres
    digits = ''.join(ch for ch in date_str if ch.isdigit())

    # ✅ Insertion chiffre par chiffre
    for i, digit in enumerate(digits):
        if i < len(positions):
            x, y = positions[i]
            c.drawString(x, y, digit)

#Fonction aide a la retour a la ligne (Tableau dans RC)
def draw_wrapped_text(canvas_obj, text, start_x, y, max_x):
    x = start_x
    words = text.split()
    for word in words:
        width = canvas_obj.stringWidth(word + ' ', "Helvetica-Bold", 11)
        if x + width > max_x:
            y -= 12  # nouvelle ligne
            x = start_x
        canvas_obj.drawString(x, y, word)
        x += width
    return y
@frappe.whitelist()
def generate_tp_pdf(docname):
    frappe.log_error("DEBUG PDF", f"Génération appelée pour {docname}")
    doc = frappe.get_doc("CompanyCreationRequest", docname)
    data = {
        "raison_sociale": doc.raison_sociale,
        "adresse_siege": doc.adresse_siege,
        "activite": doc.activite,
    }
    app_path = frappe.get_app_path("company_creation")
    template_path = os.path.join(app_path, "fixtures", "tp-template.pdf")
    base_pdf = PdfReader(template_path)
    packet = BytesIO()
    first_page = base_pdf.pages[0]
    width = float(first_page.mediabox.width)
    height = float(first_page.mediabox.height)
    c = canvas.Canvas(packet, pagesize=(width, height))
    c.setFont("Times-Bold", 12)  # Gras Times
    c.drawString(215, 624, data.get("raison_sociale") or "")
    c.drawString(162, 590.5, data.get("adresse_siege") or "")
    c.drawString(80, 574.5, data.get("activite") or "")

    c.save()
    packet.seek(0)

    overlay_pdf = PdfReader(packet)
    output = PdfWriter()

    for i, page in enumerate(base_pdf.pages):
        if i == 0:
            page.merge_page(overlay_pdf.pages[0])
        output.add_page(page)

    output_path = frappe.get_site_path("public", "files", f"tp-{docname}.pdf")
    with open(output_path, "wb") as f:
        output.write(f)

    return f"/files/tp-{docname}.pdf"

@frappe.whitelist()
def generate_rc_pdf(docname):
    frappe.log_error("DEBUG PDF", f"Génération RC pour {docname}")
    doc = frappe.get_doc("CompanyCreationRequest", docname)

    #  Données extraites du Doctype
    data = {
        "raison_sociale": doc.raison_sociale or "",
        "ville": doc.ville or "",
        "adresse_siege": doc.adresse_siege or "",
        "date_certificat": doc.date_certificat or "",
        "activite": doc.activite or "",
        "forme_juridique": doc.forme_juridique or "",
        "capital_social": str(doc.capital_social or ""),
        "founder_name": doc.founder_name or "",
        "date_lieu_naissance": doc.date_lieu_naissance or "",
        "nationality": doc.nationality or "",
        "quality": doc.quality or "",
        "address_founder": doc.address_founder or "",
        "cin_founder": doc.cin_founder or ""
    }

    # Champs à insérer par page
    fields_by_page = {
        0: {  # Page 1
            "raison_sociale": (531, 230),
             "ville": (100, 475)
           },
        1: {  # Page 2
            "raison_sociale": (188, 558),
            "adresse_siege": (142, 507),
            "date_certificat": (210, 545),
            "activite": (178, 531),
            "forme_juridique": (211, 453),
            "capital_social": (123, 439),
            "founder_name": (40, 280),
            "date_lieu_naissance": (188, 287),
            "nationality": (322, 280),
            "quality": (390, 300),
            "address_founder": (460, 287),
            "cin_founder": (732, 280)
        }
    }
    # Lecture du modèle PDF
    app_path = frappe.get_app_path("company_creation")
    template_path = os.path.join(app_path, "fixtures", "RC-template.pdf")
    base_pdf = PdfReader(template_path)
    output = PdfWriter()

    # Remplissage page par page
    for page_index, page in enumerate(base_pdf.pages):
        packet = BytesIO()
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.setFont("Times-Bold", 12)

        # Champs de cette page
        if page_index in fields_by_page:
            for field, coords in fields_by_page[page_index].items():
                x, y = coords
                if field == "address_founder":
                    draw_wrapped_text(c, str(data.get(field) or ""), x, y, 720)
                elif field == "founder_name":
                    draw_wrapped_text(c, str(data.get(field) or ""), x, y, 181)
                elif field == "date_lieu_naissance":
                    draw_wrapped_text(c, str(data.get(field) or ""), x, y, 316)
                elif field == "quality":
                    draw_wrapped_text(c, str(data.get(field) or ""), x, y, 384)
                else:
                    c.drawString(x, y, str(data.get(field) or ""))

        #  Signature uniquement sur page 2
        if page_index == 1:
            signature_text = (
                f"{data.get('founder_name','')}, adresse personnelle {data.get('address_founder','')}, "
                f"qualité de {data.get('quality','')}, certifie l'exactitude des indications portées "
                "sur la présente déclaration d'immatriculation."
            )
            y_pos = draw_wrapped_text(c, signature_text, 60, 188, 757)

        c.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        page.merge_page(overlay_pdf.pages[0])
        output.add_page(page)

    #  Sauvegarde du PDF généré
    output_path = frappe.get_site_path("public", "files", f"RC-{docname}.pdf")
    with open(output_path, "wb") as f:
        output.write(f)

    return f"/files/RC-{docname}.pdf"
@frappe.whitelist()
def generate_dl_pdf(docname):
    doc = frappe.get_doc("CompanyCreationRequest", docname)
    
    data = {
        "raison_sociale": doc.raison_sociale or "",
        "forme_juridique": doc.forme_juridique or "",
        "capital_social": str(doc.capital_social or ""),
        "adresse_siege": doc.adresse_siege or "",
        "founder_name": doc.founder_name or "",
        "date_certificat": doc.date_certificat or "",
    }

    # 📌 Définir les coordonnées
    fields_by_page = {
        0: {
            "raison_sociale": (216, 640),
            "forme_juridique": (216, 627),
            "capital_social": (170, 576),
            "adresse_siege": (160, 594),
            "founder_name": (65, 245),
             "founder_name": (75, 533)
        }
    }
    # insertion de la date du certificat negatif
    date_positions = [
    (403, 335),  # J (1er chiffre jour)
    (416, 335),  # J (2e chiffre jour)
    (443, 335),  # M (1er chiffre mois)
    (457, 335),  # M (2e chiffre mois)
    (484, 335),  # A (1er chiffre année)
    (496, 335),  # A (2e chiffre année)
    (510, 335),  # A (3e chiffre année)
    (523, 335)   # A (4e chiffre année)
    ]


    app_path = frappe.get_app_path("company_creation")
    template_path = os.path.join(app_path, "fixtures", "DL-template.pdf")
    base_pdf = PdfReader(template_path)
    output = PdfWriter()

    for page_index, page in enumerate(base_pdf.pages):
        packet = BytesIO()
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        c = canvas.Canvas(packet, pagesize=(width, height))
        c.setFont("Times-Bold", 12)

        if page_index in fields_by_page:
            for field, coords in fields_by_page[page_index].items():
                x, y = coords
                c.drawString(x, y, str(data.get(field) or ""))
        # Insérer la date
        if page_index == 0:
            insert_date_digits(c, doc.date_certificat, date_positions)
        c.save()
        packet.seek(0)
        overlay_pdf = PdfReader(packet)
        page.merge_page(overlay_pdf.pages[0])
        output.add_page(page)

    output_path = frappe.get_site_path("public", "files", f"DL-{docname}.pdf")
    with open(output_path, "wb") as f:
         output.write(f)

    return f"/files/DL-{docname}.pdf"


