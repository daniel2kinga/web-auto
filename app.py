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
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException
)
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin

app = Flask(__name__)

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diccionario para mapear meses en español a números
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
    'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
    'octubre': 10, 'noviembre': 11, 'diciembre': 12
}


def configurar_driver():
    """
    Configura y devuelve un Chrome WebDriver en modo headless.
    """
    options = Options()
    # Para Chrome 121+:
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


def parsear_fecha(fecha_str):
    """
    Convierte una fecha en español a un objeto datetime.
    Ejemplos: "12 de mayo de 2025", "12 mayo 2025", "12 mayo".
    """
    try:
        partes = fecha_str.lower().replace(',', '').split()
        dia = int(partes[0])
        mes = MESES.get(partes[1])
        if not mes:
            return None
        if len(partes) == 3:
            anio = int(partes[2])
        else:
            anio = datetime.now().year
        return datetime(anio, mes, dia)
    except Exception as e:
        logger.error(f"Error parseando fecha '{fecha_str}': {e}")
        return None


def interactuar_con_pagina(driver, url):
    """
    1) Abre la página principal (url).
    2) Hace scroll para cargar lazy-loading.
    3) Busca la miniatura del post más reciente usando varios selectores posibles.
    4) Extrae post_url y texto del post, intentando primero div.elementor-widget-container,
       y si no existe, busca dentro de <article> cualquier <p>.
    5) Descarga la miniatura como Base64.
    Devuelve (texto_del_post, imagen_url, imagen_base64).
    """
    driver.get(url)
    logger.info(f"Navegando a la página principal: {driver.current_url}")

    # Scroll en dos etapas para forzar lazy-loading
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # Esperar a que aparezca al menos un posible <img> de miniatura
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "img.wp-post-image, div.eael-grid-post-holder-inner img, a[href*='/blog/'] img, article img"
                )
            )
        )
    except TimeoutException:
        logger.error("No se encontró ninguna miniatura usando los selectores establecidos.")
        return None, None, None

    # Reunir todas las posibles miniaturas
    posibles_imgs = driver.find_elements(
        By.CSS_SELECTOR,
        "img.wp-post-image, div.eael-grid-post-holder-inner img, a[href*='/blog/'] img, article img"
    )

    if not posibles_imgs:
        logger.error("No hay elementos <img> de miniatura en la página.")
        return None, None, None

    # Tomar la primera miniatura válida
    img_el = None
    post_url = None
    for candidate in posibles_imgs:
        # Intentar extraer el <a> ancestro sin filtrar por '/blog/'
        try:
            a_anc = candidate.find_element(By.XPATH, "./ancestor::a")
            href = a_anc.get_attribute("href")
            if href and href != url:  # descartar si apunta a la misma página
                img_el = candidate
                post_url = href
                break
        except NoSuchElementException:
            continue

    if not img_el or not post_url:
        logger.error("No se pudo encontrar una miniatura dentro de un <a> válido.")
        return None, None, None

    # Extraer URL de la imagen
    imagen_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")
    if not imagen_url:
        srcset = img_el.get_attribute("srcset")
        if srcset:
            partes = [p.strip() for p in srcset.split(",")]
            if partes:
                ultima = partes[-1].split()[0]
                if ultima.startswith(("http://", "https://")):
                    imagen_url = ultima
                else:
                    imagen_url = urljoin(url, ultima)

    logger.info(f"Post más reciente: {post_url}")
    logger.info(f"Miniatura URL: {imagen_url}")

    # Navegar al post y extraer texto
    driver.get(post_url)
    logger.info(f"Navegando al post: {post_url}")

    texto_extraido = ""
    # Intentar extraer con Elementor
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.elementor-widget-container"))
        )
        bloques = driver.find_elements(
            By.CSS_SELECTOR,
            "div.elementor-widget-container p, div.elementor-widget-container h2, div.elementor-widget-container h3"
        )
        texto_extraido = " ".join([b.text.strip() for b in bloques if b.text.strip()])
    except TimeoutException:
        # Si no hay elemento Elementor, buscar dentro de <article> cualquier <p>
        logger.warning("No se encontró 'div.elementor-widget-container', intentando <article> <p>")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article p"))
            )
            parrafos = driver.find_elements(By.CSS_SELECTOR, "article p")
            texto_extraido = " ".join([p.text.strip() for p in parrafos if p.text.strip()])
        except TimeoutException:
            logger.error("No se encontró <article> con <p> para extraer texto.")
            return None, imagen_url, None

    # Descargar miniatura y convertir a Base64 (si existe)
    imagen_base64 = None
    if imagen_url:
        try:
            resp = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                imagen_base64 = base64.b64encode(resp.content).decode("utf-8")
            else:
                logger.warning(f"HTTP {resp.status_code} al descargar la miniatura.")
        except Exception as e:
            logger.error(f"Error descargando la imagen: {e}")

    return texto_extraido, imagen_url, imagen_base64


@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    """
    Endpoint que recibe JSON {"url": "https://salesystems.es/blog"}
    y devuelve JSON {"url": ..., "contenido": ..., "imagen_url": ..., "imagen_base64": ...}.
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
