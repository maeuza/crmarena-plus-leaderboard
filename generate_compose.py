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
      - PARTICIPANT_URL=http://salesforce_participant:9009
    ports:
      - "8000:9009"

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    ports:
      - "8001:9009"

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        echo "📦 Instalando dependencias de evaluación..."
        pip install httpx  # <--- ESTO ARREGLA EL ERROR DEL LOG
        echo "⏳ Esperando agentes..."
        sleep 15
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    # Corregimos los endpoints al puerto 9009 que es donde realmente subió tu app
    with open("a2a-scenario.toml", "w") as f:
        f.write('''
[green_agent]
endpoint = "http://green-agent:9009"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:9009"
''')
    print("✅ Archivos actualizados con puerto 9009 e instalador de httpx.")

if __name__ == "__main__":
    main()
