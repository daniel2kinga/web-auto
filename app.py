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
    chrome_options.add_argument("--headless")  # Puedes quitar esto si quieres ver la automatización en pantalla
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_y_clic_derecho(driver, url, username, password):
    # Navegar a la página de inicio de sesión
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    # Esperar a que los campos de usuario y contraseña estén presentes
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username")))  # Asegúrate de que ID sea el correcto
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "password")))  # Asegúrate de que ID sea el correcto

    # Ingresar las credenciales
    driver.find_element(By.ID, "username").send_keys(username)  # Cambia el ID si es necesario
    driver.find_element(By.ID, "password").send_keys(password)  # Cambia el ID si es necesario

    # Hacer clic en el botón de iniciar sesión
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[text()='Iniciar sesión']")))  # Cambia el XPATH si es necesario
    driver.find_element(By.XPATH, "//button[text()='Iniciar sesión']").click()

    # Esperar a que la nueva página cargue completamente después del login
    time.sleep(5)  # Esto puede ajustarse si la página tarda más en cargar

    app.logger.info(f"Login exitoso: {driver.current_url}")
    return driver.page_source

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "No se proporcionaron los datos necesarios"}), 400

        url = data['url']
        username = data['username']
        password = data['password']
        app.logger.info(f"Iniciando sesión en la URL: {url}")

        driver = configurar_driver()
        html_final = login_y_clic_derecho(driver, url, username, password)

        driver.quit()
        return jsonify({"url": url, "contenido": html_final})

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

        driver = configurar_driver()
        html_final = interactuar_con_pagina(driver, url)  # Interactuar con la página

        # Extraer el contenido de la página actual
        contenido = driver.find_elements(By.TAG_NAME, "p")
        texto_extraido = " ".join([element.text for element in contenido])
        app.logger.info(f"Texto extraído: {texto_extraido}")

        driver.quit()
        return jsonify({"url": url, "contenido": texto_extraido})

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
