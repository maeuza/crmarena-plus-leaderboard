import argparse
from pathlib import Path
import requests

try:
    import tomllib as toml
except ImportError:
    import tomli as toml


AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"
DEFAULT_IMAGE = "ghcr.io/maeuza/agentified-crmarena:latest"


def fetch_agent_image(agentbeats_id: str) -> str:
    if not agentbeats_id:
        return DEFAULT_IMAGE
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("docker_image", DEFAULT_IMAGE)
        return DEFAULT_IMAGE
    except Exception:
        return DEFAULT_IMAGE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    # --- GREEN AGENT ---
    green = data["green_agent"]
    green_img = green.get("image") or fetch_agent_image(green.get("agentbeats_id"))

    # --- PARTICIPANTS ---
    participant_services = ""
    participants = []

    for p in data.get("participants", []):
        name = p["name"]
        img = p.get("image") or fetch_agent_image(p.get("agentbeats_id"))
        participants.append(name)

        participant_services += f"""
  {name}:
    image: {img}
    container_name: {name}
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network
"""

    # --- docker-compose.yml ---
    compose = f"""services:
  green-agent:
    image: {green_img}
    container_name: green-agent
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9009/.well-known/agent-card.json"]
      interval: 5s
      timeout: 5s
      retries: 5
{participant_services}
  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    networks:
      - agent-network
    depends_on:
      green-agent:
        condition: service_healthy
    command:
      - sh
      - -c
      - |
        echo "Esperando agentes..."
        until curl -sf http://green-agent:9009/.well-known/agent-card.json; do sleep 2; done
        agentbeats-client /app/scenario.toml /app/output/results.json

networks:
  agent-network:
    driver: bridge
"""

    Path("docker-compose.yml").write_text(compose)

    # --- a2a-scenario.toml ---
    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\n')
        f.write('endpoint = "http://green-agent:9009"\n')

        for name in participants:
            f.write(f'\n[[participants]]\n')
            f.write(f'role = "{name}"\n')
            f.write(f'endpoint = "http://{name}:9009"\n')

    print("✅ Docker Compose y scenario generados correctamente.")


if __name__ == "__main__":
    main()
