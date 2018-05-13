edxcut
======

edxcut = edX Course Uber Tool

Would you like to script the creation of course content on an edX instance,
or the editing of course structure, including command-line access to download
specific problem, html, and video assets from a course, or
command-line access to upload new problem, html, and video assets
(including video transcripts) to an existing course?  Or would you like to
copy a single XBlock from one OpenEdX course to another, including
static assets?

Have you ever had your open edX course unexpectedly break, due to some
change in how the edX platform does grading, or due to some code
change in a custom response grading library?

Would you like to be able to automatically verify that *all* the
auto-graded problems in your edX course are functioning as expected,
without having to manually click through all the problems and remember
test cases to enter?

__edxcut__ is an open source package for performing programmatic
creation, reading, updating, and deletion (CRUD) of edX course
content, via its __edxapi__ API interface, which mimics an instructor
interacting with an OpenEdX Studio instance.  __edXcut__ also provides
the ability to perform automated unit tests of answer box grading
correctness, across all problems, in a live, open edX course instance.

Programmatic Content Creation, Reading, Updating, and Deletion
--------------------------------------------------------------

The core of __edxcut__ is the [__edxapi__ module](https://github.com/mitodl/edxcut/blob/master/edxcut/edxapi.py), 
which can be accessed and used either via a python program, or from the command line - 
[see help text](https://github.com/mitodl/edxcut/blob/master/docs/edxcut_help.md).

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
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    list_xblocks "Example Week 1: Getting Started"
```

should generate output like this:

```
Found 2 sequentials in chapter Example Week 1: Getting Started
    Lesson 1 - Getting Started -> block-v1:edX+DemoX+Demo_Course+type@sequential+block@19a30717eff543078a5d94ae9d6c18a5
    Homework - Question Styles -> block-v1:edX+DemoX+Demo_Course+type@sequential+block@basic_questions
```

and to see the verticals within, say, the "Homework - Question Styles" sequential:

```
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    list_xblocks "Example Week 1: Getting Started" "Homework - Question Styles"
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
edxcut edxapi -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    list_xblocks "Example Week 1: Getting Started" "Homework - Question Styles" "Numerical Input"
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
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    get_xblock "Example Week 1: Getting Started" "Homework - Question Styles" "Numerical Input" "Numerical Input"
```

to obtain JSON output [such as this](https://github.com/mitodl/edxcut/blob/master/sample_data/example_problem.json).
You can also obtain the same content by specifying the specific XBlock's usage key (also known as an asset ID)
instead of the chapter + sequential + vertica + asset content path, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    get_xblock block-v1:edX+DemoX+Demo_Course+type@problem+block@75f9562c77bc4858b61f907bb810d974
```

### Downloading a video XBlock and its associated video transcript

To download the content for a video XBlock, use `get_xblock`, e.g.

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    get_xblock block-v1:edX+DemoX+Demo_Course+type@video+block@5c90cffecd9b48b188cbfea176bf7fe9
```

to obtain JSON output [such as this](https://github.com/mitodl/edxcut/blob/master/sample_data/example_video.json).

To download the associated video transcript, you'll need to point to the OpenEdX LMS site (and not the Studio site), e.g.:

```
edxcut edxapi -j -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    --videoid qWxm7CA2v24 get_video_transcript 5c90cffecd9b48b188cbfea176bf7fe9 
```

Note that the `url_name` for the video is specified, and not the whole
usage_key (although there's a fallback mechanism by which if you do
provide a `usage_key`, edxapi will extract the `url_name` from it for
you).

Also note that you will need to specify the video's ID, here, a
youtube ID; that's used by edX's transcripts mechanism to find the
transcript with the correct timing.

You shold obtain obtain JSON output [such as this](https://github.com/mitodl/edxcut/blob/master/sample_data/example_transcript.srt.sjson); by specifying the `--output-srt` flag, the transcript will be provided [in srt format](https://github.com/mitodl/edxcut/blob/master/sample_data/example_transcript.srt) instead of in srt.sjson format.

### Creating new chapter, sequential, and vertical xblocks

To create a new container XBlock, just specify the path desired to the new XBlock, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    create_xblock "New Chapter" 
```

The output should give usage keys for the new XBlock, e.g.:

```
{
    "locator": "block-v1:edX+DemoX+Demo_Course+type@chapter+block@f3b7608b609b4edf881531ca00e99c9d", 
    "courseKey": "course-v1:edX+DemoX+Demo_Course"
}
```

`create_xblock` will only create a single new XBlock.  If you wish to create all the XBlocks needed in a path, e.g. new chapter, new sequential, new vertical, use the `updage_xblock` command, with the `--create` flag, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    --create update_xblock "New Chapter" "New Sequential" "New Vertical" 
```

This will return the usage key for the last XBlock created, e.g.:
```
{
    "data": null, 
    "id": "block-v1:edX+DemoX+Demo_Course+type@vertical+block@5b9ef8ee60984408b1047b1d5e4a9ef4", 
    "metadata": {
        "display_name": "New Vertical"
    }
}
```

### Creating and updating html and problem XBlocks

To create a new HTML or problem XBlock, use the `update_xblock` edxapi command, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    --create -t html  -d "<html>hello world2</html>" \
    update_xblock "New Chapter" "New Sequential" "New Vertical" "New HTML page"
```

Note that the `-t` option is used to specify the content type, e.g. `html` or `problem`.

The page will contain the HTML string specified in the `-d` argument, and the return will provide the newly created XBlock's usage key, e.g.:
```
{
    "data": "<html>hello world2</html>", 
    "id": "block-v1:edX+DemoX+Demo_Course+type@html+block@994878a552894f67b28b3e050731d5a7", 
    "metadata": {
        "display_name": "New HTML page"
    }
}
```

You may also specify that the page content should be taken from a file, using the `--data-file` option instead of `-d`.

To update an existing XBlock, use `update_xblock`, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    -t html  -d "<html>another hello world</html>" \
    update_xblock block-v1:edX+DemoX+Demo_Course+type@html+block@994878a552894f67b28b3e050731d5a7
```

using the `usage_key` block ID provided from the creation request.  This will return data saved to the new page, e.g.:
```
{
    "data": "<html>another hello world</html>", 
    "id": "block-v1:edX+DemoX+Demo_Course+type@html+block@994878a552894f67b28b3e050731d5a7", 
    "metadata": {
        "display_name": "New HTML page"
    }
}
```

### Uploading a video XBlock

A video XBlock needs additional metadata to be specified, e.g. giving the youtube ID.  This is provided using the `--extra-data` argument, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    --create -t video  -d "" \
    --extra-data '{"metadata": {"youtube_id_1_0": "qWxm7CA2v24", "start_time": "00:05:10"}}' \
    update_xblock "New Chapter" "New Sequential" "New Vertical" "New video page"
```
The response should include the metadata specified, e.g.:
```
{
    "data": null, 
    "id": "block-v1:edX+DemoX+Demo_Course+type@video+block@91b7db1cd22e4e7c9e3068852d78abd8", 
    "metadata": {
        "start_time": "00:05:10", 
        "download_video": false, 
        "display_name": "New video page", 
        "youtube_id_1_0": "qWxm7CA2v24"
    }
}
```

A transcript can also be uploaded, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    upload_transcript sample_data/example_transcript.srt 91b7db1cd22e4e7c9e3068852d78abd8 --videoid qWxm7CA2v24
```

and the response should indicate success, e.g.:
```
{
    "status": "Success", 
    "subs": "qWxm7CA2v24"
}
```

### Deleting an XBlock

To delete an XBlock, use the `delete_xblock` edxapi command, e.g.:

```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    delete_xblock "New Chapter"
```
The output should confirm deletion, e.g.:
```
Deleted block-v1:edX+DemoX+Demo_Course+type@chapter+block@f3b7608b609b4edf881531ca00e99c9d, ret=204
```

It seems the edX platform does properly delete all children of a
container which has been deleted, so deleting a chapter deletes all
the content in the chapter in addition to deleting the chapter itself.

### Static Assets

#### Listing static assets

To list all the static assets used by a course, use the `list_assets` command, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
     list_assets
```
producing JSON output [such as this](https://github.com/mitodl/edxcut/blob/master/sample_data/example_assets.json).
Note this can be slow, and the output large.

#### Retrieving static assets

To retrieve a single static asset file, use `get_asset` and specify the output filename with `-o`, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
     -o output.js \
    get_asset search_problem_grader.js	
```

To upload a new static asset, use `upload_asset`, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    upload_asset test.html
```
with a response indicating success, e.g.:
```
{
    "msg": "Upload completed", 
    "asset": {
        "display_name": "test.html", 
        "url": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@test.html", 
        "locked": false, 
        "portable_url": "/static/test.html", 
        "thumbnail": null, 
        "content_type": "", 
        "date_added": "Jul 21, 2017 at 12:36 UTC", 
        "id": "asset-v1:edX+DemoX+Demo_Course+type@asset+block@test.html", 
        "external_url": "edx.univ.edu/asset-v1:edX+DemoX+Demo_Course+type@asset+block@test.html"
    }
}
```

#### Deleting static assets

To delete a new static asset, use `delete_asset`, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    delete_asset test.html
```
An empty response indicates success; failures will result in an exception being raised.

#### Getting static asset metadata

To retrieve information about a static asset, use `get_asset_info`, e.g.:
```
edxcut edxapi -j -S -v -s https://studio.univ.edu -u staff@example.com -p edx -c course-v1:edX+DemoX+Demo_Course \
    get_asset_info test.html
```
with output like:
```
{
    "display_name": "test.html", 
    "url": "/asset-v1:edX+DemoX+Demo_Course+type@asset+block@test.html", 
    "locked": false, 
    "portable_url": "/static/test.html", 
    "thumbnail": null, 
    "content_type": "", 
    "date_added": "Jul 21, 2017 at 12:36 UTC", 
    "id": "asset-v1:edX+DemoX+Demo_Course+type@asset+block@test.html", 
    "external_url": "edx.univ.edu/asset-v1:edX+DemoX+Demo_Course+type@asset+block@test.html"
}
```

## Course Unit Testing

### Course Unit Test Specifications

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

#### Example tests file

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

Course Unit Testing Usage
-------------------------

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

### Course Unit Tests File

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

### Generating Tests with latex2edx

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

# Installation

    pip install -e git+https://github.com/mitodl/edxcut.git#egg=edxcut

## Unit tests

This package includes unit tests for build testing.

# Versions

```
0.1 - original
0.2 - grades download added to edxapi.py (sdotglenn)
0.3 - edxapi extension for course content creation, reading, updating, and deletion
0.4 - edxapi documentation
```
