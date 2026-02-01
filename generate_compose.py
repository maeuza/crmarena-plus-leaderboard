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

def fetch_agent_image(agentbeats_id: str) -> str:
    url = f"{AGENTBEATS_API_URL}/{agentbeats_id.strip()}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("docker_image", DEFAULT_IMAGE)
        return DEFAULT_IMAGE
    except:
        return DEFAULT_IMAGE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, required=True)
    args = parser.parse_args()

    with open(args.scenario, "rb") as f:
        data = toml.load(f)

    # Resolver imágenes de agentes
    green_img = data["green_agent"].get("image") or fetch_agent_image(data["green_agent"].get("agentbeats_id", ""))
    
    parts_list = []
    participant_services = ""
    for p in data.get("participants", []):
        p_img = p.get("image") or fetch_agent_image(p.get("agentbeats_id", ""))
        p_name = p["name"]
        parts_list.append({"name": p_name, "image": p_img})
        participant_services += f"""
  {p_name}:
    image: {p_img}
    container_name: {p_name}
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=purple
    networks:
      - agent-network
"""

    # SCRIPT DE ESPERA EN PYTHON (Sustituye a curl)
    # Este script intenta abrir un socket TCP al puerto 9009 de cada agente.
    wait_logic = (
        "import socket, time; "
        "def wait(host): "
        "  print(f'-- Esperando a {host}:9009 --'); "
        "  while True: "
        "    try: "
        "      with socket.create_connection((host, 9009), timeout=1): "
        "        print(f'-- {host} conectado! --'); break "
        "    except: "
        "      time.sleep(2); "
    )
    
    # Construimos el comando final
    python_wait_cmd = f"{wait_logic}wait('green-agent'); "
    for p in parts_list:
        python_wait_cmd += f"wait('{p['name']}'); "
    
    full_command = f"python3 -c \"{python_wait_cmd}\" && agentbeats-client /app/scenario.toml /app/output/results.json"

    compose_content = f"""services:
  green-agent:
    image: {green_img}
    container_name: green-agent
    environment:
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
      - AGENT_ROLE=green
    networks:
      - agent-network
{participant_services}
  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    entrypoint: ["sh", "-c", "{full_command}"]
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
"""

    Path("docker-compose.yml").write_text(compose_content)

    # Generar el archivo de escenario para el cliente
    with open("a2a-scenario.toml", "w") as f:
        f.write('[green_agent]\nendpoint = "http://green-agent:9009"\n')
        for p in parts_list:
            f.write(f'\n[[participants]]\nrole = "{p["name"]}"\nendpoint = "http://{p["name"]}:9009"\n')

    print("Archivo docker-compose.yml generado con éxito (Python-based wait).")

if __name__ == "__main__":
    main()
