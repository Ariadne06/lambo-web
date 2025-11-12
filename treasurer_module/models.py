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
