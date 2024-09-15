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

# Configuración del driver de Selenium
def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Función para iniciar sesión y hacer clic en el botón derecho
def login_y_clic_derecho(driver, url, username, password):
    driver.get(url)

    # Esperar a que el campo de usuario esté presente
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "LoginControl$UserName")))

        # Ingresar el nombre de usuario
        user_input = driver.find_element(By.NAME, "LoginControl$UserName")
        user_input.clear()
        user_input.send_keys(username)

        # Ingresar la contraseña
        password_input = driver.find_element(By.NAME, "LoginControl$Password")
        password_input.clear()
        password_input.send_keys(password)

        # Hacer clic en el botón "Iniciar sesión"
        boton_iniciar = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "btn-login")))
        boton_iniciar.click()

        # Comprobar si el inicio de sesión fue exitoso
        if verificar_sesion_iniciada(driver):
            return driver.page_source
        else:
            raise Exception("Error durante el inicio de sesión")
    except Exception as e:
        app.logger.error(f"Error durante el inicio de sesión: {e}")
        return None

# Verificar si la sesión ya está iniciada
def verificar_sesion_iniciada(driver):
    try:
        # Aquí puedes ajustar el selector para un elemento específico que solo aparece cuando la sesión está iniciada
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//elemento_que_confirma_sesion_iniciada")))
        return True
    except:
        return False

# Ruta principal para manejar la solicitud HTTP
@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "No se proporcionaron todos los parámetros necesarios"}), 400

        url = data['url']
        username = data['username']
        password = data['password']

        app.logger.info(f"Extrayendo contenido de la URL: {url}")

        driver = configurar_driver()
        html_final = login_y_clic_derecho(driver, url, username, password)

        if html_final:
            driver.quit()
            return jsonify({"url": url, "contenido": html_final})
        else:
            driver.quit()
            return jsonify({"error": "Error durante el inicio de sesión"}), 500

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
