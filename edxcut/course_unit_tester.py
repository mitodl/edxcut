'''
Unit tester for edX courses.
Checks to ensure responses to problems are graded with expected correctness.
'''

import os
import sys
import pytest

from lxml import etree
from StringIO import StringIO

import course_tests
reload(course_tests)

AnswerBoxUnitTest = course_tests.AnswerBoxUnitTest
CourseUnitTestSet = course_tests.CourseUnitTestSet

import edxapi
reload(edxapi)

edXapi = edxapi.edXapi

class CourseUnitTester(object):
    '''
    Unit tester for edX courses.
    Checks to ensure responses to problems are graded with expected correctness.
    '''
    def __init__(self, site_base_url=None, username=None, password=None, course_id=None, verbose=False, cutfn=None):
        '''
        course_id should be a fully-formed course-v1 or slash separated course id, as appropriate.

        cutfn = course unit test file (yaml format); specifies unit tests to perform; may include site_base_url,
                username, password, course_id.
        '''
        self.verbose = verbose
        self.cut_specs = None
        if cutfn:
            self.load_cut_file(cutfn)
        if site_base_url:
            self.site_base_url = site_base_url
        if username:
            self.username = username
        if not password:
            password = self.password
        if course_id:
            self.course_id = course_id
        self.ea = edXapi(self.site_base_url, self.username, password, self.course_id, verbose=self.verbose)

    def load_cut_file(self, fn):
        '''
        Load course unit test file.  YAML format (for now).
        '''
        self.cutset = CourseUnitTestSet(fn)
        self.__dict__.update(self.cutset.config)

    def run_all_tests(self):
        '''
        Run tests loaded from cut file.
        '''
        cnt = 0
        nok = 0
        nbad = 0
        all_url_names = []
        print "="*60 + " Running %s tests" % self.cutset.ntests
        print "Tests using site %s and course %s" % (self.site_base_url, self.course_id)
        print "-" * 60
        for test in self.cutset.tests:
            cnt += 1
            if test.url_name not in all_url_names:
                all_url_names.append(test.url_name)
            ret = self.test_problem(abutest=test)
            if ret['ok']:
                name = "[%s]" % test.name if test.name else ""
                print "Test %d: OK %s" % (cnt, name)
                nok += 1
            else:
                print "Test %s: Failure! url_name=%s, responses=%s, expected=%s" % (test.name,
                                                                                    test.url_name,
                                                                                    test.responses,
                                                                                    test.expected)
                print "   --> got correctness_list=%s" % ret['correctness_list']
                nbad += 1
            sys.stdout.flush()
        nprobs = len(all_url_names)
        print "="*40 + " Tests done"
        print "%s total tests, on %s unique problems; %s passed, %s failed" % (cnt, nprobs, nok, nbad)
        self.test_results = {'n_tests_ran': cnt,
                             'n_passed': nok,
                             'n_failed': nbad,
                             'n_problems': nprobs,
                             }

    def make_correctness_list_from_xml(self, xml, status_names):
        '''
        Extract whether a given response was correct or incorrect, from the content XML 
        returned for a problem, from the grader.

        Return cottectness list (a list of strings).
        '''
        status_divs = []
        correctness_list = []
        for sn, response in status_names.items():
            correctness = None
            label_type = None
            sn_orig = sn
            #
            # This is the diciest part of the edxcut process, because the edX xblock API
            # and the edX CAPA responsetypes interface is not well defined here.
            #
            # We need to extract, from the XML content returned by the problem grader,
            # whether the learner's response was graded "correct" or "incorrect".  For
            # multiple choce problems, how edX has encoded this information has changed
            # significantly over the months, largely because of the need to accommodate
            # accessibility constraints.  Beyond this, even the format of the html element
            # ID's has changed, eg from input_.... to status_... to ...-label.
            #
            sx = xml.find('.//div[@id="%s"]' % sn)		# text line input problems
            if sx is None:
                sx = xml.find('.//span[@id="%s"]' % sn)	# multiple choice problems, unanswered
            if sx is None:
                sn = "input_%s_%s" % (sn_orig[7:], response)	# <label for="input_a0effb954cca4759994f1ac9e9434bf4_3_1_choice_2" class="choicegroup_correct">
                sx = xml.find('.//label[@for="%s"]' % sn)	# multiple choice problems
                label_type = "choice input"
            if sx is None:
                # <label id="URL_NAME_2_1-choice_5-label" class="response-label field-label label-inline choicegroup_correct">
                sn = "%s-%s-label" % (sn_orig[7:], response)
                sx = xml.find('.//label[@id="%s"]' % sn)	# multiple choice problems
            if sx is None:
                contents = etree.tostring(xml)
                raise Exception("[CourseUnitTester] failed to find status in content for %s,"
                                "contents=%s" % (sn, contents))
            if correctness is None:
                try:
                    correctness = sx.get('class').strip()
                except Exception as err:
                    contents = etree.tostring(xml)
                    raise Exception("[CourseUnitTester] failed to construct correctness, err=%s, "
                                    "with status_name=%s, contents=%s" % (err, sn, contents))
                if ' ' in correctness:
                    for cstr in correctness.split(' '):
                        if 'correct' in cstr:
                            correctness = cstr
                correctness = correctness.replace('choicegroup_', '')
                correctness = correctness.replace('status', '')
                correctness = correctness.replace('inline', '')
                correctness = correctness.strip()
            correctness_list.append(correctness)
            status_divs.append(sx)
        return correctness_list

    def test_problem(self, url_name=None, responses=None, expected=None, box_indexes=None, abutest=None):
        '''
        Test that the problem specified by url_name, when fed responses, returns expected.

        responses = ordered list of input strings, or dict with key:string
        expected = either list or single string instance of "correct" or "incorrect" or "error"
        box_indexes = list of (x,y) indexes for input box locations

        if url_name, responses, and expected are not supplied, then abutest (an AnswerBoxUnitTest objet)
        must be provided.

        Returns a dict, with:
           'ok': True (if expected outcome was obtaine), or False (otherwise)
           'data': response from grader
           'xml': etree xml of content
           'correctness_list': list of correctness strings
        '''
        if abutest:
            url_name = abutest.url_name
            responses = abutest.responses
            expected = abutest.expected
            box_indexes = abutest.box_indexes
        got_eval = False

        ntries = 0
        while not got_eval:
            ntries += 1
            try:
                data = self.ea.do_xblock_check_problem(url_name, responses, box_indexes)
            except Exception as err:
                print "[CourseUnitTester] Failed testing %s (at %s), err=%s" % (url_name,
                                                                                self.ea.problem_url(url_name),
                                                                                err)
                print "--> Skipping problem!"
                return {'ok': False,
                        'data': None,
                        'xml': None,
                        'correctness_list': None,
                        'overall_correctnes': None,
                        'responses': responses,
                        'expected': expected,
                }
                sys.stdout.flush()
            if 'success' in data and "Please refresh your page" in data['success']:
                ret = self.ea.do_reset_student_attempts(url_name)
                if not (isinstance(ret, dict) and 'student' in ret):
                    raise Exception("[CourseUnitTester] Failed to reset attempts!  return=%s" % ret)
            else:
                got_eval = True
            if ntries > 10:
                got_eval = True

        parser = etree.HTMLParser()
        if 'contents' in data:
            xml = etree.parse(StringIO(data['contents']), parser)
            # <div class="correct " id="status_75f9562c77bc4858b61f907bb810d974_4_1">
            status_names = self.ea.make_response_dict(url_name, responses, prefix="status", box_indexes=box_indexes)
            if self.verbose > 3:
                print "    stats_names=%s" % status_names
            try:
                correctness_list = self.make_correctness_list_from_xml(xml, status_names)
            except Exception as err:
                if "failed to find status in content" in str(err):
                    # try reducing x index offset from 2 to 1 (some versions of edx platform index from 3, some from 2)
                    # for multiple choice problems.
                    if self.verbose:
                        print ("[CourseUnitTester] test_problem: warning, %s, with status_names=%s; "
                               "retrying with x index offset = 1" % (str(err), status_names))
                    status_names = self.ea.make_response_dict(url_name, responses, prefix="status",
                                                              box_indexes=box_indexes,
                                                              x_index_offset=1)
                    try:
                        correctness_list = self.make_correctness_list_from_xml(xml, status_names)
                    except Exception as err:
                        print "[CourseUnitTester] test_problem, error with status_names=%s, err=%s" % (status_names, err)
                        print "--> Skipping problem!"
                        return {'ok': False,
                                'data': None,
                                'xml': None,
                                'correctness_list': None,
                                'overall_correctnes': None,
                                'responses': responses,
                                'expected': expected,
                        }
                    sys.stdout.flush()
                else:
                    raise
                        
        else:
            correctness_list = []
            print "  --> oops, empty correctness_list; url=%s, ret=%s" % (self.ea.jump_to_url(url_name), data)
            xml = None

        if 'Error' in data['success']:
            isok = (expected=="error")
        elif isinstance(expected, list):
            if not len(expected)==len(correctness_list):
                isok = False
            else:
                isok = all([ex==c for (ex, c) in zip(expected, correctness_list)])
        else:
            isok = expected==data['success']
        if self.verbose:
            print "[CourseUnitTester] problem %s responses %s gives correctness %s (%s)" % (url_name, responses, correctness_list, "OK" if isok else "ERROR")
        status = {'ok': isok,
                  'data': data,
                  'xml': xml,
                  'correctness_list': correctness_list,
                  'overall_correctnes': data['success'],
                  'responses': responses,
                  'expected': expected,
                  }
        return status

