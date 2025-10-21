"""
IPA Transcription Service
Módulo que contiene toda la lógica fonética para transcripciones IPA.
Separado de la lógica del servidor FastAPI.
"""
import sqlite3
import re
from typing import Optional, List, Dict
import os


class IPATranscriptionService:
    """Servicio de transcripción IPA con todas las reglas fonéticas"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.punct_re = re.compile(r"^[.,!?;:'-]+$")
    
    def db_lookup(self, word: str, accent: str) -> Optional[str]:
        """Lookup word in database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT us, gb FROM ipa WHERE word=?", (word.lower(),))
        row = cur.fetchone()
        conn.close()
        
        if not row:
            return None
        
        us, gb = row
        if accent == 'american':
            return us or gb
        return gb or us
    
    def parse_weak_strong_format(self, ipa_text: str) -> Dict[str, str]:
        """Parse formato / [strong], [weak] / y devolver dict con formas"""
        if not ipa_text or not ipa_text.startswith('/ ') or not ipa_text.endswith(' /'):
            return {'single': ipa_text}  # Formato simple
        
        # Extraer contenido entre las barras
        content = ipa_text[2:-2]  # Remover "/ " y " /"
        
        if ', ' in content:
            strong, weak = content.split(', ', 1)
            return {'strong': strong.strip(), 'weak': weak.strip()}
        else:
            return {'single': content.strip()}
    
    def should_use_weak(self, word: str, idx: int, words: List[str]) -> bool:
        """Improved weak forms logic based on frontend rules"""
        w = re.sub(r"[^\w']", '', word.lower())
        
        # Rule 1: Words that are ALWAYS strong
        always_strong = ['i', 'my', 'may', 'might', 'ought', 'by', 'so', 'while']
        if w in always_strong:
            return False
        
        # Rule 2: Contractions are already in weak form
        if "'" in w:
            return False
        
        # Rule 3: "the" is handled specially (allophonic variation)
        if w == 'the':
            return False
        
        # Rule 4: First word tends to be strong (except "the", "a", "an", "there")
        if idx == 0:
            weak_at_start = ['the', 'a', 'an', 'there']
            if w not in weak_at_start:
                return False
        
        # Rule 5: Strong before pause (comma, period, etc.)
        if idx < len(words) - 1 and self.punct_re.match(words[idx+1] or ''):
            return False
        
        # Rule 6: Last word tends to be strong
        if idx == len(words) - 1:
            return False
        
        # Rule 7: Auxiliaries at start of questions are strong
        auxiliaries = ['is', 'are', 'was', 'were', 'have', 'has', 'had', 'do', 'does', 'did',
                       'will', 'would', 'can', 'could', 'should', 'must']
        if w in auxiliaries and idx == 0:
            return False
        
        # Rule 8: Default - use weak form in non-prominent positions
        return True
    
    def get_transcription_with_weak_strong(self, word: str, accent: str, use_weak: bool, word_index: int, all_words: List[str]) -> Optional[str]:
        """Get transcription considering weak/strong forms for RP"""
        ipa_raw = self.db_lookup(word, accent)
        if not ipa_raw:
            return None
        
        # Si es RP y tiene formato weak/strong, procesarlo
        if accent == 'rp':
            parsed = self.parse_weak_strong_format(ipa_raw)
            if 'strong' in parsed and 'weak' in parsed:
                # Aplicar lógica de weak/strong
                if use_weak and self.should_use_weak(word, word_index, all_words):
                    return parsed['weak']
                else:
                    return parsed['strong']
            elif 'single' in parsed:
                return parsed['single']
        
        # Para American o formato simple, devolver tal como está
        return ipa_raw
    
    def apply_character_corrections(self, text: str, accent: str) -> str:
        """Apply character corrections based on frontend logic"""
        corrected = text
        
        # Remove incorrect slashes from Kaikki data
        corrected = re.sub(r'^/([^/]+)/$', r'\1', corrected)  # Remove /word/ format
        corrected = corrected.replace('/', '')  # Remove any remaining slashes
        
        # Basic cleanup - use preferred characters
        corrected = corrected.replace('ɹ', 'r')  # Use r instead of ɹ
        corrected = corrected.replace('ɛ', 'e')  # Use e instead of ɛ
        corrected = corrected.replace('ɐ', 'ə')  # Normalize schwa
        
        if accent == 'american':
            # American-specific corrections
            corrected = corrected.replace('ɒ', 'ɑ')      # LOT vowel
            corrected = corrected.replace('əʊ', 'oʊ')     # GOAT vowel
            corrected = corrected.replace('ɪə', 'ɪr')     # NEAR
            corrected = corrected.replace('eə', 'er')     # SQUARE
            corrected = corrected.replace('ʊə', 'ʊr')     # CURE
            corrected = corrected.replace('ɜː', 'ɜr')     # NURSE
            corrected = re.sub(r'ɑː(\s|$)', r'ɑr\1', corrected)  # Rhotic
        
        return corrected
    
    def ends_with_vowel(self, transcription: str) -> bool:
        """Detect if a transcription ends with a vowel"""
        if not transcription:
            return False
        
        # Common IPA vowels pattern
        vowel_pattern = re.compile(r'[æɑɒɔʊuɪieoəʌɜɪaʊɔɪɛœ]ː?$')
        return bool(vowel_pattern.search(transcription.strip()))
    
    def starts_with_vowel(self, transcription: str) -> bool:
        """Detect if a transcription starts with a vowel"""
        if not transcription:
            return False
        
        vowel_pattern = re.compile(r'^[æɑɒɔʊʉuiɪeəʌɜoɘaɪaʊɔɪɜɟɨɪəeəʊəɛʎœɶɨɘɵɯɤɦɐʉɦɜɽɨɘɵɯɤ]')
        return bool(vowel_pattern.search(transcription.strip()))
    
    def apply_the_variation(self, transcription: str) -> str:
        """Apply allophonic variation to 'the'"""
        # "the" + vowel = /ði/
        # "the" + consonant = /ðə/
        the_pattern = re.compile(r'\bðə\s+([æɑɒɔʊu iɪeəʌɜaɪaʊɔɪɪəeəʊəɛ])')
        return the_pattern.sub(r'ði \1', transcription)
    
    def apply_linking_r(self, transcribed_words: List[str], original_words: List[str], accent: str) -> List[str]:
        """Apply Linking R for RP based on original spelling"""
        if accent != 'rp' or len(transcribed_words) < 2 or len(original_words) != len(transcribed_words):
            return transcribed_words
        
        result = transcribed_words.copy()
        
        for i in range(len(result) - 1):
            current_transcription = result[i]
            next_transcription = result[i + 1]
            current_original = original_words[i]
            next_original = original_words[i + 1]
            
            # Skip punctuation
            if re.match(r'^[.,!?;:\'-]+$', next_original):
                continue
            
            # Apply linking R if:
            # 1. Original word ends in 'r' or has 'r' in last syllable
            # 2. Current transcription ends with vowel
            # 3. Next transcription starts with vowel
            original_ends_in_r = bool(re.search(r'r\w*$|\w*r$', current_original, re.IGNORECASE))
            
            if (original_ends_in_r and 
                self.ends_with_vowel(current_transcription) and 
                self.starts_with_vowel(next_transcription)):
                
                # Exceptions where NOT to apply linking R
                exceptions = ['more', 'sure', 'pure']  # Words that already have R in RP
                clean_original = re.sub(r'[^\w]', '', current_original.lower())
                
                if clean_original not in exceptions and not current_transcription.endswith('r'):
                    result[i] = current_transcription + 'r'
        
        return result
    
    def apply_rp_symbol_transforms(self, text: str) -> str:
        """Apply RP symbol transformations from frontend logic"""
        transformed = text
        
        # Transform symbols according to specific rules
        transformed = transformed.replace('!', '(!)')
        transformed = transformed.replace('?', '(?)')
        transformed = transformed.replace('.', ' //')
        transformed = transformed.replace(',', ' /')
        
        return transformed
    
    def transcribe_text(self, text: str, accent: str, use_weak: bool, ignore_stress: bool) -> str:
        """Main transcription function with all phonetic rules applied"""
        tokens = re.findall(r"\b\w+'\w+\b|\b\w+\b|[.,!?;:'-]", text) or []
        out: List[str] = []
        
        for i, tok in enumerate(tokens):
            if self.punct_re.match(tok):
                out.append(tok)
                continue
                
            # Usar nueva lógica de weak/strong
            ipa = self.get_transcription_with_weak_strong(tok, accent, use_weak, i, tokens)
            
            if ipa:
                # Apply character corrections to the IPA result
                ipa = self.apply_character_corrections(ipa, accent)
                out.append(ipa)
            else:
                # Fallback: palabra no encontrada
                out.append(tok)
        
        # Apply Linking R for RP (pass both transcribed and original words)
        if accent == 'rp':
            out = self.apply_linking_r(out, tokens, accent)
        
        result = ' '.join(out)
        result = re.sub(r"\s+([.,!?;:'-])", r"\1", result)
        
        # Apply "the" variation
        result = self.apply_the_variation(result)
        
        # Apply RP symbol transformations
        if accent == 'rp':
            result = self.apply_rp_symbol_transforms(result)
        
        if ignore_stress:
            result = result.replace('ˈ', '').replace('ˌ', '')
        
        return result.strip()


def create_transcription_service(db_path: str = None) -> IPATranscriptionService:
    """Factory function to create transcription service"""
    if db_path is None:
        # Default path relative to this file
        current_dir = os.path.dirname(__file__)
        db_path = os.path.join(current_dir, 'ipa_en.sqlite')
    
    return IPATranscriptionService(db_path)