FROM python:3.11-slim

# Instalar dependencias
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    xvfb \
    libxi6 \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libappindicator1 \
    libindicator7 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxtst6 \
    fonts-liberation \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libnspr4 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libwayland-client0 \
    libxkbcommon0 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Instalar Google Chrome
RUN wget -O /tmp/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y /tmp/chrome.deb \
    && rm /tmp/chrome.deb

# Instalar requerimientos de Python
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copiar el código de la aplicación
COPY . /app
WORKDIR /app

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["python", "app.py"]
