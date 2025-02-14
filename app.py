import os
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway
    chrome_options.add_argument("--disable-cache")  # Desactivar caché
    chrome_options.add_argument("--headless")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver, url):
    # Navegar a la URL
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")
    
    # Forzar la recarga de la página (si es necesario)
    driver.refresh()
    
    # Esperar a que aparezca al menos un <p> en la página
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "p")))
    
    # Obtener y registrar el HTML de la página (opcional para depuración)
    html_final = driver.page_source
    app.logger.info(f"Contenido HTML (primeros 1000 caracteres):\n{html_final[:1000]}...")
    
    return html_final

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        app.logger.info(f"Extrayendo contenido de la URL: {url}")
        
        driver = configurar_driver()
        interactuar_con_pagina(driver, url)
        
        # Intentar extraer el texto de los elementos <p>, reintentando si se produce un error de stale element
        retries = 3
        texto_extraido = ""
        while retries:
            try:
                elementos = driver.find_elements(By.TAG_NAME, "p")
                texto_extraido = " ".join([element.text for element in elementos])
                break  # Salir del bucle si todo funciona
            except StaleElementReferenceException:
                app.logger.error("StaleElementReferenceException detectada. Reintentando...")
                retries -= 1
                time.sleep(1)
        
        if not texto_extraido:
            raise Exception("No se pudieron obtener correctamente los elementos <p>.")

        app.logger.info(f"Texto extraído: {texto_extraido}")

        driver.quit()
        return jsonify({"url": url, "contenido": texto_extraido})

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
