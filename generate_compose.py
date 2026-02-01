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
    headers = {"Accept": "application/json", "User-Agent": "AgentBeats-Hardening/1.0"}
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json().get("docker_image", DEFAULT_IMAGE)
        return DEFAULT_IMAGE
    except:
        return DEFAULT_IMAGE

def resolve_agent(agent: Dict, name: str):
    if not agent.get("image"):
        agent["image"] = fetch_agent_image(agent["agentbeats_id"]) if agent.get("agentbeats_id") else DEFAULT_IMAGE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    resolve_agent(data["green_agent"], "green_agent")
    participant_names = []
    participant_services = ""
    
    for p in data.get("participants", []):
        resolve_agent(p, p.get("name", "participant"))
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
      timeout: 5s
      retries: 5
    networks:
      - agent-network
"""

    # Construcción limpia de depends_on
    deps = ["green-agent"] + participant_names
    depends_on_yaml = "    depends_on:"
    for d in deps:
        depends_on_yaml += f"\n      {d}:\n        condition: service_healthy"

    compose = f"""services:
  green-agent:
    image: {data['green_agent']['image']}
    container_name: green-agent
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9009/.well-known/agent-card.json"]
      interval: 5s
      timeout: 5s
      retries: 5
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
{depends_on_yaml}
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
"""
    Path("docker-compose.yml").write_text(compose)

    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\nendpoint = "http://green-agent:9009"\n')
        for p in data.get("participants", []):
            f.write(f'\n[[participants]]\nrole = "{p["name"]}"\nendpoint = "http://{p["name"]}:9009"\n')
            if p.get("agentbeats_id"): f.write(f'agentbeats_id = "{p["agentbeats_id"]}"\n')

    log("Generación completada.")

if __name__ == "__main__":
    main()
