import os

JENKINS_URL      = os.environ.get("JENKINS_URL")
NIGHTLY_PIPELINE = os.environ.get('nightly_pipeline')

USER_NAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

REPORTS_PATH = "/mnt/nightly_reports"