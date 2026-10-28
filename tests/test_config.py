from home_expense_splitter.config import load_split_config, PROJECT_ROOT, DB_PATH


def test_split_config_percentages():
    # I valori esatti sono configurabili (70/30 storico, 50/50 attuale); il test
    # verifica la struttura e l'invariante somma=100, non i numeri fissi.
    cfg = load_split_config()
    a, b = cfg["percentuali"]["member_a"], cfg["percentuali"]["member_b"]
    assert a + b == 100
    assert "AMAZON" in cfg["escluse"]


def test_paths_point_into_project():
    assert (PROJECT_ROOT / "node.config").is_file()
    assert (PROJECT_ROOT / "backend").is_dir()
    assert str(DB_PATH).endswith("conti.sqlite")
