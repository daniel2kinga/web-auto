from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

def configurar_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Ejecutar en modo headless (sin interfaz gráfica)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

@app.route('/conectar', methods=['GET'])
def conectar_pagina():
    try:
        # Configurar el driver de Selenium
        driver = configurar_driver()

        # Navegar a la página de inicio de sesión de iTero
        url = 'https://bff.cloud.myitero.com/login'
        driver.get(url)

        # Obtener el título de la página o cualquier información que quieras
        titulo_pagina = driver.title

        # Cerrar el driver de Selenium
        driver.quit()

        # Retornar la información obtenida
        return jsonify({"message": "Conectado a la página", "titulo_pagina": titulo_pagina})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Configurar el servidor para usar el puerto proporcionado por Railway o un puerto local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
