# Agentic AI Security: Hijacking and Defending AI Agents

A demo-driven talk series on **agentic AI vulnerabilities and defenses**. From hijacking agents with nothing but text—to securing them with Azure's AI security stack and industry frameworks.

## ⚠️ Disclaimer

This project is for **educational purposes only**. The attacks demonstrated here are meant to raise awareness about security risks in agentic AI systems. Do not use these techniques maliciously.

## Overview

Start with these foundational resources to understand the security landscape of agentic AI systems and the key principles for protecting them:

- [Introduction: Security in the Era of Agentic AI](docs/introduction.md)
- [Securing Agentic AI: An Overview](docs/securing-agentic-ai.md)

---

## Hijacking Agentic AI

*A Live Walkthrough of Prompt Injection, Tool Abuse, and RAG Poisoning*

Agentic AI is rapidly becoming part of modern platforms and DevSecOps workflows. But with autonomy comes a new and largely misunderstood attack surface. In this demo-driven talk, we show how **agentic AI systems can be hijacked** without code exploits—using nothing but text, tools, and trust.

No slides. No theory. Just Demo, Demo, Demo!

| Demo | Description | OWASP | Impact |
| ------ | ------ | --- | --- |
| [Demo 1 – Indirect Prompt Injection](demos/demo1-indirect-prompt-injection/README.md) | Indirect Prompt Injection, where untrusted content silently manipulates agent decisions | **LLM01 · AG01, AG08** | Offer ranking manipulated → False business decision |
| [Demo 2 – MCP Tool Abuse](demos/demo2-mcp-tool-abuse/README.md) | Tool description poisoning tricks agent into calling a malicious MCP for ALL requests, exfiltrating secrets | **LLM03, LLM07 · AG02, AG06, AG10** | Debug session secrets leaked to Weather MCP → Silent data exfiltration |
| [Demo 3 – RAG Poisoning](demos/demo3-rag-poisoning/README.md) | RAG Poisoning, where internal knowledge causes persistent data exfiltration | **LLM04, LLM05 · AG07, AG08** | Forecast + context exfiltrated → Persistent data exfiltration |

**Key Takeaway:** No "hacker magic." No code exploits. Just text + trust + autonomy. 👉 That's exactly what makes them **so dangerous—and so credible**.

---

## Securing Agentic AI

*Defense in Depth for the AI Era — OWASP Frameworks, Azure Security Stack, and Live Defenses*

We proved it's broken. Now we fix it. The defense demos build on the attacks and show how to defend against them using the **OWASP Top 10 for LLM Applications (2025)**, the **OWASP Top 10 for Agentic Applications (2026)**, and **Azure's AI security tooling**.

| Demo | Description | Defends Against | Azure Service |
| ------ | ------ | --- | --- |
| [Demo 4 – Prompt Shield](demos/demo4-prompt-shield/README.md) | Evolves Demo 1's Flock agent by adding input sanitization and Prompt Shield pre-screening—documents are sanitized, hidden content is separated and scanned independently, blocking indirect prompt injection before it reaches the LLM | Demo 1 | Azure AI Content Safety |
| [Demo 5 – Secure RAG Agent](demos/demo5-secure-rag/README.md) | Evolves Demo 3's Flock agent from vulnerable to secure with 2 implemented defenses: Prompt Shield document scanning and code safety validation (plus restricted execution namespace) | Demo 3 | Azure AI Content Safety |

**Key Takeaway:** Security is an evolution, not a rewrite—each defense layers onto the same agent code. Defense in depth with Prompt Shield + code safety controls turns vulnerable agents into production-ready ones.

---

## Getting Started

Each demo includes a README with an overview, scenario, files, running instructions, flow diagrams, and key takeaways.

### Prerequisites

- **Azure OpenAI** with GPT-4.1 deployment
- **Docker & Docker Compose**
- **Azure AI Content Safety** resource (for Demos 4 & 5)

### Environment Setup

```bash
cp .env.example .env
# Edit .env with your Azure credentials
```
