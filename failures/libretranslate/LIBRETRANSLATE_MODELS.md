# LibreTranslate Language Models Setup

This guide explains how to set up and manage language models for LibreTranslate.

## Best Translation File

The best translation file from OPUS (OpenSubtitles v2024, 59M+ sentences):
```
https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/moses/en-fi.txt.zip
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs both `libretranslate` and `argostranslate` (needed for model management).

### 2. List Installed Models

```bash
python setup_libretranslate_models.py --list
```

### 3. Update Model Index

Update the list of available models from argos-index:

```bash
python setup_libretranslate_models.py --update
```

### 4. Install Language Pair Models

Install models for specific language pairs (e.g., Finnish-English):

```bash
# Install Finnish to English
python setup_libretranslate_models.py --install fi-en

# Install English to Finnish
python setup_libretranslate_models.py --install en-fi

# Install English to Swedish
python setup_libretranslate_models.py --install en-sv
```

## Model Storage Location

Models are stored in:
- Linux/Mac: `~/.local/share/argos-translate/packages`
- Windows: `%userprofile%\.local\share\argos-translate\packages`

## Docker Setup

If you're running LibreTranslate in Docker, update models inside the container:

```bash
# Update models in default container
python setup_libretranslate_models.py --docker-update

# Or specify container name
python setup_libretranslate_models.py --docker-update --docker-container my-libretranslate
```

Alternatively, you can run the command directly:

```bash
docker exec -it libretranslate ./venv/bin/python scripts/install_models.py --update
```

## Installing Custom Models

### From OPUS Files

OPUS translation files (like the OpenSubtitles file above) need to be converted to `.argosmodel` format before use. This requires the Locomotive toolkit:

1. Install Locomotive:
       git clone https://github.com/LibreTranslate/Locomotive.git
       cd Locomotive
       pip install -r requirements.txt

2. Convert OPUS files to .argosmodel:
   Follow the Locomotive documentation to train/convert your OPUS data.

3. Install the converted model:
       python setup_libretranslate_models.py --install-file /path/to/model.argosmodel

### From Local .argosmodel File

If you already have a `.argosmodel` file:

```bash
python setup_libretranslate_models.py --install-file /path/to/your_model.argosmodel
```

## Available Language Pairs

To see all available language pairs from argos-index:

```bash
python setup_libretranslate_models.py --update
python setup_libretranslate_models.py --list
```

Common language codes:
- `fi` - Finnish
- `en` - English
- `sv` - Swedish
- `de` - German
- `fr` - French
- `es` - Spanish

## Troubleshooting

### Models Not Loading

1. Check if models are installed:
       python setup_libretranslate_models.py --list

2. Verify the packages directory exists:
       ls ~/.local/share/argos-translate/packages

3. Update the model index:
       python setup_libretranslate_models.py --update

### Docker Issues

If Docker commands fail:
- Make sure the container is running: `docker ps`
- Check container name: `docker ps --format "{{.Names}}"`
- Ensure you have permissions to execute commands in the container

### Missing argostranslate Package

If you get an error about `argostranslate` not being found:

```bash
pip install argostranslate
```

## Notes

- Models are downloaded automatically when you install a language pair
- Model files can be large (hundreds of MB to several GB)
- First-time installation may take a while depending on your internet connection
- LibreTranslate loads models from the packages directory on startup
- Some models on libretranslate.com may not be in argos-index yet (they're deployed separately)

## References

- [LibreTranslate GitHub](https://github.com/LibreTranslate/LibreTranslate)
- [Argos Translate](https://github.com/argosopentech/argos-translate)
- [Locomotive (OPUS to Argos conversion)](https://github.com/LibreTranslate/Locomotive)
- [OPUS OpenSubtitles v2024](https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/moses/en-fi.txt.zip)
