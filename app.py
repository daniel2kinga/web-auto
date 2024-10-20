from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
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

        # Obtener el contenido de la página principal
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Encontrar el enlace al primer artículo
        first_article = soup.select_one('article.post')
        if not first_article:
            app.logger.error("No se encontró el primer artículo")
            return jsonify({"error": "No se encontró el primer artículo"}), 500

        post_link_element = first_article.select_one('h2.entry-title a')
        if not post_link_element:
            app.logger.error("No se encontró el enlace al artículo")
            return jsonify({"error": "No se encontró el enlace al artículo"}), 500

        post_url = post_link_element['href']
        app.logger.info(f"URL del artículo encontrado: {post_url}")

        # Obtener el contenido del artículo
        response = requests.get(post_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extraer el contenido del artículo
        contenido_elements = soup.select('div.entry-content p')
        texto_extraido = " ".join([p.get_text() for p in contenido_elements])

        # Obtener la imagen del artículo
        imagen_element = soup.select_one('div.entry-content img')
        if imagen_element:
            imagen_url = imagen_element['src']
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
