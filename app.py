import os
import base64
import requests
import time
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

app = Flask(__name__)

# Diccionario para mapear los nombres de meses en español a números
MESES = {
    'enero': 1,
    'febrero': 2,
    'marzo': 3,
    'abril': 4,
    'mayo': 5,
    'junio': 6,
    'julio': 7,
    'agosto': 8,
    'septiembre': 9,
    'octubre': 10,
    'noviembre': 11,
    'diciembre': 12
}

def configurar_driver():
    chrome_options = Options()
    # Puedes comentar la siguiente línea para ver el navegador en acción
    chrome_options.add_argument("--headless")  # Ejecutar en modo headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument('--blink-settings=imagesEnabled=true')
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-cache")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
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

def parsear_fecha(fecha_str):
    """
    Convierte una cadena de fecha en español a un objeto datetime.
    Ejemplo de entrada: "31 octubre, 2024"
    """
    try:
        partes = fecha_str.lower().replace(',', '').split()
        if len(partes) != 3:
            raise ValueError("Formato de fecha incorrecto")
        dia = int(partes[0])
        mes = MESES.get(partes[1])
        anio = int(partes[2])
        if not mes:
            raise ValueError(f"Mes desconocido: {partes[1]}")
        return datetime(anio, mes, dia)
    except Exception as e:
        app.logger.error(f"Error al parsear la fecha '{fecha_str}': {e}")
        return None

def interactuar_con_pagina(driver, url):
    # Navegar a la URL proporcionada
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        # Esperar a que las entradas del blog estén presentes
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.eael-entry-wrapper'))
        )
        app.logger.info("Entradas del blog encontradas")

        # Encontrar todas las entradas del blog
        entradas = driver.find_elements(By.CSS_SELECTOR, 'div.eael-entry-wrapper')

        if not entradas:
            app.logger.error("No se encontraron entradas en la página")
            return None, None, None

        entradas_con_fecha = []

        for entrada in entradas:
            try:
                # Encontrar el elemento <time> dentro de la entrada
                time_element = entrada.find_element(By.CSS_SELECTOR, 'time')
                fecha_str = time_element.get_attribute('datetime')
                fecha = parsear_fecha(fecha_str)
                if fecha:
                    # Obtener el enlace a la entrada
                    enlace_element = entrada.find_element(By.CSS_SELECTOR, 'a.eael-grid-post-link')
                    enlace_url = enlace_element.get_attribute('href')
                    entradas_con_fecha.append({
                        'fecha': fecha,
                        'url': enlace_url
                    })
                    app.logger.info(f"Entrada encontrada: Fecha={fecha_str}, URL={enlace_url}")
                else:
                    app.logger.warning(f"No se pudo parsear la fecha: {fecha_str}")
            except Exception as e:
                app.logger.error(f"Error al procesar una entrada del blog: {e}")
                continue

        if not entradas_con_fecha:
            app.logger.error("No se encontraron entradas con fechas válidas")
            return None, None, None

        # Ordenar las entradas por fecha descendente y seleccionar la más reciente
        entradas_con_fecha.sort(key=lambda x: x['fecha'], reverse=True)
        entrada_mas_reciente = entradas_con_fecha[0]
        app.logger.info(f"Entrada más reciente: Fecha={entrada_mas_reciente['fecha'].strftime('%Y-%m-%d')}, URL={entrada_mas_reciente['url']}")

        # Navegar a la URL de la entrada más reciente
        driver.get(entrada_mas_reciente['url'])
        app.logger.info(f"Navegando a la entrada más reciente: {driver.current_url}")

    except Exception as e:
        app.logger.error(f"No se pudo procesar las entradas del blog: {e}")
        screenshot_path = "error_processing_blog_entries.png"
        driver.save_screenshot(screenshot_path)
        app.logger.error(f"Captura de pantalla guardada en {screenshot_path}")
        return None, None, None

    # Esperar a que la página de la entrada cargue completamente
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "img"))
        )
        app.logger.info("Página de la entrada cargada completamente")
    except Exception as e:
        app.logger.error(f"Error al cargar la página de la entrada: {e}")
        screenshot_path = "error_loading_entry_page.png"
        driver.save_screenshot(screenshot_path)
        app.logger.error(f"Captura de pantalla guardada en {screenshot_path}")
        return None, None, None

    # Extraer el contenido de la página actual
    try:
        contenido = driver.find_elements(By.TAG_NAME, "p")
        texto_extraido = " ".join([element.text for element in contenido])
        app.logger.info(f"Texto extraído: {texto_extraido[:500]}...")
    except Exception as e:
        app.logger.error(f"Error al extraer el contenido de la página: {e}")
        texto_extraido = ""

    # Desplazar hasta el final de la página para cargar todas las imágenes
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)  # Aumentamos el tiempo de espera para asegurar que las imágenes carguen

    # Listar todas las imágenes para identificar el selector correcto
    try:
        imagenes = driver.find_elements(By.TAG_NAME, 'img')
        app.logger.info(f"Total de imágenes encontradas: {len(imagenes)}")
        for idx, img in enumerate(imagenes, start=1):
            src = img.get_attribute('src')
            alt = img.get_attribute('alt')
            class_attr = img.get_attribute('class')
            app.logger.info(f"Imagen {idx}: src='{src}', alt='{alt}', class='{class_attr}'")
    except Exception as e:
        app.logger.error(f"Error al listar imágenes: {e}")

    # Intentar encontrar la imagen principal
    imagen_url = None
    imagen_base64 = None

    try:
        # Ajustar el selector según las clases encontradas
        # Por ejemplo, si la imagen tiene la clase 'attachment-full size-full'
        imagen_element = driver.find_element(By.CSS_SELECTOR, 'img.attachment-full.size-full')

        # Verificar atributos de la imagen
        imagen_url = imagen_element.get_attribute('src')
        if not imagen_url or not imagen_url.startswith('http'):
            imagen_url = imagen_element.get_attribute('data-src') or imagen_element.get_attribute('data-lazy-src')

        app.logger.info(f"URL de la imagen encontrada: {imagen_url}")
    except Exception as e:
        app.logger.error(f"No se pudo encontrar la imagen en la entrada: {e}")
        driver.save_screenshot("error_finding_image.png")
        imagen_url = None

    # Descargar la imagen y codificarla en Base64
    if imagen_url and imagen_url.startswith("http"):
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

        texto_extraido, imagen_url, imagen_base64 = interactuar_con_pagina(driver, url)

        if texto_extraido is None:
            return jsonify({"error": "No se pudo extraer el texto"}), 500

        # Preparar la respuesta con el texto y la imagen
        response_data = {
            "url": url,
            "contenido": texto_extraido,
            "imagen_url": imagen_url,
            "imagen_base64": imagen_base64
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
