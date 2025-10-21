"""
Transformers Module
Contains all character corrections, symbol transformations, and post-processing rules.
"""
import re
from typing import List
from abc import ABC, abstractmethod


class Transformer(ABC):
    """Abstract base class for transformers"""
    
    @abstractmethod
    def transform(self, text: str, accent: str = None) -> str:
        """Apply transformation to text"""
        pass


class CharacterCorrector(Transformer):
    """Corrects common IPA character inconsistencies"""
    
    def __init__(self):
        # Basic character replacements
        self.basic_replacements = {
            'ɹ': 'r',  # Use r instead of ɹ
            'ɛ': 'e',  # Use e instead of ɛ
            'ɐ': 'ə',  # Normalize schwa
        }
        
        # American-specific replacements
        self.american_replacements = {
            'ɒ': 'ɑ',      # LOT vowel
            'əʊ': 'oʊ',    # GOAT vowel
            'ɪə': 'ɪr',    # NEAR
            'eə': 'er',    # SQUARE
            'ʊə': 'ʊr',    # CURE
            'ɜː': 'ɜr',    # NURSE
        }
    
    def transform(self, text: str, accent: str = None) -> str:
        """Apply character corrections"""
        corrected = text
        
        # Remove incorrect slashes from Kaikki data
        corrected = re.sub(r'^/([^/]+)/$', r'\1', corrected)
        corrected = corrected.replace('/', '')
        
        # Remove syllable boundary markers
        corrected = corrected.replace('.', '')
        
        # Apply basic replacements
        for old_char, new_char in self.basic_replacements.items():
            corrected = corrected.replace(old_char, new_char)
        
        # Apply accent-specific replacements
        if accent == 'american':
            for old_char, new_char in self.american_replacements.items():
                corrected = corrected.replace(old_char, new_char)
            
            # Special rhotic replacement
            corrected = re.sub(r'ɑː(\s|$)', r'ɑr\1', corrected)
        
        return corrected


class VowelDetector:
    """Utility class for vowel detection"""
    
    def __init__(self):
        self.vowel_end_pattern = re.compile(r'[æɑɒɔʊuɪieoəʌɜɪaʊɔɪɛœ]ː?$')
        self.vowel_start_pattern = re.compile(r'^[æɑɒɔʊʉuiɪeəʌɜoɘaɪaʊɔɪɜɟɨɪəeəʊəɛʎœɶɨɘɵɯɤɦɐʉɦɜɽɨɘɵɯɤ]')
    
    def ends_with_vowel(self, transcription: str) -> bool:
        """Check if transcription ends with a vowel"""
        if not transcription:
            return False
        return bool(self.vowel_end_pattern.search(transcription.strip()))
    
    def starts_with_vowel(self, transcription: str) -> bool:
        """Check if transcription starts with a vowel"""
        if not transcription:
            return False
        return bool(self.vowel_start_pattern.search(transcription.strip()))


class TheVariationProcessor(Transformer):
    """Handles allophonic variation of 'the'"""
    
    def __init__(self):
        # "the" + vowel = /ði/, "the" + consonant = /ðə/
        self.the_pattern = re.compile(r'\bðə\s+([æɑɒɔʊu iɪeəʌɜaɪaʊɔɪɪəeəʊəɛ])')
    
    def transform(self, text: str, accent: str = None) -> str:
        """Apply 'the' variation rule"""
        return self.the_pattern.sub(r'ði \1', text)


class LinkingRProcessor(Transformer):
    """Handles linking R for RP accent"""
    
    def __init__(self):
        self.vowel_detector = VowelDetector()
        self.exceptions = ['more', 'sure', 'pure']  # Words that already have R in RP
    
    def transform(self, text: str, accent: str = None) -> str:
        """This transformer works on word lists, not individual text"""
        # This method is not used for linking R - see apply_linking_r method instead
        return text
    
    def apply_linking_r(self, transcribed_words: List[str], original_words: List[str], accent: str) -> List[str]:
        """Apply linking R based on original spelling"""
        if accent != 'rp' or len(transcribed_words) < 2 or len(original_words) != len(transcribed_words):
            return transcribed_words
        
        result = transcribed_words.copy()
        
        for i in range(len(result) - 1):
            current_transcription = result[i]
            next_transcription = result[i + 1]
            current_original = original_words[i]
            next_original = original_words[i + 1]
            
            # Skip punctuation
            if re.match(r'^[.,!?;\'-]+$', next_original):
                continue
            
            # Check conditions for linking R
            original_ends_in_r = bool(re.search(r'r\w*$|\w*r$', current_original, re.IGNORECASE))
            
            if (original_ends_in_r and 
                self.vowel_detector.ends_with_vowel(current_transcription) and 
                self.vowel_detector.starts_with_vowel(next_transcription)):
                
                # Apply exceptions
                clean_original = re.sub(r'[^\w]', '', current_original.lower())
                
                if clean_original not in self.exceptions and not current_transcription.endswith('r'):
                    result[i] = current_transcription + 'r'
        
        return result


class RPSymbolTransformer(Transformer):
    """Transforms punctuation symbols for RP style"""
    
    def __init__(self):
        self.transformations = {
            '!': '(!)',
            '?': '(?)',
            ',': ' /',
        }
    
    def transform(self, text: str, accent: str = None) -> str:
        """Apply RP symbol transformations"""
        if accent != 'rp':
            return text
            
        transformed = text
        
        # Apply basic symbol transformations
        for symbol, replacement in self.transformations.items():
            transformed = transformed.replace(symbol, replacement)
        
        # Handle sentence-ending periods separately (not syllable boundaries)
        # Only replace periods that are at word boundaries, not within IPA transcriptions
        import re
        # Replace periods that appear as separate tokens (sentence endings)
        transformed = re.sub(r'\s*\.\s*', ' // ', transformed)  # " . " -> " // "
        transformed = re.sub(r'\.$', ' //', transformed)        # "." at end -> " //"
        transformed = transformed.strip()  # Clean up any trailing spaces
        
        return transformed


class StressRemover(Transformer):
    """Removes stress markers from IPA text"""
    
    def transform(self, text: str, accent: str = None) -> str:
        """Remove primary and secondary stress markers"""
        return text.replace('ˈ', '').replace('ˌ', '')


class TransformationPipeline:
    """Pipeline for applying multiple transformers in sequence"""
    
    def __init__(self):
        self.transformers = []
    
    def add_transformer(self, transformer: Transformer):
        """Add a transformer to the pipeline"""
        self.transformers.append(transformer)
    
    def remove_transformer(self, transformer_class):
        """Remove all transformers of specified class"""
        self.transformers = [t for t in self.transformers if not isinstance(t, transformer_class)]
    
    def transform(self, text: str, accent: str = None) -> str:
        """Apply all transformers in sequence"""
        result = text
        for transformer in self.transformers:
            result = transformer.transform(result, accent)
        return result
    
    def clear(self):
        """Remove all transformers"""
        self.transformers.clear()