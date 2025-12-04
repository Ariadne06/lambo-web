-- =============================================
-- BHW Household Report Stored Procedures
-- =============================================
-- These procedures support the household report PDF generation
-- with filters for all/active/visited households

-- =============================================
-- 1. Get All Households Report
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_all_households_report(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    household_id INT,
    household_number VARCHAR,
    household_head_name VARCHAR,
    address VARCHAR,
    sitio_name VARCHAR,
    total_families BIGINT,
    total_members BIGINT,
    last_visit_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.household_id,
        h.household_number,
        CAST(
            CASE 
                WHEN r.first_name IS NOT NULL THEN 
                    CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix)
                ELSE 
                    'N/A'
            END AS VARCHAR
        ) AS household_head_name,
        CAST(
            CONCAT_WS(', ',
                NULLIF(a.street, ''),
                NULLIF(s.sitio_name, ''),
                NULLIF(a.barangay, ''),
                NULLIF(a.city_municipality, '')
            ) AS VARCHAR
        ) AS address,
        CAST(COALESCE(s.sitio_name, 'N/A') AS VARCHAR) AS sitio_name,
        COALESCE(COUNT(DISTINCT f.family_id), 0) AS total_families,
        COALESCE(COUNT(DISTINCT fm.resident_id), 0) AS total_members,
        MAX(f.updated_at)::DATE AS last_visit_date
    FROM 
        household h
    LEFT JOIN 
        resident r ON h.household_head_id = r.resident_id
    LEFT JOIN 
        address a ON h.address_id = a.address_id
    LEFT JOIN 
        sitio s ON a.sitio_id = s.sitio_id
    LEFT JOIN 
        family f ON h.household_id = f.household_id
    LEFT JOIN 
        family_member fm ON f.family_id = fm.family_id
    WHERE 
        1=1
        AND (p_start_date IS NULL OR h.created_at::DATE >= p_start_date)
        AND (p_end_date IS NULL OR h.created_at::DATE <= p_end_date)
    GROUP BY 
        h.household_id,
        h.household_number,
        r.first_name,
        r.middle_name,
        r.last_name,
        r.suffix,
        a.street,
        a.barangay,
        a.city_municipality,
        s.sitio_name
    ORDER BY 
        h.household_number;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 2. Get Active Households Report
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_active_households_report(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    household_id INT,
    household_number VARCHAR,
    household_head_name VARCHAR,
    address VARCHAR,
    sitio_name VARCHAR,
    total_families BIGINT,
    total_members BIGINT,
    last_visit_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.household_id,
        h.household_number,
        CAST(
            CASE 
                WHEN r.first_name IS NOT NULL THEN 
                    CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix)
                ELSE 
                    'N/A'
            END AS VARCHAR
        ) AS household_head_name,
        CAST(
            CONCAT_WS(', ',
                NULLIF(a.street, ''),
                NULLIF(s.sitio_name, ''),
                NULLIF(a.barangay, ''),
                NULLIF(a.city_municipality, '')
            ) AS VARCHAR
        ) AS address,
        CAST(COALESCE(s.sitio_name, 'N/A') AS VARCHAR) AS sitio_name,
        COALESCE(COUNT(DISTINCT f.family_id), 0) AS total_families,
        COALESCE(COUNT(DISTINCT fm.resident_id), 0) AS total_members,
        MAX(f.updated_at)::DATE AS last_visit_date
    FROM 
        household h
    LEFT JOIN 
        resident r ON h.household_head_id = r.resident_id
    LEFT JOIN 
        address a ON h.address_id = a.address_id
    LEFT JOIN 
        sitio s ON a.sitio_id = s.sitio_id
    LEFT JOIN 
        family f ON h.household_id = f.household_id
    LEFT JOIN 
        family_member fm ON f.family_id = fm.family_id
    WHERE 
        h.is_active = TRUE
        AND (p_start_date IS NULL OR h.created_at::DATE >= p_start_date)
        AND (p_end_date IS NULL OR h.created_at::DATE <= p_end_date)
    GROUP BY 
        h.household_id,
        h.household_number,
        r.first_name,
        r.middle_name,
        r.last_name,
        r.suffix,
        a.street,
        a.barangay,
        a.city_municipality,
        s.sitio_name
    ORDER BY 
        h.household_number;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- 3. Get Recently Visited Households Report
-- =============================================
CREATE OR REPLACE FUNCTION bhw_get_visited_households_report(
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE (
    household_id INT,
    household_number VARCHAR,
    household_head_name VARCHAR,
    address VARCHAR,
    sitio_name VARCHAR,
    total_families BIGINT,
    total_members BIGINT,
    last_visit_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        h.household_id,
        h.household_number,
        CAST(
            CASE 
                WHEN r.first_name IS NOT NULL THEN 
                    CONCAT_WS(' ', r.first_name, r.middle_name, r.last_name, r.suffix)
                ELSE 
                    'N/A'
            END AS VARCHAR
        ) AS household_head_name,
        CAST(
            CONCAT_WS(', ',
                NULLIF(a.street, ''),
                NULLIF(s.sitio_name, ''),
                NULLIF(a.barangay, ''),
                NULLIF(a.city_municipality, '')
            ) AS VARCHAR
        ) AS address,
        CAST(COALESCE(s.sitio_name, 'N/A') AS VARCHAR) AS sitio_name,
        COALESCE(COUNT(DISTINCT f.family_id), 0) AS total_families,
        COALESCE(COUNT(DISTINCT fm.resident_id), 0) AS total_members,
        MAX(f.updated_at)::DATE AS last_visit_date
    FROM 
        household h
    LEFT JOIN 
        resident r ON h.household_head_id = r.resident_id
    LEFT JOIN 
        address a ON h.address_id = a.address_id
    LEFT JOIN 
        sitio s ON a.sitio_id = s.sitio_id
    LEFT JOIN 
        family f ON h.household_id = f.household_id
    LEFT JOIN 
        family_member fm ON f.family_id = fm.family_id
    WHERE 
        h.is_visited = TRUE
        AND (p_start_date IS NULL OR f.updated_at::DATE >= p_start_date)
        AND (p_end_date IS NULL OR f.updated_at::DATE <= p_end_date)
    GROUP BY 
        h.household_id,
        h.household_number,
        r.first_name,
        r.middle_name,
        r.last_name,
        r.suffix,
        a.street,
        a.barangay,
        a.city_municipality,
        s.sitio_name
    HAVING 
        MAX(f.updated_at)::DATE IS NOT NULL
    ORDER BY 
        MAX(f.updated_at)::DATE DESC,
        h.household_number;
END;
$$ LANGUAGE plpgsql;

-- =============================================
-- Test Queries (Comment out after verification)
-- =============================================
-- SELECT * FROM bhw_get_all_households_report(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_active_households_report(NULL, NULL) LIMIT 10;
-- SELECT * FROM bhw_get_visited_households_report('2024-01-01', '2024-12-31') LIMIT 10;
