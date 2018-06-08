from edxapi import edXapi
from lxml import etree

class ccXapi(edXapi):
    '''
    API interface to CCX (custom course on edX) instance of an edX course.
    Interfaces to the CCX coach dashboard
    '''
    def __init__(self, **args):
        super(ccXapi, self).__init__(**args)
        self.ccx_instance_num = 1
        self.ccx_csrf = None
        if self.course_id.startswith("course-v1:"):
            self.ccx_id = "%s+ccx@%d" % (self.course_id.replace('course-v1:', 'ccx-v1:'), self.ccx_instance_num)
        else:
            self.ccx_id = self.course_id
        if not self.ccx_id.startswith("ccx-v1:"):
            raise Exception("[ccXapi] Badly formed ccx course_id! Expected start with ccx-v1:, got %s" % self.ccx_id)

    @property
    def ccx_dashboard_url(self):
        return '%s/courses/%s/ccx_coach' % (self.BASE, self.ccx_id)

    def get_ccx_dashboard_csrf(self):
        url = self.ccx_dashboard_url
        ret = self.ses.get(url)
        domain = self.BASE.rsplit("//", 1)[-1]
        csrf = self.ses.cookies.get('csrftoken', domain=domain)
        return csrf

    def do_ccx_dashboard_action(self, url, data=None):
        if not self.ccx_csrf:
            self.ccx_csrf = self.get_ccx_dashboard_csrf()
            self.headers['X-CSRFToken'] = self.ccx_csrf
            if self.verbose:
                print "Got csrf=%s from ccx coach dashboard" % self.ccx_csrf
        headers = {'X-CSRFToken': self.ccx_csrf,
                   'Referer': self.ccx_dashboard_url}
        data = data or {}
        self.headers['Referer'] = url
        ret = self.ses.post(url, data=data, headers=self.headers)
        if not ret.status_code==200:
            ret = self.ses.get(url, params=data, headers=self.headers)
        if self.verbose:
            print "[edxapi] do_ccx_dashboard_action url=%s, return=%s" % (url, ret)
        return ret

    def manage_ccx_student(self, action="add", email=None):
        '''
        Perform a CCX student management action
        '''
        # http://192.168.33.10/courses/ccx-v1:edX+DemoX+Demo_Course+ccx@1/ccx_manage_student
        if self.verbose:
            print("[ccXapi] enrolling %s" % email)
        url = "%s/courses/%s/ccx_manage_student" % (self.BASE, self.ccx_id)
        data = data={'csrfmiddlewaretoken': self.ccx_csrf,
                     'student-action': action}
        if email:
            data['student-id'] = email
        ret = self.do_ccx_dashboard_action(url, data)
        return ret.content

    def enroll_student(self, email):
        '''
        Enroll student in CCX
        '''
        return self.manage_ccx_student(action='add', email=email)

    def revoke_student(self, email):
        '''
        Revoke student from CCX
        '''
        return self.manage_ccx_student(action='revoke', email=email)
        
    def list_students(self):
        '''
        List students enrolled in CCX (provided by HTML in CCX coach dashboard - not a nice api)
        '''
        url = self.ccx_dashboard_url
        ret = self.ses.get(url, headers=self.headers)
        open("data.html", 'w').write(ret.content)

        parser = etree.HTMLParser()
        xml = etree.fromstring(ret.content, parser=parser)
        # <div class="member-list-widget">
        mlist = xml.find('.//div[@class="member-list-widget"]')
        data = []
        keys = None
        for entry in mlist.findall(".//tr"):
            row = [ td.text for td in entry.findall(".//td") ]
            if not keys and not row:
                row = [ td.text for td in entry.findall(".//th") ]
                keys = row
                continue
            data.append(dict(zip(keys, row)))
        if self.verbose:
            print json.dumps(data, indent=4)
        return data
    
