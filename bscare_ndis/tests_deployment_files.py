from pathlib import Path

from django.test import SimpleTestCase


class DeploymentFileTests(SimpleTestCase):
    def test_render_build_script_collects_static_files(self):
        build_script = Path("build.sh").read_text(encoding="utf-8")

        self.assertIn("pip install -r requirements.txt", build_script)
        self.assertIn("python manage.py collectstatic --noinput", build_script)

    def test_render_runtime_dependencies_are_recorded(self):
        requirements = Path("requirements.txt").read_text(encoding="utf-8")

        self.assertIn("gunicorn", requirements)
        self.assertIn("psycopg", requirements)
        self.assertIn("whitenoise", requirements)

    def test_render_beta_runbook_documents_required_commands(self):
        runbook = Path("docs/render-beta-deployment.md").read_text(encoding="utf-8")

        self.assertIn("./build.sh", runbook)
        self.assertIn("python manage.py migrate", runbook)
        self.assertIn("python -m gunicorn bscare_ndis.wsgi:application", runbook)
        self.assertIn("DATABASE_URL", runbook)
