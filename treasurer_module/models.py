from django.db import models, connection
from typing import Optional, List, Dict, Any


class TreasurerRepo(models.Model):
	class Meta:
		managed = False

	@staticmethod
	def list_all(q: Optional[str] = None,
	            payment_status: Optional[str] = None,
	            request_filter: Optional[str] = None,
	            limit: int = 50,
	            offset: int = 0) -> List[Dict[str, Any]]:
		"""Calls treasurer_get_all_application(q, payment_status, request_filter, limit, offset) and returns list[dict]."""
		with connection.cursor() as cur:
			cur.execute(
				"SELECT * FROM treasurer_get_all_application(%s,%s,%s,%s,%s)",
				[q, payment_status, request_filter, limit, offset]
			)
			cols = [c[0] for c in cur.description]
			return [dict(zip(cols, row)) for row in cur.fetchall()]

	@staticmethod
	def count_all(q: Optional[str] = None,
	             payment_status: Optional[str] = None,
	             request_filter: Optional[str] = None) -> int:
		with connection.cursor() as cur:
			# Count by wrapping the function call
			cur.execute(
				"""
				SELECT COUNT(*) FROM treasurer_get_all_application(%s,%s,%s,%s,%s)
				""",
				[q, payment_status, request_filter, 1_000_000_000, 0]
			)
			return int(cur.fetchone()[0])

	@staticmethod
	def get_one(application_id: int) -> Optional[Dict[str, Any]]:
		"""Wrap treasurer_get_specific_application and map columns dynamically.

		The underlying SQL function has been extended (e.g., requested_by*, paid_by*). To avoid
		column-mismatch errors when the function changes, select generically and map by cursor.description.
		"""
		with connection.cursor() as cur:
			# Use the Treasurer wrapper with an explicit column list to satisfy SETOF RECORD typing
			cur.execute(
				"""
				SELECT * FROM treasurer_get_specific_application(%s) AS (
					application_id INT,
					application_code VARCHAR,
					fee_type VARCHAR,
					request VARCHAR,
					applicant_name TEXT,
					business_id INT,
					business_name TEXT,
					application_status VARCHAR,
					payment_status VARCHAR,
					total_amount NUMERIC,
					total_amount_details JSONB,
					or_number VARCHAR,
					date_paid TIMESTAMPTZ,
					requested_by VARCHAR,
					requested_by_id INT,
					requested_by_full_name TEXT,
					cancel_reason TEXT,
					canceled_at TIMESTAMPTZ,
					canceled_by_type TEXT,
					canceled_by_id INT,
					canceled_by_full_name TEXT,
					reject_reason TEXT,
					rejected_at TIMESTAMPTZ,
					rejected_by_type TEXT,
					rejected_by_id INT,
					rejected_by_full_name TEXT
				)
				""",
				[application_id]
			)
			cols = [c[0] for c in cur.description]
			row = cur.fetchone()
			return dict(zip(cols, row)) if row else None

	@staticmethod
	def set_paid(application_id: int, or_number: str, personnel_id: int) -> None:
		"""Marks as paid via set_application_to_paid(app_id, or_number, personnel_id)."""
		with connection.cursor() as cur:
			cur.execute("SELECT set_application_to_paid(%s,%s,%s)", [application_id, or_number, personnel_id])

	# ---- Dashboard helpers ----
	@staticmethod
	def get_monthly_summary(year: Optional[int] = None, q: Optional[str] = None) -> List[Dict[str, Any]]:
		"""Wrapper for treasurer_get_monthly_summary(year, q).

		Returns list of dicts with columns: year_, month_no, month_name, application_label, applications_count, total_collected.
		"""
		with connection.cursor() as cur:
			cur.execute("SELECT * FROM treasurer_get_monthly_summary(%s,%s)", [year, q])
			cols = [c[0] for c in cur.description]
			return [dict(zip(cols, row)) for row in cur.fetchall()]

	@staticmethod
	def get_distinct_application_labels(year: Optional[int] = None) -> List[str]:
		"""Convenience helper to build filter options for application_label."""
		with connection.cursor() as cur:
			cur.execute("SELECT DISTINCT application_label FROM treasurer_get_monthly_summary(%s, NULL) ORDER BY 1", [year])
			rows = cur.fetchall()
			out: List[str] = []
			for r in rows:
				v = r[0]
				if isinstance(v, str) and v.strip():
					out.append(v.strip())
			return out

	@staticmethod
	def get_recent_transactions() -> List[Dict[str, Any]]:
		"""Wrapper for get_recent_transactions() returning 5 latest items.

		Columns: transaction_id, transaction_code, application_id, application_code,
		request, applicant_name, total_amount, payment_status, date_paid
		"""
		with connection.cursor() as cur:
			cur.execute("SELECT * FROM get_recent_transactions()")
			cols = [c[0] for c in cur.description]
			return [dict(zip(cols, row)) for row in cur.fetchall()]

	@staticmethod
	def get_all_months_collections(year: int) -> List[Dict[str, Any]]:
		"""Return monthly totals for a given year via get_all_months_collections(year)."""
		with connection.cursor() as cur:
			cur.execute("SELECT * FROM get_all_months_collections(%s)", [year])
			cols = [c[0] for c in cur.description]
			return [dict(zip(cols, row)) for row in cur.fetchall()]

	@staticmethod
	def get_year_for_filter_choice() -> List[int]:
		"""Return list of years that have paid collections (ascending)."""
		with connection.cursor() as cur:
			cur.execute("SELECT * FROM get_year_for_filter_choice()")
			rows = cur.fetchall()
			out: List[int] = []
			for r in rows:
				try:
					out.append(int(r[0]))
				except Exception:
					continue
			return out

	@staticmethod
	def get_pending_payments() -> int:
		with connection.cursor() as cur:
			cur.execute("SELECT get_pending_payments()")
			row = cur.fetchone()
			return int(row[0] or 0)

	@staticmethod
	def get_total_collections_today() -> float:
		with connection.cursor() as cur:
			cur.execute("SELECT get_total_collections_today()")
			row = cur.fetchone()
			val = row[0]
			try:
				return float(val or 0)
			except Exception:
				return 0.0

	@staticmethod
	def get_total_or_issued_today() -> int:
		with connection.cursor() as cur:
			cur.execute("SELECT get_total_or_issued_today()")
			row = cur.fetchone()
			return int(row[0] or 0)

	@staticmethod
	def get_financial_report(
		year: Optional[int] = None,
		month: Optional[int] = None,
		start_date: Optional[str] = None,
		end_date: Optional[str] = None,
		limit: int = 10000,
		offset: int = 0
	) -> List[Dict[str, Any]]:
		"""Wrapper for treasurer_get_financial_report().
		
		Returns list of dicts with columns: or_number, total_amount, purpose, issued_by, issued_at
		"""
		with connection.cursor() as cur:
			cur.execute(
				"SELECT * FROM treasurer_get_financial_report(%s,%s,%s,%s,%s,%s)",
				[year, month, start_date, end_date, limit, offset]
			)
			cols = [c[0] for c in cur.description]
			return [dict(zip(cols, row)) for row in cur.fetchall()]
