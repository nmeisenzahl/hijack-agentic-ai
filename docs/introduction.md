# Introduction: Security in the Era of Agentic AI

Use this page as the opening frame for the talk before running the demos.

## Why this matters

AI is moving from chat windows into workflows that read internal context, call tools, and affect real decisions. That changes the security model: text is no longer just input data. In an agentic system, text can influence tool choice, workflow state, and side effects.

This talk uses one simple frame:

> **Agentic AI = text + tools + trust + autonomy**

Once those pieces come together, prompt injection stops being only a chatbot problem. It becomes an application security problem.

## The digital insider problem

A deployed agent can look like a trusted teammate:

- It reads internal documents.
- It summarizes and decides.
- It calls approved tools.
- It operates with legitimate permissions.
- It may act faster than a human reviewer can follow.

That makes it a **digital insider**. If an attacker can shape what the agent reads, which tool contract it trusts, or which retrieved content enters context, they may be able to steer the agent into misusing its own authority.

The primary mechanism is **indirect prompt injection** — instructions hidden in documents, tool metadata, or retrieved content that the model receives as data but executes as commands.

## What the demos show

The demos move from "text changes an answer" to "text causes a trusted action." Each demo runs both a vulnerable and a secure version so you can see the attack and the mitigation back to back.

| Demo | Use case | Boundary crossed | Mitigation shown |
|---|---|---|---|
| Demo 01: Poisoned Advisory | Vulnerability triage assistant reviews local security advisories. | Advisory text becomes operational guidance. | Azure AI Content Safety Prompt Shields scans advisory bodies before model use. |
| Demo 02: Sleeper MCP | Workforce-planning assistant uses a connected MCP benchmark tool. | MCP tool description becomes part of the model's instruction surface. | Manifest pinning plus live metadata verification detect description drift. |
| Demo 03: Sleeper Cell | Finance assistant retrieves guidance from a RAG store and runs generated Python for calculations. | Retrieved content drives a code-execution path with network egress. | AGT egress policy governs generated-code side effects; Prompt Shields blocks poisoned source docs before vector creation. |

## Why traditional assumptions break

| Traditional assumption | Agentic AI wrinkle |
|---|---|
| Code defines behavior. | Runtime text can change behavior. |
| Inputs are data. | Inputs can behave like instructions. |
| Tool permissions are enough. | The agent may choose the wrong tool for the wrong reason. |
| Trusted content is safe to read. | Trusted-looking context can be poisoned. |
| Human approval is the backstop. | Autonomy can compress review time or hide intent. |

Static analysis, dependency scanning, secrets detection, and least privilege still matter. They are just not enough on their own. Security also has to cover context quality, tool boundaries, action governance, and failure containment.

## OWASP framing

The talk uses OWASP for shared vocabulary:

- **OWASP Top 10 for LLM Applications 2026** — application-layer risks: prompt injection, sensitive information disclosure, supply chain vulnerabilities, improper output handling, excessive agency.
- **OWASP Top 10 for Agentic Applications 2026** — agent-specific risks that emerge when systems can plan, use tools, remember context, coordinate, and act autonomously.
- **OWASP Securing Agentic Applications Guide 1.0** — bridges the two Top 10 lists with practical design, deployment, and governance controls.

Each demo is mapped to specific OWASP IDs in its README and in the closing document.

## Questions to hold during the demos

As you watch each demo, ask:

1. **Text:** What content can the agent read, and who can influence it?
2. **Tools:** What actions can the agent take, directly or indirectly?
3. **Trust:** What credentials, approvals, data, or assumptions does the agent inherit?
4. **Autonomy:** Where can the agent act before a human understands the consequence?

If you can answer those four questions for a given system, you can start designing controls that match how agentic systems actually fail.

**Next:** run [Demo 01: Poisoned Advisory](../demos/01-poisoned-advisory/README.md).
