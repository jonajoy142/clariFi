import re
import time
from decimal import Decimal
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.ai.schemas.outputs import ChatAnswer, EvidenceItem, FinancialContextPack, RiskFinding
from app.ai.tools.base import ToolRuntime
from app.ai.tools.finance_tools import (
    build_tool_registry,
)
from app.ai.verification.numeric_grounding import verify_numeric_grounding
from app.models.finance import AuditEventType, ChatMessage, ChatThread
from app.repositories.finance import AuditRepository, FinanceRepository, OrganizationRepository, WorkflowRepository

try:
    from langgraph.graph import END, StateGraph
except Exception:
    END = None
    StateGraph = None


class ChatState(TypedDict, total=False):
    question: str
    intent: str
    tool_plan: list[dict[str, Any]]
    tool_outputs: dict[str, Any]
    evidence: list[dict[str, Any]]
    context_pack: FinancialContextPack
    answer: ChatAnswer


class CFOChatWorkflow:
    prompt_version = "cfo-chat-v1"
    model_used = "deterministic-template-with-llm-ready-schema"

    def __init__(self, db: Session):
        self.db = db
        self.tools = build_tool_registry()
        self.workflow_repo = WorkflowRepository(db)
        self.audit_repo = AuditRepository(db)
        self.finance_repo = FinanceRepository(db)
        self.org_repo = OrganizationRepository(db)

    def run(self, organization_id: str, question: str, thread_id: str | None = None) -> dict[str, Any]:
        started = time.perf_counter()
        run = self.workflow_repo.start(organization_id, "cfo_chat_workflow", {"question": question})
        state: ChatState = {"question": question}
        state = self._run_orchestrated_steps(organization_id, run.id, state)

        answer = state["answer"]
        audit = self.audit_repo.create(
            organization_id=organization_id,
            event_type=AuditEventType.ai_response.value,
            actor_type="system",
            entity_type="chat_message",
            action="cfo_chat_workflow.generate_answer",
            inputs={"question": question, "context_pack": answer.context_pack.model_dump(mode="json")},
            outputs=answer.model_dump(mode="json"),
            prompt_version=self.prompt_version,
            model_used=self.model_used,
            verification_status="verified" if answer.verification.passed else "rejected",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        thread = self._store_messages(organization_id, question, answer, audit.id, thread_id)
        self.workflow_repo.finish(run, {"answer": answer.answer, "audit_log_id": audit.id}, duration_ms=int((time.perf_counter() - started) * 1000))
        self.db.commit()
        return {
            "answer": answer.answer,
            "thread_id": thread.id,
            "tools_used": answer.tools_used,
            "evidence": [item.model_dump(mode="json") for item in answer.evidence],
            "audit_log_id": audit.id,
            "verification": answer.verification.model_dump(mode="json"),
        }

    def _run_orchestrated_steps(self, organization_id: str, run_id: str, state: ChatState) -> ChatState:
        steps = [
            ("classify_question", self.classify_question),
            ("plan_tools", self.plan_tools),
            ("execute_tools", lambda s: self.execute_tools(organization_id, s)),
            ("retrieve_evidence", lambda s: self.retrieve_evidence(organization_id, s)),
            ("build_context_pack", lambda s: self.build_context_pack(organization_id, s)),
            ("generate_answer", self.generate_answer),
            ("verify_answer", self.verify_answer),
        ]
        if StateGraph is None:
            for step_name, fn in steps:
                state = self._run_step(run_id, step_name, fn, state)
            return state

        graph = StateGraph(ChatState)
        for step_name, fn in steps:
            graph.add_node(step_name, lambda current_state, fn=fn, step_name=step_name: self._run_step(run_id, step_name, fn, current_state))
        graph.set_entry_point("classify_question")
        for current, next_step in zip([step[0] for step in steps], [step[0] for step in steps][1:]):
            graph.add_edge(current, next_step)
        graph.add_edge("verify_answer", END)
        compiled = graph.compile()
        return compiled.invoke(state)

    def _run_step(self, run_id: str, step_name: str, fn, state: ChatState) -> ChatState:
        before = time.perf_counter()
        next_state = fn(state)
        self.workflow_repo.step(run_id, step_name, {"question": state.get("question")}, _jsonable_state(next_state), duration_ms=int((time.perf_counter() - before) * 1000))
        return next_state

    def classify_question(self, state: ChatState) -> ChatState:
        question = state["question"].lower()
        if any(term in question for term in ["hire", "hiring", "employee at", "engineer at"]):
            intent = "hiring_question"
        elif any(term in question for term in ["how many employees", "employee count", "headcount", "team size"]):
            intent = "employee_count_question"
        elif any(term in question for term in ["burn summary", "burn breakdown", "salaries vs", "salary vs", "salaries", "payroll vs", "other costs"]):
            intent = "burn_breakdown_question"
        elif any(term in question for term in ["who owes", "owed", "receivable", "invoice", "unpaid", "overdue"]):
            intent = "receivables_question"
        elif any(term in question for term in ["raise", "fundraising", "fundraise", "start fundraising"]):
            intent = "fundraising_question"
        elif any(term in question for term in ["vendor", "aws", "cut", "subscription", "saas", "waste"]):
            intent = "vendor_question"
        elif any(term in question for term in ["tax", "reserve", "gst"]):
            intent = "tax_question"
        elif any(term in question for term in ["run out of cash", "cash gap", "cash shortage", "pays late", "pay late", "client pays late"]):
            intent = "cash_gap_question"
        elif any(term in question for term in ["cash risk", "runway", "cash position", "cash health"]):
            intent = "cash_gap_question"
        else:
            intent = "unknown_question"
        state["intent"] = intent
        return state

    def plan_tools(self, state: ChatState) -> ChatState:
        intent = state.get("intent")
        plan: list[dict[str, Any]] = []
        if intent == "hiring_question":
            plan.append({"name": "calculate_runway", "input": {}})
            monthly_cost = _extract_hiring_cost(state["question"]) or Decimal("180000")
            plan.append({"name": "simulate_hiring", "input": {"role": "Engineer", "monthly_cost": str(monthly_cost)}})
        elif intent == "receivables_question":
            plan.extend([{"name": "list_receivables", "input": {}}, {"name": "calculate_receivables", "input": {}}])
        elif intent == "employee_count_question":
            plan.append({"name": "count_employees", "input": {}})
        elif intent == "burn_breakdown_question":
            plan.extend([{"name": "calculate_burn_breakdown", "input": {}}, {"name": "calculate_burn", "input": {}}])
        elif intent == "fundraising_question":
            plan.append({"name": "calculate_runway", "input": {}})
        elif intent == "vendor_question":
            plan.extend([{"name": "calculate_burn_breakdown", "input": {}}, {"name": "calculate_burn", "input": {}}])
            plan.append({"name": "simulate_vendor_cut", "input": {"vendor_name": "OpenAI duplicate workspace", "monthly_savings": str(_extract_hiring_cost(state["question"]) or Decimal("25000"))}})
        elif intent == "tax_question":
            plan.append({"name": "calculate_tax_reserve", "input": {}})
        elif intent == "cash_gap_question":
            plan.extend([{"name": "calculate_cash_gap", "input": {}}, {"name": "list_receivables", "input": {}}])
        else:
            plan.append({"name": "calculate_runway", "input": {}})
            plan.append({"name": "calculate_receivables", "input": {}})
        plan.append({"name": "retrieve_evidence", "input": {"query": state["question"]}})
        state["tool_plan"] = plan
        return state

    def execute_tools(self, organization_id: str, state: ChatState) -> ChatState:
        runtime = ToolRuntime(db=self.db, organization_id=organization_id)
        outputs = {}
        for call in state["tool_plan"]:
            tool = self.tools.get(call["name"])
            payload = tool.input_schema(**call["input"])
            outputs[call["name"]] = tool.execute(runtime, payload)
        state["tool_outputs"] = outputs
        return state

    def retrieve_evidence(self, organization_id: str, state: ChatState) -> ChatState:
        evidence = state["tool_outputs"].get("retrieve_evidence", {}).get("items", [])
        state["evidence"] = evidence
        return state

    def build_context_pack(self, organization_id: str, state: ChatState) -> ChatState:
        org = self.org_repo.get(organization_id)
        facts = self.finance_repo.latest_fact_map(organization_id)
        outputs = state.get("tool_outputs", {})
        allowed_numbers: list[Decimal] = []
        source_fact_ids: list[str] = []
        for fact in facts.values():
            allowed_numbers.append(Decimal(str(fact.value)).quantize(Decimal("0.01")))
            source_fact_ids.append(fact.id)
        for output in outputs.values():
            _collect_numbers(output, allowed_numbers)
        evidence_items = list(state.get("evidence", []))
        for output in outputs.values():
            if isinstance(output, dict) and isinstance(output.get("evidence"), list):
                evidence_items.extend(output["evidence"])
        evidence = [
            EvidenceItem(
                source_type=item.get("source_type", "document"),
                source_id=item.get("source_id", "-"),
                title=item.get("title", "Evidence"),
                excerpt=item.get("excerpt", ""),
                amount=Decimal(str(item["amount"])) if item.get("amount") is not None else None,
                metadata=item.get("metadata", {}),
            )
            for item in evidence_items
        ]
        risk = _risk_from_facts(facts)
        state["context_pack"] = FinancialContextPack(
            organization_id=organization_id,
            user_type=org.user_type if org else "startup",
            question=state["question"],
            cash_position=outputs.get("calculate_runway", {}),
            runway=outputs.get("calculate_runway", {}) or outputs.get("calculate_cash_gap", {}),
            burn_rate=outputs.get("calculate_burn", {}),
            receivables=outputs.get("calculate_receivables", {}),
            simulations={"hiring": outputs.get("simulate_hiring")} if outputs.get("simulate_hiring") else {},
            operations=outputs,
            top_risks=[risk] if risk else [],
            evidence=evidence,
            allowed_numbers=allowed_numbers,
            source_fact_ids=source_fact_ids,
        )
        return state

    def generate_answer(self, state: ChatState) -> ChatState:
        context = state["context_pack"]
        tools_used = [call["name"] for call in state.get("tool_plan", [])]
        answer = _grounded_answer(context, state.get("intent", "cash_risk"))
        verification = verify_numeric_grounding(answer, context)
        state["answer"] = ChatAnswer(
            answer=answer,
            tools_used=tools_used,
            evidence=context.evidence,
            verification=verification,
            context_pack=context,
        )
        return state

    def verify_answer(self, state: ChatState) -> ChatState:
        answer = state["answer"]
        if not answer.verification.passed:
            context = answer.context_pack
            fallback = "I cannot produce a grounded answer because verification found unsupported numbers. Re-run the deterministic tools or inspect the audit trail."
            state["answer"] = ChatAnswer(
                answer=fallback,
                tools_used=answer.tools_used,
                evidence=answer.evidence,
                verification=answer.verification,
                context_pack=context,
            )
        return state

    def _store_messages(self, organization_id: str, question: str, answer: ChatAnswer, audit_log_id: str, thread_id: str | None) -> ChatThread:
        thread = self.db.get(ChatThread, thread_id) if thread_id else None
        if thread is None:
            thread = ChatThread(organization_id=organization_id, title=question[:80])
            self.db.add(thread)
            self.db.flush()
        self.db.add(ChatMessage(organization_id=organization_id, thread_id=thread.id, role="user", content=question))
        self.db.add(
            ChatMessage(
                organization_id=organization_id,
                thread_id=thread.id,
                role="assistant",
                content=answer.answer,
                tool_calls=[{"name": name} for name in answer.tools_used],
                evidence=[item.model_dump(mode="json") for item in answer.evidence],
                audit_log_id=audit_log_id,
            )
        )
        self.db.flush()
        return thread


def _grounded_answer(context: FinancialContextPack, intent: str) -> str:
    outputs = context.operations
    runway_fact = context.runway.get("runway_months", {})
    cash_fact = context.runway.get("current_cash", {})
    burn_fact = context.runway.get("monthly_burn", {})
    runway = Decimal(str(runway_fact.get("value", "0"))).quantize(Decimal("0.01"))
    cash = Decimal(str(cash_fact.get("value", "0"))).quantize(Decimal("0.01"))
    burn = Decimal(str(burn_fact.get("value", "0"))).quantize(Decimal("0.01"))

    if intent == "hiring_question" and context.simulations.get("hiring"):
        sim = context.simulations["hiring"]
        return (
            f"You can hire only if you accept a higher cash-risk profile. Verified runway moves from "
            f"{Decimal(str(sim['runway_before'])).quantize(Decimal('0.01'))} months to "
            f"{Decimal(str(sim['runway_after'])).quantize(Decimal('0.01'))} months. "
            f"Monthly burn moves from ₹{Decimal(str(sim['burn_before'])):,.0f} to ₹{Decimal(str(sim['burn_after'])):,.0f}. "
            f"The fully-loaded monthly payroll increase is ₹{Decimal(str(sim.get('monthly_payroll_increase', sim.get('payroll_increase')))):,.0f}/month, "
            f"one-time setup cost is ₹{Decimal(str(sim.get('one_time_cost', 0))):,.0f}, and the resulting risk level is {sim['risk_level']}. "
            f"30/60/90 day cash impact is ₹{Decimal(str(sim.get('cash_impact_30d', 0))):,.0f}, "
            f"₹{Decimal(str(sim.get('cash_impact_60d', 0))):,.0f}, and ₹{Decimal(str(sim.get('cash_impact_90d', 0))):,.0f}. "
            "The calculation came from the hiring scenario engine, not the language model."
        )
    if intent == "employee_count_question":
        employees = outputs.get("count_employees", {})
        roles = employees.get("roles", [])
        role_lines = "; ".join(
            f"{item.get('name')} ({item.get('role')}, ₹{Decimal(str(item.get('monthly_cost', 0))):,.0f}/month)"
            for item in roles
        ) or "no active roles found"
        return (
            f"There are {employees.get('employee_count', 0)} active employees in payroll_items. "
            f"Verified monthly payroll is ₹{Decimal(str(employees.get('monthly_payroll', 0))):,.0f}. "
            f"Roles: {role_lines}. This answer uses payroll_items only."
        )
    if intent == "burn_breakdown_question":
        breakdown = outputs.get("calculate_burn_breakdown", {})
        categories = breakdown.get("categories", {})
        parts = []
        for key, label in [
            ("payroll", "payroll"),
            ("vendors", "vendors"),
            ("subscriptions", "subscriptions"),
            ("taxes", "taxes"),
            ("other_operating_expenses", "other operating expenses"),
        ]:
            item = categories.get(key, {})
            parts.append(f"{label}: ₹{Decimal(str(item.get('amount', 0))):,.0f} ({Decimal(str(item.get('percentage', 0))).quantize(Decimal('0.01'))}%)")
        return (
            f"Verified burn breakdown: {'; '.join(parts)}. "
            f"The total burn basis for this breakdown is ₹{Decimal(str(breakdown.get('total_burn_basis', 0))):,.0f}. "
            "Payroll comes from payroll_items; vendors/subscriptions/taxes/other operating expenses come from normalized transactions and subscriptions."
        )
    if intent == "receivables_question":
        details = outputs.get("list_receivables", {})
        rows = details.get("receivables", [])
        if rows:
            rows_text = " ".join(
                f"{row['customer_name']} owes ₹{Decimal(str(row['amount'])):,.0f} on {row['invoice_number']}, due {row['due_on']}, "
                f"{row['days_overdue']} days overdue, priority {row['priority']}; suggested action: {row['suggested_action']}."
                for row in rows[:5]
            )
            return f"Unpaid receivables total ₹{Decimal(str(details.get('total_unpaid', 0))):,.0f}. {rows_text}"
        total = Decimal(str(context.receivables.get("total_receivables", {}).get("value", "0"))).quantize(Decimal("0.01"))
        overdue = Decimal(str(context.receivables.get("overdue_receivables", {}).get("value", "0"))).quantize(Decimal("0.01"))
        return (
            f"Customers owe ₹{total:,.0f}, of which ₹{overdue:,.0f} is overdue. "
            f"Current cash is ₹{cash:,.0f}, monthly burn is ₹{burn:,.0f}, and verified runway is {runway} months. "
            "Prioritize the overdue invoice because it improves cash without increasing fixed costs."
        )
    if intent == "fundraising_question":
        status = "start fundraising now" if runway <= Decimal("7") else "prepare materials but do not panic this week"
        return (
            f"Current verified runway is {runway} months. The default fundraising lead time is 7 months. "
            f"Recommendation: {status}. Current cash is ₹{cash:,.0f} and monthly burn is ₹{burn:,.0f}."
        )
    if intent == "vendor_question":
        recurring = Decimal(str(context.burn_rate.get("recurring_subscriptions_monthly", {}).get("value", "0"))).quantize(Decimal("0.01"))
        sim = outputs.get("simulate_vendor_cut", {})
        sim_text = ""
        if sim:
            sim_text = (
                f" A ₹{Decimal(str(sim.get('monthly_savings', 0))):,.0f}/month vendor cut would move runway from "
                f"{Decimal(str(sim.get('runway_before', 0))).quantize(Decimal('0.01'))} to "
                f"{Decimal(str(sim.get('runway_after', 0))).quantize(Decimal('0.01'))} months."
            )
        return (
            f"Recurring vendor spend is ₹{recurring:,.0f}/month. Current monthly burn is ₹{burn:,.0f} and runway is {runway} months. "
            f"Review the vendor evidence and cut duplicate SaaS-like spend before changing hiring plans.{sim_text}"
        )
    if intent == "tax_question":
        reserve = outputs.get("calculate_tax_reserve", {})
        income = Decimal(str(reserve.get("income_received_90d", {}).get("value", "0"))).quantize(Decimal("0.01"))
        suggested = Decimal(str(reserve.get("suggested_tax_reserve", {}).get("value", "0"))).quantize(Decimal("0.01"))
        return (
            f"Based on received income of ₹{income:,.0f}, the deterministic tax reserve rule suggests setting aside ₹{suggested:,.0f}. "
            "This is an estimate only and is not tax or legal advice."
        )
    if intent == "cash_gap_question":
        gap = outputs.get("calculate_cash_gap", {})
        receivables = outputs.get("list_receivables", {}).get("receivables", [])
        invoice_text = ""
        if receivables:
            first = receivables[0]
            invoice_text = (
                f" The invoice most relevant to the forecast is {first['invoice_number']} from {first['customer_name']} for "
                f"₹{Decimal(str(first['amount'])):,.0f}, due {first['due_on']} and {first['days_overdue']} days overdue."
            )
        return (
            f"Cash gap risk is {gap.get('cash_gap_risk', 'unknown')}. Current cash is ₹{cash:,.0f}, monthly burn is ₹{burn:,.0f}, "
            f"and estimated days until cash shortage is {Decimal(str(gap.get('days_until_cash_shortage', 0))).quantize(Decimal('0.01'))}. "
            f"Overdue invoice cash impact is ₹{Decimal(str(gap.get('overdue_invoice_cash_impact', 0))):,.0f}.{invoice_text}"
        )
    return (
        "I could not classify that into a supported CFO workflow. Ask about hiring, employee count, burn breakdown, receivables, fundraising, vendors, tax reserve, or cash gap."
    )


def _extract_hiring_cost(question: str) -> Decimal | None:
    match = re.search(r"₹?\s*(\d+(?:\.\d+)?)\s*L", question, re.IGNORECASE)
    if match:
        return Decimal(match.group(1)) * Decimal("100000")
    match = re.search(r"₹\s*([\d,]+)", question)
    if match:
        return Decimal(match.group(1).replace(",", ""))
    return None


def _collect_numbers(value: Any, numbers: list[Decimal]) -> None:
    if isinstance(value, dict):
        for item in value.values():
            _collect_numbers(item, numbers)
    elif isinstance(value, list):
        for item in value:
            _collect_numbers(item, numbers)
    elif isinstance(value, str):
        for match in re.findall(r"\d[\d,]*(?:\.\d+)?", value):
            try:
                numbers.append(Decimal(match.replace(",", "")).quantize(Decimal("0.01")))
            except Exception:
                continue
    else:
        try:
            numbers.append(Decimal(str(value)).quantize(Decimal("0.01")))
        except Exception:
            return


def _risk_from_facts(facts: dict) -> RiskFinding | None:
    if "runway_months" not in facts:
        return None
    runway = Decimal(str(facts["runway_months"].value))
    severity = "critical" if runway < Decimal("6") else "high" if runway < Decimal("9") else "medium"
    return RiskFinding(
        title="Runway exposure",
        severity=severity,
        financial_impact=Decimal(str(facts.get("monthly_burn").value)) if facts.get("monthly_burn") else None,
        explanation=f"Runway is {runway} months based on verified cash and burn.",
        evidence=[],
        confidence=Decimal("0.9"),
    )


def _jsonable_state(state: ChatState) -> dict[str, Any]:
    safe = {}
    for key, value in state.items():
        if hasattr(value, "model_dump"):
            safe[key] = value.model_dump(mode="json")
        elif key != "context_pack":
            safe[key] = value
    return safe
