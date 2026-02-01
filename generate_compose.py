import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

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
        set -e
        echo "📦 Instalando dependencias..."
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q
        
        echo "📂 Preparando repositorio de evaluación..."
        cd /tmp
        git clone https://github.com/agentbeats/agentified-a2a.git a2a_repo -q
        
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/a2a_repo/src
        
        echo "⏳ Esperando estabilidad de red (20s)..."
        sleep 20
        
        echo "🚀 Probando conexión a los agentes..."
        curl -s http://green-agent:9009/health || echo "⚠️ Green Agent no responde"
        curl -s http://salesforce_participant:9009/health || echo "⚠️ Salesforce Agent no responde"

        echo "🎯 Ejecutando evaluación real..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
        
        echo "📊 Tamaño final del archivo:"
        ls -lh /app/output/results.json
        cat /app/output/results.json
networks:
  agent-network:
    driver: bridge
'''
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
    
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
