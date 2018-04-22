'''
API interface to edx platform site.  
Handles logins, and performs queries.
'''

import os, sys
import re
import time
import requests
import pytest
import json
import argparse
import traceback

from collections import OrderedDict
from StringIO import StringIO
from lxml import etree
from pysrt import SubRipTime, SubRipItem, SubRipFile

#-----------------------------------------------------------------------------
# edX platform site API

class edXapi(object):
    '''
    API interface to edx platform site.  
    Handles logins, and performs queries.
    '''
    def __init__(self, base=None, username='', password='',
                 course_id=None, data_dir="DATA", verbose=False, studio=False,
                 auth=None):
        '''
        Initialize API interface to edx platform site (either LMS or CMS Studio).

        base = (string) base URL for the edX site being accessed, e.g. for a local vagrant dev box,
               use http://192.168.33.10 (LMS) or http://192.168.33.10:18010 (CMS Studio)
        username = username for user with instructor-level access
        password = password for user with instructor-level access
        course_id = (string) fully-formed opaque (course-v1) or slash separated course id, as appropriate
        data_dir = (string) path of directory where data should be stored (for data retrieval actions)
        verbose = (bool) output verbosity level
        studio = (bool) True if edX CMS studio site is being accessed (False for edX LMS site)
        auth = (tuple of strings) if provided, added to the requests session for HTTP basic auth

        '''
        self.ses = requests.Session()
        self.ses.verify = False
        if auth:
            self.ses.auth = auth
        self.is_studio = studio
        self.login_ok = False
        self.BASE = base or ("https://studio.edx.org" if studio else "https://courses.edx.org")
        self.content_stages = ["chapter", "sequential", "vertical"]
        self.verbose = verbose
        self.course_id = course_id
        self.username = username
        self.data_dir = data_dir
        self.xblock_csrf = None
        self.debug = False
        self.login(username, password)

    def login(self, username, pw):
        url = '%s/%s' % (self.BASE, "signin" if self.is_studio else "login")
        try:
            r1 = self.ses.get(url)
        except Exception as err:
            traceback.print_exc()
            raise Exception("[edxapi] failed to get login page %s, err=%s" % (url, err))

        self.csrf = None
        if not 'csrftoken' in self.ses.cookies:
            m = re.search('name="csrfmiddlewaretoken" value="([^"]+)"', r1.content)
            if 0 and m:
                self.csrf = m.group(1)
                print("[edXapi.login] using %s for csrf" % self.csrf)
            else:
                print "[edXapi.login] login issue - url=%s, page: %s" % (url, r1.content)
                raise Exception("[edXapi.login] error - no csrf token in login page")
        self.csrf = self.csrf or self.ses.cookies['csrftoken']
        url2 = '%s/%s' % (self.BASE, "login_post" if self.is_studio else "user_api/v1/account/login_session/")
        headers = {'X-CSRFToken': self.csrf,
                   'Referer': '%s/login' % self.BASE}
        r2 = self.ses.post(url2, data={'email': username, 'password': pw}, headers=headers)
        self.headers = headers

        if self.verbose and not r2.status_code==200:
            print "[edXapi] login ret = ", r2
        if not r2.status_code==200:
            print "[edXapi] Login failed!"
            print r2.text
            return False

        if self.is_studio:
            try:
                status = r2.json()
            except Exception as err:
                status = {}
            if not status.get('success'):
                raise Exception("[edXapi] Login failed! ret=%s" % r2.status_code)

        if self.debug:
            print "login ret=%s, %s" % (r2.status_code, r2.text)
        self.login_ok = True
        return True

    def set_course_id( self, course_id ):
        self.course_id = course_id
    
    def ensure_data_dir_exists(self):
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)

    def ensure_studio_site(self):
        if not self.is_studio:
            raise Exception("[edXapi] Must be initialized with studio=True for access to Studio functions")
        self.csrf = self.ses.cookies['csrftoken']
        self.headers = {'X-CSRFToken': self.csrf}
            
    def create_block_key(self, category, url_name):
        '''
        Create an edX standard xmodule block key with given type category and for the specified url_name
        '''
        if not self.course_id:
            raise Exception("[edxapi] a course_id must be specified for this operation")
        cid = self.course_id.split(':', 1)[-1]
        return "block-v1:%s+type@%s+block@%s" % (cid, category, url_name)

    #-----------------------------------------------------------------------------
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

    #-----------------------------------------------------------------------------
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
        self.headers['Referer'] = url
        ret = self.ses.post(url, data=data, headers=self.headers)
        if not ret.status_code==200:
            ret = self.ses.get(url, params=data, headers=self.headers)
        if self.verbose:
            print "[edxapi] do_instructor_dashboard_action url=%s, return=%s" % (url, ret)
        return ret

    def get_basic_course_info(self):
        '''
        Get basic course info (start date, end date, ...) from instructor dashboard
        '''
        url = "%s#view-course_info" % self.instructor_dashboard_url
        ret = self.ses.get(url)
        # print ret.content
        parser = etree.HTMLParser()
        xml = etree.parse(StringIO(ret.content), parser).getroot()
        bci_div = xml.find('.//div[@class="basic-wrapper"]')
        if bci_div is None:
            return None
        fields = ["course-organization", "course-number", "course-name", "course-display-name", "course-start-date",
                  "course-end-date", "course-started", "course-num-sections", "grade-cutoffs"]
        # look for elements like: <li class="field text is-not-editable" id="field-grade-cutoffs">
        data = {}
        for field in fields:
            felem = bci_div.find('.//li[@id="field-%s"]' % field)
            if felem is None:
                data[field] = None
            else:
                belem = felem.find('b')
                data[field] = belem.text
        if self.verbose:
            print json.dumps(data, indent=4)
        return data
        

    def list_reports_for_download(self):
        '''
        List reports available for download from instructor dashboard
        '''
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

    def download_student_state_reports(self, module_ids=None, date_filter=None):
        '''
        Download all the student state reports available.
        These are reports with names of the form "<course_id>_student_state_from_<module_id>_<datetime>.csv"

        Limit to date in date_filter if specified.
        Limit to module_ids if specified.
        '''
        all_downloads = self.list_reports_for_download()['downloads']

        downloads = []

        for dlinfo in all_downloads:
            name = dlinfo['name']
            if '_student_state_from_' not in name:
                continue
            m = re.search('student_state_from_(block-v1_.*\+block@.*)_([0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-[0-9]+).csv', name)
            if not m:
                print "[edxapi] download: Warning - unknown filename format %s" % name
                continue
            dlinfo['module_id'] = m.group(1).replace("block-v1_", "block-v1:")
            dlinfo['date'] = m.group(2)
            downloads.append(dlinfo)

        if date_filter:
            downloads = [x for x in downloads if re.search(date_filter, x['date'])]

        if self.verbose:
            print "Looking for:\n", json.dumps(module_ids, indent=4)

        if module_ids:
            downloads = [x for x in downloads if x['module_id'] in module_ids]

        found_mids = [x['module_id'] for x in downloads]
        if self.verbose:
            print "Downloading:\n", json.dumps(found_mids, indent=4)

        missing_mids = [x for x in module_ids if not x in found_mids]
        if self.verbose:
            print "Missing:\n", json.dumps(missing_mids, indent=4)

        cnt = 0
        for dinfo in downloads:
            cnt += 1
            name = dinfo['name']
            if '_student_state_from_' in name:
                url = dinfo['url']
                ret = self.ses.get(url)
                ofn = '%s/%s' % (self.data_dir, name)
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
        while True:
            ret = self.do_instructor_dashboard_action(url, data)
            try:
                data = ret.json()
            except Exception as err:
                return ret
            if "A problem responses report generation task is already in progress." in data.get('status', ''):
                print data['status']
                time.sleep(5)
                continue
            if 'The problem responses report is being created' in data.get('status', ''):
                break
            if self.verbose:
                print "Status: %s" % data.get('status', None)
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
    # Studio actions: import and export course, list courses

    def list_courses(self):
        '''
        List courses available in Studio site
        '''
        self.ensure_studio_site()
        url = "%s/home/" % self.BASE
        ret = self.ses.get(url)
        parser = etree.HTMLParser()
        xml = etree.parse(StringIO(ret.content), parser).getroot()
        courses = []
        course_ids = []
        for course in xml.findall('.//li[@class="course-item"]'):
            cid = course.get("data-course-key")
            if self.verbose:
                print cid  # etree.tostring(course)
            courses.append(course)
            course_ids.append(cid)
        return {'xml': courses,
                'course_ids': course_ids,
                }

    def create_course(self, display_name, org, number, run, nofail=False):
        '''
        Create course (via Studio API)
        '''
        self.ensure_studio_site()
        url = "%s/course/" % (self.BASE)
        self.headers['Accept'] = "application/json"
        data = {'display_name': display_name,
                'org': org,
                'number': number,
                'run': run,
        }
        self.headers['Referer'] = url
        ret = self.ses.post(url, headers=self.headers, json=data)
        if not ret.status_code==200:
            raise Exception("Failed to create course data=%s, ret=%s" % (json.dumps(data, indent=4), ret.status_code))
        rdat = ret.json()
        if (not nofail) and ('ErrMsg' in rdat):
            raise Exception("Failed to create course data=%s, ErrMsg=%s, ret=%s" % (json.dumps(data, indent=4), rdat['ErrMsg'], rdat))
        return rdat

    def delete_course(self, course_key):
        '''
        Delete course (via Studio API)
        '''
        self.ensure_studio_site()
        url = "%s/course/%s" % (self.BASE, course_key)
        self.headers['Accept'] = "application/json"
        ret = self.ses.delete(url, headers=self.headers)
        if not ret.status_code==200:
            raise Exception("Failed to delete course %s, ret=%s" % (course_key, ret.status_code))
        data = ret.json()
        return data

    def download_course_tarball(self):
        '''
        Download tar.gz of full course content (via Studio)
        '''
        self.ensure_studio_site()
        if self.verbose:
            print "Downloading tar.gz for %s" % (self.course_id)
    
        url = '%s/export/%s?_accept=application/x-tgz' % (self.BASE, self.course_id)
        r3 = self.ses.get(url)

        if not r3.ok or (r3.status_code==404):
            url = '%s/export/slashes:%s+%s?_accept=application/x-tgz' % (self.BASE, self.course_id.replace('/','+'), sem)
            r3 = self.ses.get(url)

        dt = time.ctime(time.time()).replace(' ','_').replace(':','')
        ofn = '%s/COURSE-%s___%s.tar.gz' % (self.data_dir, self.course_id.replace('/','__'), dt)
        self.ensure_data_dir_exists()
        with open(ofn, 'w') as fp:
            fp.write(r3.content)
        print "--> %s" % (ofn)
        return ofn
    
    def upload_course_tarball(self, tfn, nwait=20):
        '''
        Upload tar.gz file of course content (to Studio site)
        '''
        self.ensure_studio_site()
        if self.verbose:
            print "Uploading %s for %s" % (tfn, self.course_id)
    
        tfnbn = os.path.basename(tfn)
        url = '%s/import/%s' % (self.BASE, self.course_id)
    
        files = {'course-data': (tfnbn, open(tfn, 'rb'), 'application/x-gzip')}
        csrf = self.ses.cookies['csrftoken']
        if self.verbose:
            # print "csrf=%s" % csrf
            print url
        headers = {'X-CSRFToken':csrf,
                   'Referer': url,
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
               }

        try:
            r3 = self.ses.post(url, files=files, headers=headers)
        except Exception as err:
            print "Error %s" % str(err)
            print "url=%s, files=%s, headers=%s" % (url, files, headers)
            sys.stdout.flush()
            sys.exit(-1)
    
        url = '%s/import_status/%s/%s' % (self.BASE, self.course_id, tfnbn.replace('/','-'))

        if self.verbose:
            # print "r3 = ", r3.status_code
            print "--> %s" % (r3.content)
            print url
    
        for k in range(nwait):
            r4 = self.ses.get(url)
            if r4.ok:
                if self.verbose:
                    print r4.content
                if r4.json()["ImportStatus"]==4:
                    if self.verbose:
                        print "Done!"
                    return True
            else:
                if self.verbose:
                    print r4
                    sys.stdout.flush()
            time.sleep(2)
        return False

    def get_outline(self, usage_key=None):
        '''
        Get outline for an edX course block (via Studio).  Defaults to the entire course, 
        if the usage_key is unspecified.

        Returns data like:
        {
            "has_explicit_staff_lock": false, 
            "graded": false, 
            "explanatory_message": null, 
            "actions": {
                "draggable": true, 
                "childAddable": true, 
                "deletable": true
            }, 
            "id": "block-v1:edX+DemoX+Demo_Course+type@course+block@course", 
            "category": "course", 
            "published_on": "Jun 17, 2017 at 20:09 UTC", 
            "display_name": "edX Demonstration Course", 
            "due": null, 
            "studio_url": "/course/course-v1:edX+DemoX+Demo_Course", 
            "start": "2013-02-05T05:00:00Z", 
            "edited_on": "Jun 17, 2017 at 20:09 UTC", 
            "has_changes": true, 
            "ancestor_has_staff_lock": false, 
            "course_graders": [
                "Homework", 
                "Exam"
            ], 
            "due_date": "", 
            "format": null, 
            "visibility_state": null, 
            "released_to_students": true, 
            "staff_only_message": false, 
            "group_access": {}, 
            "release_date": "Feb 05, 2013 at 05:00 UTC", 
            "user_partitions": [], 
            "child_info": {
                "category": "chapter", 
                "display_name": "Section", 
                "children": [
                    {
                     ...
                    },
                ]
            }, 
            "published": true
        }
        '''
        self.ensure_studio_site()
        usage_key = usage_key or self.create_block_key('course', 'course')
        url = "%s/xblock/outline/%s" % (self.BASE, usage_key)
        ret = self.ses.get(url, headers={'Accept': 'application/json'})
        if not ret.status_code==200:
            raise Exception("Failed to get outline for %s via %s, ret(%s)=%s" % (usage_key, url, ret.status_code, ret.content))
        data = ret.json()
        if self.verbose > 1:
            print "Outline for '%s' has %d children" % (usage_key, len(data['child_info']['children']))
        return data

    def get_outline_via_studio_home_page(self, usage_key=None):
        '''
        Get outline for an edX course (via Studio), via the Studio home page.
        '''
        self.ensure_studio_site()
        ret = self.ses.get("%s/course/%s" % (self.BASE, self.course_id))
        m = re.search('OutlineFactory\((.*), null\);\n', ret.content, flags=re.MULTILINE)
        # open('foo.html', 'w').write(ret.content)
        if not m:
            raise Exception("No chapter listing found")
        outline = json.loads(m.group(1))
        open('foo.json', 'w').write(json.dumps(outline, indent=4))
        return outline
            
    #-----------------------------------------------------------------------------
    # xblocks: chapter, sequential, vertical, units

    def _get_block_child_info_from_content_preview(self, block_id):
        '''
        Get child info dict from content preview
        '''
        xblock = self.get_xblock(usage_key=block_id, view="container_preview")
        html = xblock['html']
        parser = etree.HTMLParser()
        xml = etree.parse(StringIO(html), parser).getroot()
        ids =[]
        child_blocks = []
        for elem in xml.findall('.//li[@class="studio-xblock-wrapper is-draggable"]'):
            cid = elem.get('data-locator')
            ids.append(cid)
            child_blocks.append(self.get_xblock(usage_key=cid))
        child_info = {'children': child_blocks,
                      'child_ids': ids,
                      }
        return child_info

    def _get_block_by_name_from_outline(self, outline=None, block_name=None, block_category=None, path=None, nofail=False):
        '''
        Get block from children of current outline level, by name (falls back to url_name)

        Return dict with information about the block.  The returned block contains all its children.

        If path is provided, then start at the course, and iterate through names in path.

        If the block desired is below a vertical, then fall back to extract the block id from the container preview.
        edX studio should be extended to provide an API to list the contents of a vertical, but sadly
        it doesn't have that functionality available.

        nofail = (bool) True if no exception should be raised when block is not found (returns False in this case)
        '''
        if (not block_name) and path is not None:
            outline = self.get_outline()   # get outline for course
            cnt = 0
            for block_name in path:	# get chapter, sequential, vertical, in that order
                category = self.content_stages[cnt] if cnt < 3 else None	# no default category after vertical
                outline = self._get_block_by_name_from_outline(outline, block_name, category)
                cnt += 1
            return outline
        elif not outline:
            outline = self.get_outline()   # get outline for course
        the_block = None
        the_block_by_name = None
        if not 'child_info' in outline:
            if outline['category']=="vertical":
                outline['child_info'] = self._get_block_child_info_from_content_preview(outline['id'])
            else:
                if nofail:
                    return False
                raise Exception("[edXapi.get_block_by_name_from_outline] Missing child_info in outline %s" % outline)
        for block in outline['child_info']['children']:
            cid = block['id']
            if block_category:
                if not block['category']==block_category:
                    raise Exception("[edXapi.get_block_by_name_from_outline] expecting category=%s, got category=%s" % (block_category,
                                                                                                                        block['category']))
            url_name = cid.rsplit('@')[-1]
            if block_name==url_name:
                the_block = block
                break
            if block['display_name']==block_name and not the_block_by_name:
                the_block_by_name = block
        if not the_block:
            the_block = the_block_by_name
        if not the_block:
            if nofail:
                return False
            raise Exception("No %s block '%s' found" % (block_category, block_name))
        return the_block

    def get_chapter_by_name(self, chapter_name):
        '''
        Get chapter outline using the chapter name (falls back to chapter url_name).

        Return dict of the chapter's outline.
        '''
        course_outline = self.get_outline()
        return self._get_block_by_name_from_outline(course_outline, chapter_name, 'chapter')
            
    def get_sequential_by_name(self, chapter_name, seq_name):
        '''
        Get sequential outline using the chapter & sequential names (falls back to url_names).

        Return dict of the sequential's outline.
        '''
        the_chapter = self.get_chapter_by_name(chapter_name)
        return self._get_block_by_name_from_outline(the_chapter, seq_name, 'sequential')
            
    def get_vertical_by_name(self, chapter_name, seq_name, vert_name):
        '''
        Get vertical outline using the chapter, sequential, and vertical names (falls back to url_names).

        Return dict of the vertical's outline.
        '''
        the_sequential = self.get_sequential_by_name(chapter_name, seq_name)
        return self._get_block_by_name_from_outline(the_sequential, vert_name, 'vertical')

    def list_sequentials(self, chapter_name):
        '''
        List sequentials in a given chapter in an edX course (via Studio)

        chapter_name = (string) either the url_name (default) or display_name of a chapter
        '''
        the_chapter = self.get_chapter_by_name(chapter_name)
        return self.list_xblocks(the_chapter, 'chapter')

    def create_sequential(self, chapter_name, seq_name):
        '''
        Create a new sequantial of the specified name, in the specified chapter.

        chapter_name = (string) either the url_name (default) or display_name of a chapter
        seq_anme = (string) name of the new sequential to create
        '''
        the_chapter = self.get_chapter_by_name(chapter_name)
        return self.create_xblock(the_chapter['id'], "sequential", seq_name)

    def delete_sequential(self, chapter_name, seq_name):
        '''
        Delete the specified sequential, via Studio.
        '''
        the_sequential = self.get_sequential_by_name(chapter_name, seq_name)
        return self.delete_xblock(the_sequential['id'])
            
    def list_verticals(self, chapter_name, seq_name):
        '''
        List verticals in a given chapter, sequential
        '''
        return self.list_xblocks(path=[chapter_name, seq_name])
            
    def create_vertical(self, chapter_name, seq_name, vert_name):
        '''
        Create vertical in a given chapter, sequential
        '''
        the_sequential = self.get_sequential_by_name(chapter_name, seq_name)
        return self.create_xblock(the_sequential['id'], "vertical", vert_name)

    def delete_vertical(self, chapter_name, seq_name, vert_name):
        '''
        Delete the specified vertical, via Studio.
        '''
        the_vertical = self.get_vertical_by_name(chapter_name, seq_name, vert_name)
        return self.delete_xblock(the_vertical['id'])

    def list_chapters(self):
        '''
        List chapters in an edX course (via Studio)
        '''
        outline = self.get_outline()
	return self.list_xblocks(outline, 'course') # top-level is course

    def create_chapter(self, name):
        '''
        Create a new chapter in an edX course (via Studio)
        '''
        self.ensure_studio_site()
        block_key = self.create_block_key('course', 'course')
        return self.create_xblock(block_key, "chapter", name)

    def delete_chapter(self, name):
        '''
        Delete the specified chapter, via Studio.
        '''
        the_chapter = self.get_chapter_by_name(name)
        return self.delete_xblock(the_chapter['id'])

    def get_xblock(self, usage_key=None, path=None, view=None):
        '''
        Get the specified xblock, via Studio.

        If path is provided, then traverse that, and delete the last block specified in the path.

        path = (list) list of xblock url_names (falling back to display_names)

        If the path has only one item, and it begins with "block-v1:", then use that as an usage-key.
        '''
        if path and len(path)==1 and path[0].startswith("block-v1:"):
            usage_key = path[0]
            path = None
        if (not usage_key) and path is not None:
            if self.verbose:
                print "[edXapi.delete_xblock] traversing path=%s" % path
            the_block = self._get_block_by_name_from_outline(path=path)
            usage_key = the_block['id']
                
        url = '%s/xblock/%s' % (self.BASE, usage_key)
        if view:
            url = url + "/" + view
        self.headers['Accept'] = "application/json"
        ret = self.ses.get(url, headers=self.headers)
        if not ret.status_code in [200, 204]:
            raise Exception("Failed to get xblock %s, view=%s, ret=%s" % (usage_key, view, ret.status_code))
        return ret.json()

    def delete_xblock(self, usage_key=None, path=None):
        '''
        Delete the specified xblock, via Studio.

        If path is provided, then traverse that, and delete the last block specified in the path.

        path = (list) list of xblock url_names (falling back to display_names)

        If the path has only one item, and it begins with "block-v1:", then use that as an usage-key.
        '''
        if path and len(path)==1 and path[0].startswith("block-v1:"):
            usage_key = path[0]
            path = None

        if (not usage_key) and path is not None:
            if self.verbose:
                print "[edXapi.delete_xblock] traversing path=%s" % path
            the_block = self._get_block_by_name_from_outline(path=path)
            usage_key = the_block['id']
            if self.verbose:
                print "[edXapi.delete_xblock] deleting block id=%s" % usage_key
                
        url = '%s/xblock/%s' % (self.BASE, usage_key)
        ret = self.ses.delete(url, headers=self.headers)
        if not ret.status_code in [200, 204]:
            raise Exception("Failed to delete %s, ret=%s" % (usage_key, ret.status_code))
        if self.verbose:
            print "Deleted %s, ret=%s" % (usage_key, ret.status_code)
        return True

    def list_xblocks(self, outline=None, category=None, path=None):
        '''
        Return dict giving xblocks one-level down in the current outline.
        This dict has its children removed (in contrast to _get_block_by_name_from_outline).

        path = (list) if provided, first traverse this list of chapter, sequential, vertical names.
        '''
        if path and len(path)==1 and path[0].startswith("block-v1:"):
            usage_key = path[0]
            path = None
            outline = self.get_xblock(usage_key=usage_key)

        elif not outline:
            outline = self.get_outline()
            cnt = 0
            for name in path:
                outline = self._get_block_by_name_from_outline(outline, name, self.content_stages[cnt])
                cnt += 1
                if cnt > 3:
                    raise Exception("Too deep a path specified to list_xblocks: path=%s" % path)
        if category:
            assert outline['category']==category
        else:
            category = outline['category']
        blocks = []
        block_category = None
        if not 'child_info' in outline:
            if outline['category']=="vertical":
                outline['child_info'] = self._get_block_child_info_from_content_preview(outline['id'])
            else:
                raise Exception("[edXapi.list_xblocks] Missing child_info in outline %s" % json.dumps(outline, indent=4))
        for block in outline['child_info']['children']:
            if 'child_info' in block:
                block.pop('child_info')
            blocks.append(block)
            if not block_category:
                block_category = block['category']
        titles = [ x['display_name'] for x in blocks ]
        if self.verbose:
            print "Found %d %ss in %s %s" % (len(blocks), block_category, category, outline['display_name'])
            for block in blocks:
                print "    %s -> %s" % (block['display_name'], block['id'])
        return {'blocks': blocks, 'titles': titles}


    def create_xblock(self, parent_locator=None, category=None, name=None, usage_key=None, path=None, data=None):
        '''
        Create a new xblock (via the Studio api) with the specified name, located
        as a child of the specified parent, of category type specified.

        parent_locator = block key for the parent
        category = sequential, vertical, html, problem, video, ...
        name = display_name of new xblock
        usage_key = (sring) block key for a pre-existing xblock, if known
        path = (list) if provided, then a list of names for [chapter, sequential, vertical]. 
               traverse this list to find parent_locator.  If name is not provided, then use
               the last element of path as the name of the new block to create.
        data = (string) data string to store, e.g. html or problem content
        '''
        self.ensure_studio_site()
        if not parent_locator and path:
            if self.verbose:
                print "[edXapi.create_xblock] traversing path=%s" % path
            if not name:
                parent = self._get_block_by_name_from_outline(path=path[:-1])
                name = path[-1]
                if not category:
                    if len(path)-1 < 3 and len(path) > 0:
                        category = self.content_stages[len(path)-1]
                    else:
                        raise Exception("[edXapi.create_xblock] no category specified, cannot guess; path= %s" % path)
            else:
                parent = self._get_block_by_name_from_outline(path=path)
                if not category:
                    category = self.content_stages[len(path)]
            parent_locator = parent['id']

        post_data = {'parent_locator': parent_locator,
                     'category': category,
                     'display_name': name,
        }
        url = '%s/xblock/' % self.BASE
        self.headers['Referer'] = url
        if usage_key:
            url += usage_key
        ret = self.ses.post(url, json=post_data, headers=self.headers)
        if not ret.status_code==200:
            msg = "[edXapi] Failed to create new %s in course %s with post_data=%s" % (category, self.course_id, str(post_data)[:200])
            msg += "\nret=%s" % ret.content
            if 0:
                print "request: ", ret.request
                print "request history:", ret.history
                print "request url:", ret.request.url
                print dir(ret.request)
                print "request method: ", ret.request.method
                print "request headers: ", ret.request.headers
            raise Exception(msg)
        rdat = ret.json()
        if data:
            block_id = rdat['locator']
            return self.update_xblock(usage_key=block_id, data=data)
        if self.verbose:
            print "[edXapi.create_xblock] Created %s '%s'" % (category, name)
            # print "--> post data = %s" % json.dumps(post_data, indent=4)
        return rdat

    def update_xblock(self, usage_key=None, data=None, path=None, create=False, category=None, extra_data=None):
        '''
        Update an existing xblock, as specified by usage_key or path.
        
        usage_key = (string) block_id of xblock to update
        data = (string) html or other content of block to store as content
        path = (list of strings) list of url_name or display_name of chapter, sequential, vertical, block to update
        create = (bool) True if any block along the path should be created when missing
        category = (string) category of xblock to create, if create=True and not already existing
        extra_data = (dict) extra data (eg metadata) to add to xblock (eg for video metadata, and config parameters)

        If the path has only one item, and it begins with "block-v1:", then use that as an usage-key.
        '''
        self.ensure_studio_site()
        if path and len(path)==1 and path[0].startswith("block-v1:"):
            usage_key = path[0]
            path = None

        if not usage_key:
            if create:
                outline = self.get_outline()   # get outline for course
                cnt = 0
                for name in path:
                    block_category = self.content_stages[cnt] if cnt < 3 else category	# no default category after vertical
                    the_block = self._get_block_by_name_from_outline(outline=outline, block_name=name,
                                                                     block_category=block_category if cnt < 3 else None, 
                                                                     nofail=True)
                    if the_block==False:	# block was missing; create it
                        ret = self.create_xblock(parent_locator=outline['id'], category=block_category, name=name)
                        the_block_id = ret['locator']
                        the_block = self.get_xblock(usage_key=the_block_id)
                        if self.verbose:
                            print "[edXapi.update_xblock] created block '%s' = %s" % (name, the_block_id)
                    outline = the_block
                    cnt += 1
            else:
                the_block = self._get_block_by_name_from_outline(path=path)
            usage_key = the_block['id']
        else:
            self.ensure_studio_site()
        post_data = {'data': data,
                     'category': category,
                     'courseKey': self.course_id,
                     'id': usage_key,
        }
        post_data.update(extra_data or {})
        url = '%s/xblock/%s' % (self.BASE, usage_key)
        self.headers['Referer'] = url
        ret = self.ses.post(url, json=post_data, headers=self.headers)
        if not ret.status_code==200:
            print("[edXapi.update_xblock] Failure with post_data=%s, headers=%s" % (post_data, self.headers))
            raise Exception("[edXapi.update_xblock] Failed to update xblock %s, ret=%s" % (usage_key, ret.status_code))
        return ret.json()

    #-----------------------------------------------------------------------------
    # static assets

    def list_static_assets(self, name=None):
        '''
        List static assets in course, via edX studio REST interface

        Eage page has JSON like:
        
        {
            "sort": "uploadDate", 
            "end": 50, 
            "assets": [
                {
                    "display_name": "problems_F12_MRI_images_MRI23.png", 
                    "url": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@problems_F12_MRI_images_MRI23.png", 
                    "locked": false, 
                    "portable_url": "/static/problems_F12_MRI_images_MRI23.png", 
                    "thumbnail": null, 
                    "content_type": "", 
                    "date_added": "Jun 19, 2017 at 16:45 UTC", 
                    "id": "asset-v1:edX+DemoX+Demo_Course+type@asset+block@problems_F12_MRI_images_MRI23.png", 
                    "external_url": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@problems_F12_MRI_images_MRI23.png"
                }, 
                ...
            ], 
            "pageSize": 50, 
            "start": 0, 
            "totalCount": 1141, 
            "page": 0
        }

        name = (string) display_name to search for and return; if None, return full list of all assets

        '''
        self.ensure_studio_site()
        assets = []
        page = 0
        done = False
        while not done:
            data = {'format': 'json',
                    'page': page,
            }
            url = '%s/assets/%s/' % (self.BASE, self.course_id)        # http://192.168.33.10:18010/assets/course-v1:edX+DemoX+Demo_Course/
            self.headers['Accept'] = "application/json"
            ret = self.ses.get(url, params=data, headers=self.headers)
            if not ret.status_code==200:
                raise Exception('[edXapi.list_static_assets] Failed to get static asset loist, url=%s, err=%s' % (url, ret.status_code))
            retdat = ret.json()
            abyname = { x['display_name']: x for x in retdat['assets'] }
            if name:
                if name in abyname:
                    return abyname[name]
            assets += retdat['assets']
            done = len(assets) >= retdat['totalCount']
            page += 1
        if name:
            return None
        return assets

    def get_static_asset_info(self, fn, nofail=False):
        '''
        Get info about static asset from course, via edX studio REST interface
        
        nofail = (bool) if True, then don't raise exception when file info not found
        '''
        asset = self.list_static_assets(name=fn)
        if (not nofail) and (not asset):
            raise Exception("[edXapi.get_static_asset_info] No asset found with display_name='%s'" % fn)
        return asset

    def get_static_asset(self, fn, ofn=None, nofail=False):
        '''
        Get content of the named static asset, from the asset interface (not necessarily Studio), e.g.:

        http://192.168.33.10:18010/asset-v1:MITx+8.MReV+course+type@asset+block/problems_F12_MRI_images_MRI23.png
        '''
        normalized_url = fn.replace('/', '_')
        course_key = self.course_id.split(':', 1)[1]
        static_asset_url = "%s/asset-v1:%s+type@asset+block/%s" % (self.BASE, course_key, normalized_url)
        self.csrf = self.ses.cookies['csrftoken']
        self.headers = {'X-CSRFToken': self.csrf}
        ret = self.ses.get(static_asset_url, headers=self.headers)
        if not ret.status_code==200:
            if nofail:
                return None
            else:
                raise Exception("[edXapi.get_static_asset] Failed to retrieve static asset %s, url=%s, ret status=%s" % (fn,
                                                                                                                         static_asset_url,
                                                                                                                         ret.status_code))
        if ofn:
            open(ofn, 'w').write(ret.content)
        if self.verbose:
            print "[edXapi.get_static_asset] Retrieved %s, content-length=%s" % (fn, len(ret.content))
        return ret.content

    def upload_static_asset(self, fn):
        '''
        Upload static asset to course, via edX studio REST interface
        '''
        self.ensure_studio_site()
        files = {'file': open(fn,'rb')}
        data = {'format': 'json'}
        url = '%s/assets/%s/' % (self.BASE, self.course_id)        # http://192.168.33.10:18010/assets/course-v1:edX+DemoX+Demo_Course/
        self.headers['Accept'] = "application/json"
        self.headers['Referer'] = url
        ret = self.ses.post(url, files=files, data=data, headers=self.headers)
        if not ret.status_code==200:
            print('[edXapi.upload_static_asset] Failed, headers=%s, cookies=%s' % (self.headers, self.ses.cookies))
            raise Exception('[edXapi.upload_static_asset] Failed to upload %s, to url=%s, err=%s' % (fn, url, ret.status_code))
        if self.verbose:
            print "uploaded file %s, ret=%s" % (fn, json.dumps(ret.json(), indent=4))
        return ret.json()

    def delete_static_asset(self, asset_key=None, fn=None):
        '''
        Delete static asset from course, via edX studio REST interface
        
        asset_key = (string) "asset-v1:" asset key, if available (else constructed from fn)
        fn = display_name of asset to delete
        '''
        self.ensure_studio_site()
        if fn.startswith("asset-v1:"):
            asset_key = fn
            fn = None
        if not asset_key:
            normalized_url = fn.replace('/', '_')
            course_key = self.course_id.split(':', 1)[1]
            asset_key = "asset-v1:%s+type@asset+block@%s" % (course_key, normalized_url)
        if not fn:
            fn = asset_key.rsplit('/', 1)[-1]
        data = {'format': 'json'}
        url = '%s/assets/%s/%s' % (self.BASE, self.course_id, asset_key)
        self.headers['Accept'] = "application/json"
        ret = self.ses.delete(url, data=data, headers=self.headers)
        if not ret.status_code in [200, 204]:
            raise Exception('[edXapi.delete_static_asset] Failed to delete %s, using url=%s, err=%s' % (fn, url, ret.status_code))
        try:
            rj = ret.json()
        except Exception as err:
            if self.verbose:
                print "[edxapi] warning - cannot get JSON from server output %s" % ret.text
            rj = ret.text
        if self.verbose:
            print "deleted file %s, ret=%s" % (fn, json.dumps(rj, indent=4))
        if ret.status_code==204:
            return 
        return rj

    #-----------------------------------------------------------------------------
    # video transcripts

    def get_video_transcript(self, url_name, videoid=None, lang="en", output_srt=False):
        '''
        Get video transcript
        '''
        if url_name.startswith("block-v1:"):
            url_name = url_name.rsplit('+block@', 1)[-1]
        data = {'videoId': videoid}
        course_key = self.course_id.split(':', 1)[1]
        block_key = "block-v1:%s+type@video+block@%s" % (course_key, url_name)
        url = '%s/courses/%s/xblock/%s/handler/transcript/translation/%s' % (self.BASE,
                                                                             self.course_id,
                                                                             block_key,
                                                                             lang,
        )
        self.headers['Accept'] = "application/json"
        ret = self.ses.get(url, params=data, headers=self.headers)
        if not ret.status_code==200:
            raise Exception('[edXapi.get_video_transcript] Failed to retrieve transcript for %s, via url=%s, err=%s' % (url_name,
                                                                                                                        ret.request.url,
                                                                                                                        ret.status_code))
        rdat = ret.json()
        if output_srt:
            return self.generate_srt_from_sjson(rdat)
        return rdat	# srt.sjson format
        
    def upload_video_transcript(self, tfn, url_name, videoid, tfp=None):
        '''
        Upload transcript for specfied url_name and videoid.  The transcrpt file should
        be in srt format (not srt.sjson).

        tfn = (string) srt transcript filename
        url_name = (string) video module url_name
        videoid = (string) youtube video ID
        tfp = (File) if provided, use this instead of opening tfn
        '''
        self.ensure_studio_site()
        if url_name.startswith("block-v1:"):
            url_name = url_name.rsplit('+block@', 1)[-1]
        tfp = tfp or open(tfn,'r')
        files = {'transcript-file': tfp}

        course_key = self.course_id.split(':', 1)[1]
        block_key = "block-v1:%s+type@video+block@%s" % (course_key, url_name)
        video_list = [{'mode': 'youtube',
                       "video": videoid,
                       "type": "youtube",
        }]
        data = {'locator': block_key,
                'video_list': json.dumps(video_list),
        }
        url = '%s/transcripts/upload' % (self.BASE)	# http://192.168.33.10:18010/transcripts/upload
        self.headers['Accept'] = "application/json"
        self.headers['Referer'] = url
        ret = self.ses.post(url, files=files, data=data, headers=self.headers)
        if not ret.status_code==200:
            if self.verbose:
                print "[edXapi.upload_transcript] failed, data=%s" % json.dumps(data, indent=4)
            raise Exception('[edXapi.upload_transcript] Failed to upload %s, to url=%s, err=%s' % (tfn, url, ret.status_code))
        if self.verbose:
            print "uploaded transcript file %s, ret=%s" % (tfn, json.dumps(ret.json(), indent=4))
        return ret.json()

    @staticmethod
    def generate_srt_from_sjson(sjson_subs):
        """Generate transcripts with speed = 1.0 from sjson to SubRip (*.srt).
        Based on code from the Open edX platform.
    
        :param sjson_subs: "sjson" subs.
        :param speed: speed of `sjson_subs`.
        :returns: "srt" subs.
        """
    
        output = ''
    
        equal_len = len(sjson_subs['start']) == len(sjson_subs['end']) == len(sjson_subs['text'])
        if not equal_len:
            return output
    
        sjson_speed_1 = sjson_subs
    
        for i in range(len(sjson_speed_1['start'])):
            item = SubRipItem(
                index=i,
                start=SubRipTime(milliseconds=sjson_speed_1['start'][i]),
                end=SubRipTime(milliseconds=sjson_speed_1['end'][i]),
                text=sjson_speed_1['text'][i]
            )
            output += (unicode(item))
            output += '\n'
        return output

    

