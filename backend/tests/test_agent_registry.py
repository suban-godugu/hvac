from backend.agents.registry import AGENTS, evaluate, list_agents, official_ids, opportunity_agent
from backend.services.official_catalog import CATALOG


def test_five_agents_cover_o1_to_o20():
    ids = [row["opportunity_id"] for mod in AGENTS for row in mod.OPPORTUNITIES]
    assert [m.AGENT_ID for m in AGENTS] == ["scheduling", "plant-control", "ventilation", "variable-speed", "operations"]
    assert "O6-O8" not in official_ids()
    catalog_ids = [row[0] for row in CATALOG]
    assert list(official_ids()) == catalog_ids
    by_agent = {m.AGENT_ID: [r["opportunity_id"] for r in m.OPPORTUNITIES] for m in AGENTS}
    assert by_agent["scheduling"] == ["O1", "O2", "O3", "O4"]
    assert by_agent["plant-control"] == ["O5", "O6", "O7", "O8", "O9"]
    assert by_agent["ventilation"] == ["O10", "O11", "O12", "O13"]
    assert by_agent["variable-speed"] == ["O14", "O15", "O16"]
    assert by_agent["operations"] == ["O17", "O18", "O19", "O20"]
    assert len(list_agents()) == 5


def test_opportunity_agent_registry_covers_catalog():
    for oid in official_ids():
        agent = opportunity_agent(oid)
        assert agent.opportunity_id == oid


def test_unknown_oid_rejected():
    try:
        evaluate("O6-O8")
        assert False, "grouped id must not evaluate"
    except ValueError:
        pass
