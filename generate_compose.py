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

    # Definimos los hosts a esperar
    hosts_to_wait = ["green-agent"] + [p["name"] for p in parts_list]
    hosts_str = ", ".join([f"'{h}'" for h in hosts_to_wait])

    # Usamos formato multi-línea para el comando de Docker
    # Esto evita el error de "did not find expected ','"
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
    entrypoint: ["sh", "-c"]
    command: 
      - |
        python3 -c "
        import socket, time
        for host in [{hosts_str}]:
            print(f'-- Esperando a {{host}}:9009 --')
            while True:
                try:
                    with socket.create_connection((host, 9009), timeout=1):
                        print(f'-- {{host}} listo! --')
                        break
                except:
                    time.sleep(2)
        "
        agentbeats-client /app/scenario.toml /app/output/results.json

networks:
  agent-network:
    driver: bridge
"""

    Path("docker-compose.yml").write_text(compose_content)

    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\nendpoint = "http://green-agent:9009"\n')
        for p in parts_list:
            f.write(f'\n[[participants]]\nrole = "{p["name"]}"\nendpoint = "http://{p["name"]}:9009"\n')

    print("docker-compose.yml generado con formato multi-línea seguro.")

if __name__ == "__main__":
    main()
