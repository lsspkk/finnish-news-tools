# Failures - wasted time

So what failed when working with agents?

Each role makes a mess, at least with Composer LLM.
It just sidetracks and does not ask if the plan was good, or realize that it was bad.

Designer does too vague plans, failing to decide for example if cache should be on frontend or not.

Agents fail  follow rules about security from instructions.
Even if I tell them at the start of each chat.

The devops agent uses old azure info, and creates functions that do not work.
Also it makes some assumptions of services that do not work, for example
the authentication and static site. Agent also improvised creating some
permissions without following the rules, that all azure changes should be
done in scripts that can be reviewed before run.

The structure of azure setup scripts and deployment is total chaos,
but has clear instructions and makes nice logs. (with secure data in them :)


Perhaps what can be learned from it?

You absolutely must know the limits of LLM that you use.
Even prompt engineering and roles, and being clear in chats wont help.
Mistakes will happen in every front.

You must be the developer and architect and split the task into small
subtasks. For each Azure service, before using: study it yourself,
before implementing, ask for websearch for newest SDK:s and best practices.

The agents wont help you.
If you know the software development lifecycle.
If you know architecture, design, development, testing, and devops yourself.
You can get some stuff working, perhaps somewhat faster then normally.

You must learn and identify where LLM shines, and where it fails.
You must get used into working in proper steps.



# 1 - LibreTranslate - 1 hr

- AI suggested LibreTranslate, but didn't list supported languages
- Assumed Finnish support, made it first provider
- Cloud needed API key, tried local server instead
- Downloaded multiple 700MB+ model files during setup
- No Finnish support—only English, Spanish, French available
- Finnish requires extra steps: download `fi-en` model from OPUS/Argos
- Agents failed to install Finnish support with a few prompts

=> Difficult setup: not easy to get working, requires lot of local resources


# 2 - Deployment - 4 hr

- AI just went for python functions v1
- And could not refactor to v2 without lot of help
- The scripts created were very confusing, too many, too little checks, not enough logging.
- Documentation was so verbose, and split into too many files.
- The local/private setup for authentication was not deployed at all.
- The custom token auth was treated in static site as if it was supported
  standard token auth, causing unauthorized access after successful login.
- The backend code expected different env variables for the connection string:
  - Blob storage: AZURE_STORAGE_CONNECTION_STRING
  - Table storage: AZURE_STORAGE_TABLE_CONNECTION_STRING
  - Azure Functions standard: AzureWebJobsStorage (used for both)
- The API response of an article did not respond with text, but metadat only.
- The translation of article API responded with finnish text.
  - Frontend called /article-scraper endpoint when checking if translation exists
  - /article-scraper is for scraping articles, not translations
  - Should call /translate-article endpoint which handles cache checking internally
  - Bug in article.html: checkArticleExists() calls fetchArticle() which uses wrong endpoint
- Passwords and other security info placed in main documentation,
  even if the context info has rule about it:
  - All security related information must be stored into azure-one/infra-one/security/folder. 
    No file outside of this folder contains any security details than this:
    - username and password authentication returns token
    - valid token is required for all API calls"

# 3 - Tranlator quota - 1 hr
- Running function app locally did not work, even with valid token
  - Did not install dependencies in function app venv 
  - Used deprecated Azure Monitor API that was removed in version 2.0.0
- Did not create backend cache for the quota even though it was in the plan
- Chose wrong translation library again, then replaced with supported one

# 4 - Publish to Git - 2 hr
- Security info was about to be published to Git despite instructions:
  - resource names, passwords, comments about what password to use etc.
- Reviewed code changes and fixed like 30 files before committing