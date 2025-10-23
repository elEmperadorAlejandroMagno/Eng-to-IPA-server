"""
External IPA Fallback Service
Consulta Wiktionary y otros diccionarios cuando una palabra no se encuentra en la DB local.
"""
import requests
import re
from typing import Optional, Dict
from bs4 import BeautifulSoup


class ExternalIPAFallback:
    """Servicio de fallback para obtener transcripciones IPA de fuentes externas"""
    
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'IPA-Transcription-Service/1.0'
        })
    
    def fetch_from_wiktionary(self, word: str) -> Optional[Dict[str, any]]:
        """
        Obtiene transcripciones IPA de Wiktionary
        
        Returns:
            Dict con 'american' y 'rp' o None si no se encuentra
        """
        try:
            url = f"https://en.wiktionary.org/api/rest_v1/page/html/{word.lower()}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar secciones de pronunciación en inglés
            result = {
                'american': None,
                'rp': None
            }
            
            # Buscar todos los spans con clase IPA
            ipa_spans = soup.find_all('span', class_='IPA')
            
            # Buscar contexto de dialecto
            for ipa_span in ipa_spans:
                ipa_text = ipa_span.get_text().strip()
                # Limpiar formato /.../ si existe
                ipa_text = re.sub(r'^/(.+)/$', r'\1', ipa_text)
                
                # Buscar el contexto anterior para identificar el dialecto
                parent = ipa_span.find_parent()
                if parent:
                    context = parent.get_text().lower()
                    
                    # Identificar American English
                    if any(marker in context for marker in ['us', 'general american', 'ga', 'genamer']):
                        if not result['american']:
                            result['american'] = ipa_text
                    
                    # Identificar British English / RP
                    elif any(marker in context for marker in ['uk', 'rp', 'received pronunciation', 'british']):
                        if not result['rp']:
                            result['rp'] = ipa_text
            
            # Si encontramos al menos una transcripción, devolver
            if result['american'] or result['rp']:
                return result
            
            return None
            
        except Exception as e:
            print(f"Error fetching from Wiktionary: {e}")
            return None
    
    def fetch_ipa(self, word: str) -> Optional[Dict[str, any]]:
        """
        Intenta obtener IPA de múltiples fuentes
        
        Returns:
            Dict con transcripciones encontradas y la fuente
        """
        # Intentar Wiktionary primero
        wiktionary_result = self.fetch_from_wiktionary(word)
        if wiktionary_result:
            return {
                'source': 'wiktionary',
                'data': wiktionary_result
            }
        
        # Aquí se pueden agregar más fuentes (Longman, etc.)
        
        return None


def create_fallback_service(timeout: int = 5) -> ExternalIPAFallback:
    """Factory para crear el servicio de fallback"""
    return ExternalIPAFallback(timeout=timeout)