#-----------------------------------------------------------------------------
# unit tests for edXapi

@pytest.fixture(scope="module")
def eapi():
    course_id = "course-v1:edX+DemoX+Demo_Course"
    ea = edXapi("http://192.168.33.10:18000", "staff@example.com", "edx", course_id=course_id)
    return ea

@pytest.fixture(scope="module")
def eapi_studio():
    cid = "course-v1:edX+DemoX+Demo_Course"
    ea = edXapi("http://192.168.33.10:18010", "staff@example.com", "edx", studio=True, course_id=cid)
    return ea

def test_course_info(eapi):
    ea = eapi
    data = ea.get_basic_course_info()
    print json.dumps(data, indent=4)
    assert data["course-name"] == "Demo_Course"

def test_get_video_transcript(eapi):
    ea = eapi
    data = ea.get_video_transcript('636541acbae448d98ab484b028c9a7f6', videoid='o2pLltkrhGM')
    print json.dumps(data, indent=4)
    assert 'What we have is a voltmeter and an amp meter.' in data['text']
    srt = ea.generate_srt_from_sjson(data)
    assert '00:03:17,220 --> 00:03:20,480' in srt
    ofn = "/tmp/edxapi_tmp_transcript.srt"
    open(ofn, 'w').write(srt)

    eas = eapi_studio()
    ret = eas.upload_video_transcript(ofn, '636541acbae448d98ab484b028c9a7f6', videoid='o2pLltkrhGM')
    assert ret['status']=="Success"

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

