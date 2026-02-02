import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    # Configuramos el Docker Compose con la instalación de dependencias en caliente
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
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        echo "📦 Preparando entorno de evaluación..."
        # Instalamos el SDK de A2A y las utilidades que pide run_scenario.py
        pip install a2a-sdk[http-server] httpx python-dotenv toml litellm
        
        echo "⏳ Esperando a que los agentes (Green y Purple) inicialicen..."
        sleep 25
        
        echo "🚀 Ejecutando CRMArena Challenge..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content.strip())
        
    # Generamos el archivo de escenario para que AgentBeats sepa dónde están los agentes
    with open("a2a-scenario.toml", "w") as f:
        f.write('''
[green_agent]
endpoint = "http://green-agent:8000"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:8000"
''')

    print("✅ Archivos generados: docker-compose.yml y a2a-scenario.toml")

if __name__ == "__main__":
    main()
