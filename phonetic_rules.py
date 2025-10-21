"""
Phonetic Rules Module
Contains all phonetic rules for weak forms, strong forms, and contextual analysis.
"""
import re
from typing import List, Dict
from abc import ABC, abstractmethod


class PhoneticRule(ABC):
    """Abstract base class for phonetic rules"""
    
    @abstractmethod
    def applies_to(self, word: str, context: Dict) -> bool:
        """Check if this rule applies to the given word and context"""
        pass
    
    @abstractmethod
    def apply(self, word: str, context: Dict) -> bool:
        """Apply the rule and return result"""
        pass


class ContractionRule(PhoneticRule):
    """Rule for contractions (already in weak form)"""
    
    def applies_to(self, word: str, context: Dict) -> bool:
        return "'" in word
    
    def apply(self, word: str, context: Dict) -> bool:
        return False  # Don't apply weak form (already contracted)


class TheVariationRule(PhoneticRule):
    """Rule for 'the' allophonic variation"""
    
    def applies_to(self, word: str, context: Dict) -> bool:
        return re.sub(r"[^\w']", '', word.lower()) == 'the'
    
    def apply(self, word: str, context: Dict) -> bool:
        return False  # Handle specially in post-processing


class ThereRule(PhoneticRule):
    """Rule for 'there' - weak when followed by 'to be' verbs"""
    
    def __init__(self):
        self.be_verbs = ['is', 'are', 'was', 'were', 'will', 'would', "'s", "'re", "'ll"]
    
    def applies_to(self, word: str, context: Dict) -> bool:
        clean_word = re.sub(r"[^\w']", '', word.lower())
        return clean_word == 'there'
    
    def apply(self, word: str, context: Dict) -> bool:
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        
        # Check if followed by 'to be' verb
        if word_index < len(words) - 1:
            next_word = re.sub(r"[^\w']", '', words[word_index + 1].lower())
            if next_word in self.be_verbs:
                return True  # Use weak form before 'to be'
        
        return False  # Use strong form otherwise


class ThatRule(PhoneticRule):
    """Rule for 'that' - weak when used as logical conclusion/subordinating conjunction"""
    
    def __init__(self):
        # Words that often precede 'that' in logical conclusions
        self.conclusion_indicators = [
            'know', 'think', 'believe', 'feel', 'say', 'said', 'tell', 'told',
            'see', 'saw', 'hear', 'heard', 'understand', 'realize', 'realized',
            'assume', 'suppose', 'hope', 'wish', 'remember', 'forget', 'noticed',
            'mean', 'means', 'meant', 'show', 'shows', 'showed', 'prove', 'proves'
        ]
    
    def applies_to(self, word: str, context: Dict) -> bool:
        clean_word = re.sub(r"[^\w']", '', word.lower())
        return clean_word == 'that'
    
    def apply(self, word: str, context: Dict) -> bool:
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        
        # Check if preceded by a verb that introduces logical conclusions
        if word_index > 0:
            prev_word = re.sub(r"[^\w']", '', words[word_index - 1].lower())
            if prev_word in self.conclusion_indicators:
                return True  # Use weak form for logical conclusions
        
        # Check if it's followed by a clause (indicating subordinating conjunction)
        if word_index < len(words) - 2:
            # Look for patterns like "that he", "that she", "that it", etc.
            next_word = re.sub(r"[^\w']", '', words[word_index + 1].lower())
            if next_word in ['he', 'she', 'it', 'they', 'we', 'you', 'i']:
                return True  # Use weak form for subordinating conjunction
        
        return False  # Use strong form for demonstrative pronoun