def test_list_courses():
    ea = edXapi("http://192.168.33.10:18010", "staff@example.com", "edx", studio=True)
    data = ea.list_courses()
    print data['course_ids']
    assert ('course-v1:edX+DemoX+Demo_Course' in data['course_ids'])
    assert ('xml' in data)

def test_create_course(eapi_studio):
    ea = eapi_studio
    data = ea.create_course('a test course', 'UnivX', 'test101', 'Future2099', nofail=True)
    print data
    # assert 'course_key' in data
    data = ea.list_courses()
    print data['course_ids']
    ckey = 'course-v1:UnivX+test101+Future2099'
    assert ckey in data['course_ids']

    ea2 = edXapi("http://192.168.33.10:18010", "staff@example.com", "edx", studio=True, course_id=ckey)
    html = "<p>hello world</p>"
    ret = ea2.update_xblock(path=["test chapter", "test sequential", "test vertical", "test html"],
                           category="html",
                           data=html,
                           create=True,
    )
    assert ret['data']==html

    ret = ea.delete_course(ckey)
    print ret
    data = ea.list_courses()
    print data['course_ids']
    assert ckey not in data['course_ids']

def x_test_download_course():
    cid = "course-v1:edX+DemoX+Demo_Course"
    ea = edXapi("http://192.168.33.10:18010", "staff@example.com", "edx", studio=True, course_id=cid)
    ret = ea.download_course_tarball()
    print "returned %s" % ret
    assert (cid in ret)

