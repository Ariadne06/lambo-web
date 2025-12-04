-- =============================================
-- BHW General Health Report Functions
-- =============================================

-- =============================================
-- 1. Get All Health Records
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_all_health_records(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    resident_id INT,
    full_name VARCHAR,
    sex VARCHAR,
    age_display VARCHAR,
    household_number VARCHAR,
    sitio_name VARCHAR,
    medical_conditions VARCHAR,
    class_name VARCHAR,
    smoker VARCHAR,
    alcohol_drinker VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    WITH medical_history_lookup AS (
        SELECT 
            1 AS id, 'Hypertension' AS name
        UNION ALL SELECT 2, 'Diabetes'
        UNION ALL SELECT 3, 'Tuberculosis'
        UNION ALL SELECT 4, 'Surgery'
    ),
    male_records AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Male' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(
                COALESCE(
                    (SELECT STRING_AGG(mh.name, ', ' ORDER BY mh.id)
                     FROM medical_history_lookup mh
                     WHERE mh.id = ANY(
                         SELECT jsonb_array_elements_text(
                             COALESCE(ghm.medical_history_ids, '[]'::jsonb)
                         )::INT
                     )),
                    'None'
                ) AS VARCHAR
            ) AS medical_conditions,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghm.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghm.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghm.created_at
        FROM General_Health_Male ghm
        JOIN Family_Member fm ON fm.family_member_id = ghm.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghm.class_id
    ),
    female_records AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Female' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(
                COALESCE(
                    (SELECT STRING_AGG(mh.name, ', ' ORDER BY mh.id)
                     FROM medical_history_lookup mh
                     WHERE mh.id = ANY(
                         SELECT jsonb_array_elements_text(
                             COALESCE(ghf.medical_history_ids, '[]'::jsonb)
                         )::INT
                     )),
                    'None'
                ) AS VARCHAR
            ) AS medical_conditions,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghf.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghf.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghf.created_at
        FROM General_Health_Female ghf
        JOIN Family_Member fm ON fm.family_member_id = ghf.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghf.class_id
    ),
    combined AS (
        SELECT * FROM male_records
        UNION ALL
        SELECT * FROM female_records
    )
    SELECT 
        c.resident_id,
        c.full_name,
        c.sex,
        c.age_display,
        c.household_number,
        c.sitio_name,
        c.medical_conditions,
        c.class_name,
        c.smoker,
        c.alcohol_drinker
    FROM combined c
    WHERE 
        (p_start_date IS NULL OR c.created_at::DATE >= p_start_date)
        AND (p_end_date IS NULL OR c.created_at::DATE <= p_end_date)
    ORDER BY c.full_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 2. Get Hypertension Cases
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_hypertension_cases(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    resident_id INT,
    full_name VARCHAR,
    sex VARCHAR,
    age_display VARCHAR,
    household_number VARCHAR,
    sitio_name VARCHAR,
    class_name VARCHAR,
    smoker VARCHAR,
    alcohol_drinker VARCHAR,
    date_recorded DATE
) AS $$
BEGIN
    RETURN QUERY
    WITH male_hypertension AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Male' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghm.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghm.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghm.created_at::DATE AS date_recorded
        FROM General_Health_Male ghm
        JOIN Family_Member fm ON fm.family_member_id = ghm.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghm.class_id
        WHERE 1 = ANY(
            SELECT jsonb_array_elements_text(COALESCE(ghm.medical_history_ids, '[]'::jsonb))::INT
        )
    ),
    female_hypertension AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Female' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghf.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghf.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghf.created_at::DATE AS date_recorded
        FROM General_Health_Female ghf
        JOIN Family_Member fm ON fm.family_member_id = ghf.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghf.class_id
        WHERE 1 = ANY(
            SELECT jsonb_array_elements_text(COALESCE(ghf.medical_history_ids, '[]'::jsonb))::INT
        )
    ),
    combined AS (
        SELECT * FROM male_hypertension
        UNION ALL
        SELECT * FROM female_hypertension
    )
    SELECT 
        c.resident_id,
        c.full_name,
        c.sex,
        c.age_display,
        c.household_number,
        c.sitio_name,
        c.class_name,
        c.smoker,
        c.alcohol_drinker,
        c.date_recorded
    FROM combined c
    WHERE 
        (p_start_date IS NULL OR c.date_recorded >= p_start_date)
        AND (p_end_date IS NULL OR c.date_recorded <= p_end_date)
    ORDER BY c.full_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 3. Get Diabetes Cases
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_diabetes_cases(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    resident_id INT,
    full_name VARCHAR,
    sex VARCHAR,
    age_display VARCHAR,
    household_number VARCHAR,
    sitio_name VARCHAR,
    class_name VARCHAR,
    smoker VARCHAR,
    alcohol_drinker VARCHAR,
    date_recorded DATE
) AS $$
BEGIN
    RETURN QUERY
    WITH male_diabetes AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Male' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghm.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghm.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghm.created_at::DATE AS date_recorded
        FROM General_Health_Male ghm
        JOIN Family_Member fm ON fm.family_member_id = ghm.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghm.class_id
        WHERE 2 = ANY(
            SELECT jsonb_array_elements_text(COALESCE(ghm.medical_history_ids, '[]'::jsonb))::INT
        )
    ),
    female_diabetes AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Female' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghf.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghf.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghf.created_at::DATE AS date_recorded
        FROM General_Health_Female ghf
        JOIN Family_Member fm ON fm.family_member_id = ghf.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghf.class_id
        WHERE 2 = ANY(
            SELECT jsonb_array_elements_text(COALESCE(ghf.medical_history_ids, '[]'::jsonb))::INT
        )
    ),
    combined AS (
        SELECT * FROM male_diabetes
        UNION ALL
        SELECT * FROM female_diabetes
    )
    SELECT 
        c.resident_id,
        c.full_name,
        c.sex,
        c.age_display,
        c.household_number,
        c.sitio_name,
        c.class_name,
        c.smoker,
        c.alcohol_drinker,
        c.date_recorded
    FROM combined c
    WHERE 
        (p_start_date IS NULL OR c.date_recorded >= p_start_date)
        AND (p_end_date IS NULL OR c.date_recorded <= p_end_date)
    ORDER BY c.full_name;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 4. Get TB Cases
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_tb_cases(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    resident_id INT,
    full_name VARCHAR,
    sex VARCHAR,
    age_display VARCHAR,
    household_number VARCHAR,
    sitio_name VARCHAR,
    class_name VARCHAR,
    smoker VARCHAR,
    alcohol_drinker VARCHAR,
    date_recorded DATE
) AS $$
BEGIN
    RETURN QUERY
    WITH male_tb AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Male' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghm.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghm.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghm.created_at::DATE AS date_recorded
        FROM General_Health_Male ghm
        JOIN Family_Member fm ON fm.family_member_id = ghm.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghm.class_id
        WHERE 3 = ANY(
            SELECT jsonb_array_elements_text(COALESCE(ghm.medical_history_ids, '[]'::jsonb))::INT
        )
    ),
    female_tb AS (
        SELECT 
            r.resident_id,
            CAST(CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix) AS VARCHAR) AS full_name,
            CAST('Female' AS VARCHAR) AS sex,
            CAST(
                CASE 
                    WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob)) >= 1 
                    THEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::TEXT
                    ELSE (EXTRACT(YEAR FROM AGE(CURRENT_DATE, r.dob))::INT * 12 + 
                          EXTRACT(MONTH FROM AGE(CURRENT_DATE, r.dob))::INT)::TEXT || ' months'
                END AS VARCHAR
            ) AS age_display,
            CAST(h.household_number AS VARCHAR) AS household_number,
            CAST(s.sitio_name AS VARCHAR) AS sitio_name,
            CAST(c.class_description AS VARCHAR) AS class_name,
            CAST(CASE WHEN ghf.smoker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS smoker,
            CAST(CASE WHEN ghf.alcohol_drinker THEN 'Yes' ELSE 'No' END AS VARCHAR) AS alcohol_drinker,
            ghf.created_at::DATE AS date_recorded
        FROM General_Health_Female ghf
        JOIN Family_Member fm ON fm.family_member_id = ghf.family_member_id
        JOIN Resident r ON r.resident_id = fm.resident_id
        JOIN Family f ON f.family_id = fm.family_id
        LEFT JOIN Household h ON h.household_id = f.household_id
        LEFT JOIN Address a ON a.address_id = r.address_id
        LEFT JOIN Sitio s ON s.sitio_id = a.sitio_id
        LEFT JOIN Class c ON c.class_id = ghf.class_id
        WHERE 3 = ANY(
            SELECT jsonb_array_elements_text(COALESCE(ghf.medical_history_ids, '[]'::jsonb))::INT
        )
    ),
    combined AS (
        SELECT * FROM male_tb
        UNION ALL
        SELECT * FROM female_tb
    )
    SELECT 
        c.resident_id,
        c.full_name,
        c.sex,
        c.age_display,
        c.household_number,
        c.sitio_name,
        c.class_name,
        c.smoker,
        c.alcohol_drinker,
        c.date_recorded
    FROM combined c
    WHERE 
        (p_start_date IS NULL OR c.date_recorded >= p_start_date)
        AND (p_end_date IS NULL OR c.date_recorded <= p_end_date)
    ORDER BY c.full_name;
END;
$$ LANGUAGE plpgsql;