class HaveRule(PhoneticRule):
    """Rule for 'have' - strong when main verb (possession/eating/obligation), weak when auxiliary"""
    
    def __init__(self):
        # Words that indicate 'have' is likely auxiliary (perfect tenses)
        self.past_participle_indicators = [
            'been', 'done', 'gone', 'seen', 'said', 'made', 'come', 'taken', 'given',
            'found', 'thought', 'worked', 'called', 'asked', 'looked', 'used', 'tried',
            'left', 'felt', 'kept', 'heard', 'brought', 'written', 'shown', 'moved',
            'played', 'turned', 'started', 'opened', 'closed', 'happened', 'become',
            'known', 'put', 'told', 'helped', 'changed', 'wanted', 'learned', 'lived'
        ]
        
        # Infinitive markers that indicate obligation (have to)
        self.infinitive_markers = ['to']
        
        # Direct objects that indicate possession/eating (main verb)
        self.possession_objects = [
            'a', 'an', 'the', 'my', 'your', 'his', 'her', 'our', 'their', 'some',
            'money', 'time', 'car', 'house', 'food', 'water', 'coffee', 'tea',
            'breakfast', 'lunch', 'dinner', 'problem', 'question', 'idea', 'plan'
        ]
    
    def applies_to(self, word: str, context: Dict) -> bool:
        clean_word = re.sub(r"[^\w']", '', word.lower())
        return clean_word == 'have'
    
    def apply(self, word: str, context: Dict) -> bool:
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        
        # Check if followed by 'to' (obligation: "have to do")
        if word_index < len(words) - 1:
            next_word = re.sub(r"[^\w']", '', words[word_index + 1].lower())
            if next_word == 'to':
                return False  # Strong form for obligation
        
        # Check if followed by direct object (possession/eating)
        if word_index < len(words) - 1:
            next_word = re.sub(r"[^\w']", '', words[word_index + 1].lower())
            if next_word in self.possession_objects:
                return False  # Strong form for possession/eating
        
        # Check if followed by past participle (auxiliary for perfect tenses)
        if word_index < len(words) - 1:
            next_word = re.sub(r"[^\w']", '', words[word_index + 1].lower())
            if next_word in self.past_participle_indicators:
                return True  # Weak form for auxiliary
        
        # Additional heuristics:
        # If 'have' is at the beginning of a question, likely auxiliary
        if word_index == 0 and len(words) > 2:
            # "Have you done...?" - auxiliary
            second_word = re.sub(r"[^\w']", '', words[1].lower())
            if second_word in ['you', 'we', 'they', 'i']:
                return True  # Weak form for auxiliary question
        
        # Default: assume main verb (possession/obligation) - strong form
        return False
    
    def get_weak_form(self, word: str, context: Dict) -> str:
        """Get appropriate weak form considering H-dropping rules"""
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        punct_re = context.get('punct_re')
        
        # Base weak form without H
        base_weak = 'əv'
        # Weak form with H (after pause or at start)
        h_weak = 'həv'
        
        # Rule 1: Keep H at the beginning of sentence
        if word_index == 0:
            return h_weak
        
        # Rule 2: Keep H after pause (punctuation)
        if word_index > 0 and punct_re:
            prev_token = words[word_index - 1]
            if punct_re.match(prev_token):
                return h_weak
        
        # Rule 3: Keep H after comma, period, etc. (even if not immediately before)
        # Check if there's punctuation in the previous few tokens
        for i in range(max(0, word_index - 2), word_index):
            if punct_re and punct_re.match(words[i]):
                return h_weak
        
        # Default: use H-dropped form (əv)
        return base_weak


class MustRule(PhoneticRule):
    """Rule for 'must' - complex contextual and phonetic rules"""
    
    def __init__(self):
        # Vowel sounds that trigger weak form with /t/
        self.vowel_sounds = ['æ', 'ɑ', 'ɒ', 'ɔ', 'ʊ', 'u', 'ɪ', 'i', 'e', 'ə', 'ʌ', 'ɜ', 'a', 'ɛ', 'o']
        
        # Consonant sounds that trigger t-dropping in weak form
        self.consonant_sounds = [
            'b', 'p', 'd', 't', 'g', 'k', 'f', 'v', 'θ', 'ð', 's', 'z', 'ʃ', 'ʒ', 
            'h', 'm', 'n', 'ŋ', 'l', 'r', 'w', 'ʧ', 'ʤ'
        ]
        
        # Words that indicate obligation (strong form)
        self.obligation_indicators = [
            'always', 'never', 'really', 'definitely', 'absolutely', 'certainly'
        ]
        
        # Weak forms of 'have' that trigger strong 'must'
        self.weak_have_forms = ['əv', 'həv']
    
    def applies_to(self, word: str, context: Dict) -> bool:
        clean_word = re.sub(r"[^\w']", '', word.lower())
        return clean_word == 'must'
    
    def apply(self, word: str, context: Dict) -> bool:
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        
        # Check if followed by weak form of 'have' -> Strong form
        if word_index < len(words) - 1:
            next_word = words[word_index + 1].lower()
            # This would need access to transcribed form, simplified check
            if 'have' in next_word and len(words) > word_index + 2:
                # If "must have done" pattern -> likely strong for obligation
                potential_participle = words[word_index + 2].lower()
                common_participles = ['done', 'been', 'gone', 'seen', 'said']
                if potential_participle in common_participles:
                    return False  # Strong form
        
        # Check for obligation context (preceded by strong indicators)
        if word_index > 0:
            prev_word = words[word_index - 1].lower()
            if prev_word in self.obligation_indicators:
                return False  # Strong form for emphasis
        
        # Default: use weak form (will be modified in get_weak_form)
        return True
    
    def get_weak_form(self, word: str, context: Dict) -> str:
        """Get appropriate weak form considering phonetic environment"""
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        
        # Base weak forms
        weak_with_t = 'məst'  # Before vowels and /j/
        weak_without_t = 'məs'  # Before consonants
        
        # Check what follows 'must'
        if word_index < len(words) - 1:
            next_word = words[word_index + 1]
            
            # Get first sound of next word (simplified)
            next_clean = re.sub(r"[^\w']", '', next_word.lower())
            if next_clean:
                first_char = next_clean[0]
                
                # If starts with vowel or 'y' (approximating /j/) -> keep /t/
                if first_char in 'aeiouy':
                    return weak_with_t
                
                # If starts with consonant -> drop /t/
                else:
                    return weak_without_t
        
        # Default: keep /t/
        return weak_with_t


