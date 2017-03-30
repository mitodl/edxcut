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

__edxcut__ is an open source package for performing automated unit
tests of answer box grading correctness, across all problems, in a
live, open edX course instance.

edxcut accepts a course unit test specification file (in YAML format),
and interacts with the edX course instance, mimicing a live learner,
via direct calls to the edX xblock APIs for problem checking and the
instructor dashboard, for resetting problem attempts.  Test cases
specify inputs, and whether the expected graded return should be
correct or incorrect, for each case.

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
