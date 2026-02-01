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
    container_name: green-agent
    environment:
      - AGENT_ROLE=green
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    networks: [agent-network]

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: salesforce_participant
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    networks: [agent-network]

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    networks: [agent-network]
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        echo "-- Instalando dependencias base --"
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests
        
        echo "-- Descargando A2A usando Python --"
        python3 -c "
        import urllib.request
        import tarfile
        import os
        url = 'https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz'
        path = '/tmp/a2a.tar.gz'
        print('Descargando...')
        urllib.request.urlretrieve(url, path)
        print('Extrayendo...')
        with tarfile.open(path, 'r:gz') as tar:
            tar.extractall(path='/tmp/a2a_raw')
        # Mover contenido para limpiar la ruta
        os.rename('/tmp/a2a_raw/' + os.listdir('/tmp/a2a_raw')[0], '/tmp/a2a')
        print('Listo.')
        "
        
        echo "-- Iniciando Evaluación CRMArena --"
        # Configuramos las rutas de los módulos instalados y descargados
        export PYTHONPATH=$PYTHONPATH:/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/a2a/src
        
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json

networks:
  agent-network:
    driver: bridge
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    with open("a2a-scenario.toml", "w") as f:
        f.write("""
[green_agent]
endpoint = "http://green-agent:9009"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:9009"
""")

    print("✅ docker-compose.yml actualizado: Descarga vía Python-urllib configurada.")

if __name__ == "__main__":
    main()
