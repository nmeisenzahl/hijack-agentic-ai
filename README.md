# Hijacking Agentic AI: A Live Walkthrough of Prompt Injection, Tool Abuse, and RAG Poisoning

Agentic AI is rapidly becoming part of modern platforms and DevSecOps workflows. But with autonomy comes a new and largely misunderstood attack surface. In this demo‑driven talk, we’ll show how **agentic AI systems can be hijacked** without code exploits. Using nothing but text, tools, and trust.

Through live demos, we explore three real‑world classes of vulnerabilities from the OWASP Top 10 for AI:

- Indirect Prompt Injection, where untrusted content silently manipulates agent decisions
- Tool / MCP Supply‑Chain Abuse, where “helpful” tools leak full agent context
- RAG Poisoning, where internal knowledge causes persistent data exfiltration

No slides. No theory. Just Demo, Demo, Demo! With ****practical DevSecOps lessons on why classic security controls fall short once AI agents start acting on your behalf.

## ⚠️ Disclaimer

This project is for **educational purposes only**. The attacks demonstrated here are meant to raise awareness about security risks in agentic AI systems. Do not use these techniques maliciously.

## Overview

- [Introduction: Security in the Era of Agentic AI](docs/introduction.md)
- [Securing Agentic AI: A Overview](docs/securing-agentic-ai.md)

## Getting Started

As AI agents gain more autonomy and tool access, they introduce new attack surfaces. This project showcases three critical vulnerability categories:

| Demo | Description | OWASP | Impact |
| ------ | ------ | --- | --- |
| [Demo 1 – Indirect Prompt Injection](demos/demo1-indirect-prompt-injection/README.md) | Indirect Prompt Injection, where untrusted content silently manipulates agent decisions | **LLM01** | Offer ranking manipulated → False business decision |
| [Demo 2 – MCP Tool Abuse](demos/demo2-mcp-tool-abuse/README.md) | Tool / MCP Supply‑Chain Abuse, where "helpful" tools leak full agent context | **LLM03** | Context leaked to web search API → Supply-chain leak |
| [Demo 3 – RAG Poisoning](demos/demo3-rag-poisoning/README.md) | RAG Poisoning, where internal knowledge causes persistent data exfiltration | **LLM04** | Forecast + context exfiltrated → Persistent data exfiltration |

Each demo includes a README with an overview, attack scenario, files, running instructions, attack flow, and key takeaways.
