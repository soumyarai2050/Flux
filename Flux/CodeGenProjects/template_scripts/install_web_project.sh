#!/bin/bash
set -e

# we are in scripts folder
# This script installs web-ui dependencies and creates production build

DEFAULT_UI_PORT="3000"

cd ..
PROJECT_NAME=${PWD##*/}
PROJECT_NAME=${PROJECT_NAME:-/}
cd - > /dev/null

# Read configuration from data/config.yaml
if [ -f "../data/config.yaml" ]; then
    SERVER_HOST=$(grep "server_host:" ../data/config.yaml | awk '{print $2}' | tr -d '"' | tr -d "'")
    SERVER_PORT=$(grep "main_server_beanie_port:" ../data/config.yaml | awk '{print $2}' | tr -d '"' | tr -d "'")
    DEFAULT_UI_PORT=$(grep "ui_port:" ../data/config.yaml | awk '{print $2}' | tr -d '"' | tr -d "'")
    if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_PORT" ]; then
        echo "ERROR: Could not read server_host or main_server_beanie_port from ../data/config.yaml"
        exit 1
    fi
else
    echo "ERROR: Configuration file ../data/config.yaml not found"
    exit 1
fi

install_and_build() {
    if [ ! -d "../web-ui" ]; then
        echo "ERROR: web-ui directory not found. Run build_web_project.sh first."
        exit 1
    fi

    cd ../web-ui

    echo "Replacing UI_PORT: $DEFAULT_UI_PORT with $SERVER_PORT/static in src/config.js"
    if [ -f "src/config.js" ]; then
        sed -i "s/$DEFAULT_UI_PORT/$SERVER_PORT\/static/g" src/config.js
    else
        echo "WARNING: src/config.js not found, skipping configuration update"
    fi

    echo "Installing npm packages..."
    npm install

    echo "Creating production build distribution..."
    export PUBLIC_URL="http://$SERVER_HOST:$SERVER_PORT/static"
    npm run build

    echo "Restoring UI_PORT in src/config.js"
    if [ -f "src/config.js" ]; then
        sed -i "s/$SERVER_PORT\/static/$DEFAULT_UI_PORT/g" src/config.js
    fi

    cd - > /dev/null
}

store_production_build() {
    cd ../web-ui
    if [ ! -d "build" ]; then
        echo "ERROR: Build directory not found. npm run build may have failed."
        exit 1
    fi
    cd - > /dev/null

    echo "Storing production build in scripts directory..."
    rm -rf "${SERVER_HOST}"
    mkdir -p "${SERVER_HOST}"/{static,templates}
    cp -pr ../web-ui/build/* "${SERVER_HOST}"/static/.
    mv "${SERVER_HOST}"/static/index.html "${SERVER_HOST}"/templates/.

    echo "Production build successfully stored in static/ and templates/ directories"
}

install_and_build
store_production_build

echo "Installation complete for project: $PROJECT_NAME"
echo "FastAPI server can now serve the static build from http://$SERVER_HOST:$SERVER_PORT/$PROJECT_NAME"
