import os
import base64
import requests
import time
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

# Diccionario para mapear los nombres de meses en español a números
MESES = {m: i for i, m in enumerate(
    ['enero','febrero','marzo','abril','mayo','junio',
     'julio','agosto','septiembre','octubre','noviembre','diciembre'], 1)}

# ---------- CONFIGURAR CHROME HEADLESS ----------
def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")     # Modo headless (Chrome 121+)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)

# ---------- PARSEAR FECHA ----------
def parsear_fecha(fecha_str):
    try:
        partes = fecha_str.lower().replace(',', '').split()
        dia = int(partes[0])
        mes = MESES[partes[1]]
        anio = int(partes[2]) if len(partes) == 3 else datetime.now().year
        return datetime(anio, mes, dia)
    except Exception as e:
        app.logger.error(f"Fecha inválida '{fecha_str}': {e}")
        return None

# ---------- EXTRAER URL DE IMAGEN ----------
def extraer_url_imagen(img_el, base_url):
    """
    Devuelve la mejor URL de una etiqueta <img> o None.
    Prueba src, data-src, data-lazy-src, data-thumb, y srcset.
    Si es relativa, hace urljoin con base_url.
    """
    # 1) Intentar atributos comunes
    cand = (
        img_el.get_attribute("src") or
        img_el.get_attribute("data-src") or
        img_el.get_attribute("data-lazy-src") or
        img_el.get_attribute("data-thumb") or
        ""
    )
    # 2) Si sigue vacío, revisar srcset (tomar la última URL, que suele ser la mayor resolución)
    if not cand:
        srcset = img_el.get_attribute("srcset")
        if srcset:
            partes = [p.strip() for p in srcset.split(',')]
            # cada parte es "url tamaño", tomamos la que esté al final
            ultima = partes[-1].split()[0]
            cand = ultima

    if cand and not cand.startswith(("http://", "https://")):
        cand = urljoin(base_url, cand)
    return cand if cand else None

# ---------- LÓGICA PRINCIPAL ----------
def interactuar_con_pagina(driver, url):
    driver.get(url)
    app.logger.info(f"Página inicial: {driver.current_url}")

    # 1) Esperar a que aparezcan las tarjetas
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.eael-grid-post-holder-inner"))
    )
    tarjetas = driver.find_elements(By.CSS_SELECTOR, "div.eael-grid-post-holder-inner")

    entradas = []
    for t in tarjetas:
        try:
            # 2) Extraer y parsear la fecha
            time_element = t.find_element(By.CSS_SELECTOR, "time")
            fecha_txt = time_element.text.strip()
            fecha = parsear_fecha(fecha_txt)
            if not fecha:
                continue

            # 3) Extraer el enlace del post
            enlace = t.find_element(By.CSS_SELECTOR, "a.eael-grid-post-link")
            post_url = enlace.get_attribute("href")

            # 4) Intentar extraer el <img> dentro del enlace; si falla, img_el = None
            try:
                img_el = enlace.find_element(By.CSS_SELECTOR, "img")
            except Exception:
                img_el = None

            entradas.append({
                "fecha": fecha,
                "url": post_url,
                "img_el": img_el
            })
        except Exception as e:
            app.logger.error(f"Tarjeta ignorada (fecha/enlace): {e}")
            continue

    if not entradas:
        app.logger.error("No se encontraron entradas con fecha válida")
        return None, None, None

    # 5) Seleccionar la entrada más reciente
    entrada = max(entradas, key=lambda x: x["fecha"])

    # 6) Extraer URL de la imagen de la tarjeta (si existe)
    imagen_url = None
    if entrada["img_el"]:
        imagen_url = extraer_url_imagen(entrada["img_el"], url)

    # 7) Navegar al post y extraer texto
    driver.get(entrada["url"])
    app.logger.info(f"Entrando al post: {entrada['url']}")

    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.elementor-widget-container"))
    )

    # 8) Reintentar extracción de texto para evitar StaleElementReferenceException
    retries = 3
    texto_extraido = ""
    while retries:
        try:
            elementos_contenido = driver.find_elements(
                By.CSS_SELECTOR,
                "div.elementor-widget-container p, div.elementor-widget-container h2, div.elementor-widget-container h3"
            )
            texto_extraido = " ".join(
                e.text.strip() for e in elementos_contenido if e.text.strip()
            )
            break
        except StaleElementReferenceException:
            retries -= 1
            time.sleep(1)

    # 9) Descargar la imagen (opcional) y convertir a base64
    imagen_base64 = None
    if imagen_url:
        try:
            respuesta = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
            if respuesta.status_code == 200:
                imagen_base64 = base64.b64encode(respuesta.content).decode("utf-8")
        except Exception as e:
            app.logger.error(f"No se pudo descargar la imagen: {e}")

    return texto_extraido, imagen_url, imagen_base64

# ---------- ENDPOINT FLASK ----------
@app.route("/extraer", methods=["POST"])
def extraer_pagina():
    data = request.json or {}
    url = data.get("url")
    if not url:
        return jsonify({"error": "No se proporcionó URL"}), 400

    driver = configurar_driver()
    try:
        texto, img_url, img_b64 = interactuar_con_pagina(driver, url)
        if texto is None:
            return jsonify({"error": "No se pudo extraer contenido"}), 500
        return jsonify({
            "url": url,
            "contenido": texto,
            "imagen_url": img_url,
            "imagen_base64": img_b64
        })
    except Exception as e:
        app.logger.error(f"Error en /extraer: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        driver.quit()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
