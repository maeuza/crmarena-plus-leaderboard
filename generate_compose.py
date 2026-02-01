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
        echo "-- Instalando dependencias --"
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests
        
        echo "-- Descargando y configurando A2A --"
        cat << 'EOF' > setup_a2a.py
        import urllib.request, zipfile, os, socket, time, shutil
        
        # 1. Descarga estable
        url = 'https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.zip'
        urllib.request.urlretrieve(url, '/tmp/a2a.zip')
        
        # 2. Extracción limpia
        with zipfile.ZipFile('/tmp/a2a.zip', 'r') as z:
            z.extractall('/tmp/a2a_raw')
        
        # Buscamos la carpeta src real (evitando el prefijo de la rama)
        base_dir = os.path.join('/tmp/a2a_raw', os.listdir('/tmp/a2a_raw')[0])
        src_dir = os.path.join(base_dir, 'src')
        
        # Movemos el contenido de src a un lugar predecible
        if os.path.exists('/tmp/a2a_lib'): shutil.rmtree('/tmp/a2a_lib')
        shutil.copytree(src_dir, '/tmp/a2a_lib')
        print(f"Librería A2A instalada en /tmp/a2a_lib. Contenido: {os.listdir('/tmp/a2a_lib')}")
        
        # 3. Espera de Agentes
        for h in ['green-agent', 'salesforce_participant']:
            print(f"Esperando a {h}...")
            while True:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    if s.connect_ex((h, 9009)) == 0: break
                time.sleep(2)
        print("Agentes listos.")
        EOF

        python3 setup_a2a.py
        
        echo "-- Ejecutando Arena --"
        # Ahora el PYTHONPATH apunta directamente a la carpeta que contiene el paquete 'a2a'
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/a2a_lib
        
        python3 /app/src/agentbeats/run_scenario.py /app/scenario.toml /app/output/results.json

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

    print("✅ docker-compose.yml actualizado con rutas de librería corregidas.")

if __name__ == "__main__":
    main()
