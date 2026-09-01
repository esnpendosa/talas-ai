"""
TALAS AI — Models Package
Import semua model agar SQLAlchemy dapat mendeteksinya saat create_all_tables().
"""
from app.models.user import User, Role, Permission, UserRole, RolePermission
from app.models.regulation import (
    Regulation,
    RegulationRelationship,
    RegulationVersion,
)
from app.models.document import Document, DocumentChunk, DocumentMetadata
from app.models.analysis import Analysis, AnalysisFinding, AnalysisSource
from app.models.chat import ChatSession, ChatMessage
from app.models.review import Review, ReviewComment
from app.models.report import Report, ReportVersion
from app.models.audit import AuditLog
from app.models.settings import AppSettings
from app.models.ai import (
    AIProvider,
    AIModel,
    AITaskConfig,
    AIUsageLog,
    AIFallbackLog,
)

__all__ = [
    # User & Auth
    "User",
    "Role",
    "Permission",
    "UserRole",
    "RolePermission",
    # Regulation
    "Regulation",
    "RegulationRelationship",
    "RegulationVersion",
    # Document
    "Document",
    "DocumentChunk",
    "DocumentMetadata",
    # Analysis
    "Analysis",
    "AnalysisFinding",
    "AnalysisSource",
    # Chat
    "ChatSession",
    "ChatMessage",
    # Review
    "Review",
    "ReviewComment",
    # Report
    "Report",
    "ReportVersion",
    # Audit
    "AuditLog",
    # Settings
    "AppSettings",
    # AI
    "AIProvider",
    "AIModel",
    "AITaskConfig",
    "AIUsageLog",
    "AIFallbackLog",
]
