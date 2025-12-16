# Failures

So what failed when working with agents?

Perhaps what can be learned from it?

# 1 - LibreTranslate

- AI suggested LibreTranslate, but didn't list supported languages
- Assumed Finnish support, made it first provider
- Cloud needed API key, tried local server instead
- Downloaded multiple 700MB+ model files during setup
- No Finnish support—only English, Spanish, French available
- Finnish requires extra steps: download `fi-en` model from OPUS/Argos
- Agents failed to install Finnish support with a few prompts

=> Difficult setup: not easy to get working, requires lot of local resources
