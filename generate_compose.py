import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any
import requests
import tomli
import tomli_w

AGENTBEATS_API_URL = "https://agentbeats.dev/api/agents"

def fetch_agent_info(agentbeats_id: str) -> dict:
    """Obtiene la info del agente usando un User-Agent real."""
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error al conectar con AgentBeats: {e}")
        if 'response' in locals():
            print(f"Respuesta del servidor: {response.text[:100]}")
        sys.exit(1)

def resolve_image(agent: dict, name: str) -> None:
    """Resuelve la imagen de Docker."""
    if "image" in agent and "agentbeats_id" in agent:
        print(f"Error: {name} tiene ambos campos. Usa solo uno.")
        sys.exit(1)
    elif "image" in agent:
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"Error: GitHub Actions requiere agentbeats_id.")
            sys.exit(1)
        agent["image"] = agent["image"]
    elif "agentbeats_id" in agent:
        info = fetch_agent_info(agent["agentbeats_id"])
        agent["image"] = info["docker_image"]
        print(f"Imagen resuelta: {agent['image']}")
    else:
        print(f"Error: {name} no tiene imagen ni ID.")
        sys.exit(1)

def format_env_vars(env_dict: dict) -> str:
    env = {"PYTHONUNBUFFERED": "1", **env_dict}
    return "\n" + "\n".join([f"      - {k}={v}" for k, v in env.items()])

def format_depends(services: list) -> str:
    return "\n" + "\n".join([f"      {s}:\n        condition: service_healthy" for s in services])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path)
    args = parser.parse_args()
    
    with open(args.scenario, "rb") as f:
        data = tomli.load(f)

    resolve_image(data.get("green_agent", {}), "green_agent")
    for p in data.get("participants", []):
        resolve_image(p, f"participant {p.get('name')}")

    # Generar docker-compose.yml
    green = data["green_agent"]
    parts = data.get("participants", [])
    p_names = [p["name"] for p in parts]
    
    p_services = ""
    for p in parts:
        p_services += f"""  {p['name']}:
    image: {p['image']}
    platform: linux/amd64
    container_name: {p['name']}
    command: ["--host", "0.0.0.0", "--port", "9009", "--card-url", "http://{p['name']}:9009"]
    environment:{format_env_vars(p.get('env', {}))}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9009/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    networks:
      - agent-network\n"""

    compose = f"""services:
  green-agent:
    image: {green['image']}
    platform: linux/amd64
    container_name: green-agent
    command: ["--host", "0.0.0.0", "--port", "9009", "--card-url", "http://green-agent:9009"]
    environment:{format_env_vars(green.get('env', {}))}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9009/.well-known/agent-card.json"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 30s
    depends_on:{format_depends(p_names)}
    networks:
      - agent-network
{p_services}
  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    depends_on:{format_depends(['green-agent'] + p_names)}
    networks:
      - agent-network
networks:
  agent-network:
    driver: bridge"""

    with open("docker-compose.yml", "w") as f: f.write(compose)
    
    # Generar a2a-scenario.toml
    p_lines = ""
    for p in parts:
        p_lines += f"[[participants]]\nrole = \"{p['name']}\"\nendpoint = \"http://{p['name']}:9009\"\n"
        if "agentbeats_id" in p: p_lines += f"agentbeats_id = \"{p['agentbeats_id']}\"\n"

    a2a = f"[green_agent]\nendpoint = \"http://green-agent:9009\"\n\n{p_lines}\n{tomli_w.dumps({'config': data.get('config', {})})}"
    with open("a2a-scenario.toml", "w") as f: f.write(a2a)
    print("Éxito: Archivos generados.")

if __name__ == "__main__":
    main()
