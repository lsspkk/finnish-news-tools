"""Translator module for handling different translation providers."""
from .base import BaseTranslator
from .libretranslate import LibreTranslateTranslator
from .azure import AzureTranslator

__all__ = ['BaseTranslator', 'LibreTranslateTranslator', 'AzureTranslator']
