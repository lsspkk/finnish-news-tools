import os
import time
import requests
import logging
from typing import List

logger = logging.getLogger(__name__)


class AzureTranslatorWrapper:
    def __init__(self, source_lang: str, target_lang: str):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.subscription_key = os.getenv('AZURE_TRANSLATOR_KEY')
        self.endpoint = os.getenv('AZURE_TRANSLATOR_ENDPOINT', 'https://api.cognitive.microsofttranslator.com/')
        self.region = os.getenv('AZURE_TRANSLATOR_REGION', 'westeurope')
        self.timeout = int(os.getenv('AZURE_TRANSLATOR_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('AZURE_TRANSLATOR_MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('AZURE_TRANSLATOR_RETRY_DELAY', '2'))
        
        if not self.endpoint.endswith('/'):
            self.endpoint = self.endpoint + '/'
        self.api_url = f"{self.endpoint}translate"
        
        if not self.subscription_key:
            raise ValueError("AZURE_TRANSLATOR_KEY environment variable not set")
        
        logger.info(f"Initialized AzureTranslatorWrapper: {source_lang} -> {target_lang}")
    
    def _get_headers(self) -> dict:
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        if self.region:
            headers['Ocp-Apim-Subscription-Region'] = self.region
        return headers
    
    def translate(self, text: str) -> str:
        if not text or not text.strip():
            return text
        
        params = {
            'api-version': '3.0',
            'from': self.source_lang,
            'to': self.target_lang
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
                        logger.warning(f"Unexpected response format: {result}")
                        return text
                elif response.status_code == 429:
                    wait_time = self.retry_delay * (attempt + 1) * 2
                    logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                elif response.status_code == 401:
                    logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                    return text
                elif response.status_code >= 500:
                    logger.warning(f"Server error {response.status_code}. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error(f"Translation failed: {response.status_code} - {response.text}")
                    return text
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout. Attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error("Max retries reached. Returning original text.")
                    return text
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}. Attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    logger.error("Max retries reached. Returning original text.")
                    return text
            
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return text
        
        logger.error("Translation failed after all retries. Returning original text.")
        return text
    
    def translate_batch(self, texts: List[str]) -> List[str]:
        return [self.translate(text) for text in texts]
