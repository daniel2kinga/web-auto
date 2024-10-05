#!/bin/sh

# Resolver la variable de entorno $PORT
PORT=${PORT:-5000}

# Ejecutar gunicorn
exec gunicorn app:app --bind 0.0.0.0:$PORT
