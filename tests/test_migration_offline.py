"""La revisione 0001 deve generare SQL additivo (no DROP) in modalita' offline su SQLite."""
import subprocess, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_offline_sql_is_additive(tmp_path):
    env = dict(os.environ, HOMEEXPENSESPLITTER_DATABASE_URL=f"sqlite:///{tmp_path/'x.sqlite'}", PYTHONUTF8="1")
    out = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    sql = out.stdout.upper()
    assert "CREATE TABLE TAGS" in sql.replace('"', "")
    assert "ADD COLUMN" in sql
    assert "DROP TABLE TRANSACTIONS" not in sql
