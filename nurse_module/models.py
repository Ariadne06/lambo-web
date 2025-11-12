from django.db import models, connection
from django.db.utils import ProgrammingError, DatabaseError  # ✅ use Django’s wrappers
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from math import ceil
from dataclasses import dataclass

# Optional: catch the specific Postgres error when a SQL function is missing
try:
    from psycopg.errors import UndefinedFunction as PGUndefinedFunction
except Exception:
    class PGUndefinedFunction(Exception):
        """Fallback so we can safely 'except PGUndefinedFunction' even if psycopg.errors is unavailable."""
        pass


# Create your models here.

class Dashboard(models.Model):
    """
    Thin query layer for dashboard-related SQL functions.
    Uses the same 'managed = False' pattern as your other classes.
    """
    class Meta:
        managed = False

    @staticmethod
    def sp_dashboard_totals(barangay: Optional[str] = None, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Calls Postgres function:
            SELECT dashboard_totals(%s, %s);
        Expects a JSON/JSONB result with keys:
            total_resident, total_non_resident, total_pending, total_male, total_female
        Returns a plain dict with 0 defaults if keys are missing.
        """
        with connection.cursor() as cursor:
            # callproc also works, but many Postgres JSON-returning functions are cleaner via execute
            cursor.execute("SELECT dashboard_totals(%s, %s);", [barangay, city])
            row = cursor.fetchone()

        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload or "{}")
        elif payload is None:
            payload = {}

        # Safe defaults
        return {
            "total_resident": int(payload.get("total_resident", 0)),
            "total_non_resident": int(payload.get("total_non_resident", 0)),
            "total_pending": int(payload.get("total_pending", 0)),
            "total_male": int(payload.get("total_male", 0)),
            "total_female": int(payload.get("total_female", 0)),
        }
    
    @staticmethod
    def sp_residents_per_sitio_json() -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT residents_per_sitio_json();")
            row = cursor.fetchone()

        val = row[0] if row else None
        if val is None:
            return []
        if isinstance(val, list):            # jsonb -> Python
            return val
        if isinstance(val, (bytes, bytearray)):
            return json.loads(val.decode("utf-8"))
        if hasattr(val, "tobytes"):          # memoryview
            return json.loads(val.tobytes().decode("utf-8"))
        if isinstance(val, str):
            return json.loads(val)
        return []  # fallback

    @staticmethod
    def sp_age_bracket_distribution() -> list[dict]:
        with connection.cursor() as cur:
            cur.execute("SELECT age_bracket_distribution();")
            row = cur.fetchone()
        val = row[0] if row else None
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            import json
            return json.loads(val)
        return []
    
class AnnouncementRepo(models.Model):
    """
    SQL wrappers for announcements with audience support.
    """
    class Meta:
        managed = False
        db_table = 'Announcement'

    # ---------- helpers ----------
    @staticmethod
    def _dictfetchall(cur) -> List[Dict]:
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def _norm_audience(val: Optional[str]) -> str:
        v = (val or "").strip().lower()
        if v in ("", "both", "everyone", "everybody", "all"): return "both"
        if v in ("resident", "residents"): return "resident"
        if v in ("personnel", "staff", "employee", "employees"): return "personnel"
        return v

    @staticmethod
    def _postprocess(rows: List[Dict]) -> List[Dict]:
        out = []
        for a in rows or []:
            a["audience"] = AnnouncementRepo._norm_audience(a.get("audience") or a.get("p_audience"))
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            out.append(a)
        return out

    # ---------- queries ----------
    @staticmethod
    def list_all(q: Optional[str] = None,
                 date_from: Optional[date] = None,
                 date_to: Optional[date] = None,
                 created_by: Optional[int] = None,
                 sort: str = 'date_desc',
                 limit: int = 100, offset: int = 0,
                 audience: Optional[str] = None) -> List[Dict]:
        with connection.cursor() as cur:
            # Updated function has audience param (8 args). If your DB still has the old one, this falls back.
            try:
                cur.execute(
                    "SELECT * FROM get_all_announcement(%s,%s,%s,%s,%s,%s,%s,%s)",
                    [q, date_from, date_to, created_by, sort, limit, offset, audience]
                )
            except Exception:
                cur.execute(
                    "SELECT * FROM get_all_announcement(%s,%s,%s,%s,%s,%s,%s)",
                    [q, date_from, date_to, created_by, sort, limit, offset]
                )
            rows = AnnouncementRepo._dictfetchall(cur)
        return AnnouncementRepo._postprocess(rows)

    @staticmethod
    def latest_for_personnel(limit: int = 3) -> List[Dict]:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM get_latest_announcements_for_personnel()")
                rows = AnnouncementRepo._dictfetchall(cur)
        except Exception:
            rows = AnnouncementRepo.list_all(sort='date_desc', limit=50, audience=None)
        rows = AnnouncementRepo._postprocess(rows)
        out = [a for a in rows if a["audience"] in ("both", "personnel")]
        return out[:limit]

    @staticmethod
    def latest_for_residents(limit: int = 3) -> List[Dict]:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM get_latest_announcements_for_residents()")
                rows = AnnouncementRepo._dictfetchall(cur)
        except Exception:
            rows = AnnouncementRepo.list_all(sort='date_desc', limit=50, audience=None)
        rows = AnnouncementRepo._postprocess(rows)
        out = [a for a in rows if a["audience"] in ("both", "resident")]
        return out[:limit]
    

class ResidentList(models.Model):
    """
    Thin query layer for the Postgres function:
      view_all_resident(p_query, p_sex, p_status_id, p_min_age, p_max_age, p_limit, p_offset)
    """
    class Meta:
        managed = False

    @staticmethod
    def _rows_to_dicts(cursor) -> List[Dict[str, Any]]:
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def search(
        p_query: Optional[str] = None,
        p_sex: Optional[str] = None,          # 'male'/'female'
        p_status_id: Optional[int] = None,
        p_min_age: Optional[int] = None,
        p_max_age: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        page = max(1, int(page or 1))
        limit = max(0, int(page_size or 50))
        offset = (page - 1) * limit

        norm_sex = None
        if p_sex:
            s = str(p_sex).strip().lower()
            if s in ("male", "female"):
                norm_sex = s

        # 1) paged rows
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM view_all_resident(%s,%s,%s,%s,%s,%s,%s);
                """,
                [p_query, norm_sex, p_status_id, p_min_age, p_max_age, limit, offset],
            )
            rows = ResidentList._rows_to_dicts(cursor)

        # 2) total count (simple approach)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)::int
                FROM view_all_resident(%s,%s,%s,%s,%s,%s,%s);
                """,
                [p_query, norm_sex, p_status_id, p_min_age, p_max_age, 2147483647, 0],
            )
            total = cursor.fetchone()[0] if cursor.rowcount != 0 else 0

        pages = max(1, ceil(total / limit)) if limit else 1

        # Build modal payloads (aligned with the template)
        for r in rows:
            payload = {
                "resident_id": r.get("resident_id"),
                "resident_code": r.get("resident_code"),
                # Use full_name directly from SQL (don’t split)
                "full_name": r.get("full_name") or "",         # <— send full_name directly
                "sex": r.get("sex"),
                "dob": str(r.get("dob")) if r.get("dob") else "",
                "age": r.get("age"),
                "religion": r.get("religion"),
                "educ_attainment": r.get("educational_attainment"),
                "religion": r.get("religion"), 
                "civil_status": r.get("civil_status"),
                "resident_status": r.get("status_name"),
                # New: bind to full_address from SQL
                "full_address": r.get("full_address"),
                # Table fields you still show:
                "household_number": r.get("household_number"),
                "family_code": r.get("family_code"),
            }
            r["payload_json"] = json.dumps(payload, ensure_ascii=False)


        return {
            "rows": rows,
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
            "offset": offset,
        }
    


@dataclass
class HouseholdDTO:
    household_id: int
    household_number: Optional[str]
    household_head: Optional[str]
    full_address: Optional[str]
    is_visited: bool
    date_visited: Optional[datetime]
    visited_by: Optional[str]
    is_active: bool
    deactivation_reason: Optional[str]
    deactivated_by: Optional[str]
    created_by: Optional[str]
    quarter_id: Optional[int]

class Household(models.Model):
    """
    Read-only adapter for get_all_households().
    """
    class Meta:
        db_table = "household"

    @staticmethod
    def get_all_households(
        q: Optional[str] = None,
        barangay: Optional[str] = None,
        sitio_id: Optional[int] = None,
        status: str = "all",
        quarter_id: Optional[int] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Tuple[List[HouseholdDTO], Dict[str, Any]]:
        """
        Calls:
          SELECT * FROM get_all_households(%s,%s,%s,%s,%s,%s,%s);
        Returns DTO list + simple pagination flags.
        """
        params = [q, barangay, sitio_id, status, quarter_id, limit, offset]
        rows: List[HouseholdDTO] = []

        with connection.cursor() as cur:
            cur.execute("""
                SELECT household_id,
                       household_number,
                       household_head,
                       full_address,
                       is_visited,
                       date_visited,
                       visited_by,
                       is_active,
                       deactivation_reason,
                       deactivated_by,
                       created_by,
                       quarter_id
                FROM get_all_households(%s,%s,%s,%s,%s,%s,%s);
            """, params)
            raw = cur.fetchall()

        for r in raw:
            rows.append(HouseholdDTO(
                household_id=r[0],
                household_number=r[1],
                household_head=r[2],
                full_address=r[3],
                is_visited=r[4],
                date_visited=r[5],
                visited_by=r[6],
                is_active=r[7],
                deactivation_reason=r[8],
                deactivated_by=r[9],
                created_by=r[10],
                quarter_id=r[11],
            ))

        # Pagination helpers (function doesn't return total count).
        has_prev = offset > 0
        has_next = len(rows) == max(1, limit) and (rows[0].household_id != 0)  # sentinel not considered "real"
        meta = {
            "limit": limit,
            "offset": offset,
            "has_prev": has_prev,
            "has_next": has_next,
            "received": len(rows),
        }
        return rows, meta
    
class QuarterCatalog(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def get_current_quarter_id() -> Optional[int]:
        with connection.cursor() as cur:
            cur.execute("SELECT get_current_quarter_id();")
            row = cur.fetchone()
        return row[0] if row else None

    @staticmethod
    def available_quarters(limit: int = 12) -> List[int]:
        with connection.cursor() as cur:
            cur.execute("""
                WITH q AS (
                  SELECT DISTINCT quarter_id
                  FROM household_quarterly
                  WHERE quarter_id IS NOT NULL
                  ORDER BY quarter_id DESC
                  LIMIT %s
                )
                SELECT quarter_id FROM q ORDER BY quarter_id DESC;
            """, [limit])
            ids = [r[0] for r in cur.fetchall()]

        curr = QuarterCatalog.get_current_quarter_id()
        if curr and curr not in ids:
            ids.append(curr)
            ids.sort(reverse=True)
        return ids
    

@dataclass
class QuarterOption:
    quarter_id: int
    quarter_number: int
    quarter_name: str
    year: int
    start_date: str   # or date, but we only display in template
    end_date: str
    display_label: str

class QuarterCatalog(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def get_current_quarter_id() -> Optional[int]:
        with connection.cursor() as cur:
            cur.execute("SELECT get_current_quarter_id();")
            row = cur.fetchone()
        return row[0] if row else None

    @staticmethod
    def get_all_quarters() -> List[QuarterOption]:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT quarter_id, quarter_number, quarter_name, year, start_date, end_date, display_label
                FROM get_all_quarters();
            """)
            rows = cur.fetchall()

        return [
            QuarterOption(
                quarter_id=r[0],
                quarter_number=r[1],
                quarter_name=r[2],
                year=r[3],
                start_date=str(r[4]),
                end_date=str(r[5]),
                display_label=r[6],
            )
            for r in rows
        ]

    @staticmethod
    def get_label_for(qid: Optional[int]) -> Optional[str]:
        if qid is None:
            return None
        items = QuarterCatalog.get_all_quarters()
        curr = QuarterCatalog.get_current_quarter_id()
        for it in items:
            if it.quarter_id == qid:
                suffix = " (current)" if curr and qid == curr else ""
                return f"Q{it.quarter_number} {it.year}{suffix}"
        return None
    
    @staticmethod
    def all() -> List[Dict]:
        """
        Returns [{'quarter_id': 12, 'quarter_number': 4, 'year': 2025, ...}, ...]
        using your SQL get_all_quarters().
        """
        with connection.cursor() as cur:
            cur.execute("""
                SELECT quarter_id, quarter_number, quarter_name, year, start_date, end_date
                FROM get_all_quarters();
            """)
            rows = cur.fetchall()

        out = []
        for qid, qnum, qname, yr, sd, ed in rows:
            out.append({
                "quarter_id": qid,
                "quarter_number": qnum,
                "year": yr,
                # choose a simple label like “Q4 2025”
                "label": f"Q{qnum} {yr}",
            })
        return out

    @staticmethod
    def label_for(quarter_id: Optional[int]) -> Optional[str]:
        if quarter_id is None:
            return None
        for q in QuarterCatalog.all():
            if q["quarter_id"] == quarter_id:
                return q["label"]
        return None
    
