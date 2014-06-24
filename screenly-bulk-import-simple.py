#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# Bulk importer for screenly, designed to just show all photos always.
# Useful for special events where you just want to run on a background TV somewhere.
# Also preset all images to show for same duration for simplicity.
# Handy for building a new SD card and giving it to someone who knows nothing 
# about Linux or wireless networking or anything but can plug in a Raspberry Pi.
#
# Usage is simple:
# 1. Create a new empty working directory
# 2. Change into that directory
# 3. Copy an existing sqlite.db there if required
# 4. Run this script
#
#    ../screenly-tools/screenly-bulk-import-simple.py BaseImagesDir/ " Some Title "
#
# 5. This script will create assets/ relative to the working directory
#
# It is advisable to have a space around the text in case the television doesnt size properly.#
#
# When finished, copy screenly_assets/* into screenly_assets/ on the destination RPi
# It will then be necessary to reset the timestamp of screenly.db to before 
# the time set in /etc/fake-hwclock.data if there is no network with NTP synchronisation,
# otherwise screenly will continually think the database has changed and reset to the start
#
# To simplify deployment, this process can be run on a normal Linux PC
# and the sqlite db and assets/ files copied to the RPi after
#
# 0. Create new sqlite database if it doesnt exist, and screenly_assets directory
# 1. Traverse directory tree of images
# 2. Generate screenly asset hash
# 3. Copy to screenly_assets directory
# 4. Add to sqlite database
# 5. Preset the start date to 1/1/2014 and the end date to show until 31/12/2029
#
__author__ = "Andrew McDonnell"
__copyright__ = "Copyright 2014"
__license__ = "GPLv2"
__version__ = "0.1"
__email__ = "bugs@andrewmcdonnell.net"

import sys
import os
import shutil
import datetime
import uuid
import os.path
import sqlite3
from contextlib import contextmanager

dbFile = "screenly.db"
assetDir = "screenly_assets"
imageDuration = 10
start =  datetime.datetime(2014, 1, 1, 0, 0)
finish =  datetime.datetime(2029, 12, 31, 23, 59)
# TODO: Work out what to do on systems that dont have this font...
bannerFont = "Liberation-Sans-Bold"
bannerText = "Photos"
# Currently we have to deal with screenly wanting the full path in the sqlite database.
targetAssetPath = os.path.join("/home/pi", assetDir)



#
# Arguments:
# $1 Path to base directory containing all photos to be imported
# $2 Text to display on a top banner
# $3 If specified, duration per image in integer seconds.
#    No error checking done, so dont enter a silly or negative integer
#
# To keep things simple, assume we are in directory to save to
#

if len(sys.argv) < 2:
  print "Missing images directory argument."
  sys.exit(1)

if len(sys.argv) >= 3:
  bannerText = sys.argv[2]


if len(sys.argv) >= 4:
  imageDuration = int(sys.argv[3])

# For now if filesystem operations fail, just let exceptions be thrown

if not os.path.isdir(assetDir):
  os.mkdir( assetDir)

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

# To check what is going on:
#
#   sqlite3 screenly.db "select * from assets" (etc)

# Traverse directory
imagesDir = sys.argv[1]
order = 1
for directory, sub, files in os.walk(imagesDir):
  for filename in files:
    imagePath = os.path.join(directory, filename)
    #        print('%s' % os.path.join(directory, filename))
    # Generate asset hash
    assetHash = uuid.uuid4().hex

    # TODO test we haven't already got one by some incredible fluke
    #      For the moment, we effectively replace
    
    # Copy image to asset directory
    assetDest = os.path.join(assetDir, assetHash)
    # shutil.copyfile( imagePath, assetDest)

    # Imagemagick operations - shrink / extend size and reduce resolution of large images
    # 1. Put a gold banner at top of black screen
    # 2. Put image in middle.
    # 3. Assume capable of running in 1920x1080
    cmd = "convert \\( -background black -fill \"#fff725\" -font \"%s\" -pointsize 116 -gravity Center -size 1840x180 " \
                     "caption:\"%s\" -gravity North -extent 1840x1080 \\) " \
                  "\\( \"%s\" -resize 1664x728 -background black -compose Copy -gravity Center -extent 1920x860 \\) " \
                  "-background blue -gravity South -composite \"jpeg:%s\"" % (bannerFont, bannerText, imagePath, assetDest)
    #print cmd
    os.system(cmd)

    # TODO: if command fails, dont add to database

    # Generate entry in database
    title = filename
    asset = {
        'asset_id': assetHash,
        'name': title,
        'uri': os.path.join(targetAssetPath, assetHash),
        'start_date': start,
        'play_order': order,
        'end_date': finish,
        'duration': imageDuration,
        'mimetype': "image",
        'is_enabled': 1
    }
    with commit(conn) as c:
      c.execute(create(asset.keys()), asset.values())

    # TODO: make this optional
    print "Imported: %s --> %s" % (title, assetHash)

    order = order + 1

# TODO: pre-scan directory so instead we can print a progressive count.
