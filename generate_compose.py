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

    compose = """version: "3.9"

services:
  green-agent:
    build: .
    container_name: green-agent
    environment:
      - AGENT_ROLE=green
      - PARTICIPANT_URL=http://salesforce_participant:8000
    ports:
      - "8000:8000"

  salesforce_participant:
    build: .
    container_name: salesforce_participant
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    ports:
      - "8001:8000"

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    depends_on:
      - green-agent
"""

    Path("docker-compose.yml").write_text(compose)

    with open("a2a-scenario.toml", "w") as f:
        f.write(
            """
[green_agent]
endpoint = "http://green-agent:8000"

[[participants]]
role = "salesforce_participant"
endpoint = "http://salesforce_participant:8000"
"""
        )

    print("✅ docker-compose.yml y a2a-scenario.toml generados correctamente")


if __name__ == "__main__":
    main()
