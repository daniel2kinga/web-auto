import os
import time
from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Configurar el driver de Selenium (Chrome)
def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Para entornos como Railway
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Ruta para conectar y obtener la página de inicio de sesión sin loguear
@app.route('/conectar', methods=['GET'])
def conectar():
    url = "https://bff.cloud.myitero.com/login"
    driver = configurar_driver()
    driver.get(url)
    
    titulo_pagina = driver.title  # Obtener el título de la página como ejemplo de conexión
    driver.quit()

    return jsonify({"message": "Conectado a la página", "titulo_pagina": titulo_pagina})

# Configuración del servidor para entornos como Railway o Heroku
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
