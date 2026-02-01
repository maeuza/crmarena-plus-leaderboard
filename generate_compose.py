import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    # Usamos comillas simples triples para el bloque externo
    # y así evitamos conflictos con las comillas dobles internas
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
        echo "-- Configurando entorno --"
        python3 -m pip install --user httpx pydantic python-dotenv rich tomli requests
        
        echo "-- Descargando A2A --"
        python3 -c "import urllib.request, tarfile, os; url = 'https://github.com/agentbeats/agentified-a2a/archive/refs/heads/main.tar.gz'; urllib.request.urlretrieve(url, '/tmp/a2a.tar.gz'); tar = tarfile.open('/tmp/a2a.tar.gz', 'r:gz'); tar.extractall('/tmp/a2a_raw'); tar.close(); os.rename('/tmp/a2a_raw/' + os.listdir('/tmp/a2a_raw')[0], '/tmp/a2a')"
        
        echo "-- Esperando agentes --"
        python3 -c "import socket, time; [ (print(f'Esperando {h}...'), [time.sleep(2) while socket.socket().connect_ex((h, 9009)) else None]) for h in ['green-agent', 'salesforce_participant'] ]" || echo "Continuando..."

        echo "-- Ejecutando Arena --"
        export PYTHONPATH=/app/src:/home/agentbeats/.local/lib/python3.10/site-packages:/tmp/a2a/src
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

    print("✅ docker-compose.yml generado correctamente.")

if __name__ == "__main__":
    main()
