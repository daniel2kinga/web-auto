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
    try:
        # Navegar a la página de inicio de sesión
        driver.get(url)
        app.logger.info(f"Navegando a: {driver.current_url}")

        # Esperar que los campos de usuario y contraseña estén presentes
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "LoginControl$UserName")))
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "LoginControl$Password")))

        # Ingresar las credenciales
        driver.find_element(By.NAME, "LoginControl$UserName").send_keys(username)
        driver.find_element(By.NAME, "LoginControl$Password").send_keys(password)

        # Hacer clic en el botón de iniciar sesión
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "btn-login")))
        driver.find_element(By.ID, "btn-login").click()

        # Esperar a que la nueva página cargue completamente después del login
        time.sleep(5)
        app.logger.info(f"Login exitoso: {driver.current_url}")
        return driver.page_source
    
    except Exception as e:
        app.logger.error(f"Error durante el inicio de sesión: {str(e)}")
        return None

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        app.logger.info(f"Datos recibidos en la solicitud: {request.get_data()}")
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            app.logger.error(f"Datos recibidos incorrectos: {data}")
            return jsonify({"error": "No se proporcionaron los datos necesarios"}), 400

        url = data['url']
        username = data['username']
        password = data['password']
        app.logger.info(f"Iniciando sesión en la URL: {url} con usuario: {username}")

        driver = configurar_driver()
        html_final = login_y_clic_derecho(driver, url, username, password)

        if html_final:
            driver.quit()
            return jsonify({"url": url, "contenido": html_final})
        else:
            driver.quit()
            return jsonify({"error": "Falló el inicio de sesión o la extracción de datos"}), 500

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
