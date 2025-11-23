from ..utils.database_helpers import get_document_types, get_clearance_purposes


class CertificateService:
    """Minimal certificate service exposing only lookup helpers."""

    @staticmethod
    def get_all_document_types():
        return get_document_types()

    @staticmethod
    def get_all_clearance_purposes():
        return get_clearance_purposes()