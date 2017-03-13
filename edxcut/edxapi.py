'''
API interface to edx platform site.  
Handles logins, and performs queries.
'''

import os, sys
import time
import requests
import pytest
import json
import argparse

from collections import OrderedDict

class edXapi(object):
    '''
    API interface to edx platform site.  
    Handles logins, and performs queries.
    '''
    def __init__(self, base="https://courses.edx.org", username='', password='', course_id=None, verbose=False):
        '''
        course_id should be a fully-formed course-v1 or slash separated course id, as appropriate.
        '''
        self.ses = requests.session()
        self.BASE = base
        self.verbose = verbose
        self.course_id = course_id
        self.username = username
        self.login(username, password)
        self.xblock_csrf = None

    def login(self, username, pw):
        url = '%s/login' % self.BASE
        r1 = self.ses.get(url)
        self.csrf = self.ses.cookies['csrftoken']
        url2 = '%s/user_api/v1/account/login_session/' % self.BASE
        headers = {'X-CSRFToken': self.csrf,
                   'Referer': '%s/login' % self.BASE}
        r2 = self.ses.post(url2, data={'email': username, 'password': pw}, headers=headers)
        self.headers = headers

        if self.verbose:
            print "[edXapi] login ret = ", r2
        if not r2.status_code==200:
            print "[edXapi] Login failed!"
            print r2.text

    def set_course_id( self, course_id ):
        self.course_id = course_id
    
    # xblocks

    @property
    def xblock_url(self):
        return '%s/courses/%s/xblock' % (self.BASE, self.course_id)

    def problem_block_id(self, url_name):
        cid = self.course_id
        if cid.startswith("course-v1:"):
            cid = cid[10:]
        return 'block-v1:%s+type@problem+block@%s' % (cid, url_name)

    def problem_url(self, url_name):
        return '%s/%s/handler/xmodule_handler' % (self.xblock_url, self.problem_block_id(url_name))

    def jump_to_url(self, url_name):
        return '%s/courses/%s/jump_to_id/%s' % (self.BASE, self.course_id, url_name)

    def get_problem_csrf(self, url_name):
        url = self.jump_to_url(url_name)
        ret = self.ses.get(url)
        csrf = self.ses.cookies['csrftoken']
        if self.verbose:
            print "[edXapi] get_problem_csrf headers=%s" % ret.headers
        return csrf

    def get_xblock_json_response(self, handler, url_name, post_data=None):
        '''
        Get JSON response from xblock for specified handler and url_name
        handlers include "problem_show"
        '''
        burl = "%s/%s" % (self.problem_url(url_name), handler)
        if not self.xblock_csrf:
            self.xblock_csrf = self.get_problem_csrf(url_name)
            self.headers['X-CSRFToken'] = self.xblock_csrf
        self.headers['Accept'] = "application/json, text/javascript, */*; q=0.01"
        self.headers['Referer'] = self.jump_to_url(url_name)
        ret = self.ses.post(burl, data=post_data or {}, headers=self.headers)
        try:
            data = ret.json()
        except Exception as err:
            raise Exception("[edXapi] get_xblock_json_response failed to get JSON format reponse "
                            "for handler %s url_name %s, err %s, ret code=%s, text=%s" % (handler,
                                                                                          url_name,
                                                                                          err,
                                                                                          ret.status_code,
                                                                                          ret.text))
        self.ret = ret
        return data

    def do_xblock_show_answer(self, url_name):
        '''
        Run a problem_show and return answer shown
        '''
        data = self.get_xblock_json_response("problem_show", url_name)
        return data

    def do_xblock_get_problem(self, url_name):
        '''
        Get problem HTML
        '''
        data = self.get_xblock_json_response("problem_get", url_name)
        return data

    def make_response_dict(self, url_name, responses, prefix="input", box_indexes=None,
                           x_index_offset=2, y_index_offset=1):
        '''
        Given an ordered list of responses to a problem (ie answer box submissions), return a dict which
        has appropriate keys ("input_<url_name>_<num>_<index>") for each response, to be used in
        submitting an xblock problem check.

        box_indexes gives the (x,y) id numbers for the input boxes.  They are used to construct
        the input box ID, which is of the form input_<url_name>_<x>_<y>, where <x> indexes which \abox 
        the input is, and <y> indexes which input element it is, within a given abox (for aboxes with
        multiple input boxes).  This list should have the same length as the responses.

        If box_indices is not provided, then it defaults to 
                 zip(range(len(responses)), [0]*len(responses))

        Note that the edX platform seems to start x from 2 (and not 1, or 0), and
        y from 1.  We have the convention that x and y both start at 0, so the offsets are
        added here.
        '''
        if not isinstance(responses, list):
            responses = [responses]
        box_indexes = box_indexes or zip(range(len(responses)), [0]*len(responses))
        return OrderedDict([ ("%s_%s_%d_%d" % (prefix, url_name, x + x_index_offset, y + y_index_offset) , val) 
                             for ((x,y), val) in zip(box_indexes, responses)])

    def do_xblock_check_problem(self, url_name, responses=None, box_indexes=None):
        '''
        Run a problem_check, given submission responses; return grader response
        '''
        if not isinstance(responses, dict):
            responses = self.make_response_dict(url_name, responses, box_indexes=box_indexes)
        post_data = []					# have to send post_data as list of tuples, to accomodate possible duplicate keys
        for inkey, response in responses.items():	# if any of the responses is a list, that's for a multiple-choice problem allowing multiple reponses
            if isinstance(response, list):
                for ritem in response:
                    post_data.append(("%s[]" % inkey, ritem))	# duplicate keys, with [] to tell edx-platform server to recreate list
            else:
                post_data.append((inkey, response))
        if self.verbose > 2:
            print "[edxapi] do_block_chck_problem: post_data=%s" % post_data
        data = self.get_xblock_json_response("problem_check", url_name, post_data=post_data)
        return data

    # instructor dashboard 

    @property
    def instructor_dashboard_url(self):
        return '%s/courses/%s/instructor' % (self.BASE, self.course_id)

    def get_instructor_dashboard_csrf(self):
        url = '%s#view-data_download' % self.instructor_dashboard_url
        ret = self.ses.get(url)
        csrf = self.ses.cookies['csrftoken']
        return csrf

    def do_instructor_dashboard_action(self, url, data=None):
        if not self.xblock_csrf:
            self.xblock_csrf = self.get_instructor_dashboard_csrf()
            self.headers['X-CSRFToken'] = self.xblock_csrf
            if self.verbose:
                print "Got csrf=%s from instructor dashboard" % self.xblock_csrf
        data = data or {}
        ret = self.ses.post(url, data=data, headers=self.headers)
        if not ret.status_code==200:
            ret = self.ses.get(url, params=data, headers=self.headers)
        if self.verbose:
            print "[edxapi] do_instructor_dashboard_action url=%s, return=%s" % (url, ret)
        return ret

    def list_reports_for_download(self):
        '''
        List reports available for download from instructor dashboard
        '''
        # url = "%s/#view-data_download" % self.instructor_dashboard_url
        url = "%s/api/list_report_downloads" % (self.instructor_dashboard_url)
        ret = self.do_instructor_dashboard_action(url)
        try:
            data = ret.json()
        except Exception as err:
            return ret
        return data

    def list_instructor_tasks(self):
        '''
        List instructor tasks
        '''
        url = "%s/api/list_instructor_tasks" % (self.instructor_dashboard_url)
        ret = self.do_instructor_dashboard_action(url)
        try:
            data = ret.json()
        except Exception as err:
            return ret
        return data


    def make_grade_report_request( self, course_id ):
        '''
        Make Current Grade report Request
        '''
        self.set_course_id( course_id )
        url = "%s/api/calculate_grades_csv" % (self.instructor_dashboard_url)
        print "[edXapi] url=%s" % url
        ret = self.do_instructor_dashboard_action(url)
        try:
            data = ret.json()
        except Exception as err:
            return ret
        return data

    def get_grade_reports(self, course_id, outputdir):
        '''
        Get Grade reports list
        '''
        self.set_course_id( course_id )
        downloads = self.list_reports_for_download()['downloads']
        cnt = 0
        grade_reports_dict = {}

        import re
        regexp = '(.*)_grade_report_(.*).csv'

        for dinfo in downloads:
            cnt += 1
            name = dinfo['name']
            parsefn = re.compile( regexp ) 
            m = re.search( parsefn, name )
            if m:
                grade_reports_dict[ name ] = dinfo
                url = dinfo['url']
                ret = self.ses.get(url)
        return grade_reports_dict

    def get_latest_grade_report( self, grade_report_dict, fname, outputdir ):

        gr_dict = {}
        for grade_report_fn in grade_report_dict:
            course_id, date_string = self.parse_grade_report_filename( grade_report_fn )
            gr_dict[ date_string ] = grade_report_fn
    
        # Write out latest report
        latest_file = gr_dict[ max(gr_dict.keys()) ]
        ofn = '%s/%s' % (outputdir, 'temp.csv')
        ofn2 = '%s/%s' % (outputdir, fname )

        # Download 
        url = grade_report_dict[ latest_file ]['url']
        ret = self.ses.get(url)
        print "[edXapi] writing original file"
        with open(ofn, 'w') as ofp:
            ofp.write( ret.text.encode('utf-8') )

        print '[edXapi] adding course_id %s and date string %s...' % (course_id, date_string)
        with open(ofn, 'r') as ofp:
            cnt = 0
            with open(ofn2, 'w') as ofp2:
                for line in ofp:
                    if cnt > 0:
                        newline = course_id + str(',') + date_string + str(',') + line.decode('utf-8')
                        ofp2.write( newline.encode('utf-8') )
                    else:
                        newline = str('course_id,Grade_timestamp,') + line.decode('utf-8')
                        ofp2.write( newline.encode('utf-8') )
                    cnt = cnt + 1

        print "[edXapi] Latest file is %s (%d bytes)" % (latest_file, len(ret.text))
        print "[edXapi] Created file %s in %s" % (ofn2, outputdir)
        os.system('rm -rf %s' % ofn)

        return latest_file

    def parse_grade_report_filename( self, filename ):
        '''
        Parse grade report filename to extract course name and time
        Ex: <course_id>_grade_report_<YYYY-MM-DD-HHMM>.csv
        Return course id and date as strings
        '''
        import re
        regexp = '(.*)_grade_report_(\d{4}-\d{2}-\d{2}).*.csv'
        parsefn = re.compile( regexp ) 
        m = re.search( parsefn, filename )
        if m:
            string_course_id = m.group(1)
            string_date = m.group(2)
    
        return self.parse_string_course_id( string_course_id ), string_date

    def parse_string_course_id( self, string_course_id ):
        '''
        Make transparent course id from grade report filename
        Return transparent course id (e.g.: HarvardX/code/term)
        '''
        # Find all character positions for occurence of _
        c = '_'
        list_pos = [pos for pos, char in enumerate(string_course_id) if char == c]

        # Org value
        org = string_course_id[:list_pos[:1][0]]
    
        # Shortname
        shortname = string_course_id[(list_pos[:1][0]+1):list_pos[-1:][0]]
    
        # Term value
        term = string_course_id[(list_pos[-1:][0]+1):]
    
        course_id = org + str('/') + shortname + str('/') + term
        return course_id

    def download_student_state_reports(self):
        '''
        Download all the student state reports available.
        These are reports with names of the form "<course_id>_student_state_from_<module_id>_<datetime>.csv"
        '''
        downloads = self.list_reports_for_download()['downloads']
        cnt = 0
        for dinfo in downloads:
            cnt += 1
            name = dinfo['name']
            if '_student_state_from_' in name:
                url = dinfo['url']
                ret = self.ses.get(url)
                ofn = 'DATA/%s' % name
                with open(ofn, 'w') as ofp:
                    ofp.write(ret.text)
                print "[%d] Retrieved %s (%d bytes)" % (cnt, ofn, len(ret.text))
                sys.stdout.flush()

    def enqueue_request_for_problem_responses(self, module_id):
        '''
        Submit queued request for problem responses
        '''
        url = "%s/api/get_problem_responses" % (self.instructor_dashboard_url)
        data = {'problem_location': module_id}
        ret = self.do_instructor_dashboard_action(url, data)
        try:
            data = ret.json()
        except Exception as err:
            return ret
        return data

    def do_reset_student_attempts(self, url_name, username=None):
        '''
        Reset student attempts
        '''
        username = username or self.username
        block_id = self.problem_block_id(url_name)
        url = "%s/api/reset_student_attempts" % (self.instructor_dashboard_url)
        data = {'problem_to_reset': block_id,
                'unique_student_identifier': username,
                'delete_module': False,
            }
        ret = self.do_instructor_dashboard_action(url, data)
        if not ret.status_code==200:
            data = {'failed': ret, 'url': url, 'params': data}
            return data
        try:
            data = ret.json()
        except Exception as err:
            data = {'failed': ret, 'url': url, 'params': data}
        return data

    def signup_staff(self, username, role='staff'):
        url = "%s/api/modify_access" % (self.instructor_dashboard_url)
        params = {'unique_student_identifier': username,
                  'rolename': role,
                  'action': 'allow',
              }
        r1 = self.do_instructor_dashboard_action(url, params)
        if self.verbose:
            print "[edXapi] instructor dashboard return = ", r1.status_code
    
    def update_forum_role_membership(self, username, role='Administrator'):
        url = "%s/api/update_forum_role_membership" % (self.instructor_dashboard_url)
        params = {'unique_student_identifier': username,
                  'rolename': role,
                  'action': 'allow',
              }
        r1 = self.do_instructor_dashboard_action(url, params)
        if self.verbose:
            print "[edXapi] instructor dashboard return = ", r1.status_code

    def delete_student_state(self, username, blocks=None):
        '''
        Delete student state for a specific xblock.  Give blocks as a list of block id's, e.g.
            blocks = ["block-v1:MITx+8.123x+3T2015+type@problem+block@EX1_Probability"]

        '''
        if not blocks:
            raise Exception("[edXapi] delete_student_state: must specify blocks to be deleted")

        self.headers['Referer'] = self.instructor_dashboard_url

        for bid in blocks:
            url = "%s/api/reset_student_attempts" % self.instructor_dashboard_url
            params = {'unique_student_identifier': username,
                      'problem_to_reset': bid,
                      'delete_module': True,
            }
            r2 = self.do_instructor_dashboard_action(url, params)
            if not r2.status_code==200:
                print "[edXapi] Failed to delete student %s state for block %s" % (username, block)
                print "="*60
                print "ERROR!"
                print r2.status_code
                print r2.request.headers
                if self.verbose:
                    print r2.text
            
