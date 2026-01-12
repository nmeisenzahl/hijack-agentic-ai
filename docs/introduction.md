# Introduction: Security in the Era of Agentic AI

## The Data: A New Class of Vulnerabilities

The 2025 GitHub Octoverse Report reveals a stark reality: **broken access control—driven largely by AI—has emerged as one of the fastest-growing vulnerability types** in modern software development.

![Most Common Vulnerability Types - CodeQL](https://github.blog/wp-content/uploads/2025/10/octoverse-2025-most-common-vulnerability-types-codeql.png?w=1536)

*Source: [GitHub Octoverse Report 2025](https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/)*

---

## Agentic AI: Digital Insiders

Agentic AI systems represent a paradigm shift. Unlike traditional software—or even prompt-driven LLMs—agentic systems can **reason, plan, select tools, execute code, access data, and take autonomous actions**.

This transforms them into what security researchers call **"digital insiders"**—entities that behave like privileged employees, but without human judgment or accountability.

**What agents can do:**

- Read emails, documents, and databases
- Modify data and deploy code
- Trigger workflows and API calls
- Make decisions with minimal oversight
- Chain actions across multiple systems

**The security implication:** Compromised agents act with legitimate permissions. Insider-threat controls now apply to software, not just people.

---

## Why Traditional Security Fails

Classic DevOps and AppSec assumptions break down with agentic AI:

| Assumption | Traditional Software | Agentic AI |
|------------|---------------------|------------|
| Code is deterministic | ✅ | ❌ |
| Behavior is predictable | ✅ | ❌ |
| Risks are known pre-deployment | ✅ | ❌ |
| Attack surface is static | ✅ | ❌ |

### Attack Surfaces Expand Beyond Code

OWASP's Top 10 for Agentic Applications shows that **text, memory, tools, and inter-agent communication** are now first-class attack surfaces:

- Agent goal hijacking
- Tool misuse and abuse
- Memory and context poisoning
- Cascading failures across agent chains

These vulnerabilities cannot be caught by static analysis alone.

### Failures Self-Propagate

Unlike other applications, agentic systems chain decisions dynamically. A single compromised input can cascade:

1. One agent ingests poisoned context
2. Another agent reasons with corrupted memory
3. A third executes malicious actions autonomously

This is **systemic failure**, not a single bug.

### AI Supply Chains Introduce New Risks

The AI ecosystem now includes attack vectors that traditional SBOMs don't cover:

- Pre-trained models with embedded behaviors
- Shared prompts and agent configurations
- MCP servers with insecure defaults
- Open-source datasets with poisoned content
- AI-generated code that hallucinates dependencies

---

## The Stakes

### Regulatory and Governance Pressure

- **[OWASP](https://www.prnewswire.com/news-releases/owasp-genai-security-project-releases-top-10-risks-and-mitigations-for-agentic-ai-security-302637364.html)** formalized a global standard for agentic AI risk in 2026
- **[Gartner](https://www.forbes.com/councils/forbestechcouncil/2026/01/09/beyond-secure-reimagining-data-protection-for-agentic-ai/)** predicts 40% of agentic AI projects will be abandoned due to security and governance failures
- Insurers are increasingly reluctant to underwrite agentic AI risks without strong controls

### Machine-Speed Attacks

Threat actors are already weaponizing agentic AI:

- Malware uses LLMs at runtime to mutate behavior
- AI-assisted attacks dramatically reduce cost and skill barriers
- The shift to machine-versus-machine speed makes manual security processes obsolete

### The Blast Radius

When an agentic AI system fails:

- **Every agent is a privileged user**
- **Every prompt is potential code**
- **Every tool is an execution surface**
- **Every mistake can autonomously propagate**

---

**→ See [Securing Agentic AI](securing-agentic-ai.md) for detailed attack mechanisms, OWASP mapping, and mitigation strategies.**
