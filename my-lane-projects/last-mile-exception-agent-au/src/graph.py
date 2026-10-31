"""LangGraph pipeline: preprocessor -> orchestrator <-> agents -> finalize.

Every node reads and writes through a typed view of the shared state. project_into() filters the
state down to the fields a node may read; merge_back() writes back only the fields it owns. The
customer's name and contact details live only in customer_full, which only the Communication Agent's
view contains."""
import operator
import time
from dataclasses import dataclass, fields
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

import agents as A
import rules
from preprocess import consolidate

MAX_REVISIONS = 2


class State(TypedDict, total=False):
    parcel_id: str
    event: dict
    event_public: dict
    customer_redacted: dict
    customer_full: dict
    parcel: dict
    collection_options: dict
    calendar: dict
    rule_engine: dict
    resolution: dict
    res_feedback: str
    res_revisions: int
    res_accepted: bool
    collection_point: dict
    escalated: bool
    escalation_reasons: list
    forced_by_rules: bool
    message: dict
    msg_feedback: str
    msg_revisions: int
    msg_accepted: bool
    outcome: str
    trace: Annotated[list, operator.add]


# ---- typed views -------------------------------------------------------------------------
@dataclass
class ResolutionAgentView:
    event: dict
    customer_redacted: dict
    parcel: dict
    collection_options: dict
    calendar: dict
    rule_engine: dict
    res_feedback: str
    WRITES = ("resolution",)


@dataclass
class CriticResolutionView:
    event: dict
    customer_redacted: dict
    parcel: dict
    collection_options: dict
    calendar: dict
    rule_engine: dict
    resolution: dict
    res_revisions: int
    WRITES = ("res_accepted", "res_feedback", "res_revisions")


@dataclass
class CommunicationAgentView:
    event_public: dict
    customer_full: dict
    parcel: dict
    calendar: dict
    resolution: dict
    collection_point: dict
    escalated: bool
    msg_feedback: str
    WRITES = ("message",)


@dataclass
class CriticCommunicationView:
    event_public: dict
    customer_redacted: dict
    parcel: dict
    calendar: dict
    resolution: dict
    collection_point: dict
    escalated: bool
    message: dict
    msg_revisions: int
    WRITES = ("msg_accepted", "msg_feedback", "msg_revisions")


def project_into(state, view):
    return view(**{f.name: state.get(f.name) for f in fields(view)})


def merge_back(view, updates):
    bad = set(updates) - set(view.WRITES) - {"trace"}
    if bad:
        raise PermissionError(f"{view.__name__} may not write {sorted(bad)}")
    return updates


def _payload(v):
    return {f.name: getattr(v, f.name) for f in fields(v) if getattr(v, f.name) not in (None, "", {})}


