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
from urllib.parse import urljoin, urlparse
import re

app = Flask(__name__)

# Configuración del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carpeta donde se guardarán las imágenes descargadas
DOWNLOAD_DIR = "downloaded_images"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Diccionario para mapear meses en español a números (no usado en este código)
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
    'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
    'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def sanitize_filename(text: str) -> str:
    """
    Convierte un texto en un nombre de archivo válido:
    - Minúsculas
    - Sin caracteres no alfanuméricos (excepto guiones bajos)
    - Espacios reemplazados por guiones bajos
    """
    text = text.strip().lower()
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    text = re.sub(r'[\s]+', '_', text)
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

def interactuar_con_pagina(driver, url, max_posts=5):
    """
    1) Abre la página principal (url).
    2) Hace scroll para cargar lazy-loading.
    3) Encuentra hasta `max_posts` tarjetas de post recientes.
    4) Para cada tarjeta, extrae:
         - Título del post (para nombrar la imagen).
         - URL de la miniatura (data-lazy-src o src).
       Construye un nombre de archivo basado en el título, asegurando unicidad.
       Descarga y guarda cada imagen en disco con ese nombre único, luego convierte a Base64.
    Devuelve una lista de dicts con:
    {
      "title": título,
      "image_url": URL original,
      "saved_filename": nombre de archivo local guardado,
      "image_base64": cadena Base64
    }
    """
    driver.get(url)
    logger.info(f"Navegando a la página principal: {driver.current_url}")

    # Scroll en dos etapas para forzar la carga de imágenes lazy
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    # Esperar a que aparezcan las tarjetas de post
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.eael-grid-post-holder-inner"))
        )
    except TimeoutException:
        logger.error("No se encontraron elementos 'div.eael-grid-post-holder-inner'.")
        return []

    tarjetas = driver.find_elements(By.CSS_SELECTOR, "div.eael-grid-post-holder-inner")
    resultados = []

    for idx, tarjeta in enumerate(tarjetas[:max_posts]):
        try:
            # 1) Extraer título del post
            try:
                titulo_el = tarjeta.find_element(By.CSS_SELECTOR, "h2.entry-title a")
                titulo = titulo_el.text.strip()
                if not titulo:
                    raise NoSuchElementException
            except NoSuchElementException:
                logger.warning(f"Tarjeta #{idx+1}: no se encontró título, usando fallback genérico.")
                titulo = f"post_{idx+1}"

            # 2) Extraer URL de la miniatura
            try:
                img_el = tarjeta.find_element(By.CSS_SELECTOR, "img.entered.lazyloaded")
            except NoSuchElementException:
                try:
                    img_el = tarjeta.find_element(By.TAG_NAME, "img")
                except NoSuchElementException:
                    img_el = None

            if not img_el:
                logger.warning(f"Tarjeta #{idx+1} ('{titulo}'): no se encontró <img> dentro de la tarjeta.")
                continue

            # Obtener URL real de la imagen
            imagen_url = img_el.get_attribute("data-lazy-src") or img_el.get_attribute("src")
            if not imagen_url:
                srcset = img_el.get_attribute("data-lazy-srcset") or img_el.get_attribute("srcset")
                if srcset:
                    partes = [p.strip().split()[0] for p in srcset.split(",") if p.strip()]
                    if partes:
                        ultima = partes[-1]
                        imagen_url = ultima if ultima.startswith(("http://", "https://")) else urljoin(url, ultima)

            if not imagen_url:
                logger.warning(f"Tarjeta #{idx+1} ('{titulo}'): no se pudo determinar URL de la imagen.")
                continue

            # 3) Construir nombre de archivo único
            ext = os.path.splitext(urlparse(imagen_url).path)[1] or ".jpg"
            base_name = sanitize_filename(titulo)
            nuevo_nombre = unique_filename(DOWNLOAD_DIR, base_name, ext)

            # 4) Descargar y guardar la imagen en disco
            saved_path = os.path.join(DOWNLOAD_DIR, nuevo_nombre)
            try:
                resp = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    with open(saved_path, "wb") as f:
                        f.write(resp.content)
                else:
                    logger.warning(f"Tarjeta #{idx+1} ('{titulo}'): HTTP {resp.status_code} al descargar imagen.")
                    continue
            except Exception as e:
                logger.error(f"Tarjeta #{idx+1} ('{titulo}'): error descargando la imagen: {e}")
                continue

            # 5) Convertir la imagen guardada a Base64
            imagen_base64 = None
            try:
                with open(saved_path, "rb") as f:
                    imagen_base64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception as e:
                logger.error(f"Tarjeta #{idx+1} ('{titulo}'): error codificando a Base64: {e}")
                imagen_base64 = None

            resultados.append({
                "title": titulo,
                "image_url": imagen_url,
                "saved_filename": nuevo_nombre,
                "image_base64": imagen_base64
            })

        except Exception as e:
            logger.error(f"Error procesando tarjeta #{idx+1}: {e}")
            continue

    return resultados

@app.route('/extraer_imagenes', methods=['POST'])
def extraer_imagenes():
    """
    Endpoint que recibe JSON {"url": "https://salesystems.es/blog", "max_posts": 5}
    y devuelve un array con info de las imágenes de los posts más recientes:
    [
        {
            "title": "...",
            "image_url": "...",
            "saved_filename": "...",
            "image_base64": "..."
        },
        ...
    ]
    """
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        max_posts = data.get('max_posts', 5)
        logger.info(f"Procesando petición para URL: {url}, max_posts={max_posts}")

        resultados = interactuar_con_pagina(driver, url, max_posts=max_posts)
        if not resultados:
            return jsonify({"error": "No se encontraron imágenes o no se pudo extraer"}), 500

        return jsonify({
            "url": url,
            "count": len(resultados),
            "posts": resultados
        })
    except Exception as e:
        logger.exception(f"Error en /extraer_imagenes: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        driver.quit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
