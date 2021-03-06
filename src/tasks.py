import os
import sys
import pkgutil
import importlib
import unittest
from invoke import task
from common import normalize_state, diff_and_save, public_dir

# Nevada has issues with captchas and isn't ready for automatic runs
SKIP_STATES = ['nevada']


@task
def collect(c, state):  # pylint: disable=unused-argument,invalid-name
  states_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'states')
  states_ispkg = {name: ispkg for _, name, ispkg in pkgutil.iter_modules([states_path])}

  if state in states_ispkg:
    states_ispkg = {state: states_ispkg[state]}
  elif state == 'limited':
    for skip in SKIP_STATES:
      states_ispkg.pop(skip)
  elif state != 'all':
    print(f"State '{state}' not found.")
    print("Available states are:\n\t" + "\n\t".join(states_ispkg.keys()))
    return

  for state_name, ispkg in states_ispkg.items():
    print(f'Process {state_name}')
    state_module = importlib.import_module(f"states.{state_name}{'.main' if ispkg else ''}")
    data = state_module.fetch_data(verbose=state != 'limited')
    data = normalize_state(data)
    diff_and_save(data, f'{state_name}.json', verbose=state != 'limited')


@task
def test(c):  # pylint: disable=unused-argument,invalid-name
  publics = [file for file in os.listdir(public_dir) if file.endswith('.json')]
  print(f"Files tested: {publics}")
  suite = unittest.TestLoader().discover('tests')
  result = unittest.TextTestRunner().run(suite)
  if not result.wasSuccessful():
    sys.exit(1)
