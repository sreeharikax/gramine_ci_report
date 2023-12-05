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
SHARED_PATH = os.environ.get("SHARED_PATH")


if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(NIGHTLY_PIPELINE))
    greport = JenkinsAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    rp = ResultAnalyser()
    fa = FailureAnalyser(rp)
    sa = SummaryAnalyser(SHARED_PATH)

    na = NightlyAnalyzer(greport, rp, fa, sa)
    if "curation" in NIGHTLY_PIPELINE:
        greport.build_details = rp.build_details = False

    na.analyze_and_report(NIGHTLY_PIPELINE)

    sa.copy_results()