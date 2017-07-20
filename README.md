edxcut
======

edxcut = edX Course Unit Tests

Have you ever had your open edX course unexpectedly break, due to some
change in how the edX platform does grading, or due to some code
change in a custom response grading library?

Would you like to be able to automatically verify that *all* the
auto-graded problems in your edX course are functioning as expected,
without having to manually click through all the problems and remember
test cases to enter?

Would you like to script the creation of course content, or the
editing of course structure, including command-line access to download
specific problem, html, and video assets from a course, or
command-line access to upload new problem, html, and video assets
(including video transcripts) to an existing course?

__edxcut__ is an open source package for performing automated unit
tests of answer box grading correctness, across all problems, in a
live, open edX course instance.  __edxcut__ also allows programmatic
creation, reading, updating, and deletion (CRUD) of edX course
content, via its __edxapi__ API interface, which mimics an instructor
interacting with an OpenEdX Studio instance.

Programmatic Content Creation, Reading, Updating, and Deletion
--------------------------------------------------------------

The core of __edxcut__ is the [__edxapi__ module](https://github.com/mitodl/edxcut/blob/master/edxcut/edxapi.py), 
which can be accessed and used either via a python program, or from the command line, viz:

```
usage: edxcut edxapi [-h] [-v] [-s SITE_BASE_URL] [-u USERNAME] [-p PASSWORD]
              [-c COURSE_ID] [--module-id-from-csv MODULE_ID_FROM_CSV]
              [-D DATA_DIR] [-S] [-j] [--json-output-html] [-t TYPE]
              [--view VIEW] [-o OUTPUT_FILE_NAME] [-d DATA]
              [--data-file DATA_FILE] [--extra-data EXTRA_DATA]
              [--videoid VIDEOID] [--output-srt] [--create] [--auth AUTH]
              [--date DATE]
              cmd [ifn [ifn ...]]

usage: edxcut edxapi [command] [args...] ...

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
                             edxcut edxapi --create -d "<html>hello world2</html>" -t html --json-output -v
                                     -s http://192.168.33.10:18010 -u staff@example.com -p edx -S
                                     -c course-v1:edX+DemoX+Demo_Course get_xblock
                                     "Example Week 2: Get Interactive" "Homework - Labs and Demos" "Code Grader" "Code Grader"
create_xblock <path>       - create xblock specified by path, with type -t, and data -d, e.g.
                             edxcut edxapi -d "<html>hello world2</html>" -t html --json-output -v
                                     -s http://192.168.33.10:18010 -u staff@example.com -p edx -S
                                     -c course-v1:edX+DemoX+Demo_Course create_xblock testchapter testsection testvertical testhtml2 
delete_xblock <path>       - delete xblock specified by path, e.g.
                             edxcut edxapi --json-output -v -s http://192.168.33.10:18010 -u staff@example.com -p edx
                                     -S -c course-v1:edX+DemoX+Demo_Course delete_xblock testchapter testsection testvertical testhtml2
update_xblock <path>       - update (and optionally create all needed) xblock at a specified path, e.g.
                             edxcut edxapi --create -d "<html>hello world2</html>" -t html --json-output -v
                                     -s http://192.168.33.10:18010 -u staff@example.com -p edx -S
                                     -c course-v1:edX+DemoX+Demo_Course update_xblock testchapter testsection testvertical testhtml2
get_video_transcript <id>  - get transcript srt.sjson data for a given url_name (id), e.g.:
                             edxcut edxapi -v -j -s http://192.168.33.10 -u staff@example.com -p edx
                                     -c course-v1:edX+DemoX+Demo_Course
                                     get_video_transcript 636541acbae448d98ab484b028c9a7f6 --videoid o2pLltkrhGM
upload_transcript <fn> <id> - upload transcript file for a given url_name (id), and videoid, e.g.:
                              edxcut edxapi --json-output -v -s http://192.168.33.10:18010 -u staff@example.com -p edx -S
                                      -c course-v1:edX+DemoX+Demo_Course
                                      upload_transcript sample.srt 86c5f7e4e99a4b8a8d54364187493c43 --videoid 7bV04R-12uw

positional arguments:
  cmd                   command)
  ifn                   Input files

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity (add more -v to increase versbosity)
  -s SITE_BASE_URL, --site-base-url SITE_BASE_URL
                        base url for course site, e.g. http://192.168.33.10
  -u USERNAME, --username USERNAME
                        username for course site access
  -p PASSWORD, --password PASSWORD
                        password for course site access
  -c COURSE_ID, --course_id COURSE_ID
                        course_id, e.g. course-v1:edX+DemoX+Demo_Course
  --module-id-from-csv MODULE_ID_FROM_CSV
                        provide name of CSV file from which to get module_id values
  -D DATA_DIR, --data-dir DATA_DIR
                        directory where data is stored
  -S, --studio          specify that the edX site being accessed is a CMS studio sute
  -j, --json-output     Dump result (eg from get_block) as JSON to stdout
  --json-output-html    Dump HTML portion of json result (eg from get_block) to stdout
  -t TYPE, --type TYPE  xblock content category type, used when creating new content xblock
  --view VIEW           xblock view, used when getting xblock
  -o OUTPUT_FILE_NAME, --output-file-name OUTPUT_FILE_NAME
                        output file name to use, e.g. for get_asset
  -d DATA, --data DATA  data to store (eg for xblock, when using create_block)
  --data-file DATA_FILE
                        filename with data to store (eg for xblock, when using create_block)
  --extra-data EXTRA_DATA
                        JSON string with extra data to store (for update_block)
  --videoid VIDEOID     videoid for get_video_transcript
  --output-srt          have get_video_transcript output srt instead of srt.sjson
  --create              for update_xblock, create if missing
  --auth AUTH           http basic auth (username,pw) tuple to use for OpenEdX site access
  --date DATE           date filter for selecting which files to download, in YYYY-MM-DD format
```

### Example: list chapters

Suppose you have an OpenEdX site at `https://studio.univ.edu`, and a
course staff user account `staff@example.com`, with password `edx` for the course with ID
`course-v1:edX+DemoX+Demo_Course`.  You can list the chapters in that course using this command:

```
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course list_chapters
```

obtaining a response like this:
```
Found 6 chapters in course edX Demonstration Course
    Introduction -> block-v1:edX+DemoX+Demo_Course+type@chapter+block@d8a6192ade314473a78242dfeedfbf5b
    Example Week 1: Getting Started -> block-v1:edX+DemoX+Demo_Course+type@chapter+block@interactive_demonstrations
    Example Week 2: Get Interactive -> block-v1:edX+DemoX+Demo_Course+type@chapter+block@graded_interactions
    Example Week 3: Be Social -> block-v1:edX+DemoX+Demo_Course+type@chapter+block@social_integration
    About Exams and Certificates -> block-v1:edX+DemoX+Demo_Course+type@chapter+block@1414ffd5143b4b508f739b563ab468b7
    holding section -> block-v1:edX+DemoX+Demo_Course+type@chapter+block@9fca584977d04885bc911ea76a9ef29e
```

You may also specify the output to be in JSON format with the `-j` flag, obtaining output 
[such as this](https://github.com/mitodl/edxcut/blob/master/sample_data/list_chapters.json).

If your OpenEdX site is behind an HTTP basic auth control, then add
`--auth username,password` with the appropriate username and password
for site access.

### Example: list sequentials in a chapter, and verticals within a sequential

The `list_xblocks` edxapi command is useful for listing the contents
of a container xblock, such as chapters and sequentials, e.g.:

```
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course list_xblocks "Example Week 1: Getting Started"
```

should generate output like this:

```
Found 2 sequentials in chapter Example Week 1: Getting Started
    Lesson 1 - Getting Started -> block-v1:edX+DemoX+Demo_Course+type@sequential+block@19a30717eff543078a5d94ae9d6c18a5
    Homework - Question Styles -> block-v1:edX+DemoX+Demo_Course+type@sequential+block@basic_questions
```

and to see the verticals within, say, the "Homework - Question Styles" sequential:

```
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course list_xblocks "Example Week 1: Getting Started" "Homework - Question Styles"
```

to obtain output like this:

```
Found 8 verticals in sequential Homework - Question Styles
    Pointing on a Picture -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@2152d4a4aadc4cb0af5256394a3d1fc7
    Drag and Drop -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@47dbd5f836544e61877a483c0b75606c
    Multiple Choice Questions -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@54bb9b142c6c4c22afc62bcb628f0e68
    Mathematical Expressions -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@vertical_0c92347a5c00
    Chemical Equations -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@vertical_1fef54c2b23b
    Numerical Input -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@2889db1677a549abb15eb4d886f95d1c
    Text input -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@e8a5cc2aed424838853defab7be45e42
    Instructor Programmed Responses -> block-v1:edX+DemoX+Demo_Course+type@vertical+block@fb6b62dbec4348528629cf2232b86aea
```

You can continue the path specification (chapter...sequential...vertical) to list the contents of a vertical, e.g.:

```
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course list_xblocks "Example Week 1: Getting Started" "Homework - Question Styles" "Numerical Input"
```

to obtain output like this:

```
Found 2 problems in vertical Numerical Input
    Numerical Input -> block-v1:edX+DemoX+Demo_Course+type@problem+block@75f9562c77bc4858b61f907bb810d974
     -> block-v1:edX+DemoX+Demo_Course+type@discussion+block@501aed9d902349eeb2191fa505548de2
```

Note this vertical has two XBlocks, but the second one has an empty
`display_name` (from the usage key (aka asset ID) you can tell it's a discussion
XBlock).

### Downloading a specific XBlock asset's content

To download the content of a specific XBlock asset, use the `get_xblock` edxapi command, followed by a path specification (providing chapter sequential vertical url_name e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course get_xblock "Example Week 1: Getting Started" "Homework - Question Styles" "Numerical Input" "Numerical Input"
```

to obtain JSON output [such as this](https://github.com/mitodl/edxcut/blob/master/sample_data/example_problem.json).
You can also obtain the same content by specifying the specific XBlock's usage key (also known as an asset ID)
instead of the chapter + sequential + vertica + asset content path, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course get_xblock block-v1:edX+DemoX+Demo_Course+type@problem+block@75f9562c77bc4858b61f907bb810d974
```

Course Unit Test Specifications
-------------------------------

For course functionality testing, edxcut accepts a course unit test
specification file (in YAML format), and interacts with the edX course
instance, mimicing a live learner, via direct calls to the edX xblock
APIs for problem checking and the instructor dashboard, for resetting
problem attempts.  Test cases specify inputs, and whether the expected
graded return should be correct or incorrect, for each case.

The course unit tests file can be produced manually, or by digesting
the course XML, or automatically, during compilation using
[latex2edx](https://github.com/mitocw/latex2edx).  When using
latex2edx, you can specify multiple test cases within the `\edXabox`
macro, including both expected correct and incorrect cases.

Example tests file
------------------

Below is an [example tests YAML file](https://github.com/mitodl/edxcut/blob/master/test_data/test_demo_course.yaml)
which can be run to test some problems in the demo course provided with the [edX fullstack](https://openedx.atlassian.net/wiki/display/OpenOPS/Running+Fullstack) (dogwood release) virtualbox VM:

```YAML
config:
  course_id: course-v1:edX+DemoX+Demo_Course
  site_base_url: http://192.168.33.10
  username: staff@example.com
  password: edx

tests:
  - url_name: 75f9562c77bc4858b61f907bb810d974
    responses: [ 43.141, 4500, 5 ]
    expected: [incorrect, correct, correct]
  - url_name: 75f9562c77bc4858b61f907bb810d974
    responses: [ 43.141, 4500, 9 ]
    expected: [incorrect, correct, incorrect]
  - url_name: 75f9562c77bc4858b61f907bb810d974
    responses: [ 43.141, 4500, 9 ]
    expected: incorrect
  - url_name: Sample_Algebraic_Problem
    responses: [A*x^2 + sqrt(y)]
    expected: correct
  - url_name: Sample_ChemFormula_Problem
    responses: [H2SO4  -> H^+ + 2 HSO4^-]
    expected: incorrect
  - url_name: Sample_ChemFormula_Problem
    responses: [H2SO4  -> H^+ + HSO4^-]
    expected: correct
```

using this command line:

    edxcut test test_data/test_demo_course.yaml

to get results like this:

    ======================================================================
    Running tests from test_data/test_demo_course.yaml
    [CourseUnitTestSet] Loaded 6 answer box unit tests from test_data/test_demo_course.yaml
    ============================================================ Running 6 tests
    Test 1: OK
    Test 2: OK
    Test 3: OK
    Test 4: OK
    Test 5: OK
    Test 6: OK
    ======================================== Tests done
    6 total tests, 6 passed, 0 failed

Note that you may need to change the `url_name` for the first three
cases, which have a edx-studio-specific hexstring, if using a different VM
instance.

Usage
-----

Here's how to run unit tests on a course on edx.org:

1. Generate course unit tests YAML file.  For example, with latex2edx:

    latex2edx -d course_directory --output-course-unit-tests my_tests.yaml -m the_course.tex
    
2. Run edxcut, adding specifications for the course ID, username, and login password:

```
    edxcut  -s https://courses.edx.org \
    	    -u my-course-tester@myorg.org \
            -p my-password \
            -c course-v1:MYx+NUM+SEM \
            test my_tests.yaml
```

Course Unit Tests File
----------------------

The course unit tests file should be in [YAML
format](https://en.wikipedia.org/wiki/YAML).  It may specify `config`
parameters, for the `course_id`, `site_base_url`, `username`, and `password`, e.g.:

```YAML
config:
  course_id: course-v1:edX+DemoX+Demo_Course
  site_base_url: http://192.168.33.10
  username: staff@example.com
  password: edx
```

The tests file should also specify one or more `tests`.  Each test
should give at least the `url_name`, `responses`, and `expected`
grader output.  For example:

```YAML
  - url_name: Sample_Algebraic_Problem
    responses: [A*x^2 + sqrt(y)]
    expected: correct
```

Note that `responses` should be a list.  `expected` should either be a
string, `correct` or `incorrect`, or it may be a list (of the same
length as `responses`, of those two strings.

Each test may also specify a `name`.

And each test may also specify `box_indexes`, which are pairs of (x,y)
coordinates for input boxes.  This is useful when there is more than
one question (ie answer box) for a given problem.  The coordinates are
used to construct the input box IDs, which is of the form
input_<url_name>_<x>_<y>, where <x> indexes which `\abox` (aka
`<*response>`) the input is, and <y> indexes which input element it
is, within a given abox (for aboxes with multiple input boxes).  This
list should have the same length as `responses`.  For example:

```YAML
tests:
- box_indexes:
  - [0, 0]
  - [1, 0]
  - [2, 0]
  - [3, 0]
  - [4, 0]
  expected: [incorrect, incorrect, incorrect, incorrect, incorrect]
  name: (Simple quantum gate identities) s12-wk1-gates/test_1
  responses: [Z, I, Y, Z, I]
  url_name: s12-wk1-gates
```

Generating Tests with latex2edx
-------------------------------

Here are some example `\edXabox` statements which may be used with
[latex2edx](https://github.com/mitocw/latex2edx), to specify answer
box unit tests:

```tex
\edXabox{type='custom' size=10 expect="I" cfn=check_paulis inline="1" test_fail="Z"}

\edXabox{type=option options="true","false" expect="false" inline="1"}

\edXabox{type=symbolic size=10 expect="7"  inline="1"}

\edXabox{type=symbolic size=10 expect="7"  inline="1" test_pass="7"}

\edXabox{type=symbolic size=10 expect="7"  inline="1" test_pass="7" test_fail="9"}
```

This is an more complex example, where the grader is a custom python
script (not shown), that knows the expected answer; here, `test_pass`
is necessary since `expect` does not provide an answer useful for the
unit test:

```tex
\edXabox{type="custom" 
  size=30 
  expect="See solutions"  
  options="expect=(Qubit('00')+Qubit('01'))/2"
  cfn=check_qcircuit_output 
  hints='myhints'
  test_pass="H(0),H(1)"
  inline="1"
}
```

Note that the latex2edx correctly handles the case when there are
multiple answer boxes in a single problem, e.g.:

```tex
\begin{edXproblem}{A problem with two aboxes}{url_name="a_problem"}

\edXabox{type="option" options="red","green","blue" expect="red"}

\edXabox{type="custom" expect="42" cfn="mytest"}
\end{edXproblem}
```

Such multi-box problems properly generate test cases with
`box_indexes` set to specify the (x,y) coordinates of the input boxes.

Installation
------------

    pip install -e git+https://github.com/mitodl/edxcut.git#egg=edxcut

Unit tests
----------

This package includes unit tests for build testing.

Versions
--------

0.1 - original
0.2 - grades download added to edxapi.py (sdotglenn)
