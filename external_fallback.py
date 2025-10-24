"""External IPA Fallback Service
Consulta Wiktionary y otros diccionarios cuando una palabra no se encuentra en la DB local.
"""
import requests
import re
from typing import Optional, Dict, List
from bs4 import BeautifulSoup
import concurrent.futures


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
    
    def fetch_from_cambridge(self, word: str) -> Optional[Dict[str, any]]:
        """
        Obtiene transcripciones IPA de Cambridge Dictionary
        
        Returns:
            Dict con 'american' y 'rp' o None si no se encuentra
        """
        try:
            url = f"https://dictionary.cambridge.org/dictionary/english/{word.lower()}"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            result = {
                'american': None,
                'rp': None
            }
            
            # Buscar pronunciaciones en Cambridge
            # Cambridge usa span class="ipa" dentro de divs con class="us dpron-i" y "uk dpron-i"
            
            # UK/RP pronunciation
            uk_section = soup.find('span', class_='uk')
            if uk_section:
                ipa_span = uk_section.find('span', class_='ipa')
                if ipa_span:
                    ipa_text = ipa_span.get_text().strip()
                    ipa_text = re.sub(r'^/(.+)/$', r'\1', ipa_text)
                    result['rp'] = ipa_text
            
            # US pronunciation
            us_section = soup.find('span', class_='us')
            if us_section:
                ipa_span = us_section.find('span', class_='ipa')
                if ipa_span:
                    ipa_text = ipa_span.get_text().strip()
                    ipa_text = re.sub(r'^/(.+)/$', r'\1', ipa_text)
                    result['american'] = ipa_text
            
            if result['american'] or result['rp']:
                return result
            
            return None
            
        except Exception as e:
            print(f"Error fetching from Cambridge: {e}")
            return None
    
    def fetch_ipa(self, word: str) -> List[Dict[str, any]]:
        """
        Obtiene IPA de múltiples fuentes simultáneamente
        
        Returns:
            Lista de resultados de diferentes fuentes
        """
        results = []
        
        # Ejecutar consultas en paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Iniciar consultas
            future_wiktionary = executor.submit(self.fetch_from_wiktionary, word)
            future_cambridge = executor.submit(self.fetch_from_cambridge, word)
            
            # Recoger resultados de Wiktionary
            try:
                wiktionary_data = future_wiktionary.result()
                if wiktionary_data:
                    results.append({
                        'source': 'wiktionary',
                        'data': wiktionary_data
                    })
            except Exception as e:
                print(f"Wiktionary fetch failed: {e}")
            
            # Recoger resultados de Cambridge
            try:
                cambridge_data = future_cambridge.result()
                if cambridge_data:
                    results.append({
                        'source': 'cambridge',
                        'data': cambridge_data
                    })
            except Exception as e:
                print(f"Cambridge fetch failed: {e}")
        
        return results


def create_fallback_service(timeout: int = 5) -> ExternalIPAFallback:
    """Factory para crear el servicio de fallback"""
    return ExternalIPAFallback(timeout=timeout)
