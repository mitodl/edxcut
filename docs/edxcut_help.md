
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
list_assets                 - list static assets in a given course
get_asset <fn>              - retrieve a single static asset file (for output specify -o output_filename)
get_asset_info <fn>         - retrieve metadata about single static asset file
upload_asset <fn>           - upload a single static asset file
delete_asset <fn | blockid> - delete a single static asset file (or specify usage key / block ID)

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
