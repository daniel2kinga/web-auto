import os
import time
import logging
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Configuración del logger para imprimir mensajes en la terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar en modo headless
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-gpu-sandbox")

    # Configuraciones adicionales para Chrome
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-notifications")

    # Configuraciones para impresión sin ventana emergente
    prefs = {
        "printing.print_preview_sticky_settings.appState": '{"recentDestinations":[{"id":"Save as PDF","origin":"local"}],"selectedDestinationId":"Save as PDF","version":2}',
        "savefile.default_directory": os.getcwd(),
        "download.default_directory": os.getcwd(),
        "profile.default_content_settings.popups": 0,
        "download.prompt_for_download": False,
        "printing.default_destination_selection_rules": {
            "kind": "local",
            "namePattern": "Save as PDF",
        },
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--kiosk-printing")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def iniciar_sesion(driver, url, username, password):
    driver.get(url)
    logger.info("Página de inicio cargada.")

    # Introducir el nombre de usuario
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.NAME, "LoginControl$UserName"))
    ).send_keys(username)
    logger.info("Nombre de usuario ingresado.")

    # Introducir la contraseña
    driver.find_element(By.NAME, "LoginControl$Password").send_keys(password)
    logger.info("Contraseña ingresada.")

    # Hacer clic en el botón de iniciar sesión
    boton_iniciar = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "btn-login"))
    )
    boton_iniciar.click()
    logger.info("Botón de iniciar sesión clicado.")

    # Esperar a que la página se cargue después del login
    WebDriverWait(driver, 40).until(
        lambda d: d.current_url != url
    )
    logger.info("Sesión iniciada correctamente.")

def hacer_click_en_casos_totales(driver):
    try:
        # Intentar hacer clic en el botón "Casos Totales" usando XPATH
        boton_casos_totales = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()='Casos totales']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", boton_casos_totales)
        time.sleep(2)
        boton_casos_totales.click()
        logger.info("Botón 'Casos Totales' clicado.")
    except Exception as e:
        logger.warning(f"El clic en 'Casos Totales' falló: {e}")
        driver.execute_script("arguments[0].click();", boton_casos_totales)

def imprimir_prescripcion(driver):
    try:
        logger.info("Imprimiendo prescripción.")
        time.sleep(8)  # Aumentar tiempo para asegurar la conexión con la impresora
    except Exception as e:
        logger.error(f"Error al intentar imprimir la prescripción: {e}")
        raise e

def interactuar_con_pagina(driver):
    hacer_click_en_casos_totales(driver)
    time.sleep(7)  # Aumentar el tiempo para permitir la carga de los datos

    for i in range(5):  # Verificar las primeras 5 filas
        try:
            logger.info(f"Procesando fila {i}...")

            # Esperar a que la fila esté presente
            fila_xpath = f"//tr[@id='tableRow_{i}']"
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located((By.XPATH, fila_xpath))
            )

            # Obtener el td con clase 'col-action'
            td_xpath = f"{fila_xpath}//td[contains(@class, 'col-action')]"
            td_col_action = driver.find_element(By.XPATH, td_xpath)

            # Verificar si el ícono de prescripción impresa existe en la fila usando su clase
            if len(td_col_action.find_elements(By.CLASS_NAME, "svg-printSuccess24")) > 0:
                logger.info(f"Icono de prescripción impresa visible en la fila {i}. No se requiere impresión.")
                continue  # Saltar a la siguiente fila si el ícono está presente
            else:
                logger.info(f"No se encontró el icono de prescripción impresa en la fila {i}. Procediendo a imprimir...")

            # Seleccionar la fila y abrir el menú de opciones (clic izquierdo)
            fila_caso = driver.find_element(By.XPATH, fila_xpath)
            driver.execute_script("arguments[0].scrollIntoView(true);", fila_caso)
            time.sleep(1)

            # Usar clic izquierdo para abrir el menú
            ActionChains(driver).move_to_element(fila_caso).click().perform()
            logger.info(f"Clic izquierdo realizado en la fila {i}.")

            # Esperar a que el menú aparezca y seleccionar "Imprimir prescripción"
            try:
                imprimir_opcion = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//li/span[contains(text(),'Imprimir prescripción')]"))
                )
                driver.execute_script("arguments[0].click();", imprimir_opcion)
                logger.info(f"Opción 'Imprimir prescripción' seleccionada.")

                # Realizar la impresión real
                imprimir_prescripcion(driver)
                time.sleep(5)  # Pausa después de la impresión
            except TimeoutException:
                logger.warning(f"La opción 'Imprimir prescripción' no apareció en la fila {i}. Continuando con la siguiente fila.")
                continue

        except (ElementNotInteractableException, TimeoutException, NoSuchElementException) as e:
            logger.error(f"Error al procesar la fila {i}: {e}")
            continue
        except Exception as e:
            logger.error(f"Error inesperado al procesar la fila {i}: {e}")
            continue

def cerrar_navegador(driver):
    driver.quit()
    logger.info("Navegador cerrado.")

def proceso_completo(url, username, password):
    logger.info("====== Iniciando proceso de automatización ======")
    driver = configurar_driver()
    try:
        iniciar_sesion(driver, url, username, password)
        interactuar_con_pagina(driver)
    except Exception as e:
        logger.error(f"Error en el proceso: {e}")
    finally:
        cerrar_navegador(driver)

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
        logger.info(f"Iniciando sesión en la URL: {url}")

        # Ejecutar el proceso completo una vez
        proceso_completo(url, username, password)

        return jsonify({"mensaje": "Interacción completada exitosamente."})

    except Exception as e:
        logger.error(f"Error al procesar la solicitud: {e}")
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

# No incluimos el bloque if __name__ == '__main__' para permitir que Gunicorn lo maneje
