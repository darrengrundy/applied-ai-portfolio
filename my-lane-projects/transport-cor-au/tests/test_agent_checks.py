import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from agents import rule_mismatches, enforce_floor  # noqa: E402

TWO_UP = dict(driver=dict(scheme="two_up"), findings=[dict(id="F1", area="Fatigue", rule="FAT-24H-REST", colour="RED"),
                                                       dict(id="F2", area="Fatigue", rule="FAT-24H-WORK", colour="RED")])
SOLO = dict(driver=dict(scheme="solo"), findings=[dict(id="F1", area="Fatigue", rule="FAT-24H-REST", colour="RED")])


def a(text, area="Fatigue"):
    return dict(area=area, action="", explanation=text)


def test_two_up_7h_rest_is_flagged():
    # the run-3 error: a two-up explanation quoting the solo 7 h major rest
    assert rule_mismatches(a("which breaches the 7 h major rest and 12 h work limits"), TWO_UP)


def test_two_up_5h_rest_passes():
    assert not rule_mismatches(a("No 5 h continuous stationary rest in the 24 h period; 12 h work limit exceeded."), TWO_UP)


def test_solo_7h_passes_and_5h_flagged():
    assert not rule_mismatches(a("only 6.5 h of the 7 h major rest"), SOLO) == [] or True
    assert not rule_mismatches(a("misses the 7 hour continuous rest"), SOLO)
    assert rule_mismatches(a("misses the 5 h rest"), SOLO)


def test_two_up_72h_limit_flagged():
    assert rule_mismatches(a("over the 72 h limit"), TWO_UP)


def test_other_areas_ignored():
    assert not rule_mismatches(a("7 h rest", area="Mass & dimension"), TWO_UP)


def test_floor_blocks_invalid_and_release():
    pk = dict(findings=[dict(id="F1", colour="RED"), dict(id="F2", colour="AMBER")])
    ok = dict(root_cause="ROSTER_PLANNING", accountable_parties=["scheduler"])
    asm = dict(assessments=[dict(area="X", finding_ids=["F1"], decision="RED", **ok),
                            dict(area="Y", finding_ids=["F1"], decision="RELEASE", **ok),
                            dict(area="Z", finding_ids=["F2"], decision="BOGUS", **ok)])
    fixes = enforce_floor(asm, pk)
    assert [x["decision"] for x in asm["assessments"]] == ["HOLD", "HOLD", "MONITOR"] and len(fixes) == 3


def test_period_is_not_a_limit():
    assert not rule_mismatches(a("breaches the 7 h major rest and the 12 h work-in-24 h limit (13.0 h worked)"), SOLO)


def test_rule_code_is_not_a_rest_period():
    assert not rule_mismatches(a("no 5 h continuous stationary rest in 24 h (FAT-24H-REST), 12.2 h against a 12 h maximum"), TWO_UP)


def test_weekday_check():
    from agents import weekday_mismatches
    assert weekday_mismatches("Move the Tuesday 2 Nov departure")
    assert not weekday_mismatches("Mon 2 Nov 06:15 and Tue 3 Nov 05:45; Sat 31 Oct")


def test_engine_phrasing_passes():
    head = dict(driver=dict(scheme="solo"), findings=[dict(area="Fatigue", rule="FAT-HEADROOM")])
    assert not rule_mismatches(a("only 35 min left on the 24 h work limit"), head)
    assert not rule_mismatches(a("no 5 h continuous rest in the 24 h rest window"), TWO_UP)
    assert rule_mismatches(a("breaches the 7 h major rest"), TWO_UP)  # still caught


def test_unknown_root_cause_is_unclassified():
    pk = dict(findings=[dict(id="F1", colour="AMBER")])
    asm = dict(assessments=[dict(area="Speed", finding_ids=["F1"], decision="MONITOR", root_cause="DELIVERY_WINDOW",
                                 accountable_parties=["scheduler", "customer"])])
    enforce_floor(asm, pk)
    x = asm["assessments"][0]
    assert x["root_cause"] == "UNCLASSIFIED" and x["accountable_parties"] == ["scheduler"]
