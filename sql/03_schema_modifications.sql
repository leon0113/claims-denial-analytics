ALTER TABLE fact_claim_lines
RENAME COLUMN transferred_to_patient TO patient_paid;

ALTER TABLE fact_claims
ADD COLUMN expected_insurance NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (expected_insurance >= 0);


