import os
import time
import requests  # Agregar esta importación para descargar la imagen
from flask import Flask, request, jsonify, send_file
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
    app.logger.info(f"Navegando a: {driver.current_url}")  # Verificar la URL actual

    try:
        # Esperar a que los artículos del blog estén presentes
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article.eael-grid-post.eael-post-grid-column'))
        )
        app.logger.info("Artículos del blog encontrados")

        # Encontrar todos los artículos
        articles = driver.find_elements(By.CSS_SELECTOR, 'article.eael-grid-post.eael-post-grid-column')

        if not articles:
            app.logger.error("No se encontraron artículos en la página")
            return None

        # Obtener el primer artículo
        first_article = articles[0]

        # Dentro del primer artículo, encontrar el enlace al post
        post_link_element = first_article.find_element(By.CSS_SELECTOR, 'div.eael-entry-overlay a')
        post_url = post_link_element.get_attribute('href')

        app.logger.info(f"Enlace al post encontrado: {post_url}")

        # Navegar a la URL del post
        driver.get(post_url)
        app.logger.info(f"Navegando al post: {driver.current_url}")

    except Exception as e:
        app.logger.error(f"No se pudo obtener el enlace del primer post del blog: {e}")
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

    # Descargar la imagen del artículo
    try:
        # Suponiendo que la imagen principal del artículo está dentro de una etiqueta <img> con una clase específica
        # Necesitamos ajustar el selector CSS según la estructura real de la página
        imagen_element = driver.find_element(By.CSS_SELECTOR, 'div.post-thumbnail img')
        imagen_url = imagen_element.get_attribute('src')

        app.logger.info(f"URL de la imagen encontrada: {imagen_url}")

        # Descargar la imagen
        imagen_respuesta = requests.get(imagen_url, stream=True)
        if imagen_respuesta.status_code == 200:
            # Guardar la imagen en un archivo temporal
            imagen_nombre = 'imagen_descargada.jpg'
            with open(imagen_nombre, 'wb') as f:
                for chunk in imagen_respuesta.iter_content(1024):
                    f.write(chunk)
            app.logger.info("Imagen descargada correctamente")
        else:
            app.logger.error("No se pudo descargar la imagen")
            imagen_nombre = None
    except Exception as e:
        app.logger.error(f"No se pudo encontrar o descargar la imagen: {e}")
        imagen_nombre = None

    return texto_extraido, imagen_nombre

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        app.logger.info(f"Extrayendo contenido de la URL: {url}")

        resultado = interactuar_con_pagina(driver, url)  # Interactuar con la página

        if resultado is None:
            return jsonify({"error": "No se pudo extraer el texto o descargar la imagen"}), 500

        texto_extraido, imagen_nombre = resultado

        response_data = {
            "url": url,
            "contenido": texto_extraido
        }

        if imagen_nombre:
            # Devolver el contenido y enviar la imagen como archivo adjunto
            return send_file(imagen_nombre, mimetype='image/jpeg', as_attachment=True, attachment_filename=imagen_nombre), 200, {'Content-Type': 'application/json'}
        else:
            return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

    finally:
        driver.quit()
        # Eliminar la imagen descargada si existe
        if 'imagen_nombre' in locals() and imagen_nombre and os.path.exists(imagen_nombre):
            os.remove(imagen_nombre)

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
