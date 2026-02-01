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
    try:
        r = requests.get(
            f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}",
            headers={"Accept": "application/json"},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("docker_image", DEFAULT_IMAGE)
    except Exception:
        pass
    return DEFAULT_IMAGE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    # Green agent
    green = data["green_agent"]
    green_image = green.get("image") or fetch_agent_image(green.get("agentbeats_id"))

    # Participants
    participant_blocks = ""
    participant_names = []

    for p in data.get("participants", []):
        name = p["name"]
        image = p.get("image") or fetch_agent_image(p.get("agentbeats_id"))
        participant_names.append(name)

        participant_blocks += f"""
  {name}:
    image: {image}
    container_name: {name}
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network
"""

    compose = f"""services:
  green-agent:
    image: {green_image}
    container_name: green-agent
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    networks:
      - agent-network
{participant_blocks}
  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    command:
      - /app/scenario.toml
      - /app/output/results.json
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    depends_on:
      green-agent:
        condition: service_started
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
"""

    Path("docker-compose.yml").write_text(compose)

    # a2a scenario
    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\n')
        f.write('endpoint = "http://green-agent:9009"\n')
        for name in participant_names:
            f.write('\n[[participants]]\n')
            f.write(f'role = "{name}"\n')
            f.write(f'endpoint = "http://{name}:9009"\n')

    print("✅ docker-compose.yml y a2a-scenario.toml generados correctamente")


if __name__ == "__main__":
    main()
