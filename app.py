import os
import time
import base64
import requests
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
    # Agregar un User-Agent para evitar ser bloqueado por el sitio web
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver, url):
    # Navegar a la URL proporcionada
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        # Esperar a que las imágenes estén presentes
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article.post img'))
        )
        app.logger.info("Imágenes encontradas en la página principal")

        # Encontrar todas las imágenes en los artículos
        image_elements = driver.find_elements(By.CSS_SELECTOR, 'article.post img')

        if not image_elements:
            app.logger.error("No se encontraron imágenes en la página")
            return None, None, None

        # Obtener la primera imagen
        first_image = image_elements[0]

        # Hacer clic en la primera imagen para navegar al artículo
        first_image.click()
        app.logger.info("Haciendo clic en la primera imagen para navegar al artículo")

        # Esperar a que la nueva página cargue completamente
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.entry-content'))
        )
        app.logger.info(f"Navegando al artículo: {driver.current_url}")

    except Exception as e:
        app.logger.error(f"Error al navegar al artículo: {e}")
        return None, None, None

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
        app.logger.error(f"No se pudo encontrar la imagen en el artículo: {e}")
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
            "url": driver.current_url,  # URL del artículo actual
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
