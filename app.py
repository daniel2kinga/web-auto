import os
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

app = Flask(__name__)

# Función para configurar Selenium con Chrome en modo headless
def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway
    
    # No se necesita 'executable_path' en Selenium 4.x
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Ruta para extraer contenido de una página web
@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']

        driver = configurar_driver()
        driver.get(url)
        time.sleep(5)  # Esperar a que cargue la página

        # Extraer contenido de la página
        contenido = driver.find_elements_by_tag_name("p")
        texto_extraido = " ".join([element.text for element in contenido])

        driver.quit()
        return jsonify({"url": url, "contenido": texto_extraido})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Usa el puerto de la variable de entorno 'PORT' o 5000 por defecto
    app.run(host='0.0.0.0', port=port)
