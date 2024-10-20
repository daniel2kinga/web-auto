from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright
import base64
import os

app = Flask(__name__)

@app.route('/extraer', methods=['POST'])
def extraer_pagina():
    try:
        data = request.json
        if not data or 'url' not in data:
            return jsonify({"error": "No se proporcionó URL"}), 400

        url = data['url']
        app.logger.info(f"Extrayendo contenido de la URL: {url}")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Navegar a la página principal
            page.goto(url)
            app.logger.info(f"Navegando a: {page.url}")

            # Esperar a que el contenido cargue
            page.wait_for_selector('article.post', timeout=10000)

            # Obtener el enlace al primer artículo
            first_article = page.query_selector('article.post h2.entry-title a')
            if not first_article:
                app.logger.error("No se encontró el enlace al primer artículo")
                return jsonify({"error": "No se encontró el enlace al primer artículo"}), 500

            post_url = first_article.get_attribute('href')
            app.logger.info(f"URL del artículo encontrado: {post_url}")

            # Navegar al artículo
            page.goto(post_url)
            app.logger.info(f"Navegando al artículo: {page.url}")

            # Esperar a que el contenido del artículo cargue
            page.wait_for_selector('div.entry-content', timeout=10000)

            # Extraer el contenido del artículo
            contenido_elements = page.query_selector_all('div.entry-content p')
            texto_extraido = " ".join([element.inner_text() for element in contenido_elements])

            # Obtener la imagen del artículo
            imagen_element = page.query_selector('div.entry-content img')
            if imagen_element:
                imagen_url = imagen_element.get_attribute('src')
                # Descargar la imagen y codificarla en Base64
                imagen_respuesta = requests.get(imagen_url)
                if imagen_respuesta.status_code == 200:
                    imagen_base64 = base64.b64encode(imagen_respuesta.content).decode('utf-8')
                else:
                    imagen_base64 = None
                    app.logger.error(f"No se pudo descargar la imagen, código de estado: {imagen_respuesta.status_code}")
            else:
                imagen_url = None
                imagen_base64 = None
                app.logger.error("No se encontró la imagen en el artículo")

            response_data = {
                "url": post_url,
                "contenido": texto_extraido,
                "imagen_url": imagen_url,
                "imagen_base64": imagen_base64
            }

            return jsonify(response_data)

    except Exception as e:
        app.logger.error(f"Error al procesar la solicitud: {e}", exc_info=True)
        return jsonify({"error": "Error interno del servidor", "details": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
