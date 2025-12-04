-- =============================================
-- BHW Maternal and Child Health Report Functions
-- =============================================

-- =============================================
-- 1. Get All Maternal Records
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_all_maternal_records(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    maternal_health_id INT,
    resident_id INT,
    mother_full_name VARCHAR,
    record_status VARCHAR,
    lmp DATE,
    edd DATE,
    date_created TIMESTAMPTZ,
    household_number VARCHAR,
    sitio_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mhr.maternal_health_id,
        mhr.maternal_id AS resident_id,
        CAST(
            CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR
        ) AS mother_full_name,
        CAST(rs.record_name AS VARCHAR) AS record_status,
        oh.last_menstrual_period AS lmp,
        oh.expected_date_of_delivery AS edd,
        mhr.date_created,
        CAST(h.household_number AS VARCHAR),
        CAST(s.sitio_name AS VARCHAR)
    FROM 
        maternal_health_record mhr
    JOIN 
        resident r ON r.resident_id = mhr.maternal_id
    JOIN 
        record_status rs ON rs.record_status_id = mhr.record_status_id
    LEFT JOIN 
        obstetrical_history oh ON oh.maternal_health_id = mhr.maternal_health_id
    LEFT JOIN 
        family_member fm ON fm.resident_id = r.resident_id
    LEFT JOIN 
        family f ON f.family_id = fm.family_id
    LEFT JOIN 
        household h ON h.household_id = f.household_id
    LEFT JOIN 
        address a ON a.address_id = h.address_id
    LEFT JOIN 
        sitio s ON s.sitio_id = a.sitio_id
    WHERE 
        (p_start_date IS NULL OR mhr.date_created::DATE >= p_start_date)
        AND (p_end_date IS NULL OR mhr.date_created::DATE <= p_end_date)
    ORDER BY 
        mhr.date_created DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 2. Get Maternal Checkup Summary
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_maternal_checkup_summary(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    maternal_health_id INT,
    mother_full_name VARCHAR,
    total_checkups BIGINT,
    last_checkup_date DATE,
    record_status VARCHAR,
    edd DATE,
    household_number VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        mhr.maternal_health_id,
        CAST(
            CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR
        ) AS mother_full_name,
        (
            SELECT COUNT(*)::BIGINT
            FROM view_specific_maternal_all_checkup_record(mhr.maternal_health_id)
        ) AS total_checkups,
        (
            SELECT MAX(date_of_checkup)::DATE
            FROM view_specific_maternal_all_checkup_record(mhr.maternal_health_id)
        ) AS last_checkup_date,
        CAST(rs.record_name AS VARCHAR) AS record_status,
        oh.expected_date_of_delivery AS edd,
        CAST(h.household_number AS VARCHAR)
    FROM 
        maternal_health_record mhr
    JOIN 
        resident r ON r.resident_id = mhr.maternal_id
    JOIN 
        record_status rs ON rs.record_status_id = mhr.record_status_id
    LEFT JOIN 
        obstetrical_history oh ON oh.maternal_health_id = mhr.maternal_health_id
    LEFT JOIN 
        family_member fm ON fm.resident_id = r.resident_id
    LEFT JOIN 
        family f ON f.family_id = fm.family_id
    LEFT JOIN 
        household h ON h.household_id = f.household_id
    WHERE 
        (p_start_date IS NULL OR mhr.date_created::DATE >= p_start_date)
        AND (p_end_date IS NULL OR mhr.date_created::DATE <= p_end_date)
    ORDER BY 
        mhr.maternal_health_id DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 3. Get Maternal Immunization Summary
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_maternal_immunization_summary(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    maternal_health_id INT,
    mother_full_name VARCHAR,
    tt_doses_received BIGINT,
    last_immunization_date DATE,
    record_status VARCHAR,
    household_number VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH immunization_summary AS (
        SELECT 
            mhr.maternal_health_id,
            CASE WHEN imm.first_dose = 'Y' THEN 1 ELSE 0 END +
            CASE WHEN imm.second_dose = 'Y' THEN 1 ELSE 0 END +
            CASE WHEN imm.third_dose = 'Y' THEN 1 ELSE 0 END +
            CASE WHEN imm.fourth_dose = 'Y' THEN 1 ELSE 0 END +
            CASE WHEN imm.fifth_dose = 'Y' THEN 1 ELSE 0 END AS doses_count,
            GREATEST(
                imm.first_dose_date,
                imm.second_dose_date,
                imm.third_dose_date,
                imm.fourth_dose_date,
                imm.fifth_dose_date
            )::DATE AS last_dose_date
        FROM 
            maternal_health_record mhr
        LEFT JOIN LATERAL 
            view_specific_maternal_immunization_status_track(mhr.maternal_health_id) imm ON true
    )
    SELECT 
        mhr.maternal_health_id,
        CAST(
            CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR
        ) AS mother_full_name,
        COALESCE(imm_sum.doses_count, 0)::BIGINT AS tt_doses_received,
        imm_sum.last_dose_date AS last_immunization_date,
        CAST(rs.record_name AS VARCHAR) AS record_status,
        CAST(h.household_number AS VARCHAR)
    FROM 
        maternal_health_record mhr
    JOIN 
        resident r ON r.resident_id = mhr.maternal_id
    JOIN 
        record_status rs ON rs.record_status_id = mhr.record_status_id
    LEFT JOIN 
        immunization_summary imm_sum ON imm_sum.maternal_health_id = mhr.maternal_health_id
    LEFT JOIN 
        family_member fm ON fm.resident_id = r.resident_id
    LEFT JOIN 
        family f ON f.family_id = fm.family_id
    LEFT JOIN 
        household h ON h.household_id = f.household_id
    WHERE 
        (p_start_date IS NULL OR mhr.date_created::DATE >= p_start_date)
        AND (p_end_date IS NULL OR mhr.date_created::DATE <= p_end_date)
    ORDER BY 
        mhr.maternal_health_id DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 4. Get All Children Records
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_all_children_records(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    child_health_id INT,
    child_resident_id INT,
    child_full_name VARCHAR,
    sex VARCHAR,
    dob DATE,
    age_display VARCHAR,
    mother_full_name VARCHAR,
    household_number VARCHAR,
    sitio_name VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (chr.child_health_id)
        chr.child_health_id,
        r.resident_id AS child_resident_id,
        CAST(
            CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR
        ) AS child_full_name,
        CAST(r.sex AS VARCHAR),
        r.dob,
        CAST(
            CASE 
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) < 1 
                THEN CONCAT(EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob)), ' months')
                ELSE CONCAT(EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)), ' years')
            END AS VARCHAR
        ) AS age_display,
        CAST(
            CONCAT_WS(' ', mother.first_name, mother.middle_name, mother.last_name, mother.suffix) AS VARCHAR
        ) AS mother_full_name,
        CAST(h.household_number AS VARCHAR),
        CAST(s.sitio_name AS VARCHAR)
    FROM 
        child_health_record chr
    JOIN 
        resident r ON r.resident_id = chr.child_id
    LEFT JOIN 
        relation rel ON rel.target_resident_id = r.resident_id 
            AND rel.relationship_id = (SELECT relationship_id FROM relationship WHERE relationship_name = 'Child')
    LEFT JOIN 
        resident mother ON mother.resident_id = rel.origin_resident_id AND mother.sex = 'Female'
    LEFT JOIN 
        family_member fm ON fm.resident_id = r.resident_id
    LEFT JOIN 
        family f ON f.family_id = fm.family_id
    LEFT JOIN 
        household h ON h.household_id = f.household_id
    LEFT JOIN 
        address a ON a.address_id = h.address_id
    LEFT JOIN 
        sitio s ON s.sitio_id = a.sitio_id
    WHERE 
        (p_start_date IS NULL OR r.dob >= p_start_date)
        AND (p_end_date IS NULL OR r.dob <= p_end_date)
    ORDER BY 
        chr.child_health_id, r.dob DESC, mother.first_name NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 5. Get Child Immunization Summary
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_child_immunization_summary(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    child_health_id INT,
    child_full_name VARCHAR,
    sex VARCHAR,
    dob DATE,
    age_display VARCHAR,
    total_vaccines_completed BIGINT,
    last_vaccine_date DATE,
    mother_full_name VARCHAR,
    household_number VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT ON (chr.child_health_id)
        chr.child_health_id,
        CAST(
            CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR
        ) AS child_full_name,
        CAST(r.sex AS VARCHAR),
        r.dob,
        CAST(
            CASE 
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) < 1 
                THEN CONCAT(EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob)), ' months')
                ELSE CONCAT(EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)), ' years')
            END AS VARCHAR
        ) AS age_display,
        (
            SELECT COUNT(*)::BIGINT
            FROM view_specific_child_immunization_record(chr.child_health_id)
            WHERE status = 'Completed'
        ) AS total_vaccines,
        (
            SELECT MAX(last_administered)::DATE
            FROM view_specific_child_immunization_record(chr.child_health_id)
            WHERE status = 'Completed'
        ) AS last_vaccine_date,
        CAST(
            CONCAT_WS(' ', mother.first_name, mother.middle_name, mother.last_name, mother.suffix) AS VARCHAR
        ) AS mother_full_name,
        CAST(h.household_number AS VARCHAR)
    FROM 
        child_health_record chr
    JOIN 
        resident r ON r.resident_id = chr.child_id
    LEFT JOIN 
        relation rel ON rel.target_resident_id = r.resident_id 
            AND rel.relationship_id = (SELECT relationship_id FROM relationship WHERE relationship_name = 'Child')
    LEFT JOIN 
        resident mother ON mother.resident_id = rel.origin_resident_id AND mother.sex = 'Female'
    LEFT JOIN 
        family_member fm ON fm.resident_id = r.resident_id
    LEFT JOIN 
        family f ON f.family_id = fm.family_id
    LEFT JOIN 
        household h ON h.household_id = f.household_id
    WHERE 
        (p_start_date IS NULL OR r.dob >= p_start_date)
        AND (p_end_date IS NULL OR r.dob <= p_end_date)
    ORDER BY 
        chr.child_health_id DESC, mother.first_name NULLS LAST;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 6. Get Child Vaccination Schedule
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_child_vaccination_schedule(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    child_health_id INT,
    child_full_name VARCHAR,
    age_display VARCHAR,
    vaccine_name VARCHAR,
    next_dose VARCHAR,
    scheduled_date DATE,
    household_number VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        sch.child_health_id,
        CAST(sch.child_full_name AS VARCHAR),
        CAST(
            CASE 
                WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) < 1 
                THEN CONCAT(EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob)), ' months')
                ELSE CONCAT(EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)), ' years')
            END AS VARCHAR
        ) AS age_display,
        CAST(sch.vaccine_name AS VARCHAR),
        CAST(sch.next_dose_name AS VARCHAR) AS next_dose,
        sch.scheduled_date::DATE,
        CAST(h.household_number AS VARCHAR)
    FROM 
        view_all_child_immunization_schedule(NULL, NULL, 0) sch
    JOIN
        child_health_record chr ON chr.child_health_id = sch.child_health_id
    JOIN 
        resident r ON r.resident_id = chr.child_id
    LEFT JOIN 
        family_member fm ON fm.resident_id = r.resident_id
    LEFT JOIN 
        family f ON f.family_id = fm.family_id
    LEFT JOIN 
        household h ON h.household_id = f.household_id
    WHERE 
        (p_start_date IS NULL OR sch.scheduled_date::DATE >= p_start_date)
        AND (p_end_date IS NULL OR sch.scheduled_date::DATE <= p_end_date)
    ORDER BY 
        sch.scheduled_date ASC, sch.child_health_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- Test Queries (Comment out after verification)
-- =============================================
-- SELECT * FROM bhw_get_all_maternal_records(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_maternal_checkup_summary(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_maternal_immunization_summary(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_all_children_records(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_child_immunization_summary(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_child_vaccination_schedule(NULL, NULL) LIMIT 10;
