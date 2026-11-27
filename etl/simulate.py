import numpy as np
import pandas as pd

RAW = "data/raw/"
SEED = 42

DENIAL_RATE = {
    "Medicare": 0.08,
    "Medicaid": 0.12,
    "Dual Eligible": 0.10,
    "Humana": 0.11,
    "Blue Cross Blue Shield": 0.09,
    "UnitedHealthcare": 0.14,
    "Aetna": 0.10,
    "Cigna Health": 0.12,
    "Anthem": 0.09,
}


LATE_RATE = 0.10          
LATE_EXTRA = 0.15         
HIGH_CHARGE_EXTRA = 0.05  
PARTIAL_RATE = 0.05       
APPEAL_RATE = 0.60 
APPEAL_DECIDE_DAYS = 45


ADJ_DAYS = {
    "GOVERNMENT": (20, 46),
    "PRIVATE": (10, 31),
    "NO_INSURANCE": (0, 1),
}

REASON_WEIGHTS = {
    "late": {
        "CO-29": 0.70,
        "CO-16": 0.10,
        "CO-11": 0.10,
        "CO-27": 0.10
    },
    "high": {
        "CO-197": 0.50,
        "CO-50": 0.30,
        "CO-16": 0.20
    },
    "general": {
        "CO-16": 0.25,
        "CO-11": 0.15, 
        "CO-27": 0.15, 
        "CO-50": 0.15,
        "CO-18": 0.10, 
        "CO-96": 0.10, 
        "CO-197": 0.10
    }
}


def load_payers():
    p = pd.read_csv(RAW + "payers.csv", usecols=["Id", "NAME", "OWNERSHIP"])
    return p.rename(columns={"Id": "payer_id", "NAME": "payer_name", "OWNERSHIP": "ownership"})



def days(n_array):
    return pd.to_timedelta(n_array, unit="D")



def simulate(claims, seed=SEED):
    rng = np.random.default_rng(seed)
    df = claims.merge(load_payers(), on="payer_id", how="left")
    n=len(df)
    
    service = pd.to_datetime(df["service_date"])
    as_of = service.max()
    
    # expected amount from insurance
    df["expected_insurance"] = df["insurance_paid"]
    
    insured = (df["ownership"] != "NO_INSURANCE") & (df["expected_insurance"] > 0)
    
    late = rng.random(n) < LATE_RATE
    
    # how much late to submit
    submit_lag = np.where(late, rng.integers(31, 61, n), rng.integers(1, 8, n))
    submitted = service + days(submit_lag)
    
    
    # insurance decision days
    lo = df["ownership"].map(lambda o: ADJ_DAYS[o][0]).to_numpy()
    hi = df["ownership"].map(lambda o: ADJ_DAYS[o][1]).to_numpy()
    
    adjudicated = submitted + days(rng.integers(lo, hi))
    
    # pending claims
    pending = (adjudicated > as_of).to_numpy()
    
    # denial percentage
    high_charge = (df["total_charge"] > df["total_charge"].quantile(0.9)).to_numpy()
    
    p_deny = (df["payer_name"].map(DENIAL_RATE).fillna(0).to_numpy() +
                np.where(late, LATE_EXTRA, 0) +
                np.where(high_charge, HIGH_CHARGE_EXTRA, 0))
    
    denied= insured.to_numpy() & (rng.random(n) < p_deny) & ~pending
    
    reason = np.full(n, None, dtype=object)
    # find denial reasons
    contexts = {
        "late": denied & late,
        "high": denied & ~late & high_charge,
        "general": denied & ~late & ~high_charge,
    }
    
    for ctx, mask in contexts.items():
        codes = list(REASON_WEIGHTS[ctx].keys())
        weights = list(REASON_WEIGHTS[ctx].values())
        reason[mask] = rng.choice(codes, size=mask.sum(), p=weights)
    
    status = np.select([pending, denied], ["PENDING", "DENIED"], default="PAID").astype(object)
    
    partial = (status == "PAID") & insured.to_numpy() & (rng.random(n) < PARTIAL_RATE)
    status[partial] = "PARTIALLY_PAID"
    
    
    days_since_adj = (as_of - adjudicated).dt.days.to_numpy()
    
    appealed = denied & (rng.random(n) < APPEAL_RATE)          # 0.60
    decided = appealed & (days_since_adj > APPEAL_DECIDE_DAYS)  # 45
    outcome = rng.random(n)
    
    appeal = np.full(n, "NONE", dtype=object)
    appeal[appealed] = "APPEALED"
    appeal[decided & (outcome < 0.55)] = "OVERTURNED"
    appeal[decided & (outcome >= 0.55) & (outcome < 0.80)] = "UPHELD"
    
    overturned = appeal == "OVERTURNED"
    upheld = appeal == "UPHELD"
    status[overturned] = "PAID"
    
    expected = df["expected_insurance"].to_numpy()
    frac = rng.uniform(0.5, 0.9, n)
    paid = np.select(
        [status == "PAID", status == "PARTIALLY_PAID"],
        [expected, expected * frac],
        default=0.0,
    )
    df["insurance_paid"] = np.round(paid, 2)
    gap = np.round(expected - df["insurance_paid"].to_numpy(), 2)
    df["outstanding_amount"] = np.where(upheld, 0.0, gap)
    
    pay_lag = np.where(overturned, rng.integers(30, 61, n), rng.integers(1, 8, n))
    paid_date = (adjudicated + days(pay_lag)).clip(upper=as_of)
    has_payment = np.isin(status, ["PAID", "PARTIALLY_PAID"])
    
        
    submitted = submitted.where(submitted <= as_of)
    adjudicated = adjudicated.where(~pending)
    paid_date = paid_date.where(has_payment)
    
    df["submitted_date"] = to_date_or_none(submitted)
    df["adjudicated_date"] = to_date_or_none(adjudicated)
    df["paid_date"] = to_date_or_none(paid_date)
    df["claim_status"] = status
    df["denial_reason_code"] = reason
    df["appeal_status"] = appeal

    cols = ["claim_id", "patient_id", "provider_id", "payer_id", "secondary_payer_id",
            "service_date", "total_charge", "expected_insurance", "insurance_paid",
            "patient_responsibility", "submitted_date", "adjudicated_date", "paid_date",
            "claim_status", "denial_reason_code", "appeal_status", "outstanding_amount"]
    return df[cols]