@dataclass
class HouseholdSummary:
    household_id: int
    household_number: str

    # ownership / structure
    house_ownership_id: Optional[int]
    house_ownership: Optional[str]
    house_type_id: Optional[int]
    house_type: Optional[str]

    # head / respondent
    household_head_id: Optional[int]
    household_head: Optional[str]
    respondent_id: Optional[int]
    respondent: Optional[str]
    respondent_rth_id: Optional[int]
    respondent_rth: Optional[str]

    # address
    house_number: Optional[str]
    street: Optional[str]
    sitio_id: Optional[int]
    barangay: Optional[str]
    city_municipality: Optional[str]
    country: Optional[str]
    full_address: Optional[str]

    # visit / status / audit
    is_visited: Optional[bool]
    visited_by: Optional[str]
    date_visited: Optional[Any]
    is_active: Optional[bool]
    created_by: Optional[str]
    created_at: Optional[Any]
    updated_at: Optional[Any]

    # aggregates
    families_count: Optional[int]
    members_count: Optional[int]
    quarter_id: Optional[int]

class HouseholdDetail:
    @staticmethod
    def get_summary(household_id: int, quarter_id: Optional[int] = None) -> Optional["HouseholdSummary"]:
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("""
                SELECT
                  household_id,
                  household_number,

                  house_ownership_id,
                  house_ownership,

                  house_type_id,
                  house_type,

                  household_head_id,
                  household_head,

                  respondent_id,
                  respondent,

                  respondent_rth_id,
                  respondent_rth,

                  house_number,
                  street,
                  sitio_id,
                  barangay,
                  city_municipality,
                  country,
                  full_address,

                  is_visited,
                  visited_by,
                  date_visited,

                  is_active,
                  created_by,
                  created_at,
                  updated_at,

                  families_count,
                  members_count,
                  quarter_id
                FROM get_specific_household(%s, %s);
            """, [household_id, quarter_id])

            row = cur.fetchone()

        if not row:
            return None

        (
            household_id_v,
            household_number_v,

            house_ownership_id_v,
            house_ownership_v,

            house_type_id_v,
            house_type_v,

            household_head_id_v,
            household_head_v,

            respondent_id_v,
            respondent_v,

            respondent_rth_id_v,
            respondent_rth_v,

            house_number_v,
            street_v,
            sitio_id_v,
            barangay_v,
            city_municipality_v,
            country_v,
            full_address_v,

            is_visited_v,
            visited_by_v,
            date_visited_v,

            is_active_v,
            created_by_v,
            created_at_v,
            updated_at_v,

            families_count_v,
            members_count_v,
            quarter_id_v,
        ) = row

        return HouseholdSummary(
            household_id=household_id_v,
            household_number=household_number_v,

            house_ownership_id=house_ownership_id_v,
            house_ownership=house_ownership_v,

            house_type_id=house_type_id_v,
            house_type=house_type_v,

            household_head_id=household_head_id_v,
            household_head=household_head_v,

            respondent_id=respondent_id_v,
            respondent=respondent_v,
            respondent_rth_id=respondent_rth_id_v,
            respondent_rth=respondent_rth_v,

            house_number=house_number_v,
            street=street_v,
            sitio_id=sitio_id_v,
            barangay=barangay_v,
            city_municipality=city_municipality_v,
            country=country_v,
            full_address=full_address_v,

            is_visited=is_visited_v,
            visited_by=visited_by_v,
            date_visited=date_visited_v,

            is_active=is_active_v,
            created_by=created_by_v,
            created_at=created_at_v,
            updated_at=updated_at_v,

            families_count=families_count_v,
            members_count=members_count_v,
            quarter_id=quarter_id_v,
        )

    @staticmethod
    def get_header_number_from_live(household_id: int) -> Optional[str]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT household_number::text FROM household WHERE household_id = %s",
                [household_id],
            )
            row = cur.fetchone()
        return row[0] if row and row[0] else None

    @staticmethod
    def get_header_number_from_any_quarter(household_id: int) -> Optional[str]:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT household_number::text
                  FROM household_quarterly
                 WHERE household_id = %s
              ORDER BY quarter_id DESC
                 LIMIT 1
                """,
                [household_id],
            )
            row = cur.fetchone()
        return row[0] if row and row[0] else None

@dataclass
class FamilyDTO:
    family_id: int
    family_code: str
    family_head: Optional[str]
    respondent_name: Optional[str]
    respondent_relation_to_fh: Optional[str]
    nhts: Optional[bool]
    indigenous_people: Optional[bool]
    household_type: Optional[str]
    water_source: Optional[str]
    waste_mgmt: Optional[str]
    toilet_type: Optional[str]

@dataclass
class MemberDTO:
    member_id: int
    display_name: str
    initials: str
    rel_to_hh_head: Optional[str]
    rel_to_fam_head: Optional[str]
    philhealth_no: Optional[str]
    membership_type: Optional[str]
    category: Optional[str]
    nutrition: Optional[str]

class HouseholdFamilies(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def list_families(household_id: int, quarter_id: Optional[int]) -> List[FamilyDTO]:
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT
                        family_id,
                        family_code,
                        family_head_name,
                        respondent_name,
                        respondent_relation_to_fh,
                        nhts,
                        indigenous_people,
                        household_type,
                        water_source,
                        waste_mgmt,
                        toilet_type
                    FROM get_household_families(%s, %s);
                """, [household_id, quarter_id])
                rows = cur.fetchall()
        except (ProgrammingError, DatabaseError, PGUndefinedFunction):
            return []

        out: List[FamilyDTO] = []
        for r in rows:
            out.append(FamilyDTO(
                family_id=r[0],
                family_code=r[1],
                family_head=r[2],
                respondent_name=r[3],
                respondent_relation_to_fh=r[4],
                nhts=r[5],
                indigenous_people=r[6],
                household_type=r[7],
                water_source=r[8],
                waste_mgmt=r[9],
                toilet_type=r[10],
            ))
        return out

    @staticmethod
    def list_members(family_id: int, quarter_id: Optional[int]) -> List[MemberDTO]:
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT
                        member_id,
                        display_name,
                        initials,
                        rel_to_hh_head,
                        rel_to_fam_head,
                        philhealth_no,
                        membership_type,
                        category,
                        nutrition
                    FROM get_family_members(%s, %s);
                """, [family_id, quarter_id])
                rows = cur.fetchall()
        except (ProgrammingError, DatabaseError, PGUndefinedFunction):
            return []

        out: List[MemberDTO] = []
        for r in rows:
            out.append(MemberDTO(
                member_id=r[0],
                display_name=r[1],
                initials=r[2],
                rel_to_hh_head=r[3],
                rel_to_fam_head=r[4],
                philhealth_no=r[5],
                membership_type=r[6],
                category=r[7],
                nutrition=r[8],
            ))
        return out
    
    @staticmethod
    def list_families_with_members(
        household_id: int,
        quarter_id: Optional[int],
    ) -> List[dict]:
        """
        Uses get_family_summaries_per_household(household_id, quarter_id)
        and expands the family_members JSONB into MemberDTOs.
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      family_id,
                      family_code,
                      family_head,
                      respondent_name,
                      respondent_relationship,
                      nhts_status,
                      indigent,
                      household_type,
                      water_source,
                      waste_management,
                      toilet_type,
                      family_members
                    FROM get_family_summaries_per_household(%s, %s);
                    """,
                    [household_id, quarter_id],
                )
                rows = cur.fetchall()
        except (ProgrammingError, DatabaseError):
            return []

        results: List[dict] = []

        for (
            family_id,
            family_code,
            family_head,
            respondent_name,
            respondent_relationship,
            nhts_status,
            indigent,
            household_type,
            water_source,
            waste_management,
            toilet_type,
            family_members_json,
        ) in rows:

            # Skip sentinel row (family_id = 0), if your SQL uses that
            if family_id == 0:
                continue

            fam = FamilyDTO(
                family_id=family_id,
                family_code=family_code,
                family_head=family_head,
                respondent_name=respondent_name,
                respondent_relation_to_fh=respondent_relationship,
                nhts=nhts_status,
                indigenous_people=indigent,
                household_type=household_type,
                water_source=water_source,
                waste_mgmt=waste_management,
                toilet_type=toilet_type,
            )

            # ---- JSONB → Python list[dict] ----
            if not family_members_json:
                members_source = []
            elif isinstance(family_members_json, (list, tuple)):
                # already decoded (rare, but safe)
                members_source = family_members_json
            else:
                # most likely a JSON string or memoryview
                try:
                    if isinstance(family_members_json, memoryview):
                        raw = family_members_json.tobytes().decode("utf-8")
                    else:
                        raw = str(family_members_json)
                    members_source = json.loads(raw)
                except Exception:
                    members_source = []

            members: List[MemberDTO] = []
            for m in members_source:
                # safety: ensure it's a dict
                if not isinstance(m, dict):
                    continue

                full_name = (m.get("full_name") or "").strip()

                # Simple initials from full name
                initials = (
                    "".join(
                        part[0].upper()
                        for part in full_name.split()
                        if part
                    )[:2]
                    or "•"
                )

                members.append(
                    MemberDTO(
                        member_id=m.get("family_member_id"),
                        display_name=full_name or "—",
                        initials=initials,
                        # These are ID fields in JSON; you can later resolve them to text labels if you want
                        rel_to_hh_head=None,  # m.get("rth_id")  -> you’d need to join a label if desired
                        rel_to_fam_head=None, # m.get("rtf_id")
                        philhealth_no=m.get("philhealthid_number"),
                        membership_type=m.get("membership_type"),
                        category=str(m.get("philhealth_category_id"))
                        if m.get("philhealth_category_id") is not None
                        else None,
                        nutrition=str(m.get("nutrition_status_id"))
                        if m.get("nutrition_status_id") is not None
                        else None,
                    )
                )

            results.append({"family": fam, "members": members})

        return results




class GeneralHealthRow(models.Model):
    """
    Unmanaged model for list rows coming from view_all_general_health().
    """
    resident_id = models.IntegerField(primary_key=True)  # pseudo pk for Django
    family_member_id = models.IntegerField()
    family_code = models.TextField()
    full_name = models.TextField()
    sex = models.TextField()
    age = models.IntegerField()

    class Meta:
        managed = False
        db_table = "view_all_general_health"

    @staticmethod
    def fetch(query=None, quarter_id=None, limit=50, offset=0):
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT resident_id, family_member_id, family_code, full_name, sex, age
                FROM view_all_general_health(%s, %s, %s, %s)
                """,
                [query, quarter_id, limit, offset],
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def count(query=None, quarter_id=None):
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM (
                  SELECT 1 FROM view_all_general_health(%s, %s, 500000, 0)
                ) t
                """,
                [query, quarter_id],
            )
            return cur.fetchone()[0]

    @staticmethod
    def fetch_detail(family_member_id: int, quarter_id=None):
        """
        Calls: SELECT * FROM view_specific_resident_general_health(p_family_member_id, p_quarter_id)
        Returns: single dict row (or None)
        """
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT
                  record_id, family_member_id, resident_id, full_name, sex,
                  family_id, family_code,
                  medical_history_ids, medical_history_names,
                  age, class_id, class_description,
                  last_menstrual_period, fp_method_yn, fp_method_id, fp_method_name,
                  fp_status_id, fp_status_name, age_of_menarche,
                  smoker, alcohol_drinker, sexually_active,
                  created_at, updated_at, added_by, added_by_full_name,
                  quarter_id
                FROM view_specific_resident_general_health(%s, %s)
                """,
                [family_member_id, quarter_id],
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c[0] for c in cur.description]
            return dict(zip(cols, row))
        





