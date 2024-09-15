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
    chrome_options.add_argument("--remote-debugging-port=9222")  # Necesario para Railway
    chrome_options.add_argument("--disable-cache")  # Desactivar caché

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def iniciar_sesion(driver, url, username, password):
    # Navegar a la página de inicio de sesión
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        # Esperar que los campos de usuario y contraseña sean visibles
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.NAME, "LoginControl$UserName")))
        WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.NAME, "LoginControl$Password")))
        WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.ID, "btn-login")))

        # Ingresar el nombre de usuario y la contraseña
        usuario_input = driver.find_element(By.NAME, "LoginControl$UserName")
        password_input = driver.find_element(By.NAME, "LoginControl$Password")
        boton_iniciar = driver.find_element(By.ID, "btn-login")

        usuario_input.clear()
        usuario_input.send_keys(username)
        app.logger.info("Usuario ingresado correctamente.")

        password_input.clear()
        password_input.send_keys(password)
        app.logger.info("Contraseña ingresada correctamente.")

        time.sleep(2)  # Pausa breve para asegurar que los datos se ingresen correctamente

        # Hacer clic en el botón de iniciar sesión
        boton_iniciar.click()
        app.logger.info("Botón de iniciar sesión clickeado.")

        # Esperar que la página cambie después de iniciar sesión
        WebDriverWait(driver, 15).until(EC.url_changes(url))
        app.logger.info("Inicio de sesión exitoso.")

        # Retornar el contenido HTML de la página después del inicio de sesión
        html_final = driver.page_source
        return html_final

    except Exception as e:
        app.logger.error(f"Error durante el inicio de sesión: {e}")
        raise e

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Datos incompletos"}), 400

        url = data['url']
        username = data['username']
        password = data['password']
        app.logger.info(f"Extrayendo contenido de la URL: {url}")

        driver = configurar_driver()
        html_final = iniciar_sesion(driver, url, username, password)

        driver.quit()
        return jsonify({"url": url, "contenido_html": html_final[:1000]})  # Retornar solo los primeros 1000 caracteres del HTML

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
