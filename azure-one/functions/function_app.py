# DEVOPS
# Main Function App file for Python v2 programming model
# Imports all functions from their respective modules

# Import shared app instance first
from shared.app import app

# Import all functions - they will register themselves with the app instance
from authenticate import authenticate
from rss_feed_parser import rss_feed_parser
from article_scraper import article_scraper
from translate_article import translate_article
from query_rate_limits import query_rate_limits
from translator_quota import translator_quota