class PositionalRule(PhoneticRule):
    """Rule for positional strong forms"""
    
    def __init__(self):
        self.weak_at_start = ['the', 'a', 'an']
        self.auxiliaries = ['is', 'are', 'was', 'were', 'have', 'has', 'had', 'do', 'does', 'did',
                           'will', 'would', 'can', 'could', 'should', 'must']
    
    def applies_to(self, word: str, context: Dict) -> bool:
        return True  # This rule always applies
    
    def apply(self, word: str, context: Dict) -> bool:
        clean_word = re.sub(r"[^\w']", '', word.lower())
        word_index = context.get('word_index', 0)
        words = context.get('words', [])
        punct_re = context.get('punct_re')
        
        # First word tends to be strong (except special cases)
        if word_index == 0:
            if clean_word not in self.weak_at_start:
                return False
        
        # Strong before pause (comma, period, etc.)
        if word_index < len(words) - 1 and punct_re and punct_re.match(words[word_index + 1] or ''):
            return False
        
        # Last word tends to be strong
        if word_index == len(words) - 1:
            return False
        
        # Auxiliaries at start of questions are strong
        if clean_word in self.auxiliaries and word_index == 0:
            return False
        
        return True  # Use weak form


class WeakFormProcessor:
    """Processor for determining weak vs strong forms"""
    
    def __init__(self):
        self.rules = [
            ContractionRule(),
            TheVariationRule(),
            ThereRule(),
            ThatRule(),
            HaveRule(),
            MustRule(),
            PositionalRule(),
        ]
        self.punct_re = re.compile(r"^[.,!?;:'-]+$")
    
    def should_use_weak(self, word: str, word_index: int, words: List[str]) -> bool:
        """
        Determine if a word should use its weak form
        
        Args:
            word: The word to analyze
            word_index: Position of word in sentence
            words: All words in the sentence
            
        Returns:
            True if weak form should be used
        """
        context = {
            'word_index': word_index,
            'words': words,
            'punct_re': self.punct_re
        }
        
        # Apply rules in order - first matching rule wins
        for rule in self.rules:
            if rule.applies_to(word, context):
                return rule.apply(word, context)
        
        # Default: use weak form in non-prominent positions
        return True
    
    def add_rule(self, rule: PhoneticRule, position: int = -1):
        """Add a new rule at specified position"""
        if position == -1:
            self.rules.append(rule)
        else:
            self.rules.insert(position, rule)
    
    def remove_rule(self, rule_class):
        """Remove a rule by class type"""
        self.rules = [rule for rule in self.rules if not isinstance(rule, rule_class)]


class WeakStrongParser:
    """Parser for weak/strong format strings"""
    
    @staticmethod
    def parse_format(ipa_text: str) -> Dict[str, str]:
        """
        Parse formato / [strong], [weak] / and return dict with forms
        
        Args:
            ipa_text: IPA text in format "/ strong, weak /" or simple format
            
        Returns:
            Dict with 'strong', 'weak' keys or 'single' key
        """
        if not ipa_text or not ipa_text.startswith('/ ') or not ipa_text.endswith(' /'):
            return {'single': ipa_text}  # Simple format
        
        # Extract content between slashes
        content = ipa_text[2:-2]  # Remove "/ " and " /"
        
        if ', ' in content:
            strong, weak = content.split(', ', 1)
            return {'strong': strong.strip(), 'weak': weak.strip()}
        else:
            return {'single': content.strip()}