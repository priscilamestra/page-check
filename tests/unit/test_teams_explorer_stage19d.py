"""19D: team actions never explode into hundreds of open cards."""
from copy import deepcopy

from pagecheck.ui.components.teams_explorer import team_tasks, team_summary, filter_team_tasks


def report():
    return {"actions_by_team": [
        {"team": "Frontend", "count": 1000,
         "actions": [{"title": "Fix labels", "action": "Add accessible names",
                      "priority": "critical", "finding_id": "axe1"},
                     {"title": "Check navigation", "action": "Verify link",
                      "priority": "medium"}]},
        {"team": "SEO", "actions": [{"title": "Review content", "action": "Review copy",
                                      "priority": "low"}]},
    ]}


def test_rows_use_actual_tasks_not_claimed_count():
    assert len(team_tasks(report())) == 3


def test_summary_gives_explicit_counts_per_team():
    assert team_summary(team_tasks(report())) == [
        {"Team": "Frontend", "Tasks": 2, "Critical": 1, "High": 0},
        {"Team": "SEO", "Tasks": 1, "Critical": 0, "High": 0},
    ]


def test_priority_sorted_without_data_loss():
    rows = team_tasks(report())
    assert [r["priority"] for r in rows] == ["critical", "medium", "low"]
    assert [r["index"] for r in rows] == [0, 1, 2]


def test_filter_by_team_and_case_insensitive_text():
    rows = team_tasks(report())
    assert len(filter_team_tasks(rows, team="SEO", search="COPY")) == 1
    assert filter_team_tasks(rows, team="SEO", search="link") == []


def test_source_data_is_not_mutated():
    original = report()
    copy = deepcopy(original)
    team_tasks(original)
    assert original == copy


def test_handles_old_reports_and_invalid_groups():
    assert team_tasks({"actions_by_team": None}) == []
    assert team_tasks({"actions_by_team": [{"team": "A", "actions": "bad"}, None]}) == []


def test_callback_names_are_supported():
    rows = team_tasks(report(), team_label=lambda _: "TEAM",
                      describe=lambda _: ("Readable", "Do it"))
    assert all(row["team"] == "TEAM" and row["recommendation"] == "Do it" for row in rows)


def test_large_action_list_stays_in_data_not_card_rendering():
    data = {"actions_by_team": [{"team": "Engineering", "actions": [
        {"title": "Investigate item", "priority": "low"} for _ in range(500)
    ]}]}
    rows = team_tasks(data)
    assert len(rows) == 500
    assert len(team_summary(rows)) == 1
    assert len({row["index"] for row in rows}) == 500
