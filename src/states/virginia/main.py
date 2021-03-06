import random
from time import sleep
import os
import logging
import glob
from bs4 import BeautifulSoup
from tqdm import tqdm
from common import cache_request, work_dir, to_list

BASE_URL = 'https://vote.elections.virginia.gov/VoterInformation/PublicContactLookup'


def get_locality_ids():
  page = cache_request(BASE_URL)
  soup = BeautifulSoup(page, 'lxml')
  return [option['value'] for option in soup.select('select>option') if option['value']]


def get_locality_datum(id_, attempt=0):
  if attempt > 5:
    return {}
  page = cache_request(
    BASE_URL,
    method='POST',
    data={'LocalityUid': id_},
    wait=random.uniform(2, 3),
  )
  soup = BeautifulSoup(page, 'lxml')
  results_wrappers = soup.select('.resultsWrapper')
  if results_wrappers:
    keys = results_wrappers[0].select('h5.display-lable')
    vals = results_wrappers[0].select('p.display-field')
    results = {key.text.strip(): val.text.strip() for key, val in zip(keys, vals)}
    locale = soup.select('select > option[selected="selected"]')[0].text.title()
    final = {
      'locale': locale,
      'county': locale if locale.endswith('County') else None,
      'city': locale if not locale.endswith('County') else None,
      'official': results['Registrar'],
      'emails': to_list(results['Email']),
      'faxes': to_list(results['Fax']),
      'url': results.get('URL'),
      'address': results.get('Mailing Address') or results.get('Address'),
      'physicalAddress': results.get('Physical Address'),
    }
    return {k: v for k, v in final.items() if v}
  cached_files = glob.glob(os.path.join(work_dir, '*.*'))
  latest_file = max(cached_files, key=os.path.getctime)
  logging.warning("error in Virginia file; deleting cached file %s; retry after wait", latest_file)
  os.remove(latest_file)
  sleep(30)
  return get_locality_datum(id_, attempt + 1)


def fetch_data(verbose=True):
  ids = get_locality_ids()
  locality_data = [get_locality_datum(id_) for id_ in tqdm(ids, disable=not verbose)]
  return locality_data


if __name__ == '__main__':
  print(fetch_data())
