import argparse
from pathlib import Path

try:
    import tomllib as toml
except ImportError:
    import tomli as toml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    green = data["green_agent"]
    green_image = green["image"]

    participant = data["participants"][0]
    participant_image = participant["image"]
    participant_name = participant["name"]

    compose = f"""
services:
  green-agent:
    image: {green_image}
    container_name: green-agent
    environment:
      - AGENT_ROLE=green
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - PARTICIPANT_URL=http://{participant_name}:8000
    ports:
      - "8000:8000"

  {participant_name}:
    image: {participant_image}
    container_name: {participant_name}
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
    ports:
      - "8001:8000"

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
      - green-agent
"""

    Path("docker-compose.yml").write_text(compose.strip())

    with open("a2a-scenario.toml", "w") as f:
        f.write(f"""
[green_agent]
endpoint = "http://green-agent:8000"

[[participants]]
role = "{participant_name}"
endpoint = "http://{participant_name}:8000"
""".strip())

    print("✅ docker-compose.yml y a2a-scenario.toml generados correctamente")


if __name__ == "__main__":
    main()
