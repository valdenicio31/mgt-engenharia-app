import ast
import os
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class PackageTests(unittest.TestCase):
    def test_required_files_exist(self):
        required = ["manage.py", "render.yaml", "build.sh", "requirements.txt", "config/settings.py", "core/models.py", "templates/dashboard.html"]
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_python_files_parse(self):
        for path in ROOT.rglob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_render_has_health_and_no_literal_secret(self):
        text = (ROOT / "render.yaml").read_text(encoding="utf-8")
        self.assertIn("healthCheckPath: /health/", text)
        self.assertIn("generateValue: true", text)
        self.assertIn("DATABASE_URL", text)
        self.assertNotIn("postgres://", text)

    def test_security_settings_present(self):
        text = (ROOT / "config/settings.py").read_text(encoding="utf-8")
        for setting in ("SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_HSTS_SECONDS", "X_FRAME_OPTIONS"):
            self.assertIn(setting, text)

    def test_scope_models_present(self):
        text = (ROOT / "core/models.py").read_text(encoding="utf-8")
        for model in ("Client", "Opportunity", "Proposal", "Project", "Task", "RAT", "AuditLog"):
            self.assertIn(f"class {model}", text)

    @unittest.skipUnless(
        os.environ.get("MGT_STRICT_PACKAGE"),
        "verificação de pacote: na máquina de desenvolvimento o .env local é esperado; "
        "definir MGT_STRICT_PACKAGE=1 ao validar o pacote/RC antes do envio",
    )
    def test_no_local_env_in_package(self):
        self.assertFalse((ROOT / ".env").exists())

if __name__ == "__main__":
    unittest.main()
