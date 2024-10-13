import os
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
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-cache")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver):
    # Navegar a la página principal
    driver.get('https://www.cnet.com/ai-atlas/')
    app.logger.info(f"Navegando a: {driver.current_url}")
    
    # Esperar a que la sección 'Reviews' esté presente
    reviews_section = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//h2[contains(text(), "Reviews")]'))
    )
    driver.execute_script("arguments[0].scrollIntoView();", reviews_section)
    time.sleep(2)  # Esperar un poco para asegurar que el contenido se carga

    # Encontrar y hacer clic en la imagen de la primera ventana en la sección 'Reviews'
    reviews_parent = reviews_section.find_element(By.XPATH, './following-sibling::*[1]')
    first_review_link = reviews_parent.find_element(By.XPATH, './/a')
    first_review_link.click()
    app.logger.info(f"Después de hacer clic, URL actual: {driver.current_url}")

    # Esperar a que la nueva página cargue completamente
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "p")))

    # Extraer el contenido de la página actual
    contenido = driver.find_elements(By.TAG_NAME, "p")
    texto_extraido = " ".join([element.text for element in contenido])
    app.logger.info(f"Texto extraído: {texto_extraido[:500]}...")  # Mostrar solo los primeros 500 caracteres

    return texto_extraido

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    driver = configurar_driver()
    try:
        # Manejar datos enviados en la solicitud POST (si es necesario)
        data = request.get_json()
        if data and 'url' in data:
            # Si se proporciona una URL en la solicitud, se puede utilizar aquí
            url = data['url']
            app.logger.info(f"Navegando a la URL proporcionada: {url}")
            driver.get(url)
            # Opcionalmente, puedes modificar 'interactuar_con_pagina' para aceptar una URL
        else:
            app.logger.info("No se proporcionó URL, utilizando el flujo predeterminado.")

        texto_extraido = interactuar_con_pagina(driver)
        return jsonify({"contenido": texto_extraido})
    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500
    finally:
        driver.quit()

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
