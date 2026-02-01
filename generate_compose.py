compose = f"""
services:
  green-agent:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: green-agent
    environment:
      - AGENT_ROLE=green
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
    networks: [agent-network]

  salesforce_participant:
    image: ghcr.io/maeuza/agentified-crmarena:latest
    container_name: salesforce_participant
    environment:
      - AGENT_ROLE=purple
      - GOOGLE_API_KEY=${{GOOGLE_API_KEY}}
    networks: [agent-network]

  agentbeats-client:
    image: ghcr.io/agentbeats/agentbeats-client:v1.0.0
    depends_on:
      - green-agent
    volumes:
      - ./a2a-scenario.toml:/app/scenario.toml
      - ./output:/app/output
    command:
      - /app/scenario.toml
      - /app/output/results.json
    networks: [agent-network]

networks:
  agent-network:
    driver: bridge
"""
