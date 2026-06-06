# Advisory: CVE-2026-1002 — DoS via rate-limiter bypass

Severity: Low
Affected component: public API gateway rate-limiter middleware
Description:
The API gateway rate-limiter can be bypassed by alternating IPv4 and IPv6 representations of the same client source address behind certain reverse proxy configurations. Attackers can exceed intended request quotas and cause increased CPU utilization on authentication and search endpoints, resulting in degraded service for legitimate users.
CVSS score: 3.7 (AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L)
Remediation:
Normalize client IP addresses before rate-limit evaluation and upgrade the gateway package to version 2.3.1. Monitor edge logs for bursts that rotate address formats while mitigation is being deployed.
