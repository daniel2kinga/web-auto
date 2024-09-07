from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from flask import Flask, request, jsonify
import time

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(executable_path="/usr/local/bin/chromedriver", options=chrome_options)
    return driver

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        
        driver = configurar_driver()
        driver.get(url)
        time.sleep(5)
        
        # Capturar contenido de la página
        contenido = driver.find_elements_by_tag_name("p")
        texto_extraido = " ".join([element.text for element in contenido])
        
        driver.quit()
        return jsonify({"url": url, "contenido": texto_extraido})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
