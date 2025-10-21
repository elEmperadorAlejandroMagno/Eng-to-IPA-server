"""
Modular IPA Transcription Service
Refactored version using composition and specialized modules for better maintainability.
"""
import re
from typing import Optional, List
import os

from database_service import DatabaseService
from phonetic_rules import WeakFormProcessor, WeakStrongParser
from transformers import (
    CharacterCorrector, TheVariationProcessor, LinkingRProcessor, 
    RPSymbolTransformer, StressRemover, TransformationPipeline
)


class ModularIPATranscriptionService:
    """
    Modular IPA transcription service using composition pattern.
    Each responsibility is handled by a specialized component.
    """
    
    def __init__(self, db_path: str):
        # Core services
        self.db_service = DatabaseService(db_path)
        self.weak_form_processor = WeakFormProcessor()
        self.parser = WeakStrongParser()
        
        # Transformers
        self.character_corrector = CharacterCorrector()
        self.the_variation_processor = TheVariationProcessor()
        self.linking_r_processor = LinkingRProcessor()
        self.rp_symbol_transformer = RPSymbolTransformer()
        self.stress_remover = StressRemover()
        
        # Build transformation pipeline
        self.pipeline = TransformationPipeline()
        self.pipeline.add_transformer(self.character_corrector)
        
        # Regex for punctuation
        self.punct_re = re.compile(r"^[.,!?;:'-]+$")
    
    def lookup_word(self, word: str, accent: str) -> Optional[str]:
        """Simple word lookup - delegates to database service"""
        return self.db_service.lookup_word(word, accent)
    
    def get_transcription_with_forms(self, word: str, accent: str, use_weak: bool, 
                                   word_index: int, all_words: List[str]) -> Optional[str]:
        """
        Get transcription considering weak/strong forms for RP
        
        Args:
            word: Word to transcribe
            accent: 'american' or 'rp'
            use_weak: Whether to use weak forms
            word_index: Position of word in sentence
            all_words: All words in sentence
            
        Returns:
            IPA transcription or None if not found
        """
        # Get raw IPA from database
        ipa_raw = self.db_service.lookup_word(word, accent)
        if not ipa_raw:
            return None
        
        # For RP, check if it has weak/strong format
        if accent == 'rp':
            parsed = self.parser.parse_format(ipa_raw)
            
            if 'strong' in parsed and 'weak' in parsed:
                # Determine which form to use
                if use_weak and self.weak_form_processor.should_use_weak(word, word_index, all_words):
                    # Special handling for words with custom weak forms (have, must)
                    clean_word = word.lower().replace("'", "")
                    if clean_word in ['have', 'must']:
                        # Get context for special weak form rules
                        context = {
                            'word_index': word_index,
                            'words': all_words,
                            'punct_re': self.weak_form_processor.punct_re
                        }
                        # Check if we have a rule with custom get_weak_form method
                        for rule in self.weak_form_processor.rules:
                            if hasattr(rule, 'get_weak_form') and rule.applies_to(word, context):
                                return rule.get_weak_form(word, context)
                    
                    return parsed['weak']
                else:
                    return parsed['strong']
            elif 'single' in parsed:
                return parsed['single']
        
        # For American or simple format, return as-is
        return ipa_raw
    
    def process_word_list(self, tokens: List[str], accent: str, use_weak: bool) -> List[str]:
        """
        Process a list of tokens into IPA transcriptions
        
        Args:
            tokens: List of words and punctuation
            accent: 'american' or 'rp'
            use_weak: Whether to use weak forms
            
        Returns:
            List of IPA transcriptions
        """
        transcribed_words = []
        
        for i, token in enumerate(tokens):
            if self.punct_re.match(token):
                transcribed_words.append(token)
                continue
            
            # Get transcription with weak/strong logic
            ipa = self.get_transcription_with_forms(token, accent, use_weak, i, tokens)
            
            if ipa:
                # Apply character corrections
                ipa = self.character_corrector.transform(ipa, accent)
                transcribed_words.append(ipa)
            else:
                # Fallback: word not found
                transcribed_words.append(token)
        
        return transcribed_words
    
    def apply_post_processing(self, transcribed_words: List[str], original_tokens: List[str], 
                            accent: str, ignore_stress: bool) -> str:
        """
        Apply all post-processing rules to transcribed words
        
        Args:
            transcribed_words: List of transcribed words
            original_tokens: Original word tokens
            accent: 'american' or 'rp'
            ignore_stress: Whether to remove stress markers
            
        Returns:
            Final processed transcription
        """
        # Apply linking R for RP
        if accent == 'rp':
            transcribed_words = self.linking_r_processor.apply_linking_r(
                transcribed_words, original_tokens, accent
            )
        
        # Join words and fix punctuation spacing
        result = ' '.join(transcribed_words)
        result = re.sub(r"\s+([.,!?;:'-])", r"\1", result)
        
        # Apply "the" variation
        result = self.the_variation_processor.transform(result, accent)
        
        # Apply RP symbol transformations
        result = self.rp_symbol_transformer.transform(result, accent)
        
        # Remove stress markers if requested
        if ignore_stress:
            result = self.stress_remover.transform(result, accent)
        
        return result.strip()
    
    def transcribe_text(self, text: str, accent: str, use_weak: bool, ignore_stress: bool) -> str:
        """
        Main transcription method - orchestrates the entire process
        
        Args:
            text: Input text to transcribe
            accent: 'american' or 'rp'
            use_weak: Whether to use weak forms
            ignore_stress: Whether to remove stress markers
            
        Returns:
            IPA transcription with all rules applied
        """
        # Tokenize input text
        tokens = re.findall(r"\b\w+'\w+\b|\b\w+\b|[.,!?;:'-]", text) or []
        
        # Process words into IPA
        transcribed_words = self.process_word_list(tokens, accent, use_weak)
        
        # Apply post-processing
        result = self.apply_post_processing(transcribed_words, tokens, accent, ignore_stress)
        
        return result
    
    # Configuration methods for customization
    
    def add_phonetic_rule(self, rule, position: int = -1):
        """Add a new phonetic rule to the weak form processor"""
        self.weak_form_processor.add_rule(rule, position)
    
    def remove_phonetic_rule(self, rule_class):
        """Remove a phonetic rule from the weak form processor"""
        self.weak_form_processor.remove_rule(rule_class)
    
    def add_transformer(self, transformer):
        """Add a new transformer to the pipeline"""
        self.pipeline.add_transformer(transformer)
    
    def remove_transformer(self, transformer_class):
        """Remove a transformer from the pipeline"""
        self.pipeline.remove_transformer(transformer_class)
    
    def get_database_stats(self):
        """Get database statistics"""
        return {
            'total_words': self.db_service.get_word_count(),
            'database_path': self.db_service.db_path
        }


def create_transcription_service(db_path: str = None) -> ModularIPATranscriptionService:
    """
    Factory function to create modular transcription service
    
    Args:
        db_path: Path to SQLite database (optional, will use config if not provided)
        
    Returns:
        Configured ModularIPATranscriptionService instance
    """
    if db_path is None:
        # Try to import config for database path
        try:
            from config import config
            db_path = config.DATABASE_PATH
        except ImportError:
            # Fallback to default path relative to this file
            current_dir = os.path.dirname(__file__)
            db_path = os.path.join(current_dir, 'ipa_en.sqlite')
    
    return ModularIPATranscriptionService(db_path)
