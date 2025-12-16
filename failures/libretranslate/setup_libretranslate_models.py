#!/usr/bin/env python3
"""
Setup script for LibreTranslate language models.

This script helps install and update language models for LibreTranslate.
Models are stored in ~/.local/share/argos-translate/packages

Best translation file (OPUS OpenSubtitles v2024):
https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/moses/en-fi.txt.zip

Note: OPUS files need to be converted to .argosmodel format using Locomotive
(https://github.com/LibreTranslate/Locomotive) before they can be used.
"""

import subprocess
import sys
import os
import pathlib
from pathlib import Path
import argparse


def get_packages_dir():
    """Get the argos-translate packages directory."""
    home = Path.home()
    packages_dir = home / ".local" / "share" / "argos-translate" / "packages"
    return packages_dir


def check_libretranslate_installed():
    """Check if libretranslate is installed."""
    try:
        import libretranslate
        return True
    except ImportError:
        return False


def check_argostranslate_installed():
    """Check if argostranslate is installed (needed for model management)."""
    try:
        import argostranslate
        import argostranslate.package
        return True
    except ImportError:
        return False


def list_installed_models():
    """List currently installed language models."""
    try:
        import argostranslate.package
        packages_dir = get_packages_dir()
        
        if not packages_dir.exists():
            print(f"Packages directory does not exist: {packages_dir}")
            return []
        
        installed = argostranslate.package.get_installed_packages()
        return installed
    except Exception as e:
        print(f"Error listing models: {e}")
        return []


def update_models():
    """Update language models from argos-index."""
    try:
        import argostranslate.package
        print("Updating language models from argos-index...")
        argostranslate.package.update_package_index()
        print("Model index updated successfully!")
        return True
    except Exception as e:
        print(f"Error updating models: {e}")
        return False


def install_model(language_pair):
    """
    Install a specific language pair model.
    
    Args:
        language_pair: Language pair code (e.g., 'fi-en', 'en-fi')
    """
    try:
        import argostranslate.package
        print(f"Installing model for language pair: {language_pair}")
        
        # Parse language pair (e.g., 'fi-en' -> from_code='fi', to_code='en')
        if '-' in language_pair:
            from_code, to_code = language_pair.split('-', 1)
        else:
            print(f"Invalid language pair format. Use format like 'fi-en' or 'en-fi'")
            return False
        
        # Update index first
        argostranslate.package.update_package_index()
        
        # Get available packages
        available_packages = argostranslate.package.get_available_packages()
        
        # Find matching package
        matching = [pkg for pkg in available_packages 
                   if pkg.from_code == from_code and pkg.to_code == to_code]
        
        if not matching:
            print(f"No model found for language pair: {from_code} -> {to_code}")
            print("\nAvailable language pairs (first 20):")
            for pkg in available_packages[:20]:
                print(f"  - {pkg.from_code} -> {pkg.to_code}: {pkg}")
            return False
        
        # Install the first matching package
        package_to_install = matching[0]
        print(f"Installing: {package_to_install.from_code} -> {package_to_install.to_code} ({package_to_install})")
        argostranslate.package.install_from_path(package_to_install.download())
        print(f"Successfully installed: {package_to_install.from_code} -> {package_to_install.to_code}")
        return True
        
    except Exception as e:
        print(f"Error installing model: {e}")
        import traceback
        traceback.print_exc()
        return False


def install_model_from_file(model_path):
    """
    Install a model from a local .argosmodel file.
    
    Args:
        model_path: Path to .argosmodel file
    """
    try:
        import argostranslate.package
        model_file = Path(model_path)
        
        if not model_file.exists():
            print(f"Model file not found: {model_path}")
            return False
        
        if not model_file.suffix == '.argosmodel':
            print(f"Warning: File does not have .argosmodel extension: {model_path}")
        
        print(f"Installing model from: {model_path}")
        argostranslate.package.install_from_path(str(model_file))
        print("Model installed successfully!")
        return True
        
    except Exception as e:
        print(f"Error installing model from file: {e}")
        return False


def docker_update_models(container_name="libretranslate"):
    """Update models in a running Docker container."""
    print(f"Updating models in Docker container: {container_name}")
    try:
        result = subprocess.run(
            ["docker", "exec", "-it", container_name, 
             "./venv/bin/python", "scripts/install_models.py", "--update"],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("Models updated in Docker container!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error updating Docker models: {e}")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Docker command not found. Make sure Docker is installed.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Setup and manage LibreTranslate language models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List installed models
  python setup_libretranslate_models.py --list

  # Update model index
  python setup_libretranslate_models.py --update

  # Install a specific language pair
  python setup_libretranslate_models.py --install fi-en

  # Install from local .argosmodel file
  python setup_libretranslate_models.py --install-file model.argosmodel

  # Update models in Docker container
  python setup_libretranslate_models.py --docker-update

Best OPUS translation file:
  https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/moses/en-fi.txt.zip

Note: OPUS files need to be converted to .argosmodel format using Locomotive:
  https://github.com/LibreTranslate/Locomotive
        """
    )
    
    parser.add_argument("--list", action="store_true",
                       help="List installed language models")
    parser.add_argument("--update", action="store_true",
                       help="Update model index from argos-index")
    parser.add_argument("--install", type=str, metavar="LANG_PAIR",
                       help="Install a language pair model (e.g., 'fi-en')")
    parser.add_argument("--install-file", type=str, metavar="PATH",
                       help="Install a model from local .argosmodel file")
    parser.add_argument("--docker-update", action="store_true",
                       help="Update models in Docker container")
    parser.add_argument("--docker-container", type=str, default="libretranslate",
                       help="Docker container name (default: libretranslate)")
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    # Check dependencies
    if not check_argostranslate_installed():
        print("Error: argostranslate package not found.")
        print("Install it with: pip install argostranslate")
        sys.exit(1)
    
    # Execute requested action
    if args.list:
        print("Installed language models:")
        print("=" * 60)
        models = list_installed_models()
        if models:
            for model in models:
                # Try to get code or from_code/to_code
                if hasattr(model, 'code'):
                    print(f"  - {model.code}: {model}")
                elif hasattr(model, 'from_code') and hasattr(model, 'to_code'):
                    print(f"  - {model.from_code} -> {model.to_code}: {model}")
                else:
                    print(f"  - {model}")
        else:
            print("  No models installed.")
        print(f"\nModels directory: {get_packages_dir()}")
        
    elif args.update:
        update_models()
        
    elif args.install:
        install_model(args.install)
        
    elif args.install_file:
        install_model_from_file(args.install_file)
        
    elif args.docker_update:
        docker_update_models(args.docker_container)
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
