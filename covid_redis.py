# cronjob to be run (every 5 mins?) to acquire current image, parse it and store data in redis

import requests
import calendar, datetime
import os, hashlib
import pytesseract, PIL, re
from contextlib import suppress
import config, redis
from emailer import send_email
import pickle

IMAGE_DIR = 'report-images'

reference_date = datetime.datetime.now()

def generate_source_info_urls(month, day):
    base_url = 'http://www.health.gov.tt/covid19/MediaReleases'
    report_url_variations = [
        f'{base_url}/{month[:3]}{day}-01.jpg',
        f'{base_url}/{month[:3]}{day}.jpg',
    ]
    report_url_variations = ["http://www.health.gov.tt/covid19/MediaReleases/ReleaseNew-01.jpg"]
    return report_url_variations

def store_to_redis(redkey, data):
    conn = redis.Redis('localhost', password=config.redis_passwd)
    conn.hmset(redkey, data)

def fetch_and_store_report_images(month, day):
    report_url_variations = generate_source_info_urls(month, day)
    for report_url in report_url_variations:
        report_request = requests.get(report_url)
        if report_request.status_code == 200:
            filename = f'{month[:3]}{day}.jpg'
            if os.path.exists(f'{IMAGE_DIR}/{filename}'):
                report_contents_hash = hashlib.md5(report_request.content).hexdigest()
                file_contents = open(f'{IMAGE_DIR}/{filename}', 'rb').read()
                file_contents_hash = hashlib.md5(file_contents).hexdigest()
                if report_contents_hash == file_contents_hash:
                    return False
            with open(f'{IMAGE_DIR}/{filename}', 'wb') as f:
                f.write(report_request.content)
            return filename
        else:
            print(f'{report_url} 404')
    return False

def parse_report_image_to_text(filename):
    image = PIL.Image.open(f'{IMAGE_DIR}/{filename}')
    image_text = pytesseract.image_to_string(image).lower().replace('covid-19', '')
    return image_text

def parse_text_to_data_dict(text):
    data = {
        'samples': 0,
        'deaths': 0,
        'discharges': 0,
        'tested_positive': 0,
        'MoH_report_num': 0,
        'report_date': '',
    }

    #Number of samples
    with suppress(ValueError, IndexError):
        index_found = text.index('number of samples')
        data['samples'] = re.findall(r'\d+', text[index_found:])[0]
    #Number of tested_positive
    with suppress(ValueError, IndexError):
        index_found = text.index('have tested positive')
        data['tested_positive'] = re.findall(r'\d+', text[index_found:])[0]
    #Number of deaths
    with suppress(ValueError, IndexError):
        index_found = text.index('number of deaths')
        data['deaths'] = re.findall(r'\d+', text[index_found:])[0]            
    #Number of discharges
    with suppress(ValueError, IndexError):
        index_found = text.index('persons discharged')
        data['discharges'] = re.findall(r'\d+', text[index_found:])[0]
    #Report number (Update #)
    with suppress(ValueError, IndexError):
        index_found = text.index('update #')
        data['MoH_report_num'] = re.findall(r'\d+', text[index_found:])[0]
    #Date on the report
    with suppress(ValueError, IndexError):
        index_found = text.index('media release')
        parsed_text = ''.join(re.findall(r'[a-zA-Z0-9\n ]', text[index_found:index_found+200])).split('\n')
        parsed_text = [line for line in parsed_text if line]
        data['report_date'] = parsed_text[1] if '2020' in parsed_text[1] else ''
    return data

def email_data_formatted(data):
    formatted = f"""
    <table>
        <tr>
            <td align="right">Samples: </td>
            <td>{data["samples"]}</td>
        </tr>
        <tr>
            <td align="right">Tested Positive: </td>
            <td>{data["tested_positive"]}</td>
        </tr>
        <tr>
            <td align="right">Deaths: </td>
            <td>{data["deaths"]}</td>
        </tr>
        <tr>
            <td align="right">Recoveries: </td>
            <td>{data["discharges"]}</td>
        </tr>
    </table>
    <br>
    <a href="https://covid.reticence.net/">Link to site with charts</a>
    <br><br><br>
    <a href="https://covid.reticence.net/unsubscribe">Unsubscribe here</a>
    """
    return formatted

month = calendar.month_name[reference_date.month]
day = reference_date.day
date = reference_date.date()

filename = fetch_and_store_report_images(month, day)
if filename:
    text = parse_report_image_to_text(filename)
    data = parse_text_to_data_dict(text)
    if data['samples'] or data['tested_positive'] or data['deaths'] or data['discharges']:
        store_to_redis(str(date), data)
        # send email
        email_list = list(pickle.load(open("email_list.pkl", "rb")))
        send_email(email_list, f'COVID-19 TT Report #{data["MoH_report_num"]}', '', email_data_formatted(data))
    else:
        print('no new data gathered')
print('---')
