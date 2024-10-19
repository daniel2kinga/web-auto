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

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver, url):
    # Navegar a la URL proporcionada
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        # Esperar a que los artículos del blog estén presentes
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article.post'))
        )
        app.logger.info("Artículos del blog encontrados")

        # Encontrar el primer artículo
        first_article = driver.find_element(By.CSS_SELECTOR, 'article.post')

        # Obtener el enlace al artículo
        post_link_element = first_article.find_element(By.CSS_SELECTOR, 'h2.entry-title a')
        post_url = post_link_element.get_attribute('href')
        app.logger.info(f"URL del artículo encontrado: {post_url}")

        # Navegar a la URL del artículo
        driver.get(post_url)
        app.logger.info(f"Navegando al artículo: {driver.current_url}")

    except Exception as e:
        app.logger.error(f"No se pudo obtener el enlace del artículo: {e}")
        return None, None, None

    # Esperar a que la nueva página cargue completamente
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )
        app.logger.info("Página del artículo cargada")
    except Exception as e:
        app.logger.error(f"Error al cargar la página del artículo: {e}")
        return None, None, None

    # Extraer el contenido de la página actual
    contenido_elements = driver.find_elements(By.TAG_NAME, "p")
    texto_extraido = " ".join([element.text for element in contenido_elements])
    app.logger.info(f"Texto extraído: {texto_extraido[:500]}...")  # Mostrar solo los primeros 500 caracteres

    # Obtener la URL de la imagen del artículo
    try:
        # Ajustar el selector CSS según la estructura real de la página
        imagen_element = driver.find_element(By.CSS_SELECTOR, 'article.post img')
        imagen_url = imagen_element.get_attribute('src') or imagen_element.get_attribute('data-src')
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
                app.logger.error("No se pudo descargar la imagen")
        except Exception as e:
            app.logger.error(f"Error al descargar la imagen: {e}")

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
            "url": url,  # Puedes cambiar esto a post_url si lo prefieres
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
    app.run(host='0.0.0.0', port=port)
