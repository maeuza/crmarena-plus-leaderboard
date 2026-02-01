import argparse
import os
from pathlib import Path
import requests

try:
    import tomllib as toml
except ImportError:
    import tomli as toml

AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"
DEFAULT_IMAGE = "ghcr.io/maeuza/agentified-crmarena:latest"

def fetch_agent_image(agentbeats_id: str) -> str:
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("docker_image", DEFAULT_IMAGE)
        return DEFAULT_IMAGE
    except:
        return DEFAULT_IMAGE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    green_img = data["green_agent"].get("image") or fetch_agent_image(data["green_agent"].get("agentbeats_id", ""))
    
    parts_list = []
    participant_services = ""
    for p in data.get("participants", []):
        p_img = p.get("image") or fetch_agent_image(p.get("agentbeats_id", ""))
        p_name = p["name"]
        parts_list.append({"name": p_name, "image": p_img})
        participant_services += f"""
  {p_name}:
    image: {p_img}
    container_name: {p_name}
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network
"""

    hosts_to_wait = ["green-agent"] + [p["name"] for p in parts_list]
    hosts_str = ", ".join([f"'{h}'" for h in hosts_to_wait])

    # SCRIPT DE EJECUCIÓN DINÁMICO
    # 1. Espera a los agentes.
    # 2. Intenta ejecutar 'agentbeats-client'.
    # 3. Si falla, busca cualquier script python en /app y lo intenta ejecutar.
    compose_content = f"""services:
  green-agent:
    image: {green_img}
    container_name: green-agent
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    networks:
      - agent-network
{participant_services}
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
        python3 -c "
        import socket, time
        hosts = [{hosts_str}]
        for host in hosts:
            while True:
                try:
                    with socket.create_connection((host, 9009), timeout=2):
                        print(f'-- {{host}} CONECTADO --')
                        break
                except:
                    time.sleep(2)
        "
        echo "-- Intentando ejecutar evaluación --"
        if command -v agentbeats-client >/dev/null 2>&1; then
            agentbeats-client /app/scenario.toml /app/output/results.json
        elif [ -f "/app/main.py" ]; then
            python3 /app/main.py /app/scenario.toml /app/output/results.json
        elif [ -f "/usr/local/bin/agentbeats-client" ]; then
            /usr/local/bin/agentbeats-client /app/scenario.toml /app/output/results.json
        else
            echo "ERROR: No se encontró el ejecutable. Contenido de /app:"
            ls -R /app
            exit 1
        fi

networks:
  agent-network:
    driver: bridge
"""

    Path("docker-compose.yml").write_text(compose_content)

    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\nendpoint = "http://green-agent:9009"\n')
        for p in parts_list:
            f.write(f'\n[[participants]]\nrole = "{p["name"]}"\nendpoint = "http://{p["name"]}:9009"\n')

    print("🚀 Docker Compose generado con lógica de auto-descubrimiento.")

if __name__ == "__main__":
    main()
