import os
import json
import logging
from typing import Dict, Any, List
import asyncio
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)

class UniversalExtractor:
    def __init__(self, pdf_path: str, openai_api_key: str = None):
        self.pdf_path = pdf_path
        self.openai_client = None
        
        if openai_api_key:
            try:
                # Configuration explicite sans arguments problématiques
                self.openai_client = OpenAI(
                    api_key=openai_api_key
                )
            except Exception as e:
                logger.error(f"Erreur initialisation OpenAI: {e}")
                self.openai_client = None
        elif os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(
                    api_key=os.getenv('OPENAI_API_KEY')
                )
            except Exception as e:
                logger.error(f"Erreur initialisation OpenAI avec env: {e}")
                self.openai_client = None
        else:
            logger.error("Pas de clé API OpenAI configurée")
    
    def extract_text(self) -> str:
        """Extraire le texte du PDF"""
        if not HAS_PDFPLUMBER:
            return "Erreur: pdfplumber non installé"
        
        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Erreur extraction: {e}")
            return ""
    
    async def extract_key_information(self, text: str) -> Dict[str, Any]:
        """Extraire TOUTES les informations importantes du document"""
        if not self.openai_client:
            return {'error': 'OpenAI non configuré'}
        
        prompt = f"""
        Analyse ce document et extrais TOUTES les informations importantes sous forme de paires clé-valeur.
        
        INSTRUCTIONS:
        - Extrais TOUS les noms, dates, montants, numéros, adresses, etc.
        - Identifie le type de document
        - Structure les informations de manière logique
        - Si c'est un document commercial, extrais les détails financiers
        - Si c'est un contrat, extrais les parties et conditions
        - Si c'est un rapport, extrais les points clés
        - Si c'est un document de type status, extraits les champs et aussi les associes ,le gerant,la repartition de capital, l objet socia,et je veux les rapporst dans un  petit tableau  dans le grand tableau.
        - Etc.
        
        DOCUMENT:
        {text[:4000]}
        
        Réponds UNIQUEMENT en JSON avec cette structure:
        {{
            "document_type": "type_du_document_detecte",
            "confidence": 0.95,
            "general_info": {{
                "title": "titre_du_document",
                "date": "date_principale_YYYY-MM-DD",
                "language": "langue_detectee",
                "pages": "nombre_estimé"
            }},
            "entities": {{
                "persons": ["nom1", "nom2"],
                "companies": ["entreprise1", "entreprise2"],
                "locations": ["lieu1", "lieu2"],
                "dates": ["date1", "date2"],
                "amounts": ["montant1", "montant2"],
                "references": ["ref1", "ref2"]
            }},
            "key_data": {{
                "champ1": "valeur1",
                "champ2": "valeur2",
                "champ3": "valeur3"
            }},
            "structured_content": [
                {{
                    "section": "nom_section",
                    "content": "contenu_de_la_section"
                }}
            ],
            "summary": "résumé_du_document_en_quelques_phrases"
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content
            
            # Nettoyer le JSON
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Erreur ChatGPT: {e}")
            return {'error': str(e)}

def extract_any_pdf(pdf_path: str, openai_key: str = None) -> Dict[str, Any]:
    """Extraction universelle de PDF"""
    try:
        extractor = UniversalExtractor(pdf_path, openai_key)
        
        # Extraire le texte
        text = extractor.extract_text()
        if not text.strip():
            return {'success': False, 'error': 'Aucun texte extrait'}
        
        # Analyser avec ChatGPT
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        analysis = loop.run_until_complete(extractor.extract_key_information(text))
        loop.close()
        
        if 'error' in analysis:
            return {'success': False, 'error': analysis['error']}
        
        # Convertir en format tableau
        table_data = convert_to_table_format(analysis)
        
        return {
            'success': True,
            'document_type': analysis.get('document_type', 'Document'),
            'confidence': analysis.get('confidence', 0),
            'raw_text': text[:1000] + "..." if len(text) > 1000 else text,
            'extracted_data': analysis,
            'table_data': table_data
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def convert_to_table_format(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Convertir l'analyse en format tableau modifiable"""
    table_data = []
    
    # Informations générales
    if 'general_info' in analysis:
        for key, value in analysis['general_info'].items():
            table_data.append({
                'category': 'Informations générales',
                'field': key.replace('_', ' ').title(),
                'value': str(value) if value else '',
                'type': 'text'
            })
    
    # Entités extraites
    if 'entities' in analysis:
        for entity_type, entity_list in analysis['entities'].items():
            if isinstance(entity_list, list) and entity_list:
                for i, entity in enumerate(entity_list):
                    table_data.append({
                        'category': 'Entités',
                        'field': f"{entity_type.replace('_', ' ').title()} {i+1}",
                        'value': str(entity),
                        'type': 'text'
                    })
    
    # Données clés
    if 'key_data' in analysis:
        for key, value in analysis['key_data'].items():
            # Détecter le type de champ
            field_type = 'text'
            if 'date' in key.lower():
                field_type = 'date'
            elif 'amount' in key.lower() or 'price' in key.lower() or 'total' in key.lower():
                field_type = 'number'
            elif 'email' in key.lower():
                field_type = 'email'
            
            table_data.append({
                'category': 'Données clés',
                'field': key.replace('_', ' ').title(),
                'value': str(value) if value else '',
                'type': field_type
            })
    
    # Contenu structuré
    if 'structured_content' in analysis:
        for i, section in enumerate(analysis['structured_content']):
            table_data.append({
                'category': 'Contenu',
                'field': section.get('section', f'Section {i+1}'),
                'value': section.get('content', ''),
                'type': 'textarea'
            })
    
    # Résumé
    if 'summary' in analysis:
        table_data.append({
            'category': 'Résumé',
            'field': 'Résumé du document',
            'value': analysis['summary'],
            'type': 'textarea'
        })
    
    return table_data
