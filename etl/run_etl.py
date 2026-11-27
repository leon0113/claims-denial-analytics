import time
from pathlib import Path
from sqlalchemy import text

from etl.db import get_engine
from etl.dimensions import load_dimension_tables
from etl.facts import build_facts
from etl.simulate import simulate, check


SQL_DIR = Path("sql")
SQL_FILES = ["01_schema.sql", "02_seed_denial_reasons.sql"]
TABLES = ["dim_payer", "dim_patient", "dim_organization", "dim_provider", "dim_denial_reason", "fact_claims", "fact_claim_lines"]

def split_sql(sql):
    lines = [ln for ln in sql.splitlines() if not ln.strip().startswith("--")]
    return [s.strip() for s in "\n".join(lines).split(";") if s.strip()]


def run_sql_files(engine):
    pass