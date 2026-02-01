import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    # El YAML ahora es más sencillo para evitar errores de red 'undefined'
    compose_content = """
services:
  green-agent:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    environment:
      - AGENT_ROLE=green
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        # 1. Instalar dependencias de Python
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q

        # 2. Descargar la librería a2a usando el propio Python
        cd /tmp
        python3 -c "import urllib.request; urllib.request.urlretrieve('https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz', 'a2a.tar.gz')"
        tar -xzf a2a.tar.gz
        
        # 3. Crear carpeta de librerías y mover el código
        mkdir -p /tmp/lib
        cp -r agentified-a2a-main/src/a2a /tmp/lib/
        
        # 4. Configurar el camino para que Python lo encuentre
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/lib
        
        echo "⏳ Esperando agentes..."
        sleep 15
        
        echo "🚀 Ejecutando evaluación..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    # El archivo de escenario ahora usa los nombres de servicio por defecto de Docker Compose
    # que cuando no defines red, es el nombre del servicio tal cual.
    with open("a2a-scenario.toml", "w") as f:
        f.write('''
[green_agent]
endpoint = "http://green-agent:9009"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:9009"
''')

if __name__ == "__main__":
    main()
