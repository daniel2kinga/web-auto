import os
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver):
    # Espera a que los elementos se carguen
    time.sleep(2)

    # Ejemplo 1: Buscar un botón y hacer clic (suponiendo que el botón tiene el tag <button>)
    try:
        boton = driver.find_element(By.TAG_NAME, "button")
        boton.click()  # Hacer clic en el botón
        time.sleep(2)  # Esperar después de hacer clic
    except:
        app.logger.info("No se encontró ningún botón en la página")

    # Ejemplo 2: Buscar un enlace (<a>) y seguir el enlace
    try:
        enlaces = driver.find_elements(By.TAG_NAME, "a")
        for enlace in enlaces:
            href = enlace.get_attribute("href")
            if href:
                app.logger.info(f"Siguiendo el enlace: {href}")
                driver.get(href)  # Navegar a la URL del enlace
                time.sleep(2)  # Esperar después de navegar
    except:
        app.logger.info("No se encontraron enlaces en la página")
    
    return driver.page_source  # Devolver el HTML final de la página

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        app.logger.info(f"Extrayendo contenido de la URL: {url}")
        
        driver = configurar_driver()
        driver.get(url)
        time.sleep(5)  # Esperar a que la página cargue completamente

        # Interactuar con la página (clic en botones, seguir enlaces, etc.)
        html_final = interactuar_con_pagina(driver)

        # Extraer el contenido final de la página
        contenido = driver.find_elements(By.TAG_NAME, "p")
        texto_extraido = " ".join([element.text for element in contenido])

        driver.quit()
        return jsonify({"url": url, "contenido": texto_extraido})

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
