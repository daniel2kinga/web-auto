import os, base64, requests, time
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

MESES = {m: i for i, m in enumerate(
    ['enero','febrero','marzo','abril','mayo','junio',
     'julio','agosto','septiembre','octubre','noviembre','diciembre'], 1)}

# ---------- CONFIGURAR CHROME HEADLESS ----------
def configurar_driver():
    co = Options()
    co.add_argument("--headless=new")           # Chrome 121+
    co.add_argument("--no-sandbox")
    co.add_argument("--disable-dev-shm-usage")
    co.add_argument("--disable-gpu")
    co.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=co)

# ---------- FECHA ----------
def parsear_fecha(fecha_str):
    try:
        d, mes, *resto = fecha_str.lower().replace(',', '').split()
        dia = int(d)
        anio = int(resto[0]) if resto else datetime.now().year
        return datetime(anio, MESES[mes], dia)
    except Exception as e:
        app.logger.error(f"Fecha inválida '{fecha_str}': {e}")
        return None

# ---------- NUEVA FUNCIÓN: EXTRAE LA URL DE LA IMAGEN ----------
def extraer_url_imagen(img_el, base_url):
    """Devuelve la mejor URL de una etiqueta <img> o None."""
    cand = (
        img_el.get_attribute("src")                              or
        img_el.get_attribute("data-src")                         or
        img_el.get_attribute("data-lazy-src")                    or
        img_el.get_attribute("data-thumb")                       or
        ""
    )
    if not cand:                         # ¿lazy con srcset?
        srcset = img_el.get_attribute("srcset")
        if srcset:
            # nos quedamos con la última (mayor resolución)
            cand = srcset.strip().split()[-2]  # formato: url   1024w
    if cand and not cand.startswith(("http://", "https://")):
        cand = urljoin(base_url, cand)
    return cand if cand else None

# ---------- LÓGICA PRINCIPAL ----------
def interactuar_con_pagina(driver, url):
    driver.get(url)
    app.logger.info(f"Página inicial: {driver.current_url}")

    # esperar tarjetas
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.eael-grid-post-holder-inner"))
    )
    tarjetas = driver.find_elements(By.CSS_SELECTOR, "div.eael-grid-post-holder-inner")

    entradas = []
    for t in tarjetas:
        try:
            fecha_txt = t.find_element(By.CSS_SELECTOR, "time").text.strip()
            fecha = parsear_fecha(fecha_txt)
            if not fecha:
                continue
            enlace = t.find_element(By.CSS_SELECTOR, "a.eael-grid-post-link")
            entradas.append({
                "fecha": fecha,
                "url": enlace.get_attribute("href"),
                "img_el": enlace.find_element(By.CSS_SELECTOR, "img") if enlace else None
            })
        except Exception as e:
            app.logger.error(f"Tarjeta ignorada: {e}")

    if not entradas:
        return None, None, None

    # más reciente
    entrada = max(entradas, key=lambda x: x["fecha"])

    # ---- imagen de la tarjeta ----
    imagen_url = extraer_url_imagen(entrada["img_el"], url) if entrada["img_el"] else None

    # ---- navegar al post y extraer texto ----
    driver.get(entrada["url"])
    app.logger.info(f"Entrando al post: {entrada['url']}")
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "div.elementor-widget-container"))
    )

    retries, texto = 3, ""
    while retries:
        try:
            bloques = driver.find_elements(
                By.CSS_SELECTOR,
                "div.elementor-widget-container p, div.elementor-widget-container h2, div.elementor-widget-container h3"
            )
            texto = " ".join(b.text.strip() for b in bloques if b.text.strip())
            break
        except StaleElementReferenceException:
            retries -= 1
            time.sleep(1)

    # ---- descargar imagen ----
    imagen_b64 = None
    if imagen_url:
        try:
            r = requests.get(imagen_url, headers={"User-Agent": "Mozilla/5.0"})
            if r.ok:
                imagen_b64 = base64.b64encode(r.content).decode()
        except Exception as e:
            app.logger.error(f"No se pudo descargar la imagen: {e}")

    return texto, imagen_url, imagen_b64

# ---------- ENDPOINT ----------
@app.route("/extraer", methods=["POST"])
def extraer_pagina():
    data = request.json or {}
    url = data.get("url")
    if not url:
        return jsonify(error="No se proporcionó URL"), 400

    driver = configurar_driver()
    try:
        texto, img_url, img_b64 = interactuar_con_pagina(driver, url)
        if texto is None:
            return jsonify(error="No se pudo extraer contenido"), 500
        return jsonify(url=url, contenido=texto, imagen_url=img_url, imagen_base64=img_b64)
    finally:
        driver.quit()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
