#!/bin/bash

# Resolver la variable de entorno $PORT
PORT=${PORT:-5000}

# Verificar si $PORT es un número válido
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo "Error: '$PORT' is not a valid port number."
  exit 1
fi

# Ejecutar gunicorn
exec gunicorn app:app --bind 0.0.0.0:$PORT

