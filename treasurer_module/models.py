from django.db import models, connection
from typing import Optional, List, Dict, Any


class TreasurerRepo(models.Model):
	class Meta:
		managed = False

	@staticmethod
	def list_all(q: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
		"""Calls treasurer_get_all_application(q, limit, offset) and returns list[dict]."""
		with connection.cursor() as cur:
			cur.execute("SELECT * FROM treasurer_get_all_application(%s,%s,%s)", [q, limit, offset])
			cols = [c[0] for c in cur.description]
			return [dict(zip(cols, row)) for row in cur.fetchall()]

	@staticmethod
	def count_all(q: Optional[str] = None) -> int:
		with connection.cursor() as cur:
			cur.execute("SELECT COUNT(*) FROM treasurer_get_all_application(%s,%s,%s)", [q, 1_000_000_000, 0])
			return int(cur.fetchone()[0])

	@staticmethod
	def get_one(application_id: int) -> Optional[Dict[str, Any]]:
		"""Wrap treasurer_get_specific_application; it returns same columns as get_specific_application."""
		with connection.cursor() as cur:
			# Use explicit column list by selecting from function with defined composite; here we fetch generically
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
					date_paid TIMESTAMPTZ
				)
				""",
				[application_id]
			)
			cols = [c[0] for c in cur.description]
			row = cur.fetchone()
			return dict(zip(cols, row)) if row else None

	@staticmethod
	def set_paid(application_id: int, or_number: str) -> None:
		with connection.cursor() as cur:
			cur.execute("SELECT set_application_to_paid(%s,%s)", [application_id, or_number])
