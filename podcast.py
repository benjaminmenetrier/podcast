#!/usr/bin/env python3

import argparse
import calendar
import datetime
import json
from rss_parser import Parser
from requests import get
import os
import pathlib
import re
import subprocess
import unicodedata
from urllib.request import urlretrieve

# Podcast files folder
podcast_dir=os.path.expanduser("~") + "/Music/Podcast" # => should be in parser

# Parser
parser = argparse.ArgumentParser()
#parser.add_argument("podcast_dir", help="Podcast directory", required=True)
parser.add_argument("--initialize", help="Initialization mode", action="store_true")
parser.add_argument("--dryrun", help="Dry run (no download)", action="store_true")

# Parse and print arguments
args = parser.parse_args()
print("Parameters:")
for arg in vars(args):
    if not arg is None:
        print(" - " + arg + ": " + str(getattr(args, arg)))

# Script directory
base_dir=os.path.dirname(os.path.realpath(__file__))

# Make directories
os.makedirs(podcast_dir, exist_ok=True)
os.makedirs(os.path.join(base_dir, "rss"), exist_ok=True)

# Load data base or initialize
if os.path.exists("database.json"):
  database = json.load(open("database.json"))
  with open("database.json.bak", "w", encoding ="utf8") as json_file: 
    json.dump(database, json_file, ensure_ascii=True, indent=2) 
else:
  database = {}

# Fill rss base
print("Processing RSS feeds")
rssbase = {}
for line in open(os.path.join(base_dir, "serverlist")):
  li=line.strip()
  if not li.startswith("#"):
    serverlist=line.rstrip().split(" ")
    url = serverlist[0]
    artist = serverlist[1]
    album = serverlist[2]
    
    response = get(url)
    rss = Parser.parse(response.text)

    for item in rss.channel.items:
      url = item.enclosure.attributes["url"]    
      itemData = {}
      itemData["title"] = item.title.content.replace("’", "'")
      filename = itemData["title"]
      filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
      filename = re.sub(r"[^\w\s-]", "", filename.lower())
      filename = re.sub(r"[-\s]+", "-", filename).strip("-_")
      itemData["artist"] = artist
      itemData["album"] = album
      itemData["url"] = item.enclosure.attributes["url"]
      if item.pub_date == None:
        itemData["date"] = "NoDate"
      else:
        dateElements = item.pub_date.content.split(" ")
        day = int(dateElements[1])
        month = list(calendar.month_abbr).index(dateElements[2])
        year = int(dateElements[3])
        itemData["date"] = str(datetime.date(year, month, day))
      filename = itemData["date"] + "_" + filename + ".mp3"
      rssbase[filename] = itemData

# Fill files base
filebase = {}
for item in pathlib.Path(podcast_dir).rglob("*.mp3"):
  # Get filename, album and artist
  head_tail = os.path.split(item)
  filename = head_tail[1]
  filebase[filename] = str(item)
with open("filebase.json", "w", encoding ="utf8") as json_file: 
  json.dump(filebase, json_file, ensure_ascii=True, indent=2) 

# Full list
fullbase = {}
for item in database:
  fullbase[item] = database[item]
for item in rssbase:
  if not item in fullbase:
    fullbase[item] = rssbase[item]
for item in filebase:
  if not item in fullbase:
    fullbase = filebase[item]

# Initialization case:
if args.initialize:
  with open("download.json", "w", encoding ="utf8") as json_file: 
    json.dump(fullbase, json_file, ensure_ascii=True, indent=2)
  dummy = input("Update download.json manually and type any key when it is done...")
  downloadbase = json.load(open("download.json"))

# Loop over full list
for item in fullbase:
  if (item in database) and (not item in filebase) and (not item in rssbase):
    # File already listened and not in RSS anymore: remove from database
    print("Removing " + database[item] + " from database")
    database.pop(item)
    with open("database.json", "w", encoding ="utf8") as json_file: 
      json.dump(database, json_file, ensure_ascii=True, indent=2) 
  elif (not item in database) and (item in filebase):
    # File present but not in database
    print("Resetting " + item + " in database")
    database[item] = filebase[item]
    with open("database.json", "w", encoding ="utf8") as json_file: 
      json.dump(database, json_file, ensure_ascii=True, indent=2) 
  elif (not item in database) and (not item in filebase) and (item in rssbase):
    # Download new file if neeeded
    url = rssbase[item]["url"]
    filepath = os.path.join(podcast_dir, rssbase[item]["artist"], rssbase[item]["album"], item)    
    toDownload = not args.dryrun
    if args.initialize and (not item in downloadbase):
      toDownload = False

    if toDownload:
      # Download
      print("Downloading " + filepath)
      os.makedirs(os.path.dirname(filepath), exist_ok=True)
      urlretrieve(url, filepath)

      # Update mp3 metadata
      subprocess.run(["id3v2", "--artist", rssbase[item]["artist"], filepath])
      subprocess.run(["id3v2", "--album", rssbase[item]["album"], filepath])
      subprocess.run(["id3v2", "--song", rssbase[item]["title"], filepath])
      subprocess.run(["id3v2", "--year", rssbase[item]["date"], filepath])
      subprocess.run(["id3v2", "--genre", "Podcast", filepath])

    # Add to database
    database[item] = filepath
    with open("database.json", "w", encoding ="utf8") as json_file: 
      json.dump(database, json_file, ensure_ascii=True, indent=2) 
  elif (not item in database) and (not item in filebase) and (not item in rssbase):
    raise Exception("Item " + item + " should not be in full list")
