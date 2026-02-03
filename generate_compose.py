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
      - PARTICIPANT_URL=http://salesforce_participant:8000
    ports:
      - "8000:8000"

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    ports:
      - "8001:8000"

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    environment:
      - PYTHONPATH=/app/src
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        echo "📦 Instalando dependencias necesarias..."
        pip install a2a-sdk[http-server] httpx python-dotenv toml litellm
        
        echo "⏳ Esperando inicialización de agentes..."
        sleep 25
        
        echo "🚀 Iniciando CRMArena Challenge..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    with open("a2a-scenario.toml", "w") as f:
        f.write('''
[green_agent]
endpoint = "http://green-agent:8000"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:8000"
''')

    print("✅ Archivos generados correctamente para maeuza/agentified-crmarena")

if __name__ == "__main__":
    main()
