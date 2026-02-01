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

    # Generamos los servicios de los participantes con Healthcheck
    participant_services = ""
    participant_names = []
    for p in parts:
        p_name = p.get('name', 'participant')
        participant_names.append(p_name)
        participant_services += f"""
  {p_name}:
    image: {p['image']}
    container_name: {p_name}
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9009/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
    networks:
      - agent-network"""

    # Generamos la lista de dependencias para el cliente
    depends_on_logic = "\\n".join([f"      {name}:\\n        condition: service_healthy" for name in ["green-agent"] + participant_names])
    # Limpiamos los saltos de línea para el f-string
    depends_on_block = f"""
    depends_on:
      green-agent:
        condition: service_healthy"""
    for name in participant_names:
        depends_on_block += f"""
      {name}:
        condition: service_healthy"""

    # Estructura completa del docker-compose.yml
    compose = f"""services:
  green-agent:
    image: {green['image']}
    container_name: green-agent
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9009/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
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
    {depends_on_block}
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
"""

    Path("docker-compose.yml").write_text(compose)

    # Generar a2a-scenario.toml
    with open("a2a-scenario.toml", "w") as f:
        f.write("[green_agent]\\n")
        f.write("endpoint = \\"http://green-agent:9009\\"\\n")
        for p in parts:
            f.write("\\n[[participants]]\\n")
            f.write(f"role = \\"{p['name']}\\"\\n")
            f.write(f"endpoint = \\"http://{p['name']}:9009\\"\\n")
            if p.get("agentbeats_id"):
                f.write(f"agentbeats_id = \\"{p['agentbeats_id']}\\"\\n")

    log("Generación exitosa con Healthchecks.")

if __name__ == "__main__":
    main()
