"""Tools for Demo 01: Poisoned Advisory."""

from __future__ import annotations


def mark_false_positive(cve_id: str) -> str:
    """Mark a vulnerability as a false positive — no patch will be applied."""
    print(f"\n⚠️  CVE {cve_id} marked FALSE POSITIVE — patch deferred, escalation closed")
    print("   Triage action: false_positive | No remediation scheduled\n")
    return f"CVE {cve_id} marked as false positive."
