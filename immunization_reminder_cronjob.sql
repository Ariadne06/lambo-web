-- =========================================================
-- Function: Check upcoming child immunization schedules
-- and notify parents 3, 2, 1 days before the scheduled date
-- =========================================================

CREATE OR REPLACE FUNCTION send_immunization_reminders()
RETURNS TABLE (
  notification_sent BOOLEAN,
  parent_resident_id INT,
  child_full_name TEXT,
  vaccine_name TEXT,
  scheduled_date DATE,
  days_until_due INT,
  message TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
  v_record RECORD;
  v_parent_record RECORD;
  v_notification_title TEXT;
  v_notification_body TEXT;
  v_deep_link TEXT;
  v_resident_user_type_id INT;
BEGIN
  -- Get the user_type_id for 'Resident' (assuming it exists)
  SELECT user_type_id INTO v_resident_user_type_id 
  FROM User_Type 
  WHERE user_type_name = 'Resident'
  LIMIT 1;

  -- Loop through all upcoming schedules that are 1, 2, or 3 days away
  FOR v_record IN
    WITH child AS (
      SELECT
        chr.child_health_id,
        chr.child_id AS child_resident_id,
        r.resident_id,
        (r.last_name || ', ' || r.first_name || COALESCE(' ' || r.middle_name, ''))::text AS full_name,
        fm.family_id,
        f.family_code::text AS family_code
      FROM Child_Health_Record chr
      JOIN Resident r    ON r.resident_id  = chr.child_id
      LEFT JOIN Family_Member fm ON fm.resident_id = r.resident_id
      LEFT JOIN Family f        ON f.family_id     = fm.family_id
    )
    SELECT
      s.schedule_id,
      s.child_health_id,
      c.child_resident_id,
      c.full_name       AS child_full_name,
      c.family_code,
      s.vaccine_type_id,
      vt.vaccine_name::text,
      s.next_dose_type_id,
      dt.dose_name::text AS next_dose_name,
      s.scheduled_date,
      (s.scheduled_date - CURRENT_DATE)::int AS days_until_due
    FROM Schedule_Child_Immunization_Record s
    JOIN child c    ON c.child_health_id = s.child_health_id
    JOIN Vaccine_Type vt ON vt.vaccine_type_id = s.vaccine_type_id
    JOIN Dose_Type dt    ON dt.dose_type_id    = s.next_dose_type_id
    WHERE (s.scheduled_date - CURRENT_DATE) IN (1, 2, 3)
    ORDER BY s.scheduled_date ASC
  LOOP
    -- Build notification content
    v_notification_title := 'Immunization Reminder: ' || v_record.vaccine_name;
    v_notification_body := v_record.child_full_name || ' has an upcoming ' || 
                           v_record.vaccine_name || ' (' || v_record.next_dose_name || ') ' ||
                           'scheduled in ' || v_record.days_until_due || ' day' || 
                           CASE WHEN v_record.days_until_due > 1 THEN 's' ELSE '' END || 
                           ' on ' || TO_CHAR(v_record.scheduled_date, 'Month DD, YYYY') || '.';
    
    -- Deep link to notifications screen
    v_deep_link := '/(tabs)/notifications';

    -- Find all parents (mother and father) of this child
    FOR v_parent_record IN
      SELECT DISTINCT
        rel.origin_resident_id AS parent_id
      FROM Relation rel
      WHERE rel.target_resident_id = v_record.child_resident_id
        AND rel.relationship_id IN (
          SELECT relationship_id 
          FROM Relationship 
          WHERE relationship_name IN ('Child')
        )
    LOOP
      -- Insert notification for each parent
      BEGIN
        INSERT INTO Notification (
          user_type_id,
          user_id,
          title,
          body,
          deep_link,
          created_at,
          is_read
        ) VALUES (
          v_resident_user_type_id,
          v_parent_record.parent_id,
          v_notification_title,
          v_notification_body,
          v_deep_link,
          NOW(),
          FALSE
        );

        -- Return success record
        notification_sent := TRUE;
        parent_resident_id := v_parent_record.parent_id;
        child_full_name := v_record.child_full_name;
        vaccine_name := v_record.vaccine_name;
        scheduled_date := v_record.scheduled_date;
        days_until_due := v_record.days_until_due;
        message := 'Notification sent successfully';
        
        RETURN NEXT;

      EXCEPTION WHEN OTHERS THEN
        -- Return error record
        notification_sent := FALSE;
        parent_resident_id := v_parent_record.parent_id;
        child_full_name := v_record.child_full_name;
        vaccine_name := v_record.vaccine_name;
        scheduled_date := v_record.scheduled_date;
        days_until_due := v_record.days_until_due;
        message := 'Error: ' || SQLERRM;
        
        RETURN NEXT;
      END;
    END LOOP;

  END LOOP;

  RETURN;
END $$;

-- =========================================================
-- Example Usage (for testing):
-- =========================================================
-- SELECT * FROM send_immunization_reminders();

-- =========================================================
-- To set up as a cron job in Supabase:
-- =========================================================
-- 1. Go to Supabase Dashboard > Database > Cron Jobs
-- 2. Create a new cron job with schedule: 0 8 * * * (runs daily at 8 AM)
-- 3. SQL command: SELECT send_immunization_reminders();
-- =========================================================

-- =========================================================
-- Alternative: Call via Django management command
-- =========================================================
-- You can also create a Django management command that calls this function
-- and schedule it using system cron or a task scheduler like Celery
-- =========================================================


-- =========================================================
-- Function: Check upcoming maternal checkup schedules
-- and notify mothers 3, 2, 1 days before the scheduled date
-- =========================================================

CREATE OR REPLACE FUNCTION send_maternal_checkup_reminders()
RETURNS TABLE (
  notification_sent BOOLEAN,
  maternal_resident_id INT,
  maternal_full_name TEXT,
  schedule_type TEXT,
  scheduled_date DATE,
  days_until_due INT,
  message TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
  v_record RECORD;
  v_notification_title TEXT;
  v_notification_body TEXT;
  v_deep_link TEXT;
  v_resident_user_type_id INT;
BEGIN
  -- Get the user_type_id for 'Resident' (assuming it exists)
  SELECT user_type_id INTO v_resident_user_type_id 
  FROM User_Type 
  WHERE type_name = 'Resident'
  LIMIT 1;

  -- Loop through all upcoming schedules that are 1, 2, or 3 days away
  FOR v_record IN
    WITH mom AS (
      SELECT 
        mhr.maternal_health_id,
        mhr.maternal_id AS maternal_resident_id,
        (r.last_name || ', ' || r.first_name || COALESCE(' ' || r.middle_name, ''))::text AS full_name,
        f.family_code::text AS family_code
      FROM Maternal_Health_Record mhr
      JOIN Resident r ON r.resident_id = mhr.maternal_id
      LEFT JOIN Family_Member fm ON fm.resident_id = r.resident_id
      LEFT JOIN Family f ON f.family_id = fm.family_id
    )
    SELECT
      s.schedule_id,
      s.maternal_health_id,
      m.maternal_resident_id,
      m.full_name AS maternal_full_name,
      m.family_code,
      s.schedule_type,
      t.trimester_name::text,
      s.scheduled_date,
      (s.scheduled_date - CURRENT_DATE)::int AS days_until_due
    FROM Schedule_Maternal_Checkup_Record s
    JOIN mom m ON m.maternal_health_id = s.maternal_health_id
    LEFT JOIN Trimester t ON t.trimester_id = s.trimester_id
    WHERE (s.scheduled_date - CURRENT_DATE) IN (1, 2, 3)
    ORDER BY s.scheduled_date ASC
  LOOP
    -- Build notification content
    v_notification_title := 'Checkup Reminder: ' || v_record.schedule_type;
    v_notification_body := 'You have an upcoming ' || v_record.schedule_type || 
                           CASE 
                             WHEN v_record.trimester_name IS NOT NULL 
                             THEN ' (' || v_record.trimester_name || ')' 
                             ELSE '' 
                           END ||
                           ' scheduled in ' || v_record.days_until_due || ' day' || 
                           CASE WHEN v_record.days_until_due > 1 THEN 's' ELSE '' END || 
                           ' on ' || TO_CHAR(v_record.scheduled_date, 'Month DD, YYYY') || '.';
    
    -- Deep link to notifications screen
    v_deep_link := '/(tabs)/notifications';

    -- Insert notification for the mother
    BEGIN
      INSERT INTO Notification (
        user_type_id,
        user_id,
        title,
        body,
        deep_link,
        created_at,
        is_read
      ) VALUES (
        v_resident_user_type_id,
        v_record.maternal_resident_id,
        v_notification_title,
        v_notification_body,
        v_deep_link,
        NOW(),
        FALSE
      );

      -- Return success record
      notification_sent := TRUE;
      maternal_resident_id := v_record.maternal_resident_id;
      maternal_full_name := v_record.maternal_full_name;
      schedule_type := v_record.schedule_type;
      scheduled_date := v_record.scheduled_date;
      days_until_due := v_record.days_until_due;
      message := 'Notification sent successfully';
      
      RETURN NEXT;

    EXCEPTION WHEN OTHERS THEN
      -- Return error record
      notification_sent := FALSE;
      maternal_resident_id := v_record.maternal_resident_id;
      maternal_full_name := v_record.maternal_full_name;
      schedule_type := v_record.schedule_type;
      scheduled_date := v_record.scheduled_date;
      days_until_due := v_record.days_until_due;
      message := 'Error: ' || SQLERRM;
      
      RETURN NEXT;
    END;

  END LOOP;

  RETURN;
END $$;

-- =========================================================
-- Example Usage (for testing):
-- =========================================================
-- SELECT * FROM send_maternal_checkup_reminders();

-- =========================================================
-- To set up as a cron job in Supabase:
-- =========================================================
-- 1. Go to Supabase Dashboard > Database > Cron Jobs
-- 2. Create a new cron job with schedule: 0 8 * * * (runs daily at 8 AM)
-- 3. SQL command: SELECT send_maternal_checkup_reminders();
-- =========================================================
