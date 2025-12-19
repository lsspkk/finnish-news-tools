# DEVOPS
# Installation Guide

## Azure CLI

Install on Ubuntu:

    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

Verify:

    az --version

Login:

    az login

## Azure Functions Core Tools

Install Node.js and npm:

    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs

Install Azure Functions Core Tools v4:

    npm install -g azure-functions-core-tools@4 --unsafe-perm true

Verify:

    func --version

Should output: 4.x.x

## Python 3.11

Install on Ubuntu:

    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3-pip

Verify:

    python3.11 --version

## Git

Install on Ubuntu:

    sudo apt install -y git

Verify:

    git --version
