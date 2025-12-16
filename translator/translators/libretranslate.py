"""LibreTranslate translator implementation."""
import time
import requests
from typing import List
from .base import BaseTranslator


class LibreTranslateTranslator(BaseTranslator):
    """LibreTranslate API translator."""
    
    def __init__(self, source_lang: str, target_langs: List[str], **kwargs):
        """
        Initialize LibreTranslate translator.
        
        Args:
            source_lang: Source language code
            target_langs: List of target language codes
            **kwargs: Additional configuration (api_url, api_key, timeout, max_retries)
        """
        super().__init__(source_lang, target_langs, **kwargs)
        self.api_url = kwargs.get('api_url', 'https://libretranslate.com/translate')
        self.api_key = kwargs.get('api_key', None)
        self.timeout = kwargs.get('timeout', 30)
        self.max_retries = kwargs.get('max_retries', 3)
        self.retry_delay = kwargs.get('retry_delay', 2)
    
    def translate(self, text: str, target_lang: str) -> str:
        """
        Translate text using LibreTranslate API.
        
        Args:
            text: Text to translate
            target_lang: Target language code
            
        Returns:
            Translated text
            
        Raises:
            Exception: If translation fails after retries
        """
        if not text or not text.strip():
            return text
        
        payload = {
            'q': text,
            'source': self.source_lang,
            'target': target_lang,
            'format': 'text'
        }
        
        if self.api_key:
            payload['api_key'] = self.api_key
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('translatedText', text)
                elif response.status_code == 429:
                    # Rate limiting - wait longer before retry
                    wait_time = self.retry_delay * (attempt + 1) * 2
                    print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code >= 500:
                    # Server error - retry
                    print(f"Server error {response.status_code}. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    # Client error - don't retry
                    error_msg = f"Translation failed: {response.status_code} - {response.text}"
                    print(f"Error: {error_msg}")
                    return text  # Return original text on error
                    
            except requests.exceptions.Timeout:
                print(f"Request timeout. Attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print("Max retries reached. Returning original text.")
                    return text
                    
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}. Attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    print("Max retries reached. Returning original text.")
                    return text
            
            except Exception as e:
                print(f"Unexpected error: {e}")
                return text
        
        # If we exhausted all retries
        print("Translation failed after all retries. Returning original text.")
        return text
