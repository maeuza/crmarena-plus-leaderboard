import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    # Este bloque define cómo se comportarán los 3 contenedores
    compose_content = '''
services:
  green-agent:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: green-agent
    environment:
      - AGENT_ROLE=green
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    networks:
      - agent-network

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: salesforce_participant
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    networks:
      - agent-network

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    networks:
      - agent-network
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        # 1. Instalar herramientas de Python que faltan
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q

        # 2. Descargar la pieza 'a2a' de GitHub manualmente (porque no hay git)
        cd /tmp
        curl -L https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz -o a2a.tar.gz
        tar -xzf a2a.tar.gz
        
        # 3. Mover el código a una carpeta que Python pueda encontrar
        mkdir -p /tmp/libraries
        cp -r agentified-a2a-main/src/a2a /tmp/libraries/
        
        # 4. Decirle a Python dónde buscar todo
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/libraries
        
        echo "⏳ Esperando a que los agentes despierten..."
        sleep 15
        
        echo "🎯 Iniciando evaluación..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
        
        echo "✅ Finalizado. Revisando archivo..."
        ls -lh /app/output/results.json

networks:
  agent-network:
    driver: bridge
'''
    
    # Generar el archivo de configuración de Docker
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    # Generar el archivo de instrucciones para los agentes
    with open("a2a-scenario.toml", "w") as f:
        f.write('''
[green_agent]
endpoint = "http://green-agent:9009"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:9009"
''')

    print("✅ Archivos de configuración generados con éxito.")

if __name__ == "__main__":
    main()
