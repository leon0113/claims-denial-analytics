INSERT INTO
    dim_denial_reason (
        reason_code,
        description,
        category,
        is_preventable
    )
VALUES
    (
        'CO-16',
        'Claim lacks information or has billing errors',
        'Documentation',
        TRUE
    ),
    (
        'CO-197',
        'Prior authorization was not obtained',
        'Authorization',
        TRUE
    ),
    (
        'CO-50',
        'Service not deemed medically necessary',
        'Authorization',
        FALSE
    ),
    (
        'CO-29',
        'Filing time limit has expired',
        'Timely Filing',
        TRUE
    ),
    (
        'CO-18',
        'Duplicate claim or service',
        'Duplicate',
        TRUE
    ),
    (
        'CO-27',
        'Service after coverage terminated',
        'Eligibility',
        TRUE
    ),
    (
        'CO-10',
        'Diagnosis inconsistent with procedure',
        'Coding',
        TRUE
    ),
    ('CO-96', 'Non-covered charge', 'Coverage', FALSE);