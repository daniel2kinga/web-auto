import os
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    
    chrome_options.add_argument("--headless")  # Ejecutar en modo headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-cache")  # Desactivar caché
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver):
    # Navegar a la página principal
    url = 'https://www.cnet.com'
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")  # Verificar la URL actual

    # Esperar a que las entradas del blog estén presentes
    try:
        # Esperar a que la primera entrada del blog esté presente y sea clicable
        first_blog_post = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'a.assetHed'))
        )
        app.logger.info("Encontrado el primer post del blog")
        # Hacer clic en la primera entrada del blog
        first_blog_post.click()
        app.logger.info("Haciendo clic en el primer post del blog")
    except Exception as e:
        app.logger.error(f"No se pudo encontrar o hacer clic en el primer post del blog: {e}")
        return None

    # Esperar a que la nueva página cargue completamente
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )
        app.logger.info("Página del artículo cargada")
    except Exception as e:
        app.logger.error(f"Error al cargar la página del artículo: {e}")
        return None

    # Extraer el contenido de la página actual
    contenido = driver.find_elements(By.TAG_NAME, "p")
    texto_extraido = " ".join([element.text for element in contenido])
    app.logger.info(f"Texto extraído: {texto_extraido[:500]}...")  # Mostrar solo los primeros 500 caracteres

    return texto_extraido

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        driver = configurar_driver()
        texto_extraido = interactuar_con_pagina(driver)  # Interactuar con la página

        if texto_extraido is None:
            return jsonify({"error": "No se pudo extraer el texto"}), 500

        driver.quit()
        return jsonify({"contenido": texto_extraido})

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

    finally:
        driver.quit()

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
