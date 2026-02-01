import argparse
import json
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
    """
    Resuelve la imagen desde AgentBeats de forma defensiva.
    Nunca lanza excepción hacia arriba.
    """
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "AgentBeats-Hardening/1.0",
    }

    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)

        if r.status_code != 200:
            raise ValueError(f"status={r.status_code}")

        ct = r.headers.get("Content-Type", "")
        if "application/json" not in ct:
            raise ValueError(f"invalid content-type: {ct}")

        data = r.json()
        image = data.get("docker_image")

        if not image:
            raise ValueError("docker_image missing")

        return image

    except Exception as e:
        log(f"AgentBeats fallback ({agentbeats_id}): {e}")
        return DEFAULT_IMAGE


def resolve_agent(agent: Dict, name: str):
    if agent.get("image"):
        log(f"{name}: usando imagen explícita")
        return

    if agent.get("agentbeats_id"):
        agent["image"] = fetch_agent_image(agent["agentbeats_id"])
        log(f"{name}: imagen resuelta -> {agent['image']}")
        return

    agent["image"] = DEFAULT_IMAGE
    log(f"{name}: imagen por defecto aplicada")


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

    services = ""

    for p in parts:
        services += f"""
  {p['name']}:
    image: {p['image']}
    container_name: {p['name']}
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network
"""

    compose = f"""
services:
  green-agent:
    image: {green['image']}
    container_name: green-agent
    environment:
      - PYTHONUNBUFFERED=1
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    networks:
      - agent-network
{services}
agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    command: ["/app/scenario.toml", "/app/output/output.json"]
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
        f.write("[green_agent]\n")
        f.write("endpoint = \"http://green-agent:9009\"\n")
        for p in parts:
            f.write("\n[[participants]]\n")
            f.write(f"role = \"{p['name']}\"\n")
            f.write(f"endpoint = \"http://{p['name']}:9009\"\n")
            if p.get("agentbeats_id"):
                f.write(f"agentbeats_id = \"{p['agentbeats_id']}\"\n")

    log("Generación completa. Stack consistente.")


if __name__ == "__main__":
    main()
