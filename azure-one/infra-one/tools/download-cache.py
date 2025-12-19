#!/usr/bin/env python3
"""
DEVOPS
Download all cache data from Azure Blob Storage to local folder
Run from infra-one folder
"""

import subprocess
import sys
import os
import json
from pathlib import Path

def load_config():
    """Load configuration from env files"""
    script_dir = Path(__file__).parent.parent
    
    # Load resource names
    resource_names = {}
    env_file = script_dir / "resource-names.env"
    if not env_file.exists():
        print(f"Error: {env_file} not found")
        sys.exit(1)
    
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                resource_names[key.strip()] = value.strip()
    
    # Load Azure settings
    azure_settings = {}
    settings_file = script_dir / "azure.settings.env"
    if settings_file.exists():
        with open(settings_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    azure_settings[key.strip()] = value.strip()
    
    return resource_names, azure_settings

def get_connection_string(storage_account_name, resource_group):
    """Get storage account connection string"""
    cmd = [
        "az", "storage", "account", "show-connection-string",
        "--name", storage_account_name,
        "--resource-group", resource_group,
        "--query", "connectionString",
        "--output", "tsv"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting connection string: {e.stderr}")
        sys.exit(1)

def download_blobs(connection_string, container_name, cache_dir, pattern="cache/*"):
    """Download blobs from Azure Storage"""
    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "az", "storage", "blob", "download-batch",
        "--source", container_name,
        "--destination", str(cache_path),
        "--pattern", pattern,
        "--connection-string", connection_string,
        "--output", "table"
    ]
    
    print(f"Downloading blobs matching pattern: {pattern}")
    print(f"Destination: {cache_dir}")
    print("")
    
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading blobs: {e}")
        return False

def list_downloaded_files(cache_dir):
    """List downloaded files"""
    cache_path = Path(cache_dir)
    if not cache_path.exists():
        return []
    
    files = []
    for file_path in cache_path.rglob("*.json"):
        files.append(str(file_path.relative_to(cache_path)))
    
    return sorted(files)

def main():
    resource_names, azure_settings = load_config()
    
    storage_account_name = resource_names.get('STORAGE_ACCOUNT_NAME')
    resource_group = resource_names.get('RESOURCE_GROUP')
    container_name = resource_names.get('STORAGE_CONTAINER') or azure_settings.get('STORAGE_CONTAINER', 'fnt-news-tools')
    
    if not storage_account_name or not resource_group:
        print("Error: STORAGE_ACCOUNT_NAME and RESOURCE_GROUP must be set in resource-names.env")
        sys.exit(1)
    
    # Local cache directory (in .gitignore)
    script_dir = Path(__file__).parent.parent
    cache_dir = script_dir.parent / "local-dev" / "cache-download"
    
    print("Downloading cache from Azure Blob Storage")
    print("=" * 50)
    print(f"Storage Account: {storage_account_name}")
    print(f"Container: {container_name}")
    print(f"Local directory: {cache_dir}")
    print("")
    
    # Get connection string
    print("Getting storage connection string...")
    connection_string = get_connection_string(storage_account_name, resource_group)
    
    # Download cache files
    if download_blobs(connection_string, container_name, str(cache_dir)):
        print("")
        print("Download complete!")
        print("")
        
        # List downloaded files
        files = list_downloaded_files(cache_dir)
        if files:
            print(f"Downloaded {len(files)} files:")
            for file in files[:20]:  # Show first 20
                print(f"  {file}")
            if len(files) > 20:
                print(f"  ... and {len(files) - 20} more")
            print("")
        
        # Show example command
        if files:
            example_file = files[0]
            print(f"To view a file:")
            print(f"  cat {cache_dir}/{example_file} | jq .")
            print("")
            print(f"To view the article from your POST request:")
            print(f"  cat {cache_dir}/cache/yle/articles/74-20200693_fi.json | jq .")
    else:
        print("Download failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()