def build(world, llm, agent_model, critic_model):
    cal = world.calendar()

    def preprocessor(s):
        t0 = time.time()
        ev = consolidate(world, s["parcel_id"])
        upd = {"event": ev, "calendar": cal, "res_revisions": 0, "msg_revisions": 0, "res_feedback": "",
               "msg_feedback": ""}
        if ev["is_noise"]:
            upd["outcome"] = "NOISE"
        else:
            c_red = world.lookup_customer(ev["customer_id"])
            parcel = world.lookup_parcel(s["parcel_id"])
            upd.update(customer_redacted=c_red, customer_full=world.lookup_customer(ev["customer_id"], include_pii=True),
                       parcel=parcel, collection_options=world.collection_options(s["parcel_id"]),
                       rule_engine=rules.evaluate(ev, c_red, parcel, cal),
                       event_public={k: ev[k] for k in ("status_code", "event_time", "customer_messages")})
        upd["trace"] = [_t("preprocessor", t0, detail={
            "rows_raw": ev["rows_raw"], "rows_after_dedup": ev["rows_after_dedup"], "status": ev["status_code"],
            "noise": ev["is_noise"], "injection_flagged": ev["guardrail_injection"], "delay_hours": ev["delay_hours"]})]
        if not ev["is_noise"]:
            upd["trace"].append(_t("rule_engine", t0, detail=upd["rule_engine"]))
        return upd

    def resolution_agent(s):
        v = project_into(s, ResolutionAgentView)
        fb = f"\nThe critic sent your last answer back: {v.res_feedback}" if v.res_feedback else ""
        out, use = llm.call(agent_model, A.RESOLUTION_TASK.format(feedback=fb), _payload(v), A.ResolutionOut)
        return merge_back(ResolutionAgentView, {"resolution": out,
                                                "trace": [_t("resolution_agent", None, use, out)]})

    def critic_resolution(s):
        v = project_into(s, CriticResolutionView)
        out, use = llm.call(critic_model, A.CRITIC_RESOLUTION_TASK, _payload(v), A.CriticOut)
        ok = out["decision"] == "ACCEPT" or not (out["issues"] or out["feedback"].strip())  # no reason given = accept
        return merge_back(CriticResolutionView, {
            "res_accepted": ok, "res_feedback": "" if ok else out["feedback"],
            "res_revisions": v.res_revisions + (0 if ok else 1), "trace": [_t("critic_resolution", None, use, out)]})

    def communication_agent(s):
        v = project_into(s, CommunicationAgentView)
        fb = f"\nThe critic sent your last message back: {v.msg_feedback}" if v.msg_feedback else ""
        out, use = llm.call(agent_model, A.COMMUNICATION_TASK.format(feedback=fb), _payload(v), A.MessageOut)
        return merge_back(CommunicationAgentView, {"message": out,
                                                   "trace": [_t("communication_agent", None, use, out)]})

    def critic_communication(s):
        v = project_into(s, CriticCommunicationView)
        out, use = llm.call(critic_model, A.CRITIC_COMMUNICATION_TASK, _payload(v), A.CriticOut)
        ok = out["decision"] == "ACCEPT" or not (out["issues"] or out["feedback"].strip())
        return merge_back(CriticCommunicationView, {
            "msg_accepted": ok, "msg_feedback": "" if ok else out["feedback"],
            "msg_revisions": v.msg_revisions + (0 if ok else 1), "trace": [_t("critic_communication", None, use, out)]})

    def orchestrator(s):
        """Deterministic router state update: settle escalation once the resolution is final."""
        upd = {"trace": []}
        res_final = s.get("resolution") and (s.get("res_accepted") or s.get("res_revisions", 0) >= MAX_REVISIONS)
        if res_final and "escalated" not in s:
            r = s["resolution"]; auto = s["rule_engine"]["automatic_triggers"]
            reasons = list(dict.fromkeys(auto + (r["escalation_reasons"] if r["escalate"] else [])))
            capped = not s.get("res_accepted")
            if capped:
                reasons.append("Agent and critic did not agree after 2 revisions")
            upd.update(escalated=bool(reasons), escalation_reasons=reasons,
                       forced_by_rules=bool(auto) and not r["escalate"],
                       collection_point=world.point(r["collection_point_id"]) if r["collection_point_id"] else {})
            upd["trace"].append(_t("orchestrator", None, detail={
                "escalated": bool(reasons), "forced_by_rule_engine": upd["forced_by_rules"],
                "revision_cap_hit": capped, "reasons": reasons}))
        return upd

    def route(s):
        if s.get("outcome") == "NOISE":
            return "finalize"
        if not s.get("resolution"):
            return "resolution_agent"
        if s.get("res_accepted") is None:
            return "critic_resolution"
        if not s["res_accepted"] and s["res_revisions"] < MAX_REVISIONS:
            return "resolution_agent_retry"
        if not s.get("message"):
            return "communication_agent"
        if s.get("msg_accepted") is None:
            return "critic_communication"
        if not s["msg_accepted"] and s["msg_revisions"] < MAX_REVISIONS:
            return "communication_agent_retry"
        return "finalize"

    def resolution_retry(s):
        upd = resolution_agent(s); upd["res_accepted"] = None  # critic must look again
        return upd

    def communication_retry(s):
        upd = communication_agent(s); upd["msg_accepted"] = None
        return upd

    def finalize(s):
        return {"outcome": s.get("outcome") or ("ESCALATED" if s.get("escalated") else "RESOLVED"),
                "trace": [_t("finalize", None)]}

    g = StateGraph(State)
    for name, fn in [("preprocessor", preprocessor), ("orchestrator", orchestrator),
                     ("resolution_agent", resolution_agent), ("resolution_agent_retry", resolution_retry),
                     ("critic_resolution", critic_resolution), ("communication_agent", communication_agent),
                     ("communication_agent_retry", communication_retry),
                     ("critic_communication", critic_communication), ("finalize", finalize)]:
        g.add_node(name, fn)
    g.set_entry_point("preprocessor")
    g.add_edge("preprocessor", "orchestrator")
    g.add_conditional_edges("orchestrator", route)
    for n in ["resolution_agent", "resolution_agent_retry", "critic_resolution", "communication_agent",
              "communication_agent_retry", "critic_communication"]:
        g.add_edge(n, "orchestrator")
    g.add_edge("finalize", END)
    return g.compile()


def _t(node, t0, usage=None, output=None, detail=None):
    e = {"node": node}
    if usage:
        e.update(model=usage["model"], latency_s=usage["latency_s"], cost_usd=usage["cost_usd"],
                 tokens={k: usage.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens",
                                                      "cache_creation_input_tokens")})
    elif t0:
        e["latency_s"] = round(time.time() - t0, 3)
    if output is not None:
        e["output"] = output
    if detail is not None:
        e["detail"] = detail
    return e
