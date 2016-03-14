#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generate a report of your daily whereabouts.

This script requires:

    - A GPS-enabled smartphone (obviously).
    - An account with Followmee (http://www.followmee.com).
    - The Followmee app enabled and active on your smartphone.
    - An API key with Followmee.
    - An account with Google developer
      (http://developers.google.com).
    - An API key with Google.
    - An instance of Dropbox running.
    - Calibri Microsoft font installed (optional).
      Change the generate_html() function if you want
      to update the report stylesheet.
    - The wkhtmltopdf library (http://wkhtmltopdf.org).
    - A Python virtualenv environment in ./venv

To run, just copy config.yml.dist to config.yml, change
the variables, and you should be good to go!
"""

# pylint: disable=F0401

from __future__ import print_function
from six.moves.urllib.request import urlopen
import simplejson as json
import dateutil.parser
from datetime import (datetime, timedelta)
import argparse
import random
import pytz
import pdfkit
import shutil
import yaml
import time as ttime
import csv
import os


def main():
    """
    Main routine.
        - Format dates for query and output
        - Ensure ./tmp directory and target directories exist.
        - Fetch tracking data from followmee.
        - Write data to CSV file in temporary folder.
            - For each row, query street address information
              from Google given latitude and longitude, and
              write to CSV.
        - Fetch map image from Google, and save to temporary
          folder.
        - Generate an HTML report and save to temporary folder.
        - Generate a PDF from HTML report, and save to temporary
          folder.
        - Copy CSV and PDF reports to target locations.
    """
    # Command-line arguments
    args = _parseargs()

    # Global configurations
    config = _parseconfig()

    timezone = pytz.timezone(config['timezone'])
    today = datetime.now(timezone)

    tmp_dir = "%s/tmp" % config['paths']['project']

    try:
        # ------------------------------------------------ #
        # - Verify and create temporary and target paths - #
        # ------------------------------------------------ #
        verify_paths(config['paths']['targets'], tmp_dir)

        # ----------------------------------------- #
        # - Fetch GPS plot data for past 24 hours - #
        # ----------------------------------------- #
        stop_date = today.strftime('%Y-%m-%d')
        start_date = (today - timedelta(1)).strftime('%Y-%m-%d')

        results = fetch_plot_data(config['followmee'], start_date,
                                  stop_date, args['verbose'])

        # ------------------ #
        # - Write CSV file - #
        # ------------------ #
        tmp_csv_path = append_csv_and_plots(config['google'], results,
                                            tmp_dir, args['verbose'])

        # ----------------------------------------- #
        # - Generate plot map URL and fetch image - #
        # ----------------------------------------- #
        tmp_png_path = fetch_map_image(config['google'], results, tmp_dir,
                                       args['verbose'])

        # ------------------ #
        # - Write PDF file - #
        # ------------------ #
        tmp_pdf_path = generate_pdf(today, tmp_dir, tmp_csv_path,
                                    tmp_png_path, args['verbose'])

        # ------------------------------ #
        # - Copy files to destinations - #
        # ------------------------------ #
        copy_files_to_destination(config['paths']['targets'], today,
                                  tmp_pdf_path, tmp_csv_path, args['verbose'])

    except Exception as e:
        print(e.args[0])


def verify_paths(target_paths, tmp_dir):
    """
    Verify paths.

    Args:
        target_paths (list): List of target report directories (str)
        tmp_dir (str): Temporary work directory
    """
    # Check for ./tmp, and create it if necessary
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    for target_path in target_paths:
        target_csv_path = '%s/csv' % target_path

        if not os.path.exists(target_path):
            os.makedirs(target_path)

        if not os.path.exists(target_csv_path):
            os.makedirs(target_csv_path)


def fetch_plot_data(config, start_date, stop_date, verbose=False):
    """
    Fetch plot data.

    Args:
        config (dict): API configuration variables
        start_date (str): Start date for query
        stop_date (str): Stop date for query
        verbose (bool): Print terminal output

    Returns:
        (list): List of dictionaries containing geolocation coordinates
    """
    if verbose:
        print('Fetching Data...')

    # Download followmee data from the past 24 hours
    history_url = ('%s/tracks.aspx?key=%s&username=%s&output=json'
                   '&function=daterangefordevice&from=%s%%20'
                   '11pm&to=%s&deviceid=%s') \
        % (config['url'],
           config['api_key'],
           config['username'],
           start_date,
           stop_date,
           config['device_id'])

    response = urlopen(history_url).read().decode('utf-8')
    results = json.loads(response)

    if 'Data' in results:
        return results['Data']

    return None


def append_csv_and_plots(config, results, tmp_dir, verbose=False):
    """
    Write CSV file of plot data, interpolating street addresses
    into each record by querying Google Geocode API for each row.

    Args:
        config (dict): API configuration variables
        results (list): List of dictionaries containing geolocation
                        coordinates
        tmp_dir (str): Temporary working directory
        verbose (bool): Print terminal output

    Returns:
        tmp_csv_path (str): Full path to working CSV file
    """
    # pylint: disable=E1101
    rand_name = "%s.csv" % random.getrandbits(128)
    tmp_csv_path = os.path.join(tmp_dir, rand_name)

    # Write CSV
    with open(tmp_csv_path, 'w') as csvfile:
        if verbose:
            print('Writing CSV...')

        writer = csv.writer(csvfile, delimiter=',',
                            quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

        writer.writerow(['Date', 'Lat', 'Lon', 'Speed (mph)',
                         'Accuracy', 'Type', 'Address'])

        for row in results:
            plot_date = dateutil.parser.parse(row.get('Date'))
            address = query_geocode(config,
                                    row.get('Latitude'),
                                    row.get('Longitude'))
            formatted_date = plot_date.strftime("%Y-%m-%d %I:%M:%S %p")

            writer.writerow([formatted_date,
                             str(row.get('Latitude')),
                             str(row.get('Longitude')),
                             row.get('Speed(mph)'),
                             str(row.get('Accuracy')),
                             row.get('Type'),
                             address])

    return tmp_csv_path


def query_geocode(config, latitude, longitude):
    """
    Query Google Geocode API for street address, given
    latitude and longitude values.

    Args:
        config (dict): API configuration variables
        latitude (int): Latitude
        longitude (int): Longitude

    Returns:
        formatted_address (str): formatted street address.
    """
    formatted_address = ''

    geocode_url = "%s/json?latlng=%s,%s&key=%s&result_type=street_address" \
        % (config['geocode_url'], latitude, longitude, config['api_key'])

    ttime.sleep(.20)

    response = urlopen(geocode_url).read().decode('utf-8')
    addr = json.loads(response)['results']

    if isinstance(addr, list):
        if len(addr) > 0 and 'formatted_address' in addr[0]:
            formatted_address = addr[0]['formatted_address'][:-5]

    return formatted_address


def fetch_map_image(config, results, tmp_dir, verbose=False):
    """
    Download Google Maps image, given the Google Maps API URL.

    Args:
        config (dict): API configuration variables
        results (list): List of dictionaries containing geolocation
                        coordinates
        tmp_dir (str): Path to temporary directory
        verbose (bool): Print terminal output

    Returns:
        tmp_png_file (str): Full path to working PNG file
    """
    if verbose:
        print('Downloading Image...')

    # Generate URL
    url = config['map_url'] + '&markers='

    for row in results:
        lat = "%.4f" % row.get('Latitude')
        lon = "%.4f" % row.get('Longitude')

        url += '|%s,%s' % (lat, lon)

    # Fetch image
    img = urlopen(url)

    rand_name = "%s.png" % random.getrandbits(128)
    tmp_png_file = os.path.join(tmp_dir, rand_name)

    with open(tmp_png_file, 'wb') as pngfile:
        shutil.copyfileobj(img, pngfile)

    return tmp_png_file


def generate_pdf(plot_date, tmp_dir, tmp_csv_path, tmp_png_path,
                 verbose=False):
    """
    Generate HTML report, then convert it to PDF.

    Args:
        plot_date (datetime): Time and date of report snapshot
        tmp_dir (str): Temporary working directory
        tmp_csv_path (str): Full path for working CSV file
        tmp_png_path (str): Full path for working PNG file
        verbose (bool): Print terminal output

    Returns:
        tmp_pdf_path (str): Full path for working PDF file
    """
    if verbose:
        print('Generating PDF...')

    day = plot_date.strftime('%d')
    year = plot_date.strftime('%Y')
    month = plot_date.strftime('%b')
    day_of_week = plot_date.strftime('%A')

    rand_name = random.getrandbits(128)
    tmp_html_path = os.path.join(tmp_dir, "%s.html" % rand_name)
    tmp_pdf_path = os.path.join(tmp_dir, "%s.pdf" % rand_name)

    html = """<html><head><style>
                html, body {
                  padding: 0;
                  margin: 35px 18px;
                  background-color: #FFFFFF;
                  font-family: Calibri;
                }
                h1 { font-weight: bold; font-size: 22pt; }
                div#data {
                  text-align: center;
                  width: 100%;
                  margin: 0 auto;
                  border: 1px solid #777777;
                  padding 0;
                }
                @media print {
                  #tdata {
                    page-break-before: always;
                  }
                }
                table#tdata: {
                  width: 98%;
                  margin: 0;
                  border-collapse: collapse;
                }
                tr#head {
                  background-color: #EFEFEF;
                  border-bottom: 1px solid #777777;
                }
                tr.even {
                  background-color: #F9F9F9;
                }
                th.l, td.l {
                  border-right: 1px solid #AAAAAA;
                }
                th {
                  text-align: center;
                  font-weight: bold;
                  font-size: 8pt;
                  padding: 4px;
                }
                td { text-align: left; font-size: 7pt; padding: 4px; }
              </style></head>
              <body>"""

    # Header
    date = '%s %s, %s, %s' % (month, day, day_of_week, year)
    html += '<h1>%s</h1>' % date

    # Map
    html += """<div style="text-align: center; width: 100%;">
               <img src="{0}" width="620" height="620" />
               </div><br />""".format(tmp_png_path)

    # Table
    html += '<div id="data"><table style="width: 100%;">'

    with open(tmp_csv_path, 'r') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)

        count = 0
        for row in reader:
            # Header
            if count == 0:
                html += """<tr id="head"><th class="l">%s</th>
                           <th class="l">%s</th><th class="l">%s</th>
                           <th class="l">%s</th><th class="l">%s</th>
                           <th class="l">%s</th><th>%s</th></tr>""" \
                    % (row[0], row[1], row[2], row[3], row[4], row[5], row[6])
            # Body
            else:
                alt_class = ''

                if count % 2 == 0:
                    alt_class = ' class="even"'

                html += """<tr id="body"%s><td class="l">%s</td>
                           <td class="l">%s</td><td class="l">%s</td>
                           <td class="l">%s</td><td class="l">%s</td>
                           <td class="l">%s</td><td>%s</td></tr>""" \
                    % (alt_class, row[0], row[1], row[2], row[3], row[4],
                       row[5], row[6])

            count += 1

    html += '</table></div></body></html>'

    # Write HTML file
    with open(tmp_html_path, 'w') as htmlfile:
        htmlfile.write(html)
        htmlfile.close()

    # Convert HTML to PDF
    with open(tmp_html_path, 'r') as htmlfile:
        pdfkit.from_file(htmlfile, tmp_pdf_path, options={'quiet': ''})

    # Clean up temporary files
    os.unlink(tmp_png_path)
    os.unlink(tmp_html_path)

    return tmp_pdf_path


def copy_files_to_destination(config, today, tmp_pdf_path, tmp_csv_path,
                              verbose=False):
    """
    Copy report CSV and PDF files to destination directories.

    Args:
        config (list): List of destination full path names
        today (datetime): Date of report snapshot
        tmp_pdf_path (str): Path of working PDF file
        tmp_csv_path (str): Path of working CSV file
        verbose (bool): Print terminal output
    """
    if verbose:
        print('Copying Report to Destination...')

    target_csv = "%s.csv" % today.strftime('%b_%d').lower()
    target_pdf = "%s.pdf" % today.strftime('%b %d')

    for target_path in config:
        target_csv_path = '%s/csv' % target_path

        target_named_pdf_path = os.path.join(target_path, target_pdf)
        target_today_pdf_path = os.path.join(target_path, '~Today.pdf')
        target_named_csv_path = os.path.join(target_csv_path, target_csv)

        shutil.copy2(tmp_pdf_path, target_named_pdf_path)
        shutil.copy2(tmp_pdf_path, target_today_pdf_path)
        shutil.copy2(tmp_csv_path, target_named_csv_path)

    # Clean up temporary files
    os.unlink(tmp_pdf_path)
    os.unlink(tmp_csv_path)


def _parseconfig():
    """
    Parse config file.

    Returns:
        config (dict): Global configuration variables
    """
    with open('config.yml', 'r') as ymlfile:
        config = yaml.load(ymlfile)

    return config


def _parseargs():
    """
    Parse command-line arguments.

    Returns:
        (dict): Populated argument namespace
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--print', dest='verbose', action='store_true')

    return parser.parse_args().__dict__


if __name__ == '__main__':
    main()
