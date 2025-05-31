import os
import time
import base64
import requests
import logging
import re
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
    TimeoutException
)
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carpeta donde se guardará la imagen descargada
DOWNLOAD_DIR = "downloaded_images"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def sanitize_filename(text: str) -> str:
    """
    Convierte un texto en un nombre de archivo válido:
    - Minúsculas
    - Sin caracteres no alfanuméricos (excepto guiones bajos y guiones)
    - Espacios reemplazados por guiones bajos
    """
    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s]+", "_", text)
    return text


def unique_filename(directory: str, base_name: str, ext: str) -> str:
    """
    Genera un nombre de archivo único en 'directory', usando 'base_name' y 'ext'.
    Si 'base_name.ext' existe, genera 'base_name_1.ext', 'base_name_2.ext', etc.
    """
    candidate = f"{base_name}{ext}"
    i = 1
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base_name}_{i}{ext}"
        i += 1
    return candidate


def configurar_driver():
    """
    Configura y devuelve un Chrome WebDriver en modo headless.
    """
    options = Options()
    # Para Chrome 121+ usar "--headless=new"
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
    1) Abre la página principal (url).
    2) Hace scroll para cargar imágenes lazy.
    3) Encuentra el primer <article> visible (asumido más reciente).
    4) Para ese article, extrae:
         - Título del post.
         - URL de la miniatura (img decodificada/lazy).
         - Enlace al post.
    5) Genera un nombre único, descarga la imagen y la guarda localmente.
    6) Abre el post y extrae todo el texto (Elementor o <article> <p>).
    7) Convierte la imagen guardada a Base64.
    Devuelve un dict con:
    {
      "title": título,
      "text": contenido del post,
      "image_url": URL de la miniatura,
      "saved_filename": nombre de archivo local,
      "image_base64": cadena Base64
    }
    Si falla en cualquier paso, devuelve None.
    """
    driver.get(url)
    logger.info(f"Navegando a la página principal: {driver.current_url}")

    # Scroll para forzar carga lazy-loading
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # 3) Esperar a que aparezca al menos un <article>
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
    except TimeoutException:
        logger.error("No se encontró ningún <article> en la página principal.")
        return None

    # Tomar el primer <article> como el post más reciente
    try:
        articulo = driver.find_element(By.CSS_SELECTOR, "article")
    except NoSuchElementException:
        logger.error("No se pudo obtener el primer <article>.")
        return None

    # 4.a) Extraer título del post
    try:
        titulo_el = articulo.find_element(By.CSS_SELECTOR, "h2.entry-title a")
        titulo = titulo_el.text.strip() or "sin_titulo"
    except NoSuchElementException:
        logger.warning("No se encontró el título; usando 'sin_titulo'.")
        titulo = "sin_titulo"

    # 4.b) Extraer enlace al post
    try:
        enlace_post = articulo.find_element(By.CSS_SELECTOR, "h2.entry-title a").get_attribute("href")
    except NoSuchElementException:
        logger.error("No se encontró el enlace del post en el <article>.")
        return None

    # 4.c) Extraer URL de la miniatura dentro del <article>
    try:
        # Buscar primer <img> decodificado/lazyloaded dentro del article
        img_el = articulo.find_element(By.CSS_SELECTOR, "img.entered.lazyloaded")
    except NoSuchElementException:
        try:
            # Fallback: cualquier <img> dentro del article
            img_el = articulo.find_element(By.TAG_NAME, "img")
        except NoSuchElementException:
            img_el = None

    if not img_el:
        logger.error("No se encontró ninguna <img> en el <article>.")
        return None

    imagen_url = img_el.get_attribute("data-lazy-src") or img_el.get_attribute("src")
    if not imagen_url:
        srcset = img_el.get_attribute("data-lazy-srcset") or img_el.get_attribute("srcset")
        if srcset:
            partes = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
            if partes:
                ultima = partes[-1]
                imagen_url = ultima if ultima.startswith(("http://", "https://")) else urljoin(url, ultima)

    if not imagen_url:
        logger.error("No se pudo determinar la URL de la miniatura.")
        return None

    # 5) Generar nombre de archivo único para guardar imagen
    ext = os.path.splitext(urlparse(imagen_url).path)[1] or ".jpg"
    base_name = sanitize_filename(titulo)
    nuevo_nombre = unique_filename(DOWNLOAD_DIR, base_name, ext)
    saved_path = os.path.join(DOWNLOAD_DIR, nuevo_nombre)

    # 6) Descargar y guardar la imagen en disco
    try:
        resp = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            with open(saved_path, "wb") as f:
                f.write(resp.content)
        else:
            logger.error(f"HTTP {resp.status_code} al descargar imagen: {imagen_url}")
            return None
    except Exception as e:
        logger.error(f"Error descargando la imagen: {e}")
        return None

    # 7) Navegar al post y extraer texto
    driver.get(enlace_post)
    logger.info(f"Navegando al post: {enlace_post}")
    texto_extraido = ""

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
        # Fallback: extraer cualquier <p> dentro de <article>
        logger.warning("No se encontró 'div.elementor-widget-container', intentando <article> <p>.")
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article p"))
            )
            parrafos = driver.find_elements(By.CSS_SELECTOR, "article p")
            texto_extraido = " ".join([p.text.strip() for p in parrafos if p.text.strip()])
        except TimeoutException:
            logger.error("No se encontró <article> con <p> para extraer texto.")
            texto_extraido = ""

    # 8) Convertir la imagen guardada a Base64
    imagen_base64 = None
    try:
        with open(saved_path, "rb") as f:
            imagen_base64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error(f"Error codificando la imagen a Base64: {e}")

    return {
        "title": titulo,
        "text": texto_extraido,
        "image_url": imagen_url,
        "saved_filename": nuevo_nombre,
        "image_base64": imagen_base64
    }


@app.route('/extraer_imagen', methods=['POST'])
def extraer_imagen():
    """
    Endpoint que recibe JSON {"url": "https://salesystems.es/blog"}
    y devuelve solo el post más reciente con su imagen:
    {
      "title": "...",
      "text": "...",
      "image_url": "...",
      "saved_filename": "...",
      "image_base64": "..."
    }
    """
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        logger.info(f"Procesando petición para URL: {url}")

        resultado = interactuar_con_pagina(driver, url)
        if not resultado:
            return jsonify({"error": "No se pudo extraer el post más reciente"}), 500

        return jsonify(resultado)
    except Exception as e:
        logger.exception(f"Error en /extraer_imagen: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        driver.quit()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
