FROM python:3.11-slim-buster

# Establecer la variable de entorno para no interactuar con los comandos apt
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias para Playwright
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        libnss3 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libgbm1 \
        libasound2 \
        libxshmfence1 \
        fonts-liberation \
        libssl-dev \
        libglib2.0-0 \
        libx11-xcb1 \
        libxcb1 \
        libx11-6 \
        && rm -rf /var/lib/apt/lists/*

# Copiar y instalar las dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar navegadores de Playwright
RUN playwright install --with-deps

# Copiar el resto de los archivos de la aplicación
COPY . /app
WORKDIR /app

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "app.py"]