#-----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cut_test_fixture():
    course_id = "course-v1:edX+DemoX+Demo_Course"
    cut = CourseUnitTester("http://192.168.33.10", "staff@example.com", "edx", course_id)
    return cut

def test_cut1(cut_test_fixture):
    cut = cut_test_fixture
    url_name = "75f9562c77bc4858b61f907bb810d974"
    responses = ['43.141', "4500", "5"]
    outcomes = cut.test_problem(url_name, responses, "incorrect")
    print outcomes
    assert (outcomes['ok']==True)
    outcomes = cut.test_problem(url_name, ['43.141', "4500", "5"], ["incorrect", "correct", 'correct'])
    print outcomes
    assert (outcomes['ok']==True)
    ret = cut.test_problem('0d759dee4f9d459c8956136dbde55f02', "France", "correct")
    assert (ret['ok']==True)
    ret = cut.test_problem('0d759dee4f9d459c8956136dbde55f02', "London", "incorrect")
    assert (ret['ok']==True)

def test_cut2(cut_test_fixture):
    cut = cut_test_fixture
    url_name = "Sample_ChemFormula_Problem"
    ret = cut.test_problem(url_name, "H2SO4 -> H^+ + HSO4^-", "correct")
    assert ret['ok']
    ret = cut.test_problem(url_name, "H2SO4  -> H^+ + HSO4^-", "correct")
    assert ret['ok']
    ret = cut.test_problem(url_name, "H2SO4  -> H^+ + 2 HSO4^-", "incorrect")
    assert ret['ok']
    ret = cut.test_problem(url_name, "H2SO4  -> H^+ ", "incorrect")
    assert ret['ok']

