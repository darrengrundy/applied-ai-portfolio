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
    exception_type: ExceptionType
    resolution: Resolution
    collection_point_id: str = Field("", description="point_id for TO_PARCEL_LOCKER or TO_POST_OFFICE, else empty")
    escalate: bool
    escalation_reasons: list[str] = Field(default_factory=list)
    playbook_sections: list[int] = Field(default_factory=list, description="Playbook section numbers you applied")
    reasoning: str = Field(description="At most 60 words: which rule decided it and why")

    _lists = field_validator("escalation_reasons", "playbook_sections", mode="before")(_as_list)


class CriticOut(BaseModel):
    decision: Literal["ACCEPT", "REVISE"]
    issues: list[str] = Field(default_factory=list)
    feedback: str = Field("", description="If REVISE: exactly what to change, citing the playbook section")

    _lists = field_validator("issues", mode="before")(_as_list)


class MessageOut(BaseModel):
    channel: Literal["SMS", "EMAIL"]
    tone: Literal["FORMAL", "CASUAL"]
    subject: str = Field("", description="Email subject; empty for SMS")
    message: str


class WismoOut(BaseModel):
    reply: str = Field(description="The reply to the customer, under 320 characters")
    status_now: str = Field(description="Where the parcel is now, in 3-6 words")


RESOLUTION_TASK = """You are the Resolution Agent. Decide what happened and what Stoa does about it, strictly by the playbook.
Work through the relevant section in order and use the first rule that applies. Use the rule-engine output: automatic
triggers mean you must set escalate=true; discretionary signals are for your judgement (section 12). Pick
collection_point_id from collection_options when the resolution is TO_PARCEL_LOCKER or TO_POST_OFFICE, applying
section 9 to each locker. You do not see the customer's name or contact details and don't need them.
{feedback}"""

CRITIC_RESOLUTION_TASK = """You are the Resolution Critic. Check the proposed decision against the playbook and the case facts:
exception type, resolution (rule order in sections 2-11), the chosen Parcel Locker or Post Office (section 9),
and escalation (section 12). Automatic triggers from the rule engine always require escalation. Don't escalate
routine first-time exceptions that the rules already resolve. ACCEPT if it is correct; REVISE with precise feedback
if not. Do not nitpick the reasoning text."""

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
ACCEPT or REVISE with precise feedback."""

WISMO_TASK = """A customer has asked where their parcel is. Answer under section 14, from the scans and any decision
already made, as they stood at the time of the question. Be warm, brief, specific; never invent a delivery time."""
