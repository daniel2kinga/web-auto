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
    chrome_options.add_argument("--headless")  # Ejecuta en modo headless (sin interfaz gráfica)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway

    # Agrega el User-Agent para simular un navegador real
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/85.0.4183.83 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def login_y_clic_derecho(driver, url, username, password):
    try:
        # Navegar a la página de inicio de sesión
        driver.get(url)
        app.logger.info(f"Navegando a: {driver.current_url}")

        # Esperar que los campos de usuario y contraseña estén visibles y habilitados
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, "LoginControl$UserName")))
        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.NAME, "LoginControl$Password")))

        # Ingresar las credenciales
        usuario_input = driver.find_element(By.NAME, "LoginControl$UserName")
        contraseña_input = driver.find_element(By.NAME, "LoginControl$Password")

        if usuario_input.is_enabled() and contraseña_input.is_enabled():
            usuario_input.send_keys(username)
            contraseña_input.send_keys(password)
        else:
            app.logger.error("Los campos de usuario o contraseña no están habilitados")
            return None

        # Esperar que el botón de iniciar sesión esté visible y habilitado
        iniciar_sesion_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "btn-login")))

        # Hacer clic en el botón de iniciar sesión
        iniciar_sesion_btn.click()

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
        # Mostrar los datos crudos de la solicitud y los encabezados
        app.logger.info(f"Datos crudos de la solicitud: {request.data.decode('utf-8')}")
        app.logger.info(f"Encabezados de la solicitud: {dict(request.headers)}")

        # Verificar que el Content-Type sea 'application/json'
        if not request.is_json:
            app.logger.error("El contenido de la solicitud no es JSON")
            return jsonify({"error": "El contenido de la solicitud debe ser JSON"}), 400

        data = request.get_json()
        app.logger.info(f"Datos procesados en formato JSON: {data}")

        if not data or 'url' not in data or 'email' not in data or 'password' not in data:
            app.logger.error(f"Datos recibidos incorrectos o incompletos: {data}")
            return jsonify({"error": "No se proporcionaron los datos necesarios"}), 400

        url = data['url']
        username = data['email']
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
    # Configurar el nivel de log para mostrar información detallada
    app.logger.setLevel('DEBUG')
    app.run(host='0.0.0.0', port=port)