def x_test_upload_course():
    import glob
    cid = "course-v1:edX+DemoX+Demo_Course"
    tfn = glob.glob("DATA/COURSE-course-v1:edX+DemoX+Demo_Course___*.tar.gz")[0]
    ea = edXapi("http://192.168.33.10:18010", "staff@example.com", "edx", studio=True, course_id=cid)
    ret = ea.upload_course_tarball(tfn)
    print "returned %s" % ret
    assert ret

def test_course_outline(eapi_studio):
    ea = eapi_studio
    data = ea.list_chapters()
    assert ('titles' in data)
    assert ('blocks' in data)
    assert ("Example Week 1: Getting Started" in data['titles'])

def test_list_xblocks1(eapi_studio):
    ea = eapi_studio
    data = ea.list_xblocks(path=["Example Week 2: Get Interactive"])
    assert ('titles' in data)
    assert ('blocks' in data)
    assert ("Homework - Labs and Demos" in data['titles'])
    assert (data['blocks'][0]['id']=="block-v1:edX+DemoX+Demo_Course+type@sequential+block@simulations")

def test_list_xblocks2(eapi_studio):
    ea = eapi_studio
    data = ea.list_xblocks(path=["Example Week 2: Get Interactive", "Homework - Labs and Demos", "Code Grader"])
    assert ('titles' in data)
    assert ('blocks' in data)
    assert ("Code Grader" in data['titles'])
    assert ("The edX system is capable of reviewing computer code" in data['blocks'][0]['data'])

