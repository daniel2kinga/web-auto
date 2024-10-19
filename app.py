import os
import time
import base64
import requests
from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Ejecutar en modo headless (comentado para depuración)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-cache")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--window-size=1920,1080")
    # User-Agent personalizado
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def interactuar_con_pagina(driver, url):
    driver.get(url)
    app.logger.info(f"Navegando a: {driver.current_url}")

    try:
        # Esperar a que el elemento sea clicable
        first_element = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'article.post h2.entry-title a'))
        )
        app.logger.info("Primer elemento encontrado y clicable")

        # Verificar visibilidad y estado
        is_displayed = first_element.is_displayed()
        is_enabled = first_element.is_enabled()
        app.logger.info(f"Visible: {is_displayed}, Habilitado: {is_enabled}")

        # Desplazarse al elemento
        driver.execute_script("arguments[0].scrollIntoView(true);", first_element)
        time.sleep(1)

        # Hacer clic usando ActionChains
        actions = ActionChains(driver)
        actions.move_to_element(first_element).click().perform()
        app.logger.info("Hizo clic en el primer elemento")

        # Esperar a que la nueva página cargue
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.entry-content'))
        )
        app.logger.info("Página del artículo cargada")

    except Exception as e:
        app.logger.error("Error al hacer clic en el primer elemento", exc_info=True)
        return None, None, None

    # Extraer contenido e imagen...
    # (El resto del código permanece igual)

# El resto del código permanece igual