def test_cut3(cut_test_fixture):
    cut = cut_test_fixture
    url_name = "Sample_Algebraic_Problem"
    ret = cut.test_problem(url_name, "A*x^2 + sqrt(y)", "correct")
    assert ret['ok']
    ret = cut.test_problem(url_name, "A*x^2 - sqrt(y)", "incorrect")
    assert ret['ok']
    ret = cut.test_problem(url_name, "A*x^2 - fuzzalj(y)", "error")
    assert ret['ok']

def test_cut4(cut_test_fixture):
    cut = cut_test_fixture
    url_name = "a0effb954cca4759994f1ac9e9434bf4"
    ret = cut.test_problem(url_name, ["dummy_default", 'choice_2'], ["incorrect", "correct"])
    print ret
    assert ret['ok']
    ret = cut.test_problem(url_name, ["dummy_default", 'choice_2', ['choice_0', 'choice_2']], ["incorrect", "correct", 'correct'])
    print ret
    assert ret['ok']
    ret = cut.test_problem(url_name, ["blue", 'choice_2', ['choice_0', 'choice_2']], ["correct", "correct", 'correct'])
    print ret
    assert ret['ok']
    ret = cut.test_problem(url_name, ["blue", 'choice_2', ['choice_0', 'choice_2']], "correct")
    print ret
    assert ret['ok']
    ret = cut.test_problem(url_name, ["blue", 'choice_2', ['choice_0', 'choice_3']], "incorrect")
    print ret
    assert ret['ok']

def test_cut5(cut_test_fixture):
    cut = cut_test_fixture
    url_name = "d2e35c1d294b4ba0b3b1048615605d2a"
    ret = cut.test_problem(url_name, """[{"1":[52.609375,158]},{"2":[295.609375,184]},{"3":[560.609375,159]},{"4":[402.609375,182]},
                                        {"5":[537.609375,192]},{"6":[192.609375,145]},{"7":[423.609375,147]},{"8":[178.609375,190]},
                                        {"9":[298.609375,146]},{"10":[541.609375,124]}]""",
                           "correct")
    assert ret['ok']
    ret = cut.test_problem(url_name, """[{"2":[295.609375,184]},{"3":[560.609375,159]},{"4":[402.609375,182]},
                                        {"5":[537.609375,192]},{"6":[192.609375,145]},{"7":[423.609375,147]},{"8":[178.609375,190]},
                                        {"9":[298.609375,146]},{"10":[541.609375,124]}]""",
                           "incorrect")
    assert ret['ok']

def test_cut_from_file1():
    cfn = "../test_data/test_demo_course.yaml"
    cut = CourseUnitTester(cutfn=cfn)
    cut.run_all_tests()
    assert(cut.test_results['n_tests_ran']==3)
    assert(cut.test_results['n_passed']==3)
    assert(cut.test_results['n_failed']==0)

#-----------------------------------------------------------------------------
            
if __name__=="__main__":
    pass

