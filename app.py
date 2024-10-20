import os
import base64
import requests
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
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Evitar detección como bot
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Evitar la detección de Selenium
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    return driver

def interactuar_con_pagina(driver, url):
    # Navegar a la URL proporcionada
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")  # Verificar la URL actual

    try:
        # Esperar a que los artículos del blog estén presentes
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article.eael-grid-post.eael-post-grid-column'))
        )
        app.logger.info("Artículos del blog encontrados")

        # Encontrar todos los artículos
        articles = driver.find_elements(By.CSS_SELECTOR, 'article.eael-grid-post.eael-post-grid-column')

        if not articles:
            app.logger.error("No se encontraron artículos en la página")
            return None, None, None

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
        # Capturar captura de pantalla para depuración
        screenshot_path = "error_loading_article.png"
        driver.save_screenshot(screenshot_path)
        app.logger.error(f"Captura de pantalla guardada en {screenshot_path}")
        return None, None, None

    # Esperar a que la nueva página cargue completamente
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "p"))
        )
        app.logger.info("Página del artículo cargada")
    except Exception as e:
        app.logger.error(f"Error al cargar la página del artículo: {e}")
        # Capturar captura de pantalla para depuración
        screenshot_path = "error_loading_article_content.png"
        driver.save_screenshot(screenshot_path)
        app.logger.error(f"Captura de pantalla guardada en {screenshot_path}")
        return None, None, None

    # Extraer el contenido de la página actual
    contenido = driver.find_elements(By.TAG_NAME, "p")
    texto_extraido = " ".join([element.text for element in contenido])
    app.logger.info(f"Texto extraído: {texto_extraido[:500]}...")  # Mostrar solo los primeros 500 caracteres

    # Extraer la URL de la imagen del artículo basándose en la clase específica del <picture>
    imagen_url = None
    imagen_base64 = None
    max_retries = 5
    retry_delay = 2  # segundos

    for attempt in range(1, max_retries + 1):
        try:
            # Seleccionar el <picture> con la clase específica 'wp-image-33924'
            picture_element = driver.find_element(By.CLASS_NAME, 'wp-image-33924')
            img_element = picture_element.find_element(By.TAG_NAME, 'img')
            current_src = img_element.get_attribute('src')
            app.logger.info(f"Intento {attempt}: src del <img> encontrado: {current_src}")

            if current_src.startswith("http"):
                imagen_url = current_src
                app.logger.info(f"URL de la imagen encontrada: {imagen_url}")
                break
            else:
                # Intentar obtener 'data-lazy-src' si 'src' es una Data URI
                data_lazy_src = img_element.get_attribute('data-lazy-src')
                if data_lazy_src and data_lazy_src.startswith("http"):
                    imagen_url = data_lazy_src
                    app.logger.info(f"URL de la imagen obtenida de 'data-lazy-src': {imagen_url}")
                    break
                else:
                    app.logger.warning(f"El src encontrado no es una URL válida (Data URI): {current_src}")
                    if attempt < max_retries:
                        app.logger.info(f"Reintentando en {retry_delay} segundos...")
                        time.sleep(retry_delay)
                    else:
                        app.logger.error("Máximo número de reintentos alcanzado. No se encontró una URL válida para la imagen.")
        except Exception as e:
            app.logger.error(f"Error al intentar encontrar la imagen con clase 'wp-image-33924': {e}")
            if attempt < max_retries:
                app.logger.info(f"Reintentando en {retry_delay} segundos...")
                time.sleep(retry_delay)
            else:
                app.logger.error("Máximo número de reintentos alcanzado. No se pudo encontrar la imagen.")
                return texto_extraido, None, None

    if not imagen_url:
        # Opcional: Listar todas las imágenes encontradas para depuración
        try:
            imagenes = driver.find_elements(By.CSS_SELECTOR, 'div.entry-content img')
            app.logger.info(f"Total de imágenes encontradas en div.entry-content: {len(imagenes)}")
            for idx, img in enumerate(imagenes, start=1):
                alt = img.get_attribute('alt')
                src = img.get_attribute('src')
                app.logger.info(f"Imagen {idx}: alt='{alt}', src='{src}'")
        except Exception as ex:
            app.logger.error(f"Error al listar imágenes para depuración: {ex}")

    # Descargar la imagen y codificarla en Base64 (opcional)
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
        app.logger.error("No se encontró una URL válida para la imagen")

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

        texto_extraido, imagen_url, imagen_base64 = interactuar_con_pagina(driver, url)  # Interactuar con la página

        if texto_extraido is None:
            return jsonify({"error": "No se pudo extraer el texto"}), 500

        # Preparar la respuesta con el texto y la imagen
        response_data = {
            "url": url,
            "contenido": texto_extraido,
            "imagen_url": imagen_url,
            "imagen_base64": imagen_base64  # Si necesitas la imagen en Base64
        }

        return jsonify(response_data)

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        app.logger.error(f"Error al procesar la solicitud: {e}\n{error_trace}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

    finally:
        driver.quit()

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
