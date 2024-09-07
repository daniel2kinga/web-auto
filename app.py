from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

app = Flask(__name__)

# Ruta para la raíz '/'
@app.route('/')
def home():
    return "Bienvenido a mi API. Usa la ruta /extraer para extraer contenido web."

# Configurar Selenium para Chrome en modo headless
def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Ruta para extraer contenido de una página web
@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    data = request.json
    url = data.get('url')
    if not url:
        return jsonify({"error": "No se proporcionó URL"}), 400

    driver = configurar_driver()
    driver.get(url)
    time.sleep(5)

    contenido = driver.find_elements_by_tag_name("p")
    texto_extraido = " ".join([element.text for element in contenido])

    driver.quit()

    return jsonify({"url": url, "contenido": texto_extraido})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
