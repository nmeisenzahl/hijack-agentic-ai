"""AGT declared-intent policy for Demo 04 — Runbook Drift.

A poisoned log line can widen the remediation agent's proposed plan, but it
cannot widen the declared intent. The workflow declares the runbook's
permitted actions as the parent intent; the remediation agent's plan must
narrow that scope. AGT rejects a widened child atomically (IntentScopeError)
and execution falls back to the runbook's trusted safe fallback steps.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from agent.models import ExecutionPlan, ProposedRemediationPlan, Runbook


class IntentActionDenied(RuntimeError):
    """Raised when AGT blocks an action that was never declared."""

    def __init__(self, action: str, reason: str):
        self.action = action
        self.reason = reason
        super().__init__(f"{action}: {reason}")


@dataclass
class IntentRuntime:
    """Declared-intent runtime scoped to one incident workflow run."""

    enabled: bool
    runbook: Runbook
    manager: Any = None
    parent_intent_id: str | None = None
    commander_intent_id: str | None = None
    remediation_intent_id: str | None = None

    @classmethod
    async def create(cls, enabled: bool, runbook: Runbook) -> "IntentRuntime":
        runtime = cls(enabled=enabled, runbook=runbook)
        if not enabled:
            return runtime

        from agent_os.intent import DriftPolicy, IntentAction, IntentManager
        from agent_os.stateless import MemoryBackend

        manager = IntentManager(backend=MemoryBackend())
        parent = await manager.declare_intent(
            agent_id="incident_workflow",
            planned_actions=[
                IntentAction(action=action) for action in runbook.permitted_actions
            ],
            drift_policy=DriftPolicy.HARD_BLOCK,
            ttl_seconds=300,
        )
        parent = await manager.approve_intent(parent.intent_id)
        commander = await manager.create_child_intent(
            parent_intent_id=parent.intent_id,
            agent_id="incident_commander",
            planned_actions=[IntentAction(action="read_logs")],
        )
        commander = await manager.approve_intent(commander.intent_id)
        runtime.manager = manager
        runtime.parent_intent_id = parent.intent_id
        runtime.commander_intent_id = commander.intent_id
        return runtime

    async def authorize_plan(self, plan: ProposedRemediationPlan) -> ExecutionPlan:
        """Authorize a proposed plan as a child intent, or fall back safely.

        A plan that exceeds the parent's runbook scope is rejected atomically
        by AGT; the runbook's safe fallback steps are authorized instead.
        """
        if not self.enabled or self.manager is None:
            return ExecutionPlan(
                alert_id=plan.alert_id,
                steps=plan.steps,
                authorization_status="disabled",
            )

        from agent_os.intent import IntentAction, IntentScopeError

        manager = self.manager
        try:
            child = await manager.create_child_intent(
                parent_intent_id=self.parent_intent_id,
                agent_id="remediation_agent",
                planned_actions=[
                    IntentAction(action=step.action) for step in plan.steps
                ],
            )
            child = await manager.approve_intent(child.intent_id)
            self.remediation_intent_id = child.intent_id
            return ExecutionPlan(
                alert_id=plan.alert_id,
                steps=plan.steps,
                authorization_status="approved_as_proposed",
                intent_id=child.intent_id,
            )
        except IntentScopeError:
            excess = sorted(
                {step.action for step in plan.steps}
                - set(self.runbook.permitted_actions)
            )
            fallback = self.runbook.safe_fallback_steps
            child = await manager.create_child_intent(
                parent_intent_id=self.parent_intent_id,
                agent_id="remediation_agent",
                planned_actions=[
                    IntentAction(action=step.action) for step in fallback
                ],
            )
            child = await manager.approve_intent(child.intent_id)
            self.remediation_intent_id = child.intent_id
            return ExecutionPlan(
                alert_id=plan.alert_id,
                steps=fallback,
                refused=excess,
                fallback_used=True,
                authorization_status="approved_fallback",
                intent_id=child.intent_id,
            )

    async def _check(
        self,
        *,
        intent_id: str | None,
        agent_id: str,
        action: str,
        params: dict[str, Any],
    ) -> None:
        if not self.enabled:
            return
        if self.manager is None or intent_id is None:
            raise RuntimeError(f"No active intent for {agent_id}")
        result = await self.manager.check_action(
            intent_id,
            action,
            params,
            agent_id,
            f"req-{uuid.uuid4().hex[:12]}",
        )
        if not result.allowed:
            raise IntentActionDenied(action, result.reason)

    async def check_commander_action(
        self,
        action: str,
        params: dict[str, Any],
    ) -> None:
        """Gate an incident-commander action on its declared child intent."""
        await self._check(
            intent_id=self.commander_intent_id,
            agent_id="incident_commander",
            action=action,
            params=params,
        )

    async def check_remediation_action(
        self,
        intent_id: str | None,
        action: str,
        params: dict[str, Any],
    ) -> None:
        """Gate a remediation action on the execution plan's child intent."""
        await self._check(
            intent_id=intent_id,
            agent_id="remediation_agent",
            action=action,
            params=params,
        )

    async def verify_children(self) -> list[Any]:
        """Verify the commander child and the latest remediation child.

        The parent intent is rendered separately via ``get_parent_intent``;
        it is never presented as recursively verified.
        """
        if not self.enabled or self.manager is None:
            return []
        verifications = []
        if self.commander_intent_id is not None:
            verifications.append(
                await self.manager.verify_intent(self.commander_intent_id)
            )
        if self.remediation_intent_id is not None:
            verifications.append(
                await self.manager.verify_intent(self.remediation_intent_id)
            )
        return verifications

    async def get_parent_intent(self) -> Any:
        """Return the declared parent intent for separate scope rendering."""
        if not self.enabled or self.manager is None or self.parent_intent_id is None:
            return None
        return await self.manager.get_intent(self.parent_intent_id)
