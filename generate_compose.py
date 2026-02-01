import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

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
        # 1. Instalar dependencias
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q

        # 2. Descargar a2a usando la URL correcta de la rama principal
        cd /tmp
        echo "🐍 Descargando librería..."
        python3 -c "import urllib.request; urllib.request.urlretrieve('https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz', 'a2a.tar.gz')"
        
        # 3. Descomprimir y organizar
        tar -xzf a2a.tar.gz
        mkdir -p /tmp/lib
        # El nombre de la carpeta al descomprimir suele ser nombre_repo-nombre_rama
        cp -r agentified-a2a-main/src/a2a /tmp/lib/
        
        # 4. Configurar PYTHONPATH
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/lib
        
        echo "⏳ Esperando agentes..."
        sleep 15
        
        echo "🚀 Ejecutando evaluación..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    # IMPORTANTE: Usamos los nombres que Docker Compose asigna por defecto
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
