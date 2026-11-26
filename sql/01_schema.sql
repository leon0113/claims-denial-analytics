DROP TABLE IF EXISTS fact_claim_lines CASCADE;

DROP TABLE IF EXISTS fact_claims CASCADE;

DROP TABLE IF EXISTS dim_denial_reason CASCADE;

DROP TABLE IF EXISTS dim_provider CASCADE;

DROP TABLE IF EXISTS dim_organization CASCADE;

DROP TABLE IF EXISTS dim_patient CASCADE;

DROP TABLE IF EXISTS dim_payer CASCADE;

CREATE TABLE
    dim_payer (
        payer_id TEXT PRIMARY KEY,
        payer_name TEXT NOT NULL,
        ownership TEXT NOT NULL CHECK (
            ownership IN ('GOVERNMENT', 'PRIVATE', 'NO_INSURANCE')
        )
    );

CREATE TABLE
    dim_patient (
        patient_id TEXT PRIMARY KEY,
        birth_date DATE NOT NULL,
        gender TEXT NOT NULL,
        city TEXT,
        state TEXT
    );

CREATE TABLE
    dim_organization (
        organization_id TEXT PRIMARY KEY,
        org_name TEXT NOT NULL,
        city TEXT,
        state TEXT
    );

CREATE TABLE
    dim_provider (
        provider_id TEXT PRIMARY KEY,
        organization_id TEXT NOT NULL REFERENCES dim_organization (organization_id),
        provider_name TEXT NOT NULL,
        speciality TEXT NOT NULL
    );

CREATE TABLE
    dim_denial_reason (
        reason_code TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        category TEXT NOT NULL,
        is_preventable BOOLEAN NOT NULL
    );

CREATE TABLE
    fact_claims (
        claim_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL REFERENCES dim_patient (patient_id),
        provider_id TEXT NOT NULL REFERENCES dim_provider (provider_id),
        payer_id TEXT NOT NULL REFERENCES dim_payer (payer_id),
        secondary_payer_id TEXT REFERENCES dim_payer (payer_id),
        service_date DATE NOT NULL,
        total_charge NUMERIC(12, 2) NOT NULL CHECK (total_charge >= 0),
        insurance_paid NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (insurance_paid >= 0),
        patient_responsibility NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (patient_responsibility >= 0),
        submitted_date DATE,
        adjudicated_date DATE,
        paid_date DATE,
        claim_status TEXT NOT NULL CHECK (
            claim_status IN ('PAID', 'PARTIALLY_PAID', 'DENIED', 'PENDING')
        ),
        denial_reason_code TEXT REFERENCES dim_denial_reason (reason_code),
        appeal_status TEXT NOT NULL DEFAULT 'NONE' CHECK (
            appeal_status IN ('NONE', 'APPEALED', 'OVERTURNED', 'UPHELD')
        ),
        outstanding_amount NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (outstanding_amount >= 0)
    );

CREATE TABLE
    fact_claim_lines (
        line_id TEXT PRIMARY KEY,
        claim_id TEXT NOT NULL REFERENCES fact_claims (claim_id),
        charge_id INTEGER NOT NULL,
        procedure_code TEXT NOT NULL,
        charge_amount NUMERIC(12, 2) NOT NULL CHECK (charge_amount >= 0),
        insurance_paid NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (insurance_paid >= 0),
        patient_paid NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (patient_paid >= 0),
        UNIQUE (claim_id, charge_id)
    );