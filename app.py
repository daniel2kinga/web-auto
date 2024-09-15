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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_y_clic_derecho(driver, url, username, password):
    try:
        driver.get(url)
        
        # Esperar hasta que se cargue el campo de email
        wait = WebDriverWait(driver, 20)
        campo_usuario = wait.until(EC.presence_of_element_located((By.NAME, "LoginControl$UserName")))
        campo_usuario.send_keys(username)

        # Esperar hasta que se cargue el campo de contraseña
        campo_password = wait.until(EC.presence_of_element_located((By.NAME, "LoginControl$Password")))
        campo_password.send_keys(password)

        # Esperar hasta que el botón "Iniciar sesión" esté interactuable
        boton_iniciar = wait.until(EC.element_to_be_clickable((By.ID, "btn-login")))
        boton_iniciar.click()

        # Verificar si la sesión se ha iniciado correctamente
        if verificar_sesion_iniciada(driver):
            app.logger.info("Sesión iniciada correctamente.")
            return driver.page_source
        else:
            app.logger.error("El inicio de sesión no fue exitoso.")
            return None
    except Exception as e:
        app.logger.error(f"Error durante el inicio de sesión: {e}")
        return None

def verificar_sesion_iniciada(driver):
    try:
        # Verificar si un elemento presente después de iniciar sesión está disponible
        wait = WebDriverWait(driver, 20)
        elemento_autenticado = wait.until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))  # Ejemplo de un elemento posterior al login
        )
        return True
    except:
        return False

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "No se proporcionó URL, usuario o contraseña"}), 400

        url = data['url']
        username = data['username']
        password = data['password']

        driver = configurar_driver()
        html_final = login_y_clic_derecho(driver, url, username, password)

        if html_final:
            driver.quit()
            return jsonify({"url": url, "contenido": html_final})
        else:
            driver.quit()
            return jsonify({"error": "Fallo en el inicio de sesión"}), 500

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
