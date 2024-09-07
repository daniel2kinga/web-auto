#!/bin/bash

# Descargar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Instalar Chrome
apt-get install -y ./google-chrome-stable_current_amd64.deb

# Descargar ChromeDriver
CHROME_VERSION=$(google-chrome --version | grep -oP '\d{2,3}')
DRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION")
wget https://chromedriver.storage.googleapis.com/$DRIVER_VERSION/chromedriver_linux64.zip

# Extraer ChromeDriver
unzip chromedriver_linux64.zip
chmod +x chromedriver
mv chromedriver /usr/local/bin/
