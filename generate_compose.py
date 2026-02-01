import argparse
import urllib.request
import tarfile
import shutil
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    # --- PREPARACIÓN DE LIBRERÍA (Fuera del contenedor) ---
    print("📦 Descargando librería a2a mediante Python standard...")
    libs_dir = Path("./libs")
    libs_dir.mkdir(exist_ok=True)
    
    # URL pública del código fuente (ZIP/TAR de la rama main)
    url = "https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz"
    tar_path = libs_dir / "a2a.tar.gz"
    
    # Descargar
    urllib.request.urlretrieve(url, tar_path)
    
    # Extraer solo la carpeta src/a2a
    with tarfile.open(tar_path) as tar:
        tar.extractall(path=libs_dir)
    
    # Mover la carpeta para que la ruta sea limpia: ./libs/a2a
    source_folder = libs_dir / "agentified-a2a-main" / "src" / "a2a"
    final_folder = libs_dir / "a2a"
    
    if final_folder.exists():
        shutil.rmtree(final_folder)
    shutil.move(str(source_folder), str(final_folder))
    print("✅ Librería lista en ./libs/a2a")

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
      - ./libs:/app/libs
    entrypoint: ["/bin/sh", "-c"]
    command: 
      - |
        # 1. Instalar dependencias mínimas
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests -q
        
        # 2. PYTHONPATH apunta a /app/libs donde ya pusimos el código
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
