# Advisory: CVE-2026-1005 — Debug headers leak internal IPs

Severity: Low
Affected component: edge proxy debug response headers
Description:
When legacy troubleshooting mode is enabled, the edge proxy includes internal upstream IP addresses and node identifiers in response headers returned to external clients. The leaked metadata can help attackers map private network ranges and target backend systems more efficiently.
CVSS score: 3.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N)
Remediation:
Disable legacy troubleshooting mode and upgrade the proxy image to release 1.18.5. Rotate exposed node identifiers if they are used in monitoring dashboards or operational runbooks accessible outside the platform team.
