#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Randomise order of existing screenly database entries
#
__author__ = "Andrew McDonnell"
__copyright__ = "Copyright 2014"
__license__ = "GPLv2"
__version__ = "0.1"
__email__ = "bugs@andrewmcdonnell.net"

import sys
import sqlite3
import random
from contextlib import contextmanager

dbFile = "screenly.db"

#
# Arguments:
# $1 Path to screenly.db (defaults to $HOME/.screenly/screenly.db if unspecified)
#

if len(sys.argv) >= 2:
  dbFile = sys.argv[1]

conn = sqlite3.connect(dbFile, detect_types=sqlite3.PARSE_DECLTYPES)

# This function copied from screenly-ose/db.py
@contextmanager
def cursor(connection):
  cur = connection.cursor()
  yield cur
  cur.close()

# This function copied from screenly-ose/db.py
@contextmanager
def commit(connection):
  cur = connection.cursor()
  yield cur
  connection.commit()
  cur.close()

# SQL code derived from screenly-ose/asset_helpers.py
# Create sqlite db if it doesnt exist yet
with cursor(conn) as c:
  c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='assets'")
  if c.fetchone() is None:
    c.execute( 'CREATE TABLE assets(' + \
      'asset_id text primary key, name text, uri text, md5 text, ' + \
      'start_date timestamp, end_date timestamp, duration text, ' + \
      'mimetype text, is_enabled integer default 0, ' + \
      'nocache integer default 0, play_order integer default 0)')

# This takes a key value pair structure and converts it into a SQL insert statement
comma = ','.join
create = lambda keys: 'insert into assets (' + comma(keys) + ') values (' + comma(['?'] * len(keys)) + ')'

with cursor(conn) as c:
  c.execute('select asset_id, play_order from assets')
  assets = c.fetchall()
  N = len(assets)
  ordering = list(xrange(N))
  # Simple random shuffle, we dont need cryptographic complexity : just pick an order then remove it  

  with commit(conn) as c:
    for asset in assets:
      playOrder = random.choice(ordering)
      ordering.remove(playOrder)
      c.execute("update assets set play_order = %d where asset_id='%s'" % (playOrder, asset[0]))

