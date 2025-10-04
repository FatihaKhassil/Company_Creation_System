import os
import json
import logging
from typing import Dict, Any, List
import asyncio

# Dépendances
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

# ----------------------------
# Prompt ciblé (utilitaire)
# ----------------------------
def build_targeted_prompt(text: str, target_fields: list) -> str:
    """
    Construit un prompt qui oblige le modèle à renvoyer un JSON
    avec EXACTEMENT les fieldnames fournis.
    """
    targets_block = "\n".join(
        [f"- {f.get('fieldname','')} :: {f.get('label','')}" for f in target_fields]
    )

    return f"""
Tu es un extracteur de données. Ton rôle est d'extraire UNIQUEMENT les champs demandés
et de retourner un JSON VALIDE. Respecte STRICTEMENT les consignes suivantes :

RÈGLES :
- Ne crée PAS de nouvelles clés. Utilise EXCLUSIVEMENT les 'fieldname' fournis.
- Si un champ est introuvable avec certitude, mets une chaîne vide "".
- N'invente PAS de valeurs.
- Normalise les dates au format YYYY-MM-DD si possible.
- Pour les montants, renvoie la valeur brute trouvée (sans calcul).
- Ajoute 'confidence' (0.0 à 1.0) par champ selon la clarté de l'extrait.
- NE RENVOIE AUCUN TEXTE HORS JSON.

LISTE DES CHAMPS CIBLES (fieldname :: label) :
{targets_block}

DOCUMENT (extrait) :
{text[:4000]}

RÉPONDS UNIQUEMENT par un JSON de la forme :
{{
  "document_type": "type_detecte_ou_inconnu",
  "global_confidence": 0.0,
  "target_fields": [
    {{"fieldname": "champ1_fieldname", "label": "label_informatif_si_connu", "value": "valeur_ou_vide", "confidence": 0.0}}
  ],
  "notes": ""
}}
"""


class UniversalExtractor:
    def __init__(
        self,
        pdf_path: str,
        openai_api_key: str = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_tokens: int = 1500,
        custom_prompt_general: str = "",
        custom_prompt_targeted: str = ""
    ):
        self.pdf_path = pdf_path
        self.model = model
        self.temperature = float(temperature or 0.1)
        self.max_tokens = int(max_tokens or 1500)
        self.prompt_general = (custom_prompt_general or "").strip()
        self.prompt_targeted = (custom_prompt_targeted or "").strip()

        self.openai_client = None
        if openai_api_key:
            try:
                self.openai_client = OpenAI(api_key=openai_api_key)
            except Exception as e:
                logger.error(f"Erreur initialisation OpenAI: {e}")
        elif os.getenv('OPENAI_API_KEY'):
            try:
                self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            except Exception as e:
                logger.error(f"Erreur initialisation OpenAI avec env: {e}")
        else:
            logger.error("Pas de clé API OpenAI configurée")

    def extract_text(self) -> str:
        """Extraire le texte du PDF (retourne '' si échec/absent)."""
        if not HAS_PDFPLUMBER:
            logger.error("pdfplumber non installé")
            return ""

        text = ""
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Erreur extraction texte pdfplumber: {e}")
            return ""

    async def extract_key_information(self, text: str) -> Dict[str, Any]:
        """Extraction large (TOUTES infos importantes)."""
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
                "champ2": "valeur2"
            }},
            "structured_content": [
                {{"section": "nom_section", "content": "contenu_de_la_section"}}
            ],
            "summary": "résumé_du_document"
        }}
        """

        try:
            # Préfixe par un prompt général custom si défini
            if self.prompt_general:
                prompt = f"{self.prompt_general.strip()}\n\n---\n\n{prompt}"

            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            content = response.choices[0].message.content
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Erreur ChatGPT (large): {e}")
            return {'error': str(e)}

    async def extract_key_information_with_targets(self, text: str, target_fields: list) -> Dict[str, Any]:
        """Extraction ciblée par liste de champs (fieldname/label)."""
        if not self.openai_client:
            return {'error': 'OpenAI non configuré'}

        prompt = build_targeted_prompt(text, target_fields)
        if self.prompt_targeted:
            prompt = f"{self.prompt_targeted.strip()}\n\n---\n\n{prompt}"

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0 if self.temperature is None else self.temperature,
                max_tokens=self.max_tokens
            )
            content = response.choices[0].message.content
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Erreur ChatGPT (targeted): {e}")
            return {'error': str(e)}


def extract_any_pdf(
    pdf_path: str,
    openai_key: str = None,
    targets: List[Dict[str, Any]] = None,
    settings: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Extraction universelle de PDF. Si 'targets' est fourni, extraction ciblée."""
    settings = settings or {}
    try:
        extractor = UniversalExtractor(
            pdf_path,
            openai_api_key=openai_key,
            model=settings.get("model", "gpt-4o-mini"),
            temperature=settings.get("temperature", 0.1),
            max_tokens=settings.get("max_tokens", 1500),
            custom_prompt_general=settings.get("prompt_general", ""),
            custom_prompt_targeted=settings.get("prompt_targeted", "")
        )

        # 1) Texte
        text = extractor.extract_text()
        if not text.strip():
            return {'success': False, 'error': 'Aucun texte extrait (PDF scanné ? pdfplumber absent ?)'}

        # 2) LLM
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        targeted_result = None
        if targets:
            targeted_result = loop.run_until_complete(
                extractor.extract_key_information_with_targets(text, targets)
            )
            if targeted_result and 'error' in targeted_result:
                targeted_result = None

        # 3) Large si pas de cibles (ou ciblé KO)
        if not targeted_result:
            analysis = loop.run_until_complete(extractor.extract_key_information(text))
            if 'error' in analysis:
                loop.close()
                return {'success': False, 'error': analysis['error']}
            table_data = convert_to_table_format(analysis)
            loop.close()
            return {
                'success': True,
                'document_type': analysis.get('document_type', 'Document'),
                'confidence': analysis.get('confidence', analysis.get('global_confidence', 0.9)),
                'raw_text': text[:1000] + "..." if len(text) > 1000 else text,
                'extracted_data': analysis,
                'table_data': table_data
            }

        # 4) Ciblé OK → table "Doctype Fields"
        loop.close()
        targeted_table = []
        for item in (targeted_result.get('target_fields') or []):
            targeted_table.append({
                'category': 'Doctype Fields',
                'field': f"{item.get('fieldname','')}",  # fieldname exact
                'value': item.get('value', '') or '',
                'type': 'text',
                'confidence': item.get('confidence'),
                'label': item.get('label', '')
            })

        return {
            'success': True,
            'document_type': targeted_result.get('document_type') or 'Document',
            'confidence': targeted_result.get('global_confidence', 0.9),
            'raw_text': text[:1000] + "..." if len(text) > 1000 else text,
            'extracted_data': targeted_result,
            'table_data': targeted_table
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def convert_to_table_format(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Convertir l'analyse large en format tableau."""
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

    # Entités
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
            field_type = 'text'
            lk = key.lower()
            if 'date' in lk:
                field_type = 'date'
            elif any(k in lk for k in ['amount', 'price', 'total']):
                field_type = 'number'
            elif 'email' in lk:
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
