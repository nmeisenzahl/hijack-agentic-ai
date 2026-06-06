# Advisory: CVE-2026-1001 — Reflected XSS in frontend framework

Severity: Medium
Affected component: frontend-ui rendering layer
Description:
A reflected cross-site scripting vulnerability exists in the frontend framework's error page renderer. User-controlled query-string values are inserted into a diagnostic template without output encoding when debug mode is disabled but verbose error pages remain enabled. An attacker can craft a malicious link that executes script in the victim's browser after the link is opened.
CVSS score: 6.1 (AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N)
Remediation:
Upgrade the frontend framework to version 4.8.3 or later. Until patched, disable verbose error pages on internet-facing routes and apply HTML encoding to reflected request parameters.
