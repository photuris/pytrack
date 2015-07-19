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

from six.moves.urllib.request import urlopen
import simplejson as json
import dateutil.parser
from datetime import (datetime, timedelta)
import pytz
import pdfkit
import shutil
import yaml
import time as ttime
import csv
import os


# ---------------
# - Config File -
# ---------------
with open('config.yml', 'r') as ymlfile:
    config = yaml.load(ymlfile)

# -----------------
# - Followmee API -
# -----------------
F_USERNAME = config['followmee']['username']
F_DEVICE_ID = config['followmee']['device_id']
F_APIKEY = config['followmee']['api_key']
F_URL = 'http://www.followmee.com/api'

# --------------
# - Google API -
# --------------
G_APIKEY = config['google']['api_key']
G_URL = 'https://maps.googleapis.com/maps/api/geocode'
M_URL = 'https://maps.googleapis.com/maps/api/staticmap?size=620x620'

# -----------
# - Dropbox -
# -----------
DROPBOX_PATH = config['paths']['dropbox']
PROJECT_PATH = config['paths']['project']
DROPBOX_CSV_PATH = '%s/csv' % DROPBOX_PATH

# -------------------
# - Date formatting -
# -------------------
TIMEZONE = config['timezone']

tz = pytz.timezone(TIMEZONE)
today = datetime.now(tz)
yesterday = today - timedelta(1)
today_str = today.strftime('%Y-%m-%d')
yesterday_str = yesterday.strftime('%Y-%m-%d')
day = today.strftime('%d')
year = today.strftime('%Y')
month = today.strftime('%b')
day_of_week = today.strftime('%A')
day_str = today.strftime('%b %d')
day_str_lower = today.strftime('%b_%d').lower()


def main():
    """
    Main routine.

    - Ensure ./tmp directory exists.
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
    - Copy CSV and PDF report to Dropbox location.
    """
    # Check for ./tmp, and create it if necessary
    if not os.path.exists('./tmp'):
        os.makedirs('./tmp')

    print('Fetching Data...')

    # Download followmee data from the past 24 hours
    history_url = ('%s/tracks.aspx?key=%s&username=%s&output=json'
                   '&function=daterangefordevice&from=%s%%20'
                   '11pm&to=%s&deviceid=%s') \
        % (F_URL, F_APIKEY, F_USERNAME, yesterday_str, today_str, F_DEVICE_ID)

    response = urlopen(history_url).read().decode('utf-8')
    results = json.loads(response)

    m_url = M_URL

    # Write CSV
    with open('./tmp/%s.csv' % day_str_lower, 'w', newline='') as csvfile:
        print('Writing CSV...')

        writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(['Date', 'Lat', 'Lon', 'Speed (mph)',
                         'Accuracy', 'Type', 'Address'])

        m_url += '&markers='

        for row in results.get('Data'):
            date = dateutil.parser.parse(row.get('Date'))
            address = query_geocode(row.get('Latitude'), row.get('Longitude'))

            writer.writerow([date.strftime("%Y-%m-%d %I:%M:%S %p"),
                             str(row.get('Latitude')),
                             str(row.get('Longitude')),
                             row.get('Speed(mph)'), str(row.get('Accuracy')),
                             row.get('Type'),
                             address])

            lat = "%.4f" % row.get('Latitude')
            lon = "%.4f" % row.get('Longitude')

            m_url += '|%s,%s' % (lat, lon)

    fetch_map_image(m_url)

    generate_html()

    os.unlink('./tmp/%s.png' % day_str)
    os.unlink('./tmp/%s.html' % day_str)

    shutil.copy2('./tmp/%s.pdf' % day_str, DROPBOX_PATH)
    shutil.copy2('./tmp/%s.csv' % day_str_lower, DROPBOX_CSV_PATH)


def query_geocode(latitude, longitude):
    """
    Query Google Geocode API for street address, given
    latitude and longitude values.

    Args:
        latitude (int): latitude.
        longitude (int): longitude.

    Returns:
        (str): formatted street address.
    """
    geocode_url = "%s/json?latlng=%s,%s&key=%s&result_type=street_address" \
        % (G_URL, latitude, longitude, G_APIKEY)

    ttime.sleep(.20)

    response = urlopen(geocode_url).read().decode('utf-8')

    return json.loads(response)['results'][0]['formatted_address'][:-5]


def fetch_map_image(url):
    """
    Download Google Maps image, given URL.

    Args:
        url (str): the map generate url.
    """
    print('Downloading Image...')

    img = urlopen(url)

    with open('./tmp/%s.png' % day_str, 'wb') as pngfile:
        shutil.copyfileobj(img, pngfile)


def generate_html():
    """
    Generate HTML report, then convert to PDF.

    Save report to temporary directory.
    """
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
               <img src="{0}/tmp/{1}.png"
                    width="620" height="620" />
               </div><br />""".format(PROJECT_PATH, day_str)

    # Table
    html += '<div id="data"><table style="width: 100%;">'

    with open('./tmp/%s.csv' % day_str_lower, 'r') as csvfile:
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
                if count % 2 == 0:
                    alt_class = ' class="even"'
                else:
                    alt_class = ''

                html += """<tr id="body"%s><td class="l">%s</td>
                           <td class="l">%s</td><td class="l">%s</td>
                           <td class="l">%s</td><td class="l">%s</td>
                           <td class="l">%s</td><td>%s</td></tr>""" \
                    % (alt_class, row[0], row[1], row[2], row[3], row[4],
                       row[5], row[6])

            count += 1

    html += '</table></div></body></html>'

    with open('./tmp/%s.html' % day_str, 'w') as htmlfile:
        htmlfile.write(html)
        htmlfile.close()

    with open('./tmp/%s.html' % day_str, 'r') as htmlfile:
        pdfkit.from_file(htmlfile, './tmp/%s.pdf' % day_str)


if __name__ == '__main__':
    main()
