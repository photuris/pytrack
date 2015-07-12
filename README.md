# pytrack

Generate a report of your daily whereabouts.

This script requires:

  - A GPS-enabled smartphone (obviously), with the
    Followmee app enabled and active.

  - An account and API key with Followmee
    (http://www.followmee.com).

  - An account and API key with Google developer
    (http://developers.google.com).

  - An instance of Dropbox running
    (optional - the target directory doesn't have to be
     a Dropbox target - I just like it because it
     automatically offloads the reports to a remote-
     accessible location).

  - Calibri Microsoft font installed (optional).

    Just change the generate_html() function if you want
    to update the report stylesheet.

  - The wkhtmltopdf library (http://wkhtmltopdf.org).

  - A Python virtualenv environment in ./venv

To install and run:

  1. Install the wkhtmltopdf library.

  2. Copy config.yml.dist to config.yml and change the
     variables to the appropriate values.

  3. Activate your virtualenv:

      1. virtualenv venv

      2. source venv/bin/activate

  4. Install the required modules:

      - $ pip install -r requirements.txt

  5. Run the script!

      - $ python track.py

Also included is a shell script that can be used for calling
the python script from within crontab (it auto-activates the
virtual environment for you).

Every hour is a good frequency in my opinion, like so:

    00  *  *  *  *   /home/username/Projects/pytrack/track.sh