def test_get_xblock1(eapi_studio):
    ea = eapi_studio
    data = ea.get_xblock(path=["Example Week 2: Get Interactive", "Homework - Labs and Demos", "Code Grader", "Code Grader"])
    assert ("The edX system is capable of reviewing computer code" in data['data'])
    assert (data['category']=="html")

def test_create_xblock1(eapi_studio):
    ea = eapi_studio
    ret = ea.create_xblock(path=["test chapter"])
    ret = ea.create_xblock(path=["test chapter", "test sequential"])
    ret = ea.create_xblock(path=["test chapter", "test sequential", "test vertical"])
    html = "<p>hello world</p>"
    ret = ea.create_xblock(path=["test chapter", "test sequential", "test vertical", "test html"],
                           data=html, category="html")
    assert ('data' in ret)
    assert ('metadata' in ret)
    assert (ret['metadata']['display_name']=="test html")
    ea.delete_xblock(path=["test chapter", "test sequential", "test vertical", "test html"])
    ea.delete_xblock(path=["test chapter", "test sequential", "test vertical"])
    ea.delete_xblock(path=["test chapter", "test sequential"])
    ea.delete_xblock(path=["test chapter"])

def test_update_xblock1(eapi_studio):
    ea = eapi_studio
    html = "<p>hello world</p>"
    ret = ea.update_xblock(path=["test chapter", "test sequential", "test vertical", "test html"],
                           category="html",
                           data=html,
                           create=True,
    )
    assert ret['data']==html
    data = ea.list_xblocks(path=["test chapter", "test sequential", "test vertical"])
    assert 'test html' in data['titles']
    ea.delete_xblock(path=['test chapter'])

