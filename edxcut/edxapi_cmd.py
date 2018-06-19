import sys
import json
import argparse

from edxapi import edXapi
from ccxapi import ccXapi

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
get_course_metadata        - get course metadata (JSON), e.g. start and end dates (from Studio)
update_course_metadata <d> - update course metadata, given new data (JSON format: alternatively use --data-file): via Studio
set_course_end_date <d>    - set course end date to that specified; date should be strings like "2016-01-07T14:00:00Z"
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
get_due_date <id>          - get due date for specified block ID (should be a sequential)
set_due_date <id> <date>   - set due date for specified block ID (should be a sequential); date should be like "2016-01-07T14:00:00Z"
set_all_due_dates <date>   - set all due dates for sequential blocks in course, to that specified
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

Commands for CCX course instances:

list_students               - list students enrolled in CCX instance
enroll_student <email>      - enroll student in CCX instance

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
    parser.add_argument("--ccx", help="Perform actions on a CCX course instance", action="store_true")
    
    if not args:
        args = parser.parse_args(arglist)
    
    if args.auth:
        args.auth = tuple(args.auth.split(',', 1))

    apimod = edXapi
    if args.ccx or args.course_id.startswith("ccx-v1:"):
        apimod = ccXapi			# enable additioanl CCX-specific commands for CCX course instances

    try:
        ea = apimod(base=args.site_base_url, username=args.username, password=args.password,
                    course_id=args.course_id, data_dir=args.data_dir, verbose=args.verbose,
                    studio=args.studio, auth=args.auth)
    except Exception as err:
        print err
        print "Error accessing OpenEdX site - if you're accessing Studio, did you specify the -S flag?"
        sys.exit(-1)

    ret = None
    if args.data_file:
        args.data = open(args.data_file).read()
        if args.verbose:
            print("Read data from %s" % args.data_file)

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
        if args.verbose:
            print("ret=%s" % ret)
        names = [x['name'] for x in ret['downloads']]
        print json.dumps(names, indent=4)

    elif args.cmd=="download_student_state":
        ea.download_student_state_reports(module_ids=args.ifn, date_filter=args.date)

    elif args.cmd=="get_problem_responses":
        module_ids = args.ifn
        for mid in module_ids:
            ret = ea.enqueue_request_for_problem_responses(mid)
            print "%s -> %s" % (mid, ret)
            time.sleep(20)

    elif args.cmd=="get_course_info":
        ret = ea.get_basic_course_info()
        if args.verbose:
            print("course info ret=%s" % ret)

    elif args.cmd=="download_course":
        ea.download_course_tarball()

    elif args.cmd=="upload_course":
        ea.upload_course_tarball(args.ifn[0])

    elif args.cmd=="list_courses":
        ret = ea.list_courses()['course_ids']

    elif args.cmd=="get_course_metadata":
        ret = ea.get_course_metadata()

    elif args.cmd=="update_course_metadata":
        if args.data:
            try:
                md = json.loads(args.data)
            except Exception as err:
                raise Exception("Metadata (from file %s) should be in JSON format: err=%s" % (args.data_file, str(err)))
        else:
            try:
                md = json.loads(args.ifn[0])
            except Exception as err:
                raise Exception("Metadata should be in JSON format: err=%s" % str(err))
        ret = ea.update_course_metadata(md)

    elif args.cmd=="set_course_end_date":
        end_date = args.ifn[0]
        enrollment_end = None
        if len(args.ifn)>1:
            enrollment_end = args.ifn[1]
        ret = ea.set_course_end_date(end_date, enrollment_end=enrollment_end)
        
    elif args.cmd=="create_chapter":
        ea.create_chapter(args.ifn[0])

    elif args.cmd=="delete_chapter":
        ea.delete_chapter(args.ifn[0])

    elif args.cmd=="list_chapters":
        ret = ea.list_chapters()

    elif args.cmd=="get_outline":
        if len(args.ifn):
            ret = ea.get_outline(args.ifn[0])
        else:
            ret = ea.get_outline()

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

    elif args.cmd=="get_due_date":
        ret = ea.get_due_date(args.ifn[0])

    elif args.cmd=="set_due_date":
        ret = ea.set_due_date(args.ifn[0], args.ifn[1])

    elif args.cmd=="set_all_due_dates":
        ret = ea.set_all_due_dates(args.ifn[0])

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

    # ccx commands

    elif args.cmd=="enroll_student":
        email = args.ifn[0]
        ret = ea.enroll_student(email)

    elif args.cmd=="list_students":
        ret = ea.list_students()

    elif args.cmd=="revoke_student":
        email = args.ifn[0]
        ret = ea.revoke_student(email)

    # unknown

    else:
        print ("Unknown command %s" % args.cmd)

    if args.json_output_html:
        print ret['html']
    elif args.output_srt:
        print ret
    elif args.json_output and ret is not None:
        try:
            print json.dumps(ret, indent=4)
        except Exception as err:
            print("Output is not JSON serializable, ret=%s" % ret)

#-----------------------------------------------------------------------------
