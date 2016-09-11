import sys
import yaml
from lxml import etree

class make_tests_from_xbundle_files(object):
    def __init__(self, files, optargs=None):
        self.files = files
        self.optargs = optargs or {}
        for fn in files:
            self.process_file(fn)
            
    def process_file(self, fn):
        xml = etree.parse(fn).getroot()
        tests = []
        for problem in xml.findall('.//problem'):
            url_name = problem.get('url_name')
            responses = []
            for cr in problem.findall('.//customresponse'):
                for line in cr.findall('.//textline'):
                    responses.append(line.get('correct_answer'))
            test = {'url_name': url_name, 'responses': responses, 'expected': ['correct'] * len(responses)}
            tests.append(test)
        sys.stderr.write("%d tests added\n" % len(tests))
        
        cut_spec = {'config': {}, 'tests': tests}
        config_keys = ["username", "password", "course_id", "site_base_url"]
        for ck in config_keys:
            val = getattr(self.optargs, ck)
            if val:
                cut_spec['config'][ck] = val

        print yaml.dump(cut_spec)

