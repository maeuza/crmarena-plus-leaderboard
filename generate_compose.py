import argparse
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


def fetch_agent_image(agentbeats_id: str) -> str:
    if not agentbeats_id:
        return DEFAULT_IMAGE

    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    try:
        r = requests.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json().get("docker_image", DEFAULT_IMAGE)
    except Exception:
        pass

    return DEFAULT_IMAGE


def resolve_agent(agent: Dict) -> str:
    if agent.get("image"):
        return agent["image"]
    return fetch_agent_image(agent.get("agentbeats_id", ""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    # --- Green agent ---
    green_image = resolve_agent(data["green_agent"])

    # --- Participants ---
    participants = []
    for p in data.get("participants", []):
        participants.append({
            "name": p["name"],
            "image": resolve_agent(p)
        })

    # --- docker-compose.yml ---
    compose = [
        "services:",
        "  green-agent:",
        f"    image: {green_image}",
        "    container_name: green-agent",
        "    environment:",
        "      - PYTHONUNBUFFERED=1",
        "      - GOOGLE_API_KEY=${GOOGLE_API_KEY}",
        "      - AGENT_ROLE=green",
        "    healthcheck:",
        "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:9009/.well-known/agent-card.json\"]",
        "      interval: 5s",
        "      timeout: 5s",
        "      retries: 5",
        "    networks:",
        "      - agent-network",
    ]

    for p in participants:
        compose.extend([
            f"  {p['name']}:",
            f"    image: {p['image']}",
            f"    container_name: {p['name']}",
            "    environment:",
            "      - PYTHONUNBUFFERED=1",
            "      - GOOGLE_API_KEY=${GOOGLE_API_KEY}",
            "      - AGENT_ROLE=purple",
            "    healthcheck:",
            "      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:9009/.well-known/agent-card.json\"]",
            "      interval: 5s",
            "      timeout: 5s",
            "      retries: 5",
            "    networks:",
            "      - agent-network",
        ])

    compose.extend([
        "  agentbeats-client:",
        "    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0",
        "    container_name: agentbeats-client",
        "    volumes:",
        "      - ./a2a-scenario.toml:/app/scenario.toml",
        "      - ./output:/app/output",
        "    command:",
        "      - /app/scenario.toml",
        "      - /app/output/results.json",
        "    depends_on:",
        "      green-agent:",
        "        condition: service_healthy",
    ])

    for p in participants:
        compose.extend([
            f"      {p['name']}:",
            "        condition: service_healthy",
        ])

    compose.extend([
        "    networks:",
        "      - agent-network",
        "",
        "networks:",
        "  agent-network:",
        "    driver: bridge",
        "",
    ])

    Path("docker-compose.yml").write_text("\n".join(compose))

    # --- a2a-scenario.toml ---
    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\n')
        f.write('endpoint = "http://green-agent:9009"\n')

        for p in participants:
            f.write("\n[[participants]]\n")
            f.write(f'role = "{p["name"]}"\n')
            f.write(f'endpoint = "http://{p["name"]}:9009"\n')

    print("✅ Stack generado correctamente (AgentBeats compatible).")


if __name__ == "__main__":
    main()
