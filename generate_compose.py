version: "3.9"

services:
  green-agent:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: green-agent
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - AGENT_ROLE=green
      - PYTHONUNBUFFERED=1
    ports:
      - "9009"
    networks:
      - agent-network

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: salesforce_participant
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - AGENT_ROLE=purple
      - PYTHONUNBUFFERED=1
    ports:
      - "9009"
    networks:
      - agent-network

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    container_name: agentbeats-client
    environment:
      # 🔑 CLAVE DEL FIX
      - AGENTBEATS_CLIENT_RETRY_SECONDS=60
      - PYTHONUNBUFFERED=1
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    command:
      - /app/scenario.toml
      - /app/output/results.json
    depends_on:
      - green-agent
      - salesforce_participant
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
