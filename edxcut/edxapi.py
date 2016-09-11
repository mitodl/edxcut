'''
API interface to edx platform site.  
Handles logins, and performs queries.
'''

import os, sys
import time
import requests
import pytest

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
            raise Exception("[edXapi] get_xblock_json_response failed to get JSON format reponse for handler %s url_name %s, err %s, ret text=%s" % (handler,
                                                                                                                                                     url_name,
                                                                                                                                                     err,
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

    def make_response_dict(self, url_name, responses, prefix="input", box_indexes=None):
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
        x_index_offset = 2
        y_index_offset = 1
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

    def do_reset_student_attempts(self, url_name, username):
        '''
        Reset student attempts
        '''
        block_id = self.problem_block_id(url_name)
        url = "%s/api/reset_student_attempts" % (self.instructor_dashboard_url)
        data = {'problem_to_reset': block_id,
                'unique_student_identifier': username,
                'delete_module': False,
            }
        ret = self.ses.get(url, params=data, headers=self.headers)
        if self.verbose:
            print "[edxapi] do_reset_student_attempts return=%s" % ret
        try:
            data = ret.json()
        except Exception as err:
            data = {'failed': ret}
        return data

    def signup_staff(self, username, role='staff'):
        url = "%s/api/modify_access" % (self.instructor_dashboard_url)
        params = {'unique_student_identifier': username,
                  'rolename': role,
                  'action': 'allow',
              }
        r1 = self.ses.get(url, params=params, headers=self.headers)
        if self.verbose:
            print "[edXapi] instructor dashboard return = ", r1.status_code
    
    def update_forum_role_membership(self, username, role='Administrator'):
        url = "%s/api/update_forum_role_membership" % (self.instructor_dashboard_url)
        params = {'unique_student_identifier': username,
                  'rolename': role,
                  'action': 'allow',
              }
        r1 = self.ses.get(url, params=params, headers=self.headers)
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
            r2 = self.ses.get(url, params={'unique_student_identifier': username,
                                           'problem_to_reset': bid,
                                           'delete_module': True,
                                       },
                              headers=self.headers
                          )
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
