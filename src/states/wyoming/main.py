from collections import defaultdict
import re
from common import fetch_pdf_text

PDF_URL = "https://sos.wyo.gov/Elections/Docs/WYCountyClerks_AbsRequest_VRChange.pdf"

email_suffixes = ['.us', '.gov', '.net', '.com', '.org']


def group_rows(lines):
  rows = []

  num_counties_seen = 0
  row = []
  for line in lines:
    if 'County Clerk' in line:
      num_counties_seen += 1
      if num_counties_seen == 3:
        rows.append(row)
        row = []
        num_counties_seen = 1
    row.append(line)

  # Get the last row.
  rows.append(row)
  return rows


def group_counties(rows):
  formatted_rows = []

  for row in rows:  # pylint: disable=too-many-nested-blocks
    first_county = defaultdict(list)
    first_county['title'] = row[0]

    second_county = defaultdict(list)
    # Last row only has one county.
    if 'County Clerk' in row[1]:
      second_county['title'] = row[1]
    current_county = first_county

    key = 'address'
    # Email section is inconsistent.
    email_section = False
    for i, line in enumerate(row):
      line = row[i]
      line = line.strip(' \n')
      if len(line) == 0:
        continue

      if 'County Clerk' in line:
        continue

      if 'Ph.' in line:
        key = 'phone_number'
      elif 'Fax' in line:
        key = 'fax'
      elif 'Email' in line:
        key = 'email'
      else:
        # Need to make sure following line doesn't have email suffix, too.
        if email_section:
          if not any(suffix in line for suffix in email_suffixes):
            if not any(suffix in row[i + 1] for suffix in email_suffixes):
              current_county = second_county
              key = 'address'
              email_section = False

      if any(suffix in line for suffix in email_suffixes):
        email_section = True

      current_county[key].append(line)

    formatted_rows.append(first_county)
    formatted_rows.append(second_county)

  # Remove last nonexistent county.
  formatted_rows = formatted_rows[:-1]

  return formatted_rows


def generate_county_dict_list(formatted_rows):
  counties = []

  for formatted_row in formatted_rows:
    county = defaultdict(list)
    county['county'] = formatted_row['title'].strip(' \n')[:-len(' Clerk')]
    county['locale'] = county['county']
    county['address'] = ' '.join(formatted_row['address'])
    # Remove space between '-' in zipcode.
    if '-' in county['address']:
      address_string = county['address']
      dash_index = address_string.index('-')
      if address_string[dash_index - 1] == ' ':
        address_string = address_string[:dash_index - 1] + address_string[dash_index:]
      if address_string[dash_index + 1] == ' ':
        address_string = address_string[:dash_index] + address_string[dash_index + 1:]
      county['address'] = address_string

    full_email = ''
    for email_line in formatted_row['email']:
      if 'Email' in email_line:
        continue
      full_email += email_line
      if any(suffix in email_line for suffix in email_suffixes):
        county['emails'].append(full_email)
        full_email = ''

    full_phone_number = ''
    for phone_number_line in formatted_row['phone_number']:
      phone_number_line = phone_number_line.strip('Ph. ')
      # One phone number as 'or' in it...
      if 'or' in phone_number_line:
        phone_number_line = phone_number_line[:phone_number_line.index('or')]
      # Some phone numbers span multiple lines.
      full_phone_number += phone_number_line
    # Manually add '-' since some phone numbers span multiple lines.
    full_phone_number = full_phone_number.replace('.', '')
    full_phone_number = (full_phone_number[:3] + "-" + full_phone_number[3:6] + "-" + full_phone_number[6:])
    county['phones'].append(full_phone_number.replace('.', '-'))

    for fax_line in formatted_row['fax']:
      fax_line = fax_line.strip('Fax ')
      county['faxes'].append(fax_line.replace('.', '-'))

    counties.append(dict(county))

  return counties


def fetch_data(verbose=True):  # pylint: disable=unused-argument
  text = fetch_pdf_text(PDF_URL)

  # Remove Page # of #
  text = re.sub(r"\sPage\s\n\d\sof\s\n\d\s", "", text)

  text = re.sub(r"[^\n](Ph.|Fax)", r"\n\1", text)
  lines = text.split('\n')

  # Remove first couples of lines which are PDF header.
  lines = lines[9:]

  rows = group_rows(lines)

  grouped_rows = group_counties(rows)

  counties = generate_county_dict_list(grouped_rows)

  return counties


if __name__ == '__main__':
  print(fetch_data())
