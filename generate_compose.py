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
TIMEOUT = 10

def log(msg: str):
    print(f"[agentbeats] {msg}", file=sys.stderr)

def fetch_agent_image(agentbeats_id: str) -> str:
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "AgentBeats-Hardening/1.0",
    }
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            return data.get("docker_image", DEFAULT_IMAGE)
        return DEFAULT_IMAGE
    except Exception as e:
        log(f"Fallback para {agentbeats_id}: {e}")
        return DEFAULT_IMAGE

def resolve_agent(agent: Dict, name: str):
    if agent.get("image"):
        return
    if agent.get("agentbeats_id"):
        agent["image"] = fetch_agent_image(agent["agentbeats_id"])
    else:
        agent["image"] = DEFAULT_IMAGE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    resolve_agent(data["green_agent"], "green_agent")
    for p in data.get("participants", []):
        resolve_agent(p, p.get("name", "participant"))

    green = data["green_agent"]
    parts = data.get("participants", [])

    # Generamos los servicios de los participantes con indentación de 2 espacios
    participant_services = ""
    for p in parts:
        participant_services += f"""
  {p['name']}:
    image: {p['image']}
    container_name: {p['name']}
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network"""

    # Estructura del docker-compose.yml (OJO a la indentación debajo de 'services:')
    compose = f"""services:
  green-agent:
    image: {green['image']}
    container_name: green-agent
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    networks:
      - agent-network
{participant_services}

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    command: ["/app/scenario.toml", "/app/output/results.json"]
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

    # Generar a2a-scenario.toml
    with open("a2a-scenario.toml", "w") as f:
        f.write("[green_agent]\n")
        f.write("endpoint = \"http://green-agent:9009\"\n")
        for p in parts:
            f.write("\n[[participants]]\n")
            f.write(f"role = \"{p['name']}\"\n")
            f.write(f"endpoint = \"http://{p['name']}:9009\"\n")
            if p.get("agentbeats_id"):
                f.write(f"agentbeats_id = \"{p['agentbeats_id']}\"\n")

    log("Archivos generados correctamente.")

if __name__ == "__main__":
    main()