#-----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def eapi():
    course_id = "course-v1:edX+DemoX+Demo_Course"
    ea = edXapi("http://192.168.33.10", "staff@example.com", "edx", course_id)
    return ea

def test_xb0(eapi):
    ea = eapi
    url_name = "75f9562c77bc4858b61f907bb810d974"
    data = ea.do_xblock_show_answer(url_name)
    print data
    assert ('progress_changed' in data)
    assert (len(data['answers']))

def test_xb1(eapi):
    ea = eapi
    url_name = "75f9562c77bc4858b61f907bb810d974"
    responses = ['3.141', "4500", "5"]
    ret = ea.do_xblock_check_problem(url_name, responses)
    assert(ret['success']=="correct")

def test_xb2(eapi):
    ea = eapi
    url_name = "75f9562c77bc4858b61f907bb810d974"
    responses = ['43.141', "4500", "5"]
    ret = ea.do_xblock_check_problem(url_name, responses)
    assert(ret['success']=="incorrect")

def test_xb3(eapi):
    ea = eapi
    url_name = "75f9562c77bc4858b61f907bb810d974"
    data = ea.do_xblock_get_problem(url_name)
    print data
    assert (len(data['html']))

#-----------------------------------------------------------------------------

class VAction(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        curval = getattr(args, self.dest, 0) or 0
        values=values.count('v')+1
        setattr(args, self.dest, values + curval)

#-----------------------------------------------------------------------------

def CommandLine(args=None, arglist=None):
    '''
    edxapi command line.  Accepts args, to allow for simple unit testing.
    '''
    help_text = """usage: %prog [command] [args...] ...

Commands:

list_reports               - list reports available for download in the instructor dashboard
get_problem_responses      - enqueue request for problem responses; specify module_id (as block_id)
                             or use --module-id-from-csv 
download_student_state     - download problem response (aka student state) reports which are avaialble

"""
    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument("cmd", help="command)")
    parser.add_argument("ifn", nargs='*', help="Input files")
    parser.add_argument('-v', "--verbose", nargs=0, help="increase output verbosity (add more -v to increase versbosity)", action=VAction, dest='verbose')
    parser.add_argument("-s", "--site-base-url", type=str, help="base url for course site, e.g. http://192.168.33.10", default=None)
    parser.add_argument("-u", "--username", type=str, help="username for course site access", default=None)
    parser.add_argument("-p", "--password", type=str, help="password for course site access", default=None)
    parser.add_argument("-c", "--course_id", type=str, help="course_id, e.g. course-v1:edX+DemoX+Demo_Course", default=None)
    parser.add_argument("--module-id-from-csv", type=str, help="provide name of CSV file from which to get module_id", default=None)
    
    if not args:
        args = parser.parse_args(arglist)
    
    ea = edXapi(base=args.site_base_url, username=args.username, password=args.password,
                course_id=args.course_id, verbose=args.verbose)

    if args.module_id_from_csv:
        import csv
        args.ifn = args.ifn or []
        mids = []
        for k in csv.DictReader(open(args.module_id_from_csv)):
            mids.append(k['ModuleID'])
        mids = list(set(mids))
        print "Found %d module ID's in csv file %s" % (len(mids), args.module_id_from_csv)
        args.ifn += mids

    if args.cmd=="list_reports":
        ret = ea.list_reports_for_download()
        names = [x['name'] for x in ret['downloads']]
        print json.dumps(names, indent=4)

    elif args.cmd=="download_student_state":
        ea.download_student_state_reports()

    elif args.cmd=="get_problem_responses":
        module_ids = args.ifn
        for mid in module_ids:
            ret = ea.enqueue_request_for_problem_responses(mid)
            print "%s -> %s" % (mid, ret)

    else:
        print ("Unknown command %s" % args.cmd)

#-----------------------------------------------------------------------------

if __name__=="__main__":
    CommandLine()