def test_update_xblock2(eapi_studio):
    ea = eapi_studio
    html = ""
    edjs = '{"metadata": {"display_name": "Video name", "sub": "", "html5_sources": [], "youtube_id_1_0": "7bV04R-12uw"}}'
    ret = ea.update_xblock(path=["test chapter", "test sequential", "test vertical", "test video"],
                           category="video",
                           data=html,
                           create=True,
                           extra_data = json.loads(edjs),
    )
    assert ret['metadata']['youtube_id_1_0']=="7bV04R-12uw"
    data = ea.list_xblocks(path=["test chapter", "test sequential", "test vertical"])
    assert 'Video name' in data['titles']
    ea.delete_xblock(path=['test chapter'])

def test_list_assets(eapi_studio):
    ea = eapi_studio
    data = ea.list_static_assets()
    assert len(data) > 10
    dd = {x['display_name']: x for x in data}
    assert 'eDX.html' in dd
    assert 'url' in dd['eDX.html']

def test_upload_asset1(eapi_studio):
    ea = eapi_studio
    mdir = os.path.dirname(__file__)
    tfn = "%s/test_data/test_image.png" % mdir
    tfnb = os.path.basename(tfn)
    assert os.path.exists(tfn)
    ea.upload_static_asset(tfn)
    data = ea.get_static_asset_info(tfnb)
    assert data['display_name']==tfnb
    ea.delete_static_asset(fn=tfnb)
    data = ea.get_static_asset_info(tfnb, nofail=True)
    assert data is None

