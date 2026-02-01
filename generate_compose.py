"""Generate Docker Compose configuration from scenario.toml"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomli
except ImportError:
    try:
        import tomllib as tomli
    except ImportError:
        print("Error: tomli required. Install with: pip install tomli")
        sys.exit(1)
try:
    import tomli_w
except ImportError:
    print("Error: tomli-w required. Install with: pip install tomli-w")
    sys.exit(1)
try:
    import requests
except ImportError:
    print("Error: requests required. Install with: pip install requests")
    sys.exit(1)

AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"

def fetch_agent_info(agentbeats_id: str) -> dict:
    """Fetch agent info from agentbeats.dev API with robust headers."""
    # Limpiamos el ID de cualquier espacio o caracter invisible
    clean_id = agentbeats_id.strip()
    url = f"{AGENTBEATS_API_URL}/{clean_id}"
    
    # Cabeceras que simulan un navegador real para evitar bloqueos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Intentamos decodificar el JSON
        return response.json()
        
    except requests.exceptions.HTTPError as e:
        print(f"Error HTTP: {e}")
        if response.status_code == 404:
            print(f"Error: El ID {clean_id} no fue encontrado en la API.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: No se pudo procesar la respuesta de la API para el agente {clean_id}")
        # Si no es JSON, mostramos qué devolvió el servidor para entender el problema
        if 'response' in locals():
            print(f"Respuesta del servidor (primeros 100 caracteres): {response.text[:100]}")
        sys.exit(1)

COMPOSE_PATH = "docker-compose.yml"
A2A_SCENARIO_PATH = "a2a-scenario.toml"
ENV_PATH = ".env.example"
DEFAULT_PORT = 9009
DEFAULT_ENV_VARS = {"PYTHONUNBUFFERED": "1"}

COMPOSE_TEMPLATE = """# Auto-generated from scenario.toml
services:
  green-agent:
    image: {green_image}
    platform: linux/amd64
    container_name: green-agent
    command: ["--host", "0.0.0.0", "--port", "{green_port}", "--card-url", "http://green-agent:{green_port}"]
    environment:{green_env}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{green_port}/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    depends_on:{green_depends}
    networks:
      - agent-network
{participant_services}
  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    platform: linux/amd64
    container_name: agentbeats-client
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    command: ["scenario.toml", "output/results.json"]
    depends_on:{client_depends}
    networks:
      - agent-network
networks:
  agent-network:
    driver: bridge
"""

PARTICIPANT_TEMPLATE = """  {name}:
    image: {image}
    platform: linux/amd64
    container_name: {name}
    command: ["--host", "0.0.0.0", "--port", "{port}", "--card-url", "http://{name}:{port}"]
    environment:{env}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{port}/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    networks:
      - agent-network
"""

A2A_SCENARIO_TEMPLATE = """[green_agent]
endpoint = "http://green-agent:{green_port}"
{participants}
{config}"""

def resolve_image(agent: dict, name: str) -> None:
    has_image = "image" in agent
    has_id = "agentbeats_id" in agent
    if has_image and has_id:
        print(f"Error: {name} tiene ambos 'image' y 'agentbeats_id'")
        sys.exit(1)
    elif has_image:
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"Error: {name} requiere 'agentbeats_id' en GitHub Actions.")
            sys.exit(1)
        print(f"Usando imagen de {name}: {agent['image']}")
    elif has_id:
        info = fetch_agent_info(agent["agentbeats_id"])
        agent["image"] = info["docker_image"]
        print(f"Imagen resuelta para {name}: {agent['image']}")
    else:
        print(f"Error: {name} debe tener 'image' o 'agentbeats_id'")
        sys.exit(1)

def parse_scenario(scenario_path: Path) -> dict[str, Any]:
    toml_data = scenario_path.read_text()
    data = tomli.loads(toml_data)
    green = data.get("green_agent", {})
    resolve_image(green, "green_agent")
    participants = data.get("participants", [])
    for participant in participants:
        name = participant.get("name", "unknown")
        resolve_image(participant, f"participante '{name}'")
    return data

def format_env_vars(env_dict: dict[str, Any]) -> str:
    env_vars = {**DEFAULT_ENV_VARS, **env_dict}
    lines = [f"      - {key}={value}" for key, value in env_vars.items()]
    return "\n" + "\n".join(lines)

def format_depends_on(services: list) -> str:
    lines = []
    for service in services:
        lines.append(f"      {service}:")
        lines.append(f"        condition: service_healthy")
    return "\n" + "\n".join(lines)

def generate_docker_compose(scenario: dict[str, Any]) -> str:
    green = scenario["green_agent"]
    participants = scenario.get("participants", [])
    participant_names = [p["name"] for p in participants]
    participant_services = "\n".join([
        PARTICIPANT_TEMPLATE.format(
            name=p["name"], image=p["image"], port=DEFAULT_PORT,
            env=format_env_vars(p.get("env", {}))
        ) for p in participants
    ])
    all_services = ["green-agent"] + participant_names
    return COMPOSE_TEMPLATE.format(
        green_image=green["image"], green_port=DEFAULT_PORT,
        green_env=format_env_vars(green.get("env", {})),
        green_depends=format_depends_on(participant_names),
        participant_services=participant_services,
        client_depends=format_depends_on(all_services)
    )

def generate_a2a_scenario(scenario: dict[str, Any]) -> str:
    green = scenario["green_agent"]
    participants = scenario.get("participants", [])
    p_lines = []
    for p in participants:
        lines = [f"[[participants]]", f"role = \"{p['name']}\"", f"endpoint = \"http://{p['name']}:{DEFAULT_PORT}\""]
        if "agentbeats_id" in p: lines.append(f"agentbeats_id = \"{p['agentbeats_id']}\"")
        p_lines.append("\n".join(lines) + "\n")
    config_section = scenario.get("config", {})
    return A2A_SCENARIO_TEMPLATE.format(
        green_port=DEFAULT_PORT, participants="\n".join(p_lines),
        config=tomli_w.dumps({"config": config_section})
    )

def generate_env_file(scenario: dict[str, Any]) -> str:
    green = scenario["green_agent"]
    participants = scenario.get("participants", [])
    secrets = set()
    pattern = re.compile(r'\$\{([^}]+)\}')
    for v in list(green.get("env", {}).values()) + [v for p in participants for v in p.get("env", {}).values()]:
        for match in pattern.findall(str(v)): secrets.add(match)
    return "\n".join([f"{s}=" for s in sorted(secrets)]) + "\n" if secrets else ""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path)
    args = parser.parse_args()
    scenario = parse_scenario(args.scenario)
    with open(COMPOSE_PATH, "w") as f: f.write(generate_docker_compose(scenario))
    with open(A2A_SCENARIO_PATH, "w") as f: f.write(generate_a2a_scenario(scenario))
    env = generate_env_file(scenario)
    if env:
        with open(ENV_PATH, "w") as f: f.write(env)
    print("Archivos generados con éxito.")

if __name__ == "__main__":
    main()
