"""
TALAS AI — Test Configuration
Test bahwa konfigurasi dibaca dengan benar.
"""
import pytest


class TestConfiguration:
    """Test konfigurasi aplikasi."""

    def test_settings_loaded(self):
        """Settings harus dapat diload."""
        from app.config import get_settings
        settings = get_settings()
        assert settings is not None
        assert settings.APP_NAME == "TALAS AI"

    def test_default_ai_mode_is_local(self):
        """Default AI mode harus LOCAL ONLY untuk privasi."""
        from app.config import get_settings
        settings = get_settings()
        assert settings.DEFAULT_AI_MODE == "local_only"

    def test_cloud_ai_disabled_by_default(self):
        """Cloud AI harus disabled secara default."""
        from app.config import get_settings
        settings = get_settings()
        assert settings.CLOUD_AI_ENABLED is False

    def test_secret_key_minimum_length(self):
        """Secret key harus minimal 16 karakter."""
        from app.config import get_settings
        settings = get_settings()
        assert len(settings.SECRET_KEY) >= 16

    def test_allowed_extensions(self):
        """Ekstensi yang diizinkan harus ada."""
        from app.config import get_settings
        settings = get_settings()
        extensions = settings.allowed_extensions_list
        assert "pdf" in extensions
        assert "docx" in extensions

    def test_max_upload_bytes(self):
        """max_upload_bytes harus konsisten dengan MAX_UPLOAD_SIZE_MB."""
        from app.config import get_settings
        settings = get_settings()
        expected = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        assert settings.max_upload_bytes == expected

    def test_invalid_secret_key_raises_error(self):
        """Secret key yang terlalu pendek harus raise error."""
        import os
        from pydantic import ValidationError

        # Simpan nilai asli
        original = os.environ.get("SECRET_KEY", "")
        try:
            os.environ["SECRET_KEY"] = "short"
            # Clear cache
            from app.config import Settings
            with pytest.raises(ValidationError):
                Settings(SECRET_KEY="short")
        finally:
            if original:
                os.environ["SECRET_KEY"] = original
            else:
                os.environ.pop("SECRET_KEY", None)
