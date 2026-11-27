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
    with engine.begin() as conn:
        for name in SQL_FILES:
            queries = split_sql((SQL_DIR/name).read_text(encoding="utf-8"))
            
            for query in queries:
                conn.execute(text(query))
            
            print(f"file name> {name} has {len(queries)} queries")
            


def load_facts(engine, claims, lines):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE fact_claim_lines, fact_claims"))
        
        claims.to_sql("fact_claims", conn, if_exists="append", index=False, method="multi", chunksize=1000)
        
        lines.to_sql("fact_claim_lines", conn, if_exists="append", index=False,  method="multi", chunksize=1000)
        
    print(f"fact_claims created with {len(claims)} rows")
    print(f"fact_claim_lines created with {len(lines)} rows")
    
    
    
def count_rows(engine):
    with engine.connect() as conn:
        for table in TABLES:
            n = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table:<20} {n:>7,}")
            


# new: database validation func
def validate_in_db(engine):
    sql = (SQL_DIR / "04_validation.sql").read_text(encoding="utf-8")
    with engine.connect() as conn:
        rows = conn.execute(text(sql)).fetchall()

    print("Database checks:")
    failures = 0
    for name, count in rows:
        failures += count
        result = "ok" if count == 0 else "FAILED"
        print(f"  {name:<45} {count:>5}  {result}")
    return failures



            
def step(name):
    print(f"\n[{time.strftime('%H:%M:%S')}] {name}")
    

def main():
    start = time.perf_counter()
    engine = get_engine()
    
    step("1/5 rebuilding shcema and seed data")
    run_sql_files(engine)
    
    step("2/5 loading dimensions")
    load_dimension_tables(engine)  
    
    step("3/5 building facts")
    claims, lines = build_facts()    

    step("4/5 simulating claim outcomes")
    sim = simulate(claims)
    if check(sim) > 0:
        raise SystemExit("simulated checks failed and nothing was loaded")
    

    step("5/5 loading facts")
    load_facts(engine, sim, lines)
    
    step("6/6 validating loaded data")
    if validate_in_db(engine) > 0:
        raise SystemExit("Database checks failed. See the report above.")
    
    
    count_rows(engine)
    print(f"created in {time.perf_counter() - start}sec")
    


if __name__ == "__main__":
    main()
    

    