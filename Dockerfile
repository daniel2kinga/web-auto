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
    xdg-utils

# Instalar Google Chrome versión estable
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -fy install

# Configurar la variable de entorno para Chrome en modo headless
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PATH=$PATH:/usr/local/bin/

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

