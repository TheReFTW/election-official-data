from urllib.parse import urlparse, parse_qs
import re
import random
import unicodedata

from bs4 import BeautifulSoup

from common import dir_path, cache_request, to_list, normalize_state, diff_and_save


BASE_URL = "https://mvic.sos.state.mi.us/Clerk"

# resolved issue with SSL cert chain by fixing intermediate cert
# base64 root-intermediate-site certs saved from Chrome, converted to pem using openssl,
# concatenated into mich_chain.pem
SSL_CERT = f'{dir_path(__file__)}\\mich_chain.pem'

re_official = re.compile('^\s*(.*?)\s*[,\n]')
re_address = re.compile('\n(.*)\nPhone', flags=re.MULTILINE+re.DOTALL)
re_phone = re.compile('\nPhone:[^\n\S]*(.+?)\s*\n')
re_fax = re.compile('Fax:[^\n\S]*(.+?)\s*\n')

def random_wait(min_wait=.1, max_wait=.3):
  return random.uniform(min_wait, max_wait)

def parse_jurisdiction(soup, jurisdiction_name, county_name):
  city = re.sub(r'\s+Twp', ' Township', jurisdiction_name)
  county = county_name.title().strip()
  body = soup.find('div', class_='card-body')
  info = re.sub('\s*\n\s*', '\n', unicodedata.normalize('NFKD',body.text).strip())
  return {
    'locale': f'{city}:{county}',
    'city': city,
    'county': county,
    'emails': [a['href'].replace('mailto:','').strip() for a in body.select("a[href^=mailto]")],
    'phones': re_phone.findall(info),
    'faxes': re_fax.findall(info),
    'official': re_official.findall(info)[0],
    'address': re_address.findall(info)[0].replace('\n',', '),
  }

def crawl_and_parse():
  data = []
  text = cache_request(BASE_URL, verify=SSL_CERT)
  soup = BeautifulSoup(text, 'html.parser')
  for county in soup.find('select', id='Counties')('option'):
    if not county.get('value'):
      continue
    county_text = cache_request(
      f'{BASE_URL}/SearchByCounty',
      method='POST',
      data={'CountyID': county.get('value')},
      wait=random_wait(),
      verify=SSL_CERT
    )
    county_soup = BeautifulSoup(county_text, 'html.parser')
    for jurisdiction_a in county_soup('a', class_='local-clerk-link'):
      qrystr_params = parse_qs(urlparse(jurisdiction_a.get('href')).query)
      jurisdiction_data = {k: v[0] for k,v in qrystr_params.items() if k != 'dummy'}
      jurisdiction_text = cache_request(
        f'{BASE_URL}/LocalClerk',
        method='POST',
        data=jurisdiction_data,
        wait=random_wait(),
        verify=SSL_CERT
      )
      jurisdiction_soup = BeautifulSoup(jurisdiction_text, 'html.parser')
      data.append(parse_jurisdiction(
        jurisdiction_soup,
        jurisdiction_data['jurisdictionName'],
        county.text
      ))

  data = normalize_state(data)
  diff_and_save(data, 'public/michigan.json')

if __name__ == '__main__':
  crawl_and_parse()