def test_get_sequentials(eapi_studio):
    ea = eapi_studio
    data = ea.list_sequentials("Example Week 1: Getting Started")
    assert ('titles' in data)
    assert ('blocks' in data)
    assert ("Homework - Question Styles" in data['titles'])

def test_create_chapter(eapi_studio):
    ea = eapi_studio
    name = "test chapter"
    try:
        ea.delete_chapter(name)
    except Exception as err:
        pass
    ret = ea.create_chapter(name)
    ret = ea.delete_chapter(name)
    the_err = ""
    try:
        ea.delete_chapter(name)
    except Exception as err:
        the_err = str(err)
    assert ("No chapter block '%s' found" % name) in the_err

def test_create_sequential(eapi_studio):
    ea = eapi_studio
    name = "test chapter"
    seq_name = "test sequential"
    try:
        ea.delete_chapter(name)
    except Exception as err:
        pass
    ret = ea.create_chapter(name)

    ret = ea.create_sequential(name, seq_name)
    ret = ea.delete_sequential(name, seq_name)
    the_err = ""
    try:
        ea.delete_sequential(name, seq_name)
    except Exception as err:
        the_err = str(err)
    assert ("No sequential block '%s' found" % seq_name) in the_err

    ret = ea.delete_chapter(name)

def test_verticals(eapi_studio):
    ea = eapi_studio
    ret = ea.list_verticals("Introduction", "Demo Course Overview")
    assert 'blocks' in ret
    assert 'Introduction: Video and Sequences' in ret['titles']

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
    help_text = """usage: edxcut edxapi [command] [args...] ...

Commands:

list_reports               - list reports available for download in the instructor dashboard
get_problem_responses      - enqueue request for problem responses; specify module_id (as block_id)
                             or use --module-id-from-csv 
download_student_state     - download problem response (aka student state) reports which are avaialble
get_course_info            - extract basic course info (eg start and end dates) from the instructor dashboard
download_course            - downlaod course tarball (from edX CMS studio site)
upload_course <tfn>        - upload the specified course .tar.gz file
list_courses               - list courses (in an edX CMS studio site), e.g.
                             edxcut edxapi --json-output -s http://192.168.33.10:18010 -u staff@example.com -p edx -S list_courses
get_outline <name>         - list xblocks in specified chapter
list_chapters              - list available chapters
create_chapter <name>      - create a new chapter of the specified name
delete_chapter <name>      - delete a chapter of the specified name
list_xblocks <path>        - list xblocks located at the specified path (<chapter> <sequential> <vertical>)
get_xblock <path>          - retrieve xblock (with xblock source data) at th specified path, e.g.
                             edxcut edxapi --create -d "<html>hello world2</html>" -t html --json-output -v \
                                    -s http://192.168.33.10:18010 -u staff@example.com -p edx -S \
                                    -c course-v1:edX+DemoX+Demo_Course get_xblock \
                                    "Example Week 2: Get Interactive" "Homework - Labs and Demos" "Code Grader" "Code Grader"
create_xblock <path>       - create xblock specified by path, with type -t, and data -d, e.g.
                             edxcut edxapi -d "<html>hello world2</html>" -t html --json-output -v \
                                    -s http://192.168.33.10:18010 -u staff@example.com -p edx -S \
                                    -c course-v1:edX+DemoX+Demo_Course create_xblock testchapter testsection testvertical testhtml2 
delete_xblock <path>       - delete xblock specified by path, e.g.
                             edxcut edxapi --json-output -v -s http://192.168.33.10:18010 -u staff@example.com -p edx \
                                    -S -c course-v1:edX+DemoX+Demo_Course delete_xblock testchapter testsection testvertical testhtml2
update_xblock <path>       - update (and optionally create all needed) xblock at a specified path, e.g.
                             edxcut edxapi --create -d "<html>hello world2</html>" -t html --json-output -v \
                                    -s http://192.168.33.10:18010 -u staff@example.com -p edx -S \
                                    -c course-v1:edX+DemoX+Demo_Course update_xblock testchapter testsection testvertical testhtml2
get_video_transcript <id>  - get transcript srt.sjson data for a given url_name (id), e.g.:
                             edxcut edxapi -v -j -s http://192.168.33.10 -u staff@example.com -p edx \
                                    -c course-v1:edX+DemoX+Demo_Course \
                                    get_video_transcript 636541acbae448d98ab484b028c9a7f6 --videoid o2pLltkrhGM
upload_transcript <fn> <id> - upload transcript file for a given url_name (id), and videoid, e.g.:
                              edxcut edxapi --json-output -v -s http://192.168.33.10:18010 -u staff@example.com -p edx -S \
                                     -c course-v1:edX+DemoX+Demo_Course \
                                     upload_transcript sample.srt 86c5f7e4e99a4b8a8d54364187493c43 --videoid 7bV04R-12uw
list_assets                 - list static assets in a given course
get_asset <fn>              - retrieve a single static asset file (for output specify -o output_filename)
get_asset_info <fn>         - retrieve metadata about single static asset file
upload_asset <fn>           - upload a single static asset file
delete_asset <fn | blockid> - delete a single static asset file (or specify usage key / block ID)

"""
    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument("cmd", help="command")
    parser.add_argument("ifn", nargs='*', help="Input files")
    parser.add_argument('-v', "--verbose", nargs=0, help="increase output verbosity (add more -v to increase versbosity)", action=VAction, dest='verbose')
    parser.add_argument("-s", "--site-base-url", type=str, help="base url for course site, e.g. http://192.168.33.10", default=None)
    parser.add_argument("-u", "--username", type=str, help="username for course site access", default=None)
    parser.add_argument("-p", "--password", type=str, help="password for course site access", default=None)
    parser.add_argument("-c", "--course_id", type=str, help="course_id, e.g. course-v1:edX+DemoX+Demo_Course", default=None)
    parser.add_argument("--module-id-from-csv", type=str, help="provide name of CSV file from which to get module_id values", default=None)
    parser.add_argument("-D", "--data-dir", type=str, help="directory where data is stored", default="DATA")
    parser.add_argument("-S", "--studio", help="specify that the edX site being accessed is a CMS studio sute", action="store_true")
    parser.add_argument("-j", "--json-output", help="Dump result (eg from get_block) as JSON to stdout", action="store_true")
    parser.add_argument("--json-output-html", help="Dump HTML portion of json result (eg from get_block) to stdout", action="store_true")
    parser.add_argument("-t", "--type", type=str, help="xblock content category type, used when creating new content xblock", default=None)
    parser.add_argument("--view", type=str, help="xblock view, used when getting xblock", default=None)
    parser.add_argument("-o", "--output-file-name", type=str, help="output file name to use, e.g. for get_asset", default=None)
    parser.add_argument("-d", "--data", type=str, help="data to store (eg for xblock, when using create_block)", default=None)
    parser.add_argument("--data-file", type=str, help="filename with data to store (eg for xblock, when using create_block)", default=None)
    parser.add_argument("--extra-data", type=str, help="JSON string with extra data to store (for update_block)", default=None)
    parser.add_argument("--videoid", type=str, help="videoid for get_video_transcript", default=None)
    parser.add_argument("--output-srt", help="have get_video_transcript output srt instead of srt.sjson", action="store_true")
    parser.add_argument("--create", help="for update_xblock, create if missing", action="store_true")
    parser.add_argument("--auth", help="http basic auth username,pw to use for OpenEdX site access", default=None)
    parser.add_argument("--date", type=str, help="date filter for selecting which files to download, in YYYY-MM-DD format", default=None)
    
    if not args:
        args = parser.parse_args(arglist)
    
    if args.auth:
        args.auth = tuple(args.auth.split(',', 1))

    try:
        ea = edXapi(base=args.site_base_url, username=args.username, password=args.password,
                    course_id=args.course_id, data_dir=args.data_dir, verbose=args.verbose,
                    studio=args.studio, auth=args.auth)
    except Exception as err:
        print err
        print "Error accessing OpenEdX site - if you're accessing Studio, did you specify the -S flag?"
        sys.exit(-1)

    ret = None
    if args.data_file:
        args.data = open(args.data.file).read()

    if not ea.login_ok:
        print "Error - login failed, aborting actions"
        sys.exit(-1)

    if args.module_id_from_csv:
        import csv
        args.ifn = args.ifn or []
        mids = []
        for k in csv.DictReader(open(args.module_id_from_csv)):
            mid = k['ModuleID']
            if mid:
                mids.append(mid)
        mids = list(set(mids))
        print "Found %d module ID's in csv file %s" % (len(mids), args.module_id_from_csv)
        args.ifn += mids

    if args.cmd=="list_reports":
        ret = ea.list_reports_for_download()
        names = [x['name'] for x in ret['downloads']]
        print json.dumps(names, indent=4)

    elif args.cmd=="download_student_state":
        ea.download_student_state_reports(module_ids=args.ifn, date_filter=args.date)

    elif args.cmd=="get_problem_responses":
        module_ids = args.ifn
        for mid in module_ids:
            ret = ea.enqueue_request_for_problem_responses(mid)
            print "%s -> %s" % (mid, ret)

    elif args.cmd=="get_course_info":
        ret = ea.get_basic_course_info()

    elif args.cmd=="download_course":
        ea.download_course_tarball()

    elif args.cmd=="upload_course":
        ea.upload_course_tarball(args.ifn[0])

    elif args.cmd=="list_courses":
        ret = ea.list_courses()['course_ids']

    elif args.cmd=="create_chapter":
        ea.create_chapter(args.ifn[0])

    elif args.cmd=="delete_chapter":
        ea.delete_chapter(args.ifn[0])

    elif args.cmd=="list_chapters":
        ret = ea.list_chapters()

    elif args.cmd=="get_outline":
        ea.get_outline(args.ifn[0])

    elif args.cmd=="list_sequentials":
        ea.list_sequentials(args.ifn[0])

    elif args.cmd=="create_sequential":
        ea.create_sequential(args.ifn[0], args.ifn[1])

    elif args.cmd=="delete_sequential":
        ea.delete_sequential(args.ifn[0], args.ifn[1])

    elif args.cmd=="list_verticals":
        ea.list_verticals(args.ifn[0], args.ifn[1])

    elif args.cmd=="create_vertical":
        ea.create_vertical(args.ifn[0], args.ifn[1], args.ifn[2])

    elif args.cmd=="delete_vertical":
        ea.delete_vertical(args.ifn[0], args.ifn[1], args.ifn[2])

    elif args.cmd=="list_xblocks":
        ret = ea.list_xblocks(path=args.ifn)

    elif args.cmd=="create_xblock":
        ret = ea.create_xblock(path=args.ifn, category=args.type, data=args.data)

    elif args.cmd=="update_xblock":
        if args.extra_data:
            try:
                args.extra_data = json.loads(args.extra_data)
            except Exception as err:
                print "Error!  Could not parse extra_data argument as JSON, extra_data=%s" % args.extra_data
                sys.exit(-1)
        ret = ea.update_xblock(path=args.ifn, category=args.type, data=args.data, create=args.create, extra_data=args.extra_data)

    elif args.cmd=="get_xblock":
        ret = ea.get_xblock(path=args.ifn, view=args.view)

    elif args.cmd=="delete_xblock":
        ret = ea.delete_xblock(path=args.ifn)

    elif args.cmd=="list_assets":
        ret = ea.list_static_assets()

    elif args.cmd=="get_asset_info":
        ret = ea.get_static_asset_info(fn=args.ifn[0])

    elif args.cmd=="get_asset":
        content = ea.get_static_asset(fn=args.ifn[0], ofn=args.output_file_name)

    elif args.cmd=="upload_asset":
        ret = ea.upload_static_asset(fn=args.ifn[0])

    elif args.cmd=="delete_asset":
        ret = ea.delete_static_asset(fn=args.ifn[0])

    elif args.cmd=="get_video_transcript":
        ret = ea.get_video_transcript(url_name=args.ifn[0], videoid=args.videoid, output_srt=args.output_srt)

    elif args.cmd=="upload_transcript":
        ret = ea.upload_video_transcript(tfn=args.ifn[0], url_name=args.ifn[1], videoid=args.videoid)

    elif args.cmd=="create_course":
        if 'args.course_id'.startswith('course-v1'):
            org, number, run = args.course_id.split('v1:', 1)[1].split('+')
        else:
            org, number, run = args.course_id.split('/')
        ret = ea.create_course(display_name=args.ifn[0], org=org, number=number, run=run)

    elif args.cmd=="delete_course":
        ret = ea.delete_course(args.course_id)

    else:
        print ("Unknown command %s" % args.cmd)

    if args.json_output_html:
        print ret['html']
    elif args.output_srt:
        print ret
    elif args.json_output and ret is not None:
        print json.dumps(ret, indent=4)

#-----------------------------------------------------------------------------

if __name__=="__main__":
    CommandLine()
