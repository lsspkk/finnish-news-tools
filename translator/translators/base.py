"""Base translator interface."""
from abc import ABC, abstractmethod
from typing import Dict, List


class BaseTranslator(ABC):
    """Abstract base class for translation providers."""
    
    def __init__(self, source_lang: str, target_langs: List[str], **kwargs):
        """
        Initialize translator.
        
        Args:
            source_lang: Source language code (e.g., 'fi')
            target_langs: List of target language codes (e.g., ['en', 'sv'])
            **kwargs: Additional configuration parameters
        """
        self.source_lang = source_lang
        self.target_langs = target_langs
        self.config = kwargs
    
    @abstractmethod
    def translate(self, text: str, target_lang: str) -> str:
        """
        Translate text to target language.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            
        Returns:
            Translated text
        """
        pass
    
    def translate_batch(self, texts: List[str], target_lang: str) -> List[str]:
        """
        Translate multiple texts to target language.
        
        Args:
            texts: List of texts to translate
            target_lang: Target language code
            
        Returns:
            List of translated texts
        """
        return [self.translate(text, target_lang) for text in texts]
    
    def translate_to_all_targets(self, text: str) -> Dict[str, str]:
        """
        Translate text to all target languages.
        
        Args:
            text: Text to translate
            
        Returns:
            Dictionary mapping language codes to translations
        """
        translations = {}
        for lang in self.target_langs:
            translations[lang] = self.translate(text, lang)
        return translations
