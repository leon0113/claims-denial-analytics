--! Insights 1: an overview of fact_claim table
SELECT
    COUNT(*) AS "total_claims",
    SUM(total_charge) As "total_charges",
    SUM(expected_insurance) As "total_expected_from_insurances",
    SUM(insurance_paid) AS "total_paid_by_insurances",
    SUM(patient_responsibility) AS "total_paid_by_patient",
    SUM(outstanding_amount) AS "total_outstanding_amount",
    SUM(
        expected_insurance - insurance_paid - outstanding_amount
    ) AS "total_write_off"
from
    fact_claims;



--! Insights 2
WITH
    totals AS (
        SELECT
            COUNT(*) AS "total_claims",
            SUM(total_charge) As "total_charges",
            SUM(expected_insurance) As "total_expected_from_insurances",
            SUM(insurance_paid) AS "total_paid_by_insurances",
            SUM(patient_responsibility) AS "total_paid_by_patient",
            SUM(outstanding_amount) AS "total_outstanding_amount",
            SUM(
                expected_insurance - insurance_paid - outstanding_amount
            ) AS "total_write_off"
        from
            fact_claims
    )
SELECT
    ROUND(
        (
            (total_paid_by_insurances + total_paid_by_patient) / total_charges
        ) * 100.0,
        2
    ) AS "gross_collection_rate",
    ROUND(
        (
            total_paid_by_insurances / total_expected_from_insurances
        ) * 100.0,
        2
    ) AS "gross_collected_from_insurance",
    ROUND(
        (total_write_off / total_expected_from_insurances) * 100.0,
        2
    ) AS "gross_write_off_rate",
    ROUND(
        (total_paid_by_patient / total_charges) * 100.0,
        2
    ) AS "gross_collection_rate_from_patients"
FROM
    totals;


--! Insights 3
SELECT
    COUNT(*) AS "total_claims",
    COUNT(*) FILTER (
        WHERE
            denial_reason_code IS NOT NULL
    ) AS "total_initial_denials",
    COUNT(*) FILTER (
        WHERE
            denial_reason_code IS NULL
            AND claim_status = 'PAID'
    ) AS "total_clean_claims",
    ROUND(
        (
            COUNT(*) FILTER (
                WHERE
                    denial_reason_code IS NOT NULL
            ) * 100.0
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS "initial_denials_rate",
    ROUND(
        (
            COUNT(*) FILTER (
                WHERE
                    denial_reason_code IS NULL
                    AND claim_status = 'PAID'
            ) * 100.0
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS "clean_claims_rate"
FROM
    fact_claims
WHERE
    claim_status <> 'PENDING'
    AND expected_insurance > 0;




--! Insights 4
SELECT
    COUNT(*) FILTER (
        WHERE
            appeal_status <> 'NONE'
    ) AS "total_appeals",
    COUNT(*) FILTER (
        WHERE
            appeal_status = 'APPEALED'
    ) AS "total_appeals_ongoing",
    COUNT(*) FILTER (
        WHERE
            appeal_status = 'OVERTURNED'
    ) AS "total_appeals_won",
    COUNT(*) FILTER (
        WHERE
            appeal_status = 'UPHELD'
    ) AS "total_appeals_lost",
    ROUND(
        COUNT(*) FILTER (
            WHERE
                appeal_status = 'OVERTURNED'
        ) * 100.0 / COUNT(*) FILTER (
            WHERE
                appeal_status IN ('OVERTURNED', 'UPHELD')
        ),
        2
    ) AS "appeal_win_rate"
FROM
    fact_claims;



--! Insights 5
SELECT
    ROUND(AVG(submitted_date - service_date), 2) AS "avg_days_to_submit",
    ROUND(AVG(adjudicated_date - submitted_date), 2) AS "avg_days_to_adjudicate",
    ROUND(AVG(paid_date - service_date), 2) AS "avg_days_to_payment"
FROM
    fact_claims
WHERE
    claim_status = 'PAID'
    AND expected_insurance > 0;