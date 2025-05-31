import os
import time
import base64
import requests
import logging
from urllib.parse import urljoin
from datetime import datetime
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Configuración del logger para imprimir mensajes en la terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Diccionario para mapear los nombres de meses en español a números
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
    'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
    'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def configurar_driver():
    """Configura Chrome en modo headless y devuelve el driver."""
    chrome_options = Options()
    # Modo headless (requiere Chrome 121+ para "--headless=new")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    # Opciones para evitar detección de automatización (opcional)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def parsear_fecha(fecha_str):
    """
    Convierte una fecha en español a un objeto datetime.
    Ejemplos de formatos esperados: "12 de mayo de 2025", "12 mayo 2025", "12 mayo".
    """
    try:
        partes = fecha_str.lower().replace(',', '').split()
        dia = int(partes[0])
        mes = MESES.get(partes[1])
        if not mes:
            return None
        # Si incluyen año, está en la posición 2; si no, usamos el año actual.
        if len(partes) == 3:
            anio = int(partes[2])
        else:
            anio = datetime.now().year
        return datetime(anio, mes, dia)
    except Exception as e:
        app.logger.error(f"Error al parsear la fecha '{fecha_str}': {e}")
        return None

def interactuar_con_pagina(driver, url):
    """
    Abre la página principal (url), extrae la entrada más reciente (por fecha),
    recupera la miniatura (img) de esa entrada y luego extrae el contenido del post.
    Devuelve (texto_del_post, imagen_url, imagen_base64) o (None, None, None) en caso de fallo.
    """
    driver.get(url)
    app.logger.info(f"Navegando a la página principal: {driver.current_url}")

    # (Opcional) Depuración: vuelca el HTML completo a los logs para inspección
    app.logger.info("=== INICIO HTML de la página principal ===")
    app.logger.info(driver.page_source)
    app.logger.info("=== FIN HTML de la página principal ===")

    # Esperar hasta que aparezcan las tarjetas de post (ejemplo: <article class="post">)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.post"))
        )
    except Exception as e:
        app.logger.error(f"No se encontraron elementos 'article.post': {e}")
        return None, None, None

    tarjetas = driver.find_elements(By.CSS_SELECTOR, "article.post")
    entradas = []

    for t in tarjetas:
        try:
            # 1) Extraer y parsear la fecha
            time_element = t.find_element(By.CSS_SELECTOR, "time")
            fecha_str = time_element.text.strip()
            fecha = parsear_fecha(fecha_str)
            if not fecha:
                continue

            # 2) Extraer el enlace al post (dentro del título h2.entry-title > a)
            enlace = t.find_element(By.CSS_SELECTOR, "h2.entry-title a")
            post_url = enlace.get_attribute("href")

            # 3) Extraer la miniatura:
            #    Suponemos que la miniatura está en <a class="post-thumbnail"><img class="wp-post-image"></a>
            try:
                img_el = t.find_element(By.CSS_SELECTOR, "a.post-thumbnail img.wp-post-image")
            except Exception:
                img_el = None  # No se encontró el <img> con esas clases

            entradas.append({
                "fecha": fecha,
                "url": post_url,
                "img_el": img_el
            })
        except Exception as e:
            app.logger.error(f"Tarjeta ignorada (fecha/enlace): {e}")
            continue

    if not entradas:
        app.logger.error("No se encontraron entradas con fecha válida.")
        return None, None, None

    # Seleccionar la entrada más reciente por fecha
    entrada_mas_reciente = max(entradas, key=lambda x: x["fecha"])

    # Extraer URL de la imagen (miniatura) si existe
    imagen_url = None
    if entrada_mas_reciente["img_el"]:
        img_el = entrada_mas_reciente["img_el"]
        # Intentar primero src, luego data-src
        imagen_url = img_el.get_attribute("src") or img_el.get_attribute("data-src")
        # Si está en srcset, tomar la última URL
        if not imagen_url:
            srcset = img_el.get_attribute("srcset")
            if srcset:
                # Partimos por comas: "url1 300w, url2 1024w" -> tomamos url2
                partes = [parte.strip() for parte in srcset.split(",")]
                if partes:
                    ultima = partes[-1].split()[0]
                    imagen_url = ultima if ultima.startswith(("http://", "https://")) else urljoin(url, ultima)

    # Navegar a la página del post para extraer el contenido de texto
    driver.get(entrada_mas_reciente["url"])
    app.logger.info(f"Navegando al post: {entrada_mas_reciente['url']}")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.elementor-widget-container"))
        )
    except Exception as e:
        app.logger.error(f"No se pudo cargar el contenido del post: {e}")
        return None, imagen_url, None

    # Extraer texto: párrafos y encabezados dentro de div.elementor-widget-container
    retries = 3
    texto_extraido = ""
    while retries:
        try:
            bloques = driver.find_elements(
                By.CSS_SELECTOR,
                "div.elementor-widget-container p, div.elementor-widget-container h2, div.elementor-widget-container h3"
            )
            texto_extraido = " ".join(
                b.text.strip() for b in bloques if b.text.strip()
            )
            break
        except StaleElementReferenceException:
            retries -= 1
            time.sleep(1)

    # Convertir la imagen a Base64 (si tenemos URL)
    imagen_base64 = None
    if imagen_url:
        try:
            respuesta = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
            if respuesta.status_code == 200:
                imagen_base64 = base64.b64encode(respuesta.content).decode("utf-8")
        except Exception as e:
            app.logger.error(f"Error descargando la imagen: {e}")

    return texto_extraido, imagen_url, imagen_base64

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    """Endpoint Flask para extraer contenido e imagen del post más reciente."""
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        logger.info(f"Recibida petición para extraer de: {url}")

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
