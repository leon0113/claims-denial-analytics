import numpy as np
import pandas as pd

# common file path
RAW = "data/raw/"
START_DATE = pd.Timestamp("2024-01-01", tz="UTC")


#! -------------------------------- extract data from csv's ------------------------------------------

def read_claims():
    cols = ["Id", "PATIENTID", "PROVIDERID", "PRIMARYPATIENTINSURANCEID", "SECONDARYPATIENTINSURANCEID", "SERVICEDATE"]

    df_claims = pd.read_csv(RAW + "claims.csv", usecols=cols)
    df_claims["SERVICEDATE"] = pd.to_datetime(df_claims["SERVICEDATE"])

    df_claims = df_claims[df_claims["SERVICEDATE"] >= START_DATE] # data from 2024 to now only
    return df_claims


def read_transactions(claim_ids):
    cols = ["ID", "CLAIMID", "CHARGEID", "TYPE", "AMOUNT", "PAYMENTS", "TRANSFERTYPE", "PROCEDURECODE", "METHOD"]

    t = pd.read_csv(RAW + "claims_transactions.csv", usecols=cols, dtype={
        "TRANSFERTYPE": str,
        "PROCEDURECODE": str
    })
    # need only those which claim id matches with our claims(2024+)
    t = t[t["CLAIMID"].isin(claim_ids)]
    return t


def get_no_insurance_id():
    p = pd.read_csv(RAW + "payers.csv", usecols=["Id", "NAME"])

    return p.loc[p["NAME"] == "NO_INSURANCE", "Id"].iloc[0]


# !---------------------------- transform data for POstgres db ---------------------------

def build_lines(t):
    # rearrange rows in-order of a claims
    t = t.sort_values(["CLAIMID", "CHARGEID"]).copy()
    is_charge = t["TYPE"] == "CHARGE"

    # find rows of one charge
    t["line_id"] = t["ID"].where(is_charge)
    t["line_id"] = t.groupby("CLAIMID")["line_id"].ffill()

    # find the party who will pay
    set_party = t["TYPE"].isin(["CHARGE", "TRANSFERIN"])
    t["party"] = t["TRANSFERTYPE"].where(set_party)

    # fill party of full charge rows
    t["party"] = t.groupby("line_id")["party"].ffill()

    # who paid each charge
    pay = t[t["TYPE"] == "PAYMENT"].copy()
    by_patient = (pay["METHOD"] == "COPAY") | (pay["party"] == "p")

    pay["patient_paid"] = pay["PAYMENTS"].where(by_patient, 0)
    pay["insurance_paid"] = pay["PAYMENTS"].where(~by_patient, 0)

    # sum of paid amount of each charge
    paid = pay.groupby("line_id", as_index=False)[["patient_paid", "insurance_paid"]].sum()

    # merge paid table with charges
    charges = t[is_charge][["line_id", "CLAIMID", "CHARGEID", "PROCEDURECODE", "AMOUNT"]]
    lines = charges.merge(paid, on="line_id", how="left")

    lines[["patient_paid", "insurance_paid"]] = lines[["patient_paid", "insurance_paid"]].fillna(0)

    lines = lines.rename(columns={
        "CLAIMID": "claim_id",
        "CHARGEID": "charge_id",
        "PROCEDURECODE": "procedure_code",
        "AMOUNT": "charge_amount"
    })

    cols = ["line_id", "claim_id", "charge_id", "procedure_code",
            "charge_amount", "insurance_paid", "patient_paid"]

    lines = lines[cols]

    money_cols = ["charge_amount", "insurance_paid", "patient_paid"]
    lines[money_cols] = lines[money_cols].round(2)

    return lines, t



def build_claims(c, lines, no_insurance_id):
    totals = (
        lines.groupby("claim_id", as_index=False).agg(total_charge=("charge_amount", "sum"),
                                                      insurance_paid=("insurance_paid","sum"),
                                                      patient_responsibility=("patient_paid","sum")
                                                      )
    )

    claims = c.rename(columns={
        "Id": "claim_id",
        "PATIENTID": "patient_id",
        "PROVIDERID": "provider_id",
        "PRIMARYPATIENTINSURANCEID": "payer_id",
        "SECONDARYPATIENTINSURANCEID": "secondary_payer_id",
        "SERVICEDATE": "service_date"
    })

    claims["payer_id"] = claims["payer_id"].fillna(no_insurance_id)
    claims["service_date"] = claims["service_date"].dt.date

    claims = claims.merge(totals, on="claim_id", how="left")

    money_cols = ["total_charge", "insurance_paid", "patient_responsibility"]

    claims[money_cols] = claims[money_cols].round(2)
    return claims

# !-------------------------------- validate and check data ---------------------------------

def validate(claims, lines, t):
    payer_ids = set(pd.read_csv(RAW + "payers.csv", usecols=["Id"])["Id"])

    no_lines = claims["total_charge"].isna().sum()
    print(f"claims with no charge: {no_lines}")

    wrong_secondary_payers = (claims["secondary_payer_id"].notna() & ~claims["secondary_payer_id"].isin(payer_ids)).sum()
    print(f"unknown secondary insurances: {wrong_secondary_payers}")

    money_cols = ["charge_amount", "insurance_paid", "patient_paid"]

    print(f"minus moeny lines: {(lines[money_cols] < 0).any(axis=1).sum()}")
    print(f"line_id duplicated {lines['line_id'].duplicated().sum()}")

    print(f"None line id's: {t['line_id'].isna().sum()}")
    



def reconcile(t, lines):
    # get the total paid for each (claim and charge)
    lines = lines.copy()

    lines["gap"] = (lines["charge_amount"] - lines["insurance_paid"] - lines["patient_paid"]).round(2)

    matched = (lines["gap"].abs() <= 0.01).mean() * 100 # should be ~100%

    print(f"line non-gap : {matched.round(2)}%")
    print(f"total gap : {lines['gap'].sum()}")

    party_p = t[(t["TYPE"] == "PAYMENT") & (t["party"] == "p")]["PAYMENTS"].sum()
    copay = t[(t["TYPE"] == "PAYMENT") & (t["METHOD"] == "COPAY")]["PAYMENTS"].sum()

    print(f"patient pay: {party_p}")
    print(f"copay method: {copay}")
    


def build_facts():
    c = read_claims()
    t = read_transactions(c["Id"])

    lines, t = build_lines(t)
    claims = build_claims(c, lines, get_no_insurance_id())

    validate(claims, lines, t)
    reconcile(t, lines)

    return claims, lines


if __name__ == "__main__":
    claims, lines = build_facts()

    print("claim shape", claims.shape)


    print("lines shape", lines.shape)

    print("total charge", claims["total_charge"].sum())
    print("insurance paid", claims["insurance_paid"].sum())
    print("patient paid", claims["patient_responsibility"].sum().round(2))