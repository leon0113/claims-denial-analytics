import pandas as pd
from sqlalchemy import text
from etl.db import get_engine

# common file path
RAW = "data/raw/"


# !------------------ extract data from csv and transform col names to Postgresql col names-----------
def build_dim_payer():
    df = pd.read_csv(RAW + 'payers.csv', usecols=["Id", "NAME", "OWNERSHIP"])
    df = df.rename(columns={
        "Id": "payer_id",
        "NAME": "payer_name",
        "OWNERSHIP": "ownership"
    })

    return df


def build_dim_organization():
    df = pd.read_csv(RAW+ "organizations.csv", usecols=["Id", "NAME", "CITY", "STATE"])
    df = df.rename(columns={
        "Id": "organization_id",
        "NAME": "org_name",
        "CITY": "city",
        "STATE": "state"
    })

    return df



def build_dim_provider():
    df = pd.read_csv(RAW+ "providers.csv", usecols=["Id", "ORGANIZATION", "NAME", "SPECIALITY"])
    df = df.rename(columns={
        "Id": "provider_id",
        "ORGANIZATION": "organization_id",
        "NAME": "provider_name",
        "SPECIALITY": "speciality"
    })

    df["speciality"] = df["speciality"].fillna("UNKNOWN")

    return df



def build_dim_patient():
    df = pd.read_csv(RAW+ "patients.csv", usecols=["Id", "BIRTHDATE", "GENDER", "CITY", "STATE"])
    df = df.rename(columns={
        "Id": "patient_id",
        "BIRTHDATE": "birth_date",
        "GENDER": "gender",
        "CITY": "city",
        "STATE": "state"
    })

    df["birth_date"] = pd.to_datetime(df["birth_date"]).dt.date # converting string to type datetime

    return df


# ! ------------------------------ validate PK and FK consistency

def validate(dims):
    orgs_id = set(dims["dim_organization"]["organization_id"])

    missing_org_id = ~dims["dim_organization"]["organization_id"].isin(orgs_id)

    if missing_org_id.any():
        raise ValueError(f"providers missing organization_ids: {missing_org_id}")

    for name, df in dims.items():
        pk = df.columns[0]

        if df[pk].duplicated().any():
            raise ValueError(f"{name} as duplicate pks: {pk}")

    print("Validation done!")


# ! ---------------------- load transformed data to remote postgres db --------------------
def load_dimension_tables(engine):
    dims = {
        "dim_payer": build_dim_payer(),
        "dim_organization": build_dim_organization(),
        "dim_provider": build_dim_provider(),
        "dim_patient": build_dim_patient(),
    }

    validate(dims)

    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE dim_payer, dim_organization, dim_provider, dim_patient CASCADE"
        ))

        for name, df in dims.items():
            df.to_sql(name, conn, if_exists="append", index=False, method="multi", chunksize=1000)

            print(f"{name} created, size: {len(df)}")



if __name__ == "__main__":
    load_dimension_tables(get_engine())