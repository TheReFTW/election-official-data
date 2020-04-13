import json
import re
from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

def line_gen(siblings):
  text = ''
  for x in siblings:
    if isinstance(x, NavigableString):
      text += x.strip()
    elif isinstance(x, Tag) and x.name == 'br':
      yield text
      text = ''
    elif isinstance(x, Tag) and x.name == 'span':
      text += x.text.strip()
    elif isinstance(x, Tag) and x.name == 'h3':
      yield text
      return

def parse_county(county, datum):
  absentee_voting_contact = next(contact
    for contact in datum.select('h3.contentpage-h3')
    if contact.text == 'Absentee voting contact'
  )

  _iter = line_gen(absentee_voting_contact.next_siblings)

  name = next(_iter)
  phone = next(_iter)
  fax = next(_iter)
  email = next(_iter)
  return {
    'county': county.text,
    'name': name,
    'phone': re.search('Phone: ([0-9\-]+)', phone).group(1),
    'fax': re.search('Fax: ([0-9\-]+)', fax).group(1),
    'email': re.search('Email:\s*(\S+)', email).group(1),
  }

with open('results/page.html') as fh:
  soup = BeautifulSoup(fh, 'lxml')
  counties = soup.select('h2.contentpage-h2')

  data = []
  for county in counties:
    data_id = county['data-target'].split('#')[1]
    datum = soup.find(id=data_id)
    data += [parse_county(county, datum)]

with open('public/results.json', 'w') as fh:
  json.dump(data, fh)
