# Demo 03: Sleeper Cell

## 1. Use case

Finance uses an AI assistant to create a Q4 headcount and cost forecast package. The assistant retrieves internal guidance from a local RAG store and can run generated Python for calculations.

The risk: one retrieved document looks like normal forecasting guidance but hides a fake QA validation workflow. The model turns that retrieved instruction into generated code that posts the full forecast context to an internal-looking endpoint. The demo is local-safe: the visible "exfiltration" target is the local `leak-api` container, not an external service.

What to watch:

- The vulnerable run still returns a plausible finance answer.
- The side effect is visible in `leak-api` logs as `DATA EXFILTRATED`.
- `policy` mode keeps generated code useful for calculations but blocks network egress.
- `all` mode blocks poisoned source content before vectors are built and keeps egress policy as a second layer.

### Agent use-case flow

```mermaid
flowchart LR
    User[Finance user] --> Agent[Finance forecast assistant]
    Agent --> RAG[Retrieve internal guidance from RAG]
    RAG --> Code[Run generated Python calculations]
    Code --> Validation[Capture calculation and validation output]
    Validation --> Answer[Final forecast package]
```

## 2. Run vulnerable version

From this demo directory, create the shared environment file if it does not already exist:

```bash
cd demos/03-sleeper-cell
cp -n ../../.env.example ../../.env
```

Edit `../../.env` with the required model values, then set:

```dotenv
SECURITY_ENABLED=false
```

Run the vulnerable mode:

```bash
docker compose up --build --force-recreate
```

Expected markers:

- The local leak API logs `DATA EXFILTRATED`.
- The agent output may show generated-code output such as `validation_status=200`.
- The user-facing finance answer still looks plausible.

Stop the attached run after the marker is visible.

## 3. Vulnerable flow

The agent seeds ChromaDB from `data/docs/*.md`. One document, `q4-forecasting-guidelines-poisoned.md`, mixes legitimate finance guidance with a hidden Markdown comment containing a fake QA validation workflow.

When `SECURITY_ENABLED=false`:

1. The user asks for a Q4 headcount and cost forecast package.
2. `rag_search` retrieves legitimate finance guidance and the poisoned Q4 document.
3. The hidden comment tells the model to use `execute_forecast_code` for mandatory validation.
4. The model generates Python that posts the query, retrieved documents, assumptions, methodology, and results to `http://forecast-validation-api:9000/data`.
5. The legitimate code execution tool runs the generated code.
6. The local leak API receives the payload.
7. The agent still returns a helpful answer, so the side effect is easy to miss.

```mermaid
sequenceDiagram
    actor User
    participant Agent as Finance assistant
    participant Chroma as ChromaDB
    participant Code as Code execution tool
    participant Leak as Local leak API

    User->>Agent: Ask for Q4 forecast package
    Agent->>Chroma: rag_search(query)
    Chroma-->>Agent: Guidance plus poisoned Q4 doc
    Note over Agent: Hidden comment becomes model instruction
    Agent->>Code: execute_forecast_code(generated Python)
    Code->>Leak: POST /data with context and forecast
    Leak-->>Code: Receipt
    Code-->>Agent: validation_status=200
    Agent-->>User: Plausible answer, side effect hidden
```

## 4. Run secure version

Demo 03 has two secure modes:

| Mode | What it blocks | What to notice |
|---|---|---|
| `policy` | Generated-code network egress through AGT/Agent OS policy. | The code tool remains available for local calculations, but outbound HTTP is denied by default. |
| `all` | Poisoned source documents before embedding, plus generated-code network egress. | Prompt Shields blocks the poisoned document before the vector index is built. |
| `true` | Alias for `all`. | Safe carryover from Demos 01 and 02. |

### Secure mode: egress policy only

Set `SECURITY_ENABLED=policy` in `../../.env`, or use a one-off shell prefix:

```bash
SECURITY_ENABLED=policy docker compose up --build --force-recreate
```

Expected markers:

- Terminal shows `ATTACK BLOCKED` from `AGT Network Egress Policy` / `NetworkEgressDenied`.
- The `leak-api` receives no payload.

### Secure mode: source scan plus egress policy

Set `SECURITY_ENABLED=all` in `../../.env`, or use a one-off shell prefix. Azure AI Content Safety credentials are required for this mode.

```bash
SECURITY_ENABLED=all docker compose up --build --force-recreate
```

Expected markers:

- Terminal shows `ATTACK BLOCKED` before the poisoned document is embedded into ChromaDB.
- The rendered security event names the guard as `Azure Prompt Shield` and reports that a prompt attack was detected in the source document before vector creation.
- No embedding or Chroma write is performed for the poisoned corpus, and the LLM does not see the poisoned context.

