import os
import time
import base64
import requests
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Ejecutar en modo headless (comentado para depuración)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-cache")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    # User-Agent personalizado
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver, url):
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        # Esperar a que el elemento sea clicable
        first_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'article.post h2.entry-title a'))
        )
        app.logger.info("Primer elemento encontrado y clicable")

        # Verificar visibilidad y estado
        is_displayed = first_element.is_displayed()
        is_enabled = first_element.is_enabled()
        app.logger.info(f"Visible: {is_displayed}, Habilitado: {is_enabled}")

        # Desplazarse al elemento
        driver.execute_script("arguments[0].scrollIntoView(true);", first_element)
        time.sleep(1)

        # Hacer clic usando ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(first_element).click().perform()
        app.logger.info("Hizo clic en el primer elemento")

        # Esperar a que la nueva página cargue
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.entry-content'))
        )
        app.logger.info("Página del artículo cargada")

    except Exception as e:
        app.logger.error("Error al hacer clic en el primer elemento", exc_info=True)
        return None, None, None

    # Extraer contenido e imagen...
    # (El resto del código permanece igual)

# El resto del código permanece igual


    # Extraer el contenido del artículo
    try:
        contenido_elements = driver.find_elements(By.CSS_SELECTOR, 'div.entry-content p')
        texto_extraido = " ".join([element.text for element in contenido_elements])
        app.logger.info(f"Texto extraído: {texto_extraido[:100]}...")
    except Exception as e:
        app.logger.error(f"Error al extraer el contenido: {e}")
        texto_extraido = None

    # Obtener la imagen del artículo
    try:
        imagen_element = driver.find_element(By.CSS_SELECTOR, 'div.entry-content img')
        imagen_url = imagen_element.get_attribute('src')
        app.logger.info(f"URL de la imagen encontrada: {imagen_url}")
    except Exception as e:
        app.logger.error(f"No se pudo encontrar la imagen: {e}")
        imagen_url = None

    # Descargar la imagen y codificarla en Base64
    imagen_base64 = None
    if imagen_url:
        try:
            imagen_respuesta = requests.get(imagen_url)
            if imagen_respuesta.status_code == 200:
                imagen_base64 = base64.b64encode(imagen_respuesta.content).decode('utf-8')
                app.logger.info("Imagen descargada y codificada en Base64")
            else:
                app.logger.error(f"No se pudo descargar la imagen, código de estado: {imagen_respuesta.status_code}")
        except Exception as e:
            app.logger.error(f"Error al descargar la imagen: {e}")
    else:
        app.logger.error("No se encontró la URL de la imagen")

    return texto_extraido, imagen_url, imagen_base64

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        app.logger.info(f"Extrayendo contenido de la URL: {url}")

        resultado = interactuar_con_pagina(driver, url)

        if resultado is None:
            return jsonify({"error": "No se pudo extraer el texto o la imagen"}), 500

        texto_extraido, imagen_url, imagen_base64 = resultado

        response_data = {
            "url": url,
            "contenido": texto_extraido,
            "imagen_url": imagen_url,
            "imagen_base64": imagen_base64
        }

        return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

    finally:
        driver.quit()

# Configurar el servidor para usar el puerto proporcionado
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
