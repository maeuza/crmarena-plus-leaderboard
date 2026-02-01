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
        # Instalación silenciosa para no llenar el log
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q
        
        cd /tmp
        # Clonamos el repo de la librería
        git clone https://github.com/agentbeats/agentified-a2a.git a2a_repo -q
        
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/a2a_repo/src
        
        echo "🚀 Esperando 15 segundos a que los agentes estabilicen..."
        sleep 15
        
        echo "🎯 Iniciando evaluación..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
        echo "✅ Proceso completado."

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

    print("✅ docker-compose.yml listo.")

if __name__ == "__main__":
    main()
