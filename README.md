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

Installation
------------

    pip install -e git+https://github.com/mitodl/edxcut.git#egg=edxcut

Unit tests
----------

This package includes unit tests for build testing.