def to_date_or_none(s):
    return [d.date() if pd.notna(d) else None for d in s]



def check(sim):
    status = sim["claim_status"]

    sub = pd.to_datetime(sim["submitted_date"])
    adj = pd.to_datetime(sim["adjudicated_date"])
    pay = pd.to_datetime(sim["paid_date"])
    svc = pd.to_datetime(sim["service_date"])

    rules = {
        "denied claims without a reason": (status == "DENIED") & sim["denial_reason_code"].isna(),
        "paid claims without a paid date": (status == "PAID") & sim["paid_date"].isna(),
        "pending claims with an adjudication date": (status == "PENDING") & sim["adjudicated_date"].notna(),
        "negative outstanding amounts": sim["outstanding_amount"] < 0,
        "insurance paid more than expected": sim["insurance_paid"] > sim["expected_insurance"] + 0.01,
        "dates out of order": (sub < svc) | (adj < sub) | (pay < adj),
    }

    print("Checks:")
    failures = 0 
    for rule, failed in rules.items():
        count = failed.sum()
        failures += count
        result = "ok" if count == 0 else "FAILED"
        print(f"  {rule:<42} {count:>5}  {result}")
    return failures


def summary(sim):
    df = sim.merge(load_payers(), on="payer_id")

    print("\nClaim status:")
    print(sim["claim_status"].value_counts().to_string())

    # only claims where the insurer owed something and has already decided
    decided = df[(df["claim_status"] != "PENDING") & (df["expected_insurance"] > 0)]
    by_payer = (
        decided.groupby("payer_name")
        .agg(claims=("claim_id", "count"),
             denials=("denial_reason_code", lambda s: s.notna().sum()))
    )
    by_payer["denial_rate_%"] = (by_payer["denials"] / by_payer["claims"] * 100).round(1)

    print("\nInitial denial rate by payer:")
    print(by_payer.sort_values("denial_rate_%", ascending=False).to_string())

    print("\nDenial reasons:")
    print(sim["denial_reason_code"].value_counts().to_string())

    print("\nAppeal status:")
    print(sim["appeal_status"].value_counts().to_string())

    print(f"\nTotal outstanding (A/R): ${sim['outstanding_amount'].sum():,.2f}")


if __name__ == "__main__":
    from etl.facts import build_facts

    claims, lines = build_facts()
    sim = simulate(claims)

    print(f"\nSimulated claims: {len(sim):,} rows, {sim.shape[1]} columns\n")
    check(sim)
    summary(sim)