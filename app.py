import os
import time
import base64
import requests
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def configurar_driver():
    """
    Configura y devuelve un Chrome WebDriver en modo headless.
    """
    options = Options()
    # Para Chrome versión 121+:
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    # Evitar detección de automatización
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def interactuar_con_pagina(driver, url):
    """
    1. Va a la página principal (url).
    2. Espera hasta que aparezca al menos un <a href*="/blog/"> con <img> dentro.
    3. Toma esa primera miniatura y su enlace (post_url) como el “post más reciente”.
    4. Extrae la URL de la imagen (src o data-src).
    5. Navega a post_url y extrae todo el texto dentro de <div class="elementor-widget-container">.
    6. Descarga la imagen_url (si existe) y la convierte a base64.
    Devuelve (texto_del_post, imagen_url, imagen_base64). Si algo falla, devuelve (None, None, None).
    """
    # 1) Abrir la página principal
    driver.get(url)
    logger.info(f"Navegando a la página principal: {driver.current_url}")

    # 2) Esperar hasta que aparezca al menos un <a href*="/blog/"> <img>
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "a[href*='/blog/'] img")
            )
        )
    except Exception as e:
        logger.error(f"No se encontró miniatura en la página principal: {e}")
        return None, None, None

    # 3) Tomar la primera miniatura
    img_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/blog/'] img")
    if not img_elements:
        logger.error("No se hallaron elementos <a href*='/blog/'] img")
        return None, None, None

    img_el = img_elements[0]
    # El <img> está dentro de un <a>; subimos un nodo para obtener post_url
    try:
        post_link_el = img_el.find_element(By.XPATH, "./ancestor::a")
        post_url = post_link_el.get_attribute("href")
    except Exception as e:
        logger.error(f"No se pudo extraer el enlace del post desde la miniatura: {e}")
        return None, None, None

    # 4) Extraer URL de la imagen (src o data-src)
    imagen_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")
    # Si la URL está en srcset, tomar la última posición
    if not imagen_url:
        srcset = img_el.get_attribute("srcset")
        if srcset:
            partes = [p.strip() for p in srcset.split(",")]
            if partes:
                ultima = partes[-1].split()[0]
                # Si es relativa, convertir a absoluta
                if ultima.startswith(("http://", "https://")):
                    imagen_url = ultima
                else:
                    from urllib.parse import urljoin
                    imagen_url = urljoin(url, ultima)

    logger.info(f"Post más reciente identificado: {post_url}")
    logger.info(f"Miniatura encontrada: {imagen_url}")

    # 5) Navegar al post y extraer texto
    driver.get(post_url)
    logger.info(f"Navegando al post: {post_url}")
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.elementor-widget-container")
            )
        )
    except Exception as e:
        logger.error(f"No se cargó el contenido del post: {e}")
        return None, imagen_url, None

    # Extraer todos los párrafos y encabezados dentro de "div.elementor-widget-container"
    texto_extraido = ""
    retries = 3
    while retries:
        try:
            bloques = driver.find_elements(
                By.CSS_SELECTOR,
                "div.elementor-widget-container p, div.elementor-widget-container h2, div.elementor-widget-container h3"
            )
            texto_extraido = " ".join([b.text.strip() for b in bloques if b.text.strip()])
            break
        except Exception:
            retries -= 1
            time.sleep(1)

    # 6) Descargar la imagen y convertir a base64
    imagen_base64 = None
    if imagen_url:
        try:
            resp = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                imagen_base64 = base64.b64encode(resp.content).decode("utf-8")
            else:
                logger.warning(f"Ocurrió un HTTP {resp.status_code} al descargar la imagen.")
        except Exception as e:
            logger.error(f"Error descargando la imagen: {e}")

    return texto_extraido, imagen_url, imagen_base64


@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    """
    Endpoint que recibe JSON { "url": "https://salesystems.es/blog" }
    y devuelve { "url": ..., "contenido": ..., "imagen_url": ..., "imagen_base64": ... }.
    """
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        logger.info(f"Procesando petición para URL: {url}")

        texto, img_url, img_b64 = interactuar_con_pagina(driver, url)
        if texto is None:
            return jsonify({"error": "No se pudo extraer el contenido"}), 500

        return jsonify({
            "url": url,
            "contenido": texto,
            "imagen_url": img_url,
            "imagen_base64": img_b64
        })
    except Exception as e:
        logger.exception(f"Error en /extraer: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        driver.quit()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
