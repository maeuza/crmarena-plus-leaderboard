import argparse
import os
import sys
from pathlib import Path
from typing import Dict
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
    for p in data.get("participants", []):
        p_img = p.get("image") or fetch_agent_image(p.get("agentbeats_id", ""))
        parts_list.append({"name": p["name"], "image": p_img})

    participant_services = ""
    for p in parts_list:
        participant_services += f"""
  {p['name']}:
    image: {p['image']}
    container_name: {p['name']}
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network
"""

    # Preparamos el comando de espera que sugeriste
    # Esperamos a green-agent y a los participantes antes de iniciar
    wait_script = "until curl -sf http://green-agent:9009/.well-known/agent-card.json"
    for p in parts_list:
        wait_script += f" && curl -sf http://{p['name']}:9009/.well-known/agent-card.json"
    
    wait_script += "; do echo 'Esperando a que los agentes respondan...'; sleep 2; done; "
    wait_script += "agentbeats-client /app/scenario.toml /app/output/results.json"

    compose = f"""services:
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
    # Aplicamos tu lógica de espera aquí
    entrypoint: ["sh", "-c", "{wait_script}"]
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
"""
    Path("docker-compose.yml").write_text(compose)

    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\nendpoint = "http://green-agent:9009"\n')
        for p in parts_list:
            f.write(f'\n[[participants]]\nrole = "{p["name"]}"\nendpoint = "http://{p["name"]}:9009"\n')

    print("Generación completada con script de espera dinámico.")

if __name__ == "__main__":
    main()
