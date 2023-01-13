from lib import JenkinsAnalysis
from lib import ResultAnalyser
from lib import FailureAnalyser
from lib import SummaryAnalyser
from lib import GramineNightly
from lib import CurationNightly


JENKINS_URL = os.environ.get('jenkins_url')
NIGHTLY_PIPELINE = os.environ.get('nightly_pipeline')

USER_NAME = os.environ.get('username')
PASSWORD = os.environ.get('password')


if __name__ == "__main__":

    print("Starting Jenkins Nightly Analysis for {}".format(NIGHTLY_PIPELINE))
    greport = JenkinsAnalysis(JENKINS_URL, USER_NAME, PASSWORD)
    rp = ResultAnalyser()
    fa = FailureAnalyser(rp)
    sa = SummaryAnalyser()

    if "curation" in NIGHTLY_PIPELINE:
        cn = CurationNightly(greport, rp, fa, sa)
        cn.analyze_and_report(NIGHTLY_PIPELINE)
    else:
        gn = GramineNightly(greport, rp, fa, sa)
        gn.analyze_and_report(NIGHTLY_PIPELINE)

    sa.copy_results()