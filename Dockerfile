# Usa una imagen oficial de Python como base
FROM python:3.11-slim

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    apt-transport-https \
    ca-certificates \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libxss1 \
    libappindicator1 \
    xdg-utils

# Instalar Google Chrome
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

# Descargar ChromeDriver y moverlo al path correcto
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d{2,3}') \
    && DRIVER_VERSION=$(wget -qO- "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION") \
    && wget https://chromedriver.storage.googleapis.com/$DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && chmod +x chromedriver \
    && mv chromedriver /usr/local/bin/

# Configurar la variable de entorno para Chrome en modo headless
ENV PATH="/usr/local/bin/chromedriver:${PATH}"
ENV CHROME_BIN="/usr/bin/google-chrome"

# Crear un directorio de trabajo
WORKDIR /app

# Copiar los archivos del proyecto
COPY . /app

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto en el que correrá la aplicación Flask
EXPOSE 5000

# Ejecutar la aplicación
CMD ["gunicorn", "-w", "4", "app:app"]
