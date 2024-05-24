from lib import JenkinsAnalysis
from lib import ResultAnalyser
from lib import FailureAnalyser
from lib import SummaryAnalyser
from lib import NightlyAnalyzer
import os


JENKINS_URL      = os.environ.get("JENKINS_URL")
NIGHTLY_PIPELINE = os.environ.get('nightly_pipeline')

USER_NAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

REPORTS_PATH = "/mnt/nightly_reports"

del os.environ["http_proxy"]
del os.environ["https_proxy"]


if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(NIGHTLY_PIPELINE))
    greport = JenkinsAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    rp = ResultAnalyser()
    fa = FailureAnalyser(rp)
    sa = SummaryAnalyser(REPORTS_PATH)

    na = NightlyAnalyzer(greport, rp, fa, sa)
    if "curation" in NIGHTLY_PIPELINE:
        greport.build_details = rp.build_details = False

    na.analyze_and_report(NIGHTLY_PIPELINE)

    sa.copy_results()
