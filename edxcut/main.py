'''
Run unit tests on edX courses, to ensure problem responses are graded properly.
Also can be used to create unit tests, from an xbundle file.
'''

import sys
import argparse
from course_unit_tester import CourseUnitTester
from collections import defaultdict

#-----------------------------------------------------------------------------

class VAction(argparse.Action):
    def __call__(self, parser, args, values, option_string=None):
        curval = getattr(args, self.dest, 0) or 0
        values=values.count('v')+1
        setattr(args, self.dest, values + curval)

#-----------------------------------------------------------------------------

def CommandLine(args=None, arglist=None):
    '''
    Main command line.  Accepts args, to allow for simple unit testing.
    '''
    help_text = """usage: %prog [command] [args...] ...

Commands:

test               - give unit test yaml file(s) as argument(s)
make_tests         - give xbundle file(s) as argument(s); produces test yaml file as output
                     (on stdout, or use -o)
edxapi             - run edxapi (edxapi -h for more)

Examples:

- ...
"""
    if len(sys.argv)>1 and sys.argv[1]=="edxapi":
        import edxapi_cmd
        return edxapi_cmd.CommandLine(arglist=sys.argv[2:])

    parser = argparse.ArgumentParser(description=help_text, formatter_class=argparse.RawTextHelpFormatter)
    
    parser.add_argument("cmd", help="command)")
    parser.add_argument("ifn", nargs='*', help="Input files")
    parser.add_argument('-v', "--verbose", nargs=0, help="increase output verbosity (add more -v to increase versbosity)", action=VAction, dest='verbose')
    parser.add_argument("-s", "--site-base-url", type=str, help="base url for course site, e.g. http://192.168.33.10", default=None)
    parser.add_argument("-u", "--username", type=str, help="username for course site access", default=None)
    parser.add_argument("-p", "--password", type=str, help="password for course site access", default=None)
    parser.add_argument("-c", "--course_id", type=str, help="course_id, e.g. course-v1:edX+DemoX+Demo_Course", default=None)
    
    if not args:
        args = parser.parse_args(arglist)

    if args.cmd=="test":
        counts = defaultdict(int)
        if len(args.ifn) > 1:
            print "="*70
            print "Running tests from %d files" % len(args.ifn)
        for fn in args.ifn:
            print "="*70
            print "==>  Running tests from %s " % fn
            cut = CourseUnitTester(site_base_url=args.site_base_url,
                                   username=args.username,
                                   password=args.password,
                                   verbose=args.verbose,
                                   course_id=args.course_id,
                                   cutfn=fn)
            cut.run_all_tests()
            for k,v in cut.test_results.items():
                counts[k] += v
        print "="*70
        print "Ran tests from %d files" % len(args.ifn)
        print ("Overall: %s total tests, on %s unique problems; "
               "%s passed, %s failed" % (counts['n_tests_ran'],
                                         counts['n_problems'],
                                         counts['n_passed'],
                                         counts['n_failed']))

    elif args.cmd=="make_tests":
        import make_tests
        make_tests.make_tests_from_xbundle_files(args.ifn, args)

    else:
        print ("Unknown command %s" % args.cmd)

#-----------------------------------------------------------------------------

if __name__=="__main__":
    CommandLine()

    
