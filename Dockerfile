# Usar una imagen base de Python
FROM python:3.9-slim

# Instalar dependencias del sistema y Firefox
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    bzip2 \
    libnss3 \
    libgtk-3-0 \
    libdbus-glib-1-2 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libpango1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    fonts-liberation \
    libappindicator3-1 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Instalar GeckoDriver
RUN GECKODRIVER_VERSION=0.31.0 \
    && wget https://github.com/mozilla/geckodriver/releases/download/v$GECKODRIVER_VERSION/geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz \
    && tar -xzf geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz -C /usr/local/bin \
    && rm geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de la aplicación
COPY . /app

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto (opcional)
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
