"""Azure Translator implementation."""
import time
import requests
from typing import List
from .base import BaseTranslator


class AzureTranslator(BaseTranslator):
    """Azure Translator API translator."""
    
    def __init__(self, source_lang: str, target_langs: List[str], **kwargs):
        """
        Initialize Azure Translator.
        
        Args:
            source_lang: Source language code
            target_langs: List of target language codes
            **kwargs: Additional configuration (subscription_key, endpoint, region, timeout, max_retries)
        """
        super().__init__(source_lang, target_langs, **kwargs)
        self.subscription_key = kwargs.get('subscription_key', None)
        self.endpoint = kwargs.get('endpoint', 'https://api.cognitive.microsofttranslator.com/')
        self.region = kwargs.get('region', None)
        self.timeout = kwargs.get('timeout', 30)
        self.max_retries = kwargs.get('max_retries', 3)
        self.retry_delay = kwargs.get('retry_delay', 2)
        
        # Azure Translator API endpoint
        if not self.endpoint.endswith('/'):
            self.endpoint = self.endpoint + '/'
        self.api_url = f"{self.endpoint}translate"
        
        if not self.subscription_key:
            raise ValueError("Azure Translator requires subscription_key")
    
    def _get_headers(self) -> dict:
        """Get request headers for Azure Translator API."""
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        if self.region:
            headers['Ocp-Apim-Subscription-Region'] = self.region
        return headers
    
    def _normalize_language_code(self, lang_code: str) -> str:
        """
        Normalize language code for Azure Translator.
        
        Azure uses specific language codes (e.g., zh-Hans instead of zh).
        This method handles common mappings.
        """
        # Common language code mappings
        mappings = {
            'zh': 'zh-Hans',  # Default Chinese to Simplified
        }
        return mappings.get(lang_code, lang_code)
    
    def translate(self, text: str, target_lang: str) -> str:
        """
        Translate text using Azure Translator API.
        
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
        
        # Normalize language codes
        source_lang = self._normalize_language_code(self.source_lang)
        target_lang = self._normalize_language_code(target_lang)
        
        # Azure Translator API v3.0 format
        params = {
            'api-version': '3.0',
            'from': source_lang,
            'to': target_lang
        }
        
        body = [{'text': text}]
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    params=params,
                    json=body,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result and len(result) > 0 and 'translations' in result[0]:
                        return result[0]['translations'][0]['text']
                    else:
                        print(f"Unexpected response format: {result}")
                        return text
                elif response.status_code == 429:
                    # Rate limiting - wait longer before retry
                    wait_time = self.retry_delay * (attempt + 1) * 2
                    print(f"Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 401:
                    # Authentication error - don't retry
                    error_msg = f"Authentication failed: {response.status_code} - {response.text}"
                    print(f"Error: {error_msg}")
                    return text
                elif response.status_code >= 500:
                    # Server error - retry
                    print(f"Server error {response.status_code}. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    # Client error - don't retry
                    error_msg = f"Translation failed: {response.status_code} - {response.text}"
                    print(f"Error: {error_msg}")
                    return text
                    
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
