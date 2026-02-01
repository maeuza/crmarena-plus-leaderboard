import argparse
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    # --- PASO NUEVO: Descargamos la librería desde el Workflow, no desde el contenedor ---
    print("📦 Preparando librería a2a fuera del contenedor...")
    lib_path = Path("./libs/a2a")
    if not lib_path.exists():
        # Clonamos solo la carpeta necesaria usando un truco de git
        subprocess.run(["mkdir", "-p", "libs"], check=True)
        subprocess.run([
            "git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
            "https://github.com/agentbeats/agentified-a2a", "libs/repo"
        ], check=True)
        subprocess.run(["sh", "-c", "cd libs/repo && git sparse-checkout set src/a2a"], check=True)
        subprocess.run(["cp", "-r", "libs/repo/src/a2a", "libs/a2a"], check=True)

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
      - ./libs:/app/libs  # <-- Pasamos la librería ya descargada
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        # 1. Instalar dependencias
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q
        
        # 2. Configurar PYTHONPATH para que lea la carpeta /app/libs
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/app/libs
        
        echo "⏳ Esperando agentes..."
        sleep 15
        
        echo "🚀 Ejecutando evaluación..."
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json
"""
    
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
