import os
import time
import traceback
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

# Configurar el driver de Selenium
def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Verificar si la sesión ya está iniciada
def verificar_sesion_iniciada(driver):
    try:
        wait = WebDriverWait(driver, 10)
        elemento_autenticado = wait.until(EC.presence_of_element_located((By.ID, "logoutButton")))  # Cambia el ID según el elemento que indique una sesión iniciada
        return True if elemento_autenticado else False
    except:
        return False

# Iniciar sesión y realizar clic derecho en un elemento
def login_y_clic_derecho(driver, url, username, password):
    driver.get(url)
    time.sleep(3)  # Esperar a que la página cargue

    # Verificar si la sesión ya está iniciada
    if verificar_sesion_iniciada(driver):
        app.logger.info("Sesión ya iniciada.")
        return driver.page_source  # Si la sesión ya está iniciada, retornar el HTML actual

    try:
        # Ingresar nombre de usuario
        input_usuario = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "LoginControl$UserName")))
        input_usuario.clear()
        input_usuario.send_keys(username)

        # Ingresar contraseña
        input_contrasena = driver.find_element(By.NAME, "LoginControl$Password")
        input_contrasena.clear()
        input_contrasena.send_keys(password)

        # Hacer clic en el botón de "Iniciar sesión"
        boton_iniciar = driver.find_element(By.ID, "btn-login")
        boton_iniciar.click()

        # Esperar a que la página cargue después del inicio de sesión
        WebDriverWait(driver, 10).until(EC.url_changes(url))

        # Verificar si el inicio de sesión fue exitoso
        if not verificar_sesion_iniciada(driver):
            app.logger.error("El inicio de sesión no fue exitoso.")
            return None

        app.logger.info("Inicio de sesión exitoso.")
        return driver.page_source  # Retornar el HTML de la página después del inicio de sesión

    except Exception as e:
        app.logger.error(f"Error durante el inicio de sesión: {e}")
        app.logger.error(traceback.format_exc())
        return None

# Ruta para extraer el contenido de la página
@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "No se proporcionaron todos los datos necesarios (url, username, password)"}), 400

        url = data['url']
        username = data['username']
        password = data['password']

        app.logger.info(f"Extrayendo contenido de la URL: {url}")

        driver = configurar_driver()

        # Iniciar sesión y obtener el HTML resultante
        html_final = login_y_clic_derecho(driver, url, username, password)

        if html_final is None:
            return jsonify({"error": "Error al iniciar sesión o al extraer la página"}), 500

        # Extraer el contenido final de la página (en este caso, todos los párrafos <p>)
        contenido = driver.find_elements(By.TAG_NAME, "p")
        texto_extraido = " ".join([element.text for element in contenido])

        driver.quit()
        return jsonify({"url": url, "contenido": texto_extraido})

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
