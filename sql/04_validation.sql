WITH line_totals AS (
    SELECT claim_id,
           SUM(charge_amount)  AS charge,
           SUM(insurance_paid) AS insurance,
           SUM(patient_paid)   AS patient
    FROM fact_claim_lines
    GROUP BY claim_id
)

SELECT 'claims without lines' AS check_name, COUNT(*) AS failures
FROM fact_claims c
LEFT JOIN line_totals lt ON lt.claim_id = c.claim_id
WHERE lt.claim_id IS NULL

UNION ALL
SELECT 'claim total does not match its lines', COUNT(*)
FROM fact_claims c
JOIN line_totals lt ON lt.claim_id = c.claim_id
WHERE ABS(c.total_charge - lt.charge) > 0.01

UNION ALL
SELECT 'expected insurance does not match lines', COUNT(*)
FROM fact_claims c
JOIN line_totals lt ON lt.claim_id = c.claim_id
WHERE ABS(c.expected_insurance - lt.insurance) > 0.01

UNION ALL
SELECT 'patient responsibility does not match lines', COUNT(*)
FROM fact_claims c
JOIN line_totals lt ON lt.claim_id = c.claim_id
WHERE ABS(c.patient_responsibility - lt.patient) > 0.01

UNION ALL
SELECT 'line split does not add up to the charge', COUNT(*)
FROM fact_claim_lines
WHERE ABS(insurance_paid + patient_paid - charge_amount) > 0.01

UNION ALL
SELECT 'paid + outstanding does not equal expected', COUNT(*)
FROM fact_claims
WHERE appeal_status <> 'UPHELD'
  AND ABS(insurance_paid + outstanding_amount - expected_insurance) > 0.01

UNION ALL
SELECT 'denial reason on a claim never denied', COUNT(*)
FROM fact_claims
WHERE denial_reason_code IS NOT NULL
  AND claim_status <> 'DENIED'
  AND appeal_status <> 'OVERTURNED'

UNION ALL
SELECT 'self-pay claims that were denied', COUNT(*)
FROM fact_claims c
JOIN dim_payer p ON p.payer_id = c.payer_id
WHERE p.ownership = 'NO_INSURANCE'
  AND c.denial_reason_code IS NOT NULL

UNION ALL
SELECT 'pending claims with a decision or payment', COUNT(*)
FROM fact_claims
WHERE claim_status = 'PENDING'
  AND (adjudicated_date IS NOT NULL OR paid_date IS NOT NULL)

UNION ALL
SELECT 'dates out of order', COUNT(*)
FROM fact_claims
WHERE submitted_date < service_date
   OR adjudicated_date < submitted_date
   OR paid_date < adjudicated_date