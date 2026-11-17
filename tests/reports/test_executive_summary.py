from osdagbridge.core.reports.demo import demonstration_data
from osdagbridge.core.reports.executive_summary import executive_summary


def test_synthetic_failure_is_reported_without_blanket_pass_claim():
    data = demonstration_data()
    source = executive_summary(data["inputs"], data["outputs"], {})
    assert "Exceeds UR limit" in source
    assert "1.15 (End diaphragms)" in source
    assert "design pass" not in source
    assert "does not run or validate a structural analysis" in source


def test_missing_components_are_incomplete_instead_of_pass():
    source = executive_summary({}, {}, {})
    assert "Incomplete results" in source
    assert "No valid demand/capacity results" in source
    assert "design pass" not in source


def test_girder_columns_show_individual_utilization():
    data = demonstration_data()
    source = executive_summary(data["inputs"], data["outputs"], {})
    assert "Utilization Ratio & 0.72 & 0.88 & 1.08 & 0.93" in source
