import os
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.firefox import GeckoDriverManager
import time

app = Flask(__name__)

def configurar_driver():
    firefox_options = Options()
    firefox_options.add_argument("--no-sandbox")
    firefox_options.add_argument("--disable-dev-shm-usage")
    firefox_options.add_argument("--disable-gpu")
    
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)
    return driver

def iniciar_sesion(driver, url, username, password):
    driver.get(url)
    
    # Introducir el nombre de usuario
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.NAME, "LoginControl$UserName"))
    ).send_keys(username)
    
    # Introducir la contraseña
    driver.find_element(By.NAME, "LoginControl$Password").send_keys(password)
    
    # Hacer clic en el botón de iniciar sesión
    boton_iniciar = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.ID, "btn-login"))
    )
    boton_iniciar.click()
    
    # Esperar a que la página se cargue después del login
    WebDriverWait(driver, 20).until(
        EC.url_changes(url)
    )

def hacer_click_en_casos_totales(driver):
    try:
        # Intentar hacer clic en el botón "Casos Totales" usando XPATH
        boton_casos_totales = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Casos totales']"))
        )
        driver.execute_script("arguments[0].scrollIntoView();", boton_casos_totales)  # Desplazarse hasta el botón
        time.sleep(1)  # Añadir pausa antes de hacer clic
        boton_casos_totales.click()
    except Exception as e:
        # Si el clic normal falla, usar JavaScript para forzar el clic
        app.logger.warning(f"El clic en 'Casos Totales' falló. Usando JavaScript para hacer clic: {e}")
        driver.execute_script("arguments[0].click();", boton_casos_totales)

def descargar_escaneo(driver):
    try:
        # Esperar a que aparezca el botón de "Descargar" en la ventana emergente y hacer clic en él
        boton_descargar = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/main/ng-component/eup-dashboard/eup-labexport/div/div/div/div/div[4]/eup-button/button/span[3]"))
        )

        time.sleep(1)  # Añadir una pausa para evitar problemas con la carga
        # Intentar hacer clic en el botón con JavaScript si el clic estándar falla
        driver.execute_script("arguments[0].click();", boton_descargar)
        app.logger.info("Escaneo descargado exitosamente.")

    except Exception as e:
        app.logger.error(f"Error al intentar descargar el escaneo: {e}")
        raise e  # Lanzar el error para ver más detalles

def interactuar_con_pagina(driver):
    # Hacer clic en el botón "Casos Totales"
    hacer_click_en_casos_totales(driver)
    time.sleep(2)  # Pausa para permitir la carga de los datos
    
    # Verificar las primeras 5 filas
    for i in range(5):
        try:
            app.logger.info(f"Procesando fila {i}...")

            # Verificar si el icono de descarga existe en la fila usando XPATH
            icono_descarga_presente = len(driver.find_elements(By.XPATH, f"//tr[@id='tableRow_{i}']//svg[@class='svg-downloadSuccess24']")) > 0
            
            if not icono_descarga_presente:
                app.logger.info(f"Escaneo no descargado en la fila {i}. Procediendo a descargar...")

                # Seleccionar la fila y abrir el menú de opciones
                fila_caso = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.ID, f"tableRow_{i}"))
                )
                
                # Hacer clic izquierdo en la fila
                actions = ActionChains(driver)
                actions.move_to_element(fila_caso).click().perform()

                time.sleep(2)  # Pausa antes de buscar el menú

                # Esperar a que el menú aparezca y hacer clic en "Descargar escaneo"
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//li[contains(., 'Descargar escaneo')]"))
                ).click()

                # Hacer clic en el botón "Descargar" en la ventana emergente
                descargar_escaneo(driver)
                time.sleep(2)  # Pausa después de la descarga
            else:
                app.logger.info(f"El escaneo de la fila {i} ya está descargado. No se requiere acción.")
                time.sleep(1)  # Pausa entre cada fila
        
        except Exception as e:
            app.logger.error(f"Error al procesar la fila {i}: {e}")
            continue

# Endpoint principal para extraer información
@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data or 'username' not in data or 'password' not in data:
            return jsonify({"error": "Datos insuficientes"}), 400

        url = data['url']
        username = data['username']
        password = data['password']
        app.logger.info(f"Iniciando sesión en la URL: {url}")

        driver = configurar_driver()
        iniciar_sesion(driver, url, username, password)  # Iniciar sesión

        interactuar_con_pagina(driver)  # Interactuar con la página después del login

        # Mantener el navegador abierto
        return jsonify({"mensaje": "Interacción completada. Navegador abierto."})
    
    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# Iniciar la aplicación Flask
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
