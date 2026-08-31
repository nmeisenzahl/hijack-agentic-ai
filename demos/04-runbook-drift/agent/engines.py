"""Deterministic Flock custom engines for Demo 04 — Runbook Drift.

``IntentGateEngine`` authorizes the commander's proposed plan through the
AGT declared-intent runtime (atomic rejection widens nothing; the runbook's
trusted fallback is authorized instead). ``RemediationEngine`` then
dispatches the authorized plan step by step, recording executed, refused,
and failed actions without ever aborting later steps.
"""

from __future__ import annotations

import inspect

from flock.components.agent.base import EngineComponent
from flock.registry import type_registry
from flock.utils.runtime import EvalInputs, EvalResult
from pydantic import PrivateAttr

from agent.models import ExecutionPlan, ProposedRemediationPlan, RemediationOutcome
from agent.security.intent_policy import IntentActionDenied, IntentRuntime

for _model in (ProposedRemediationPlan, ExecutionPlan, RemediationOutcome):
    type_registry.register(_model)
del _model


class IntentGateEngine(EngineComponent):
    """Authorize a ProposedRemediationPlan into an ExecutionPlan via AGT."""

    _intent_runtime: IntentRuntime = PrivateAttr()

    def __init__(self, intent_runtime: IntentRuntime):
        super().__init__()
        self._intent_runtime = intent_runtime

    async def evaluate(self, agent, ctx, inputs: EvalInputs, output_group):
        proposal = inputs.first_as(ProposedRemediationPlan)
        if proposal is None:
            raise RuntimeError("intent_gate received no ProposedRemediationPlan")
        plan = await self._intent_runtime.authorize_plan(proposal)
        return EvalResult.from_object(plan, agent=agent)


class RemediationEngine(EngineComponent):
    """Execute an authorized ExecutionPlan against the governed tools."""

    async def evaluate(self, agent, ctx, inputs: EvalInputs, output_group):
        plan = inputs.first_as(ExecutionPlan)
        if plan is None:
            raise RuntimeError("remediation_agent received no ExecutionPlan")

        tools_by_name = {
            tool.__name__: tool for tool in agent.tools
        }
        executed: list[str] = []
        refused: list[str] = []
        failed: list[str] = []

        for step in plan.steps:
            tool = tools_by_name.get(step.action)
            if tool is None:
                failed.append(f"{step.action}: tool not registered")
                continue
            signature = inspect.signature(tool)
            parameters = signature.parameters
            if any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            ):
                filtered = dict(step.params)
            else:
                filtered = {
                    key: value
                    for key, value in step.params.items()
                    if key in parameters
                }
            required = {
                name
                for name, parameter in parameters.items()
                if parameter.default is inspect.Parameter.empty
                and parameter.kind
                in (
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                )
            }
            missing = sorted(required - set(filtered))
            if missing:
                failed.append(
                    f"{step.action}: missing required parameter {missing[0]}"
                )
                continue
            try:
                await tool(**filtered)
            except IntentActionDenied:
                refused.append(step.action)
            except Exception as exc:
                failed.append(f"{step.action}: {exc}")
            else:
                executed.append(step.action)

        outcome = RemediationOutcome(
            alert_id=plan.alert_id,
            executed=executed,
            refused=sorted(set(plan.refused + refused)),
            failed=failed,
            escalated="escalate_to_human" in executed,
        )
        return EvalResult.from_object(outcome, agent=agent)