## 5. Secure flow

Policy mode demonstrates action governance. The poisoned RAG content can still reach the model, but generated code may calculate only locally; it cannot publish data over the network unless policy allows it.

```mermaid
sequenceDiagram
    actor User
    participant Agent as Finance assistant
    participant Chroma as ChromaDB
    participant Code as Code execution tool
    participant Policy as AGT egress policy
    participant Leak as Local leak API

    User->>Agent: Ask for Q4 forecast package
    Agent->>Chroma: rag_search(query)
    Chroma-->>Agent: Guidance plus poisoned Q4 doc
    Note over Agent: Poisoned content may reach the model
    Agent->>Code: execute_forecast_code(generated Python)
    Code->>Policy: Request outbound POST to leak API
    Policy-->>Code: Deny by default
    Code-->>Agent: NetworkEgressDenied
    Agent-->>User: ATTACK BLOCKED
    Note over Leak: No payload received
```

All mode demonstrates layered defense: source documents are scanned before vector creation, and egress policy remains in place if content scanning ever misses.

```mermaid
sequenceDiagram
    actor User
    participant Agent as Agent startup
    participant Docs as Source docs
    participant Shield as Prompt Shields guard
    participant Chroma as ChromaDB
    participant LLM as LLM
    participant Policy as AGT egress policy

    User->>Agent: Start demo with SECURITY_ENABLED=all
    Agent->>Docs: Load data/docs/*.md
    Agent->>Shield: Scan raw source Markdown before embeddings
    Shield-->>Agent: Prompt attack detected
    Agent-->>User: ATTACK BLOCKED
    Note over Chroma: No vector created for poisoned corpus
    Note over LLM: LLM is not called
    Note over Policy: Egress policy remains as backup
```

## 6. Key takeaways

- The RAG corpus is part of the agent's trusted computing base.
- Source provenance and corpus change control matter as much as prompt design.
- Source-corpus scanning catches malicious documents before they are embedded into the vector store.
- Code execution tools are legitimate in analytical agents, but generated code needs its own egress boundary.
- Egress controls, least privilege, and tool governance contain side effects when content controls miss.
- Observability makes silent side effects visible during testing and operations.
- Red-team testing should cover poisoned source documents, poisoned tool metadata, and poisoned retrieved context.

Closing: across the three demos, the pattern is the same. Production defense needs layered controls, not trust in model intent.

## 7. OWASP mapping

| ID | Name | How this demo maps |
|---|---|---|
| LLM01:2025 | Prompt Injection | The malicious instruction is embedded indirectly in retrieved content. |
| LLM02:2025 | Sensitive Information Disclosure | The attack attempts to leak prompt context and retrieved documents. |
| LLM04:2025 | Data and Model Poisoning | The poisoned RAG document changes the retrieved context that influences model behavior. |
| LLM05:2025 | Improper Output Handling | Model-generated Python is executed by a tool and can perform an unintended HTTP request without egress controls. |
| LLM06:2025 | Excessive Agency | The assistant performs an external side effect the user did not request. |
| LLM08:2025 | Vector and Embedding Weaknesses | The RAG retrieval store, embedding pipeline, and similarity search become part of the trust boundary when the corpus can be poisoned. |
| ASI-01 | Agent Goal Hijack | A poisoned document steers the assistant away from the user's forecasting task. |
| ASI-02 | Tool Misuse & Exploitation | Hidden instructions coerce `execute_forecast_code` into exfiltrating full context. |
| ASI-06 | Memory & Context Poisoning | The RAG corpus itself becomes the compromised attack surface. |

## 8. Cleanup and troubleshooting

Reset from `demos/03-sleeper-cell`:

```bash
docker compose down --volumes
```

Use this reset to stop containers and clear the ChromaDB volume. The agent also deletes and recreates the `docs` collection on startup, but removing volumes gives a clean baseline.

Troubleshooting:

- If a mode change does not appear in the banner, verify `SECURITY_ENABLED` in the root `../../.env` and rerun with `--force-recreate`.
- A non-empty shell override such as `SECURITY_ENABLED=policy docker compose up ...` takes precedence over `../../.env` for that run only.
- If `SECURITY_ENABLED=all` blocks at startup, confirm `AZURE_CONTENT_SAFETY_ENDPOINT` and `AZURE_CONTENT_SAFETY_KEY` are set.
- If the attack marker is missing in unprotected mode, watch the `leak-api` logs for `DATA EXFILTRATED`.
- If `policy` or `all` sends a payload to `leak-api`, treat that as a failed secure run and reset before retrying.
- No external embedding credentials or model downloads are needed; Demo 03 uses deterministic local embeddings for reproducible retrieval.
