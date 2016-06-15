#!/usr/bin/env python

import sys
import time
import traceback
from argparse import ArgumentParser
from collections import namedtuple
from urlparse import urljoin

import requests

discotimeout = 4 # In seconds.
tokenkey = 'server-token'
resplim = 64 # Response output character limit; only printed if not OK.

Result = namedtuple('Result', ('code', 'message'))

class Main(object):

  # Parse arguments.
  def __init__(self):
    parser = ArgumentParser(description='Check Mesos service for health.')
    parser.add_argument('-d', '--discovery', required=True,
      help='discovery server URL')
    parser.add_argument('-s', '--service', required=True,
      help='service name to check')
    parser.add_argument('-e', '--endpoint', default='health',
      help='endpoint to check; default %(default)r')
    parser.add_argument('-t', '--timeout', type=float, default=5,
      help='endpoint check timeout in seconds; default %(default)s')
    parser.add_argument('-c', '--critical', type=int, default=1,
      help='minimum instances before critical; default %(default)s; '
      'set to 0 to disable')
    parser.add_argument('-w', '--warn', type=int, default=1,
      help='minimum instances before warning; default %(default)s; '
      'set to 0 to disable')
    args = parser.parse_args()

    # Parser error terminates process with code 2 ("CRITICAL").
    if args.timeout <= 0:
      parser.error('timeout must be positive')
    if args.critical < 0:
      parser.error('critical must be non-negative')
    if args.warn < 0:
      parser.error('warn must be non-negative')
    if args.warn < args.critical:
      parser.error('warn must be at least as large as critical')

    self.args = args

  def get_announcements(self):
    url = urljoin(self.args.discovery, 'state')
    state = requests.get(url, timeout=discotimeout).json()
    return [a for a in state if a['serviceType'] == self.args.service]

  @staticmethod
  def count_announcements(announcements):
    seen = set()
    count = 0
    for ann in announcements:
      metadata = ann.get('metadata', {})
      if tokenkey not in metadata:
        # No token; this is ok.
        count += 1
        continue
      token = metadata[tokenkey]
      if token not in seen:
        seen.add(token)
        count += 1
    return count

  @staticmethod
  def make_result(code, topic, message):
    state = {2: 'critical', 1: 'warning', 0: 'ok'}[code]
    return Result(code, '%s %s: %s' % (topic, state, message))

  @classmethod
  def make_result_with_announcement(cls, code, topic, ann, message):
    msg = '%s\nservice URI %s' % (message, ann['serviceUri'])
    return cls.make_result(code, topic, msg)

  def make_announcement_result(self, code, count):
    msg = '%s\ncrit./warn thresh.: %s/%s' % (
      count, self.args.critical, self.args.warn)
    return self.make_result(code, 'announcements', msg)

  @classmethod
  def make_response_result(cls, code, ann, status_code, duration, text):
    msg = '%s from endpoint\nduration %.3fs' % (status_code, duration)
    if code != 0:
      if len(text) > resplim: text = text[:resplim] + '...'
      msg += '\n' + text
    return cls.make_result_with_announcement(code, 'health', ann, msg)

  def make_timeout_result(self, ann, type):
    return self.make_result_with_announcement(
      2, '%s timeout' % type, ann, 'thresh. %.3f' % self.args.timeout)

  def check_endpoint(self, ann):
    serviceuri = ann['serviceUri']
    url = urljoin(serviceuri, self.args.endpoint)
    start = time.time()
    try:
      resp = requests.get(url, timeout=self.args.timeout)
      duration = time.time() - start
      code = resp.status_code // 100
      if code == 2:
        return self.make_response_result(
          0, ann, resp.status_code, duration, resp.text)
      if code == 4:
        return self.make_response_result(
          1, ann, resp.status_code, duration, resp.text)
      if code == 5:
        return self.make_response_result(
          2, ann, resp.status_code, duration, resp.text)
      raise Exception('unexpected status code', resp.status_code)
    except requests.exceptions.ConnectTimeout:
      return self.make_timeout_result(ann, 'connect')
    except requests.exceptions.ReadTimeout:
      return self.make_timeout_result(ann, 'read')
    except requests.exceptions.RequestException:
      return self.make_result_with_announcement(2, 'health',
        ann, 'unhandled exception\n' + traceback.format_exc())

  def run(self):
    try:
      announcements = self.get_announcements()
    except Exception:
      print 'failed to get announcements'
      print traceback.format_exc()
      return 3

    # Will contain Result instances.
    results = []

    count = self.count_announcements(announcements)
    if count < self.args.critical:
      results.append(self.make_announcement_result(2, count))
    elif count < self.args.warn:
      results.append(self.make_announcement_result(1, count))
    else:
      results.append(self.make_announcement_result(0, count))

    for ann in announcements:
      res = self.check_endpoint(ann)
      if res is not None: results.append(res)

    # Print worst results first and return with worst code.
    results.sort(reverse=True)
    for res in results:
      print res.message
      print '---'
    return results[0].code

sys.exit(Main().run())
