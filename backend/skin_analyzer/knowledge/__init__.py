"""Offline cosmetic analysis and recommendations."""
from .analysis import generate_report
from .kb import KnowledgeBase
from .models import Report
from .serialization import report_to_dict

__all__ = ["KnowledgeBase", "Report", "generate_report", "report_to_dict"]
