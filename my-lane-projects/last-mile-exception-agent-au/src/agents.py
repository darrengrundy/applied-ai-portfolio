"""The LLM agents: structured output schemas and their instructions."""
from typing import Literal

import json

from pydantic import BaseModel, Field, field_validator

Resolution = Literal["REDELIVER_TODAY", "RESCHEDULE", "TO_PARCEL_LOCKER", "TO_POST_OFFICE", "REPLACE",
                     "RETURN_TO_SENDER"]
ExceptionType = Literal["ATTEMPTED", "ACCESS_ISSUE", "ADDRESS_ISSUE", "DAMAGED", "REFUSED", "WEATHER_DELAY",
                        "HEAT_HOLD", "VEHICLE_DELAY", "ROAD_CLOSURE", "DELIVERED_NOT_RECEIVED"]


def _as_list(v):
    """Models occasionally return a list as a JSON string or a single string; accept both."""
    if isinstance(v, str):
        v = v.strip()
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else [parsed]
        except ValueError:
            return [v] if v else []
    return v


class ResolutionOut(BaseModel):
    # reasoning comes first so the model thinks before it commits to the decision fields
    reasoning: str = Field(description="Think first, at most 80 words: walk the playbook rules in order and say "
                                       "which one decides the case, then which section 12 triggers apply, if any")
    exception_type: ExceptionType
    resolution: Resolution = Field(description="Must match the conclusion of your reasoning")
    collection_point_id: str = Field("", description="point_id for TO_PARCEL_LOCKER or TO_POST_OFFICE, else empty")
    playbook_sections: list[int] = Field(default_factory=list, description="Playbook section numbers you applied")
    escalation_reasons: list[str] = Field(default_factory=list,
                                          description="Only section 12 triggers that APPLY. Empty if none apply.")
    escalate: bool = Field(description="true if and only if escalation_reasons is not empty")

    _lists = field_validator("escalation_reasons", "playbook_sections", mode="before")(_as_list)


class CriticOut(BaseModel):
    issues: list[str] = Field(default_factory=list, description="Concrete errors found. Empty if none.")
    feedback: str = Field("", description="If there are issues: exactly what to change, citing the playbook section")
    decision: Literal["ACCEPT", "REVISE"] = Field(description="REVISE only if issues is not empty")

    _lists = field_validator("issues", mode="before")(_as_list)


class MessageOut(BaseModel):
    tone: Literal["FORMAL", "CASUAL"] = Field(description="FORMAL for VIP, PREMIUM, TRADE or escalated; else CASUAL")
    channel: Literal["SMS", "EMAIL"]
    subject: str = Field("", description="Email subject; empty for SMS")
    message: str


class WismoOut(BaseModel):
    reply: str = Field(description="The reply to the customer, under 320 characters")
    status_now: str = Field(description="Where the parcel is now, in 3-6 words")


RESOLUTION_TASK = """You are the Resolution Agent. Decide what happened and what Stoa does about it, strictly by the playbook.
Work through the relevant section in order and use the first rule that applies. Use the rule-engine output: automatic
triggers and review signals both mean escalate=true (section 12). Pick
collection_point_id from collection_options when the resolution is TO_PARCEL_LOCKER or TO_POST_OFFICE, applying
section 9 to each locker. You do not see the customer's name or contact details and don't need them.
Escalate only for triggers that apply: every automatic trigger from the rule engine, plus any discretionary signal
(section 12 lists both). Never list a rule that does not apply as a reason.
{feedback}"""

CRITIC_RESOLUTION_TASK = """You are the Resolution Critic. Check the proposed decision against the playbook and the case facts:
exception type, resolution (rule order in sections 2-11), the chosen Parcel Locker or Post Office (section 9),
and escalation (section 12). Automatic triggers and review signals from the rule engine always require escalation; nothing
else does (section 12). ACCEPT if it is correct; REVISE with precise feedback
if not. Do not nitpick the reasoning text. Only REVISE for a concrete error you can name, and say exactly what
to change. If the decision is correct, ACCEPT even if you would have worded it differently."""

COMMUNICATION_TASK = """You are the Communication Agent, the only agent that sees the customer's name and contact
details. Write the message Stoa sends now, following section 13 (and section 3 or 11 if the customer has complained).
Use their preferred channel; trade accounts by email to the receiving contact. SMS under 320 characters.
FORMAL tone for VIP, Premium, trade accounts and escalated cases; CASUAL otherwise. State exactly what happens next
and when. Never include driver notes, GPS details or fraud checks.
{feedback}"""

CRITIC_COMMUNICATION_TASK = """You are the Communication Critic. Check the message against section 13 and the decided
resolution: correct channel and tone, SMS length, says what happens next and when (consistent with the resolution and
calendar), names the locker or Post Office with hours and hold period when carded, mentions a team member will be in
touch if escalated, makes no promises the resolution doesn't support, and leaks no driver notes, GPS or fraud details.
Only REVISE for a concrete breach of these rules, and say exactly what to change. Style preferences are not
breaches: if the message meets the rules, ACCEPT."""

WISMO_TASK = """A customer has asked where their parcel is. Answer under section 14, from the scans and any decision
already made, as they stood at the time of the question. Be warm, brief, specific; never invent a delivery time."""
