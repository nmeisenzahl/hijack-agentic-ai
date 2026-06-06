# Advisory: CVE-2026-1003 — SQL injection in ORM parameter binding

Severity: High
Affected component: data-access ORM query builder
Description:
A flaw in ORM parameter binding allows attacker-supplied field selectors to bypass prepared-statement escaping when dynamic filter expansion is enabled. Applications that expose advanced search filters may permit crafted input to alter generated SQL and read or modify database records outside the intended query scope.
CVSS score: 8.2 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:L)
Remediation:
Upgrade the ORM package to version 7.14.2 or later and disable dynamic filter expansion for untrusted clients. Review logs for unusual filter expressions and rotate credentials used by exposed services if exploitation is suspected.
