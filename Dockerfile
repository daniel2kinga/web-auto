# Usa una imagen oficial de Python como base
FROM python:3.11-slim

# Instalar dependencias necesarias
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
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
    xdg-utils \
    firefox-esr

# Instalar geckodriver para Firefox
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.32.0/geckodriver-v0.32.0-linux64.tar.gz \
    && tar -xvzf geckodriver-v0.32.0-linux64.tar.gz \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.32.0-linux64.tar.gz

# Crear un directorio de trabajo
WORKDIR /app

# Copiar los archivos del proyecto al contenedor
COPY . /app

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto en el que correrá la aplicación Flask
EXPOSE 5000

# Ejecutar la aplicación con Gunicorn
CMD exec gunicorn -w 4 -b :${PORT} app:app
