import os
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
from datetime import datetime

app = Flask(__name__)

# Diccionario para mapear los nombres de meses en español a números
MESES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 
    'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9, 
    'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def parsear_fecha(fecha_str):
    """Convierte una fecha en español a un objeto datetime."""
    try:
        partes = fecha_str.lower().replace(',', '').split()
        dia = int(partes[0])
        mes = MESES.get(partes[1])
        anio = datetime.now().year if len(partes) == 2 else int(partes[2])
        return datetime(anio, mes, dia)
    except Exception as e:
        app.logger.error(f"Error al parsear la fecha '{fecha_str}': {e}")
        return None

def interactuar_con_pagina(driver, url):
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.eael-grid-post-holder-inner'))
        )
        entradas = driver.find_elements(By.CSS_SELECTOR, 'div.eael-grid-post-holder-inner')

        entradas_con_fecha = []
        for entrada in entradas:
            try:
                time_element = entrada.find_element(By.CSS_SELECTOR, 'time')
                fecha_str = time_element.text.strip()
                fecha = parsear_fecha(fecha_str)
                if fecha:
                    enlace_element = entrada.find_element(By.CSS_SELECTOR, 'a.eael-grid-post-link')
                    enlace_url = enlace_element.get_attribute('href')
                    entradas_con_fecha.append({'fecha': fecha, 'url': enlace_url, 'entrada_element': entrada})
            except Exception as e:
                app.logger.error(f"Error procesando entrada: {e}")

        if not entradas_con_fecha:
            app.logger.error("No se encontraron entradas con fechas válidas")
            return None, None, None

        entradas_con_fecha.sort(key=lambda x: x['fecha'], reverse=True)
        entrada_mas_reciente = entradas_con_fecha[0]

        # Extraer imagen de la página principal
        try:
            imagen_element = entrada_mas_reciente['entrada_element'].find_element(By.CSS_SELECTOR, 'img')
            imagen_url = imagen_element.get_attribute('src')
        except Exception:
            imagen_url = None

        # Navegar al enlace del blog más reciente
        driver.get(entrada_mas_reciente['url'])
        app.logger.info(f"Navegando a la entrada: {entrada_mas_reciente['url']}")

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.elementor-widget-container'))
        )

        # Extraer contenido del blog
        contenido_elementos = driver.find_elements(By.CSS_SELECTOR, 'div.elementor-widget-container p, div.elementor-widget-container h2, div.elementor-widget-container h3')
        texto_extraido = " ".join([element.text.strip() for element in contenido_elementos if element.text.strip()])

    except Exception as e:
        app.logger.error(f"Error al procesar las entradas: {e}")
        return None, None, None

    # Descargar la imagen
    imagen_base64 = None
    if imagen_url:
        try:
            respuesta = requests.get(imagen_url)
            if respuesta.status_code == 200:
                imagen_base64 = base64.b64encode(respuesta.content).decode('utf-8')
        except Exception as e:
            app.logger.error(f"Error descargando la imagen: {e}")

    return texto_extraido, imagen_url, imagen_base64

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    driver = configurar_driver()
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        texto_extraido, imagen_url, imagen_base64 = interactuar_con_pagina(driver, url)

        if texto_extraido is None:
            return jsonify({"error": "No se pudo extraer el contenido"}), 500

        return jsonify({
            "url": url,
            "contenido": texto_extraido,
            "imagen_url": imagen_url,
            "imagen_base64": imagen_base64
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        driver.quit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
