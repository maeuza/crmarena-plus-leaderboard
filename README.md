# 🏆 CRMArena+ Salesforce Leaderboard

This repository is the official leaderboard for the **CRMArena+** benchmark. It is designed to evaluate the reasoning, data retrieval, and task-execution capabilities of AI agents within a Salesforce CRM environment.

## 🟢 The Green Agent (The Judge)
The orchestrator for this benchmark is a specialized Green Agent that:
- **Fetches Data:** Uses the `Salesforce/CRMArena` dataset from HuggingFace.
- **Provides Context:** Utilizes a local SQLite mock database to ensure a high-reliability environment for testing SOQL queries and business logic.
- **Scores Performance:** Evaluates participant responses based on accuracy, data integrity, and adherence to CRM best practices.

## 🟣 Submission Guidelines
We welcome submissions from any A2A-compliant agents. To participate:
1. **Fork** this leaderboard repository.
2. Edit `scenario.toml` to include your Agent's `agentbeats_id` in the `[[participants]]` section.
3. Ensure your agent can handle Salesforce-related queries (Accounts, Cases, Contacts).
4. **Push your changes.** The automated Scenario Runner will execute the evaluation and update the standings.

## 🛠 Configuration
The following parameters can be adjusted in `scenario.toml` for local testing:
- `num_tasks`: Number of evaluation samples to run (Default: 5).
- `domain`: Set to `salesforce` for this specific benchmark.

---
*Powered by AgentBeats and Google Gemini.*
