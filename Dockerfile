# Utilizar una imagen base de Python
FROM python:3.9-slim

# Establecer la variable de entorno PYTHONUNBUFFERED
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema necesarias para Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libnss3 \
    libxshmfence1 \
    libglu1-mesa \
    libxi6 \
    libgconf-2-4 \
    libpango1.0-0 \
    libpangocairo-1.0-0 \
    libxcb-dri3-0 \
    && rm -rf /var/lib/apt/lists/*

# Descargar e instalar Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable

# Crear directorio de la aplicación
WORKDIR /app

# Copiar archivos de la aplicación
COPY . /app

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto
EXPOSE 5000

# Comando para ejecutar la aplicación con Gunicorn
CMD ["gunicorn", "--workers=1", "--timeout=120", "-b", "0.0.0.0:5000", "app:app"]
