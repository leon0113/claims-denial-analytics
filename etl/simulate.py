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
    "GOVERMENT": (20, 46),
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

