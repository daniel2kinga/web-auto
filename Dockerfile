# Imagen base
FROM python:3.9-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    bzip2 \
    && rm -rf /var/lib/apt/lists/*

# Instalar GeckoDriver
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.31.0/geckodriver-v0.31.0-linux64.tar.gz \
    && tar -xzf geckodriver-v0.31.0-linux64.tar.gz -C /usr/local/bin \
    && rm geckodriver-v0.31.0-linux64.tar.gz

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar archivos de la aplicación
COPY . /app

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto
EXPOSE 5000

# Comando para iniciar la aplicación
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
