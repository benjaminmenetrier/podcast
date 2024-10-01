#!/usr/bin/env python3

import argparse
import calendar
import datetime
import inquirer
import json
import taglib
from pydub import AudioSegment
import os
import pathlib
import re
from rss_parser import RSSParser
import subprocess
import unicodedata

# Podcast files folder (should be in parser)
podcast_dir = os.path.expanduser("~") + "/Music/Podcast"

# Parser
#parser = argparse.ArgumentParser()
#parser.add_argument("podcast_dir", help="Podcast directory", required=True)

# Parse and print arguments
#args = parser.parse_args()
#print("Parameters:")
#for arg in vars(args):
#    if not arg is None:
#        print(" - " + arg + ": " + str(getattr(args, arg)))

# Script directory
base_dir = os.path.dirname(os.path.realpath(__file__))

# Make directories
os.makedirs(podcast_dir, exist_ok=True)

# Load data base or initialize
if os.path.exists("database.json"):
  database = json.load(open("database.json"))
  with open("database.json.bak", "w", encoding ="utf8") as json_file:
    json.dump(database, json_file, ensure_ascii =True, indent=2)
else:
  database = {}

# Fill rss base
print("Processing RSS feeds")
rssbase = {}
for line in open(os.path.join(base_dir, "serverlist")):
  li = line.strip()
  if not li.startswith("#"):
    serverlist = line.rstrip().split(" ")
    url = serverlist[0]
    artist = serverlist[1]
    album = serverlist[2]
    print("- Checking " + url, end=" ... ")
    try:
      os.remove("rss_stream")
    except OSError:
      pass
    result = subprocess.run(['wget', '-O', 'rss_stream', '-o', 'wget_log', url])
    with open("rss_stream") as f:
      data = f.read()
    rss = RSSParser.parse(data)

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
        itemData["day"] = int(dateElements[1])
        itemData["month"] = list(calendar.month_abbr).index(dateElements[2])
        itemData["year"] = int(dateElements[3])
        itemData["date"] = str(datetime.date(itemData["year"], itemData["month"], itemData["day"]))
      filename = itemData["date"] + "_" + filename + ".mp3"
      rssbase[filename] = itemData
    print(str(len(rss.channel.items)) + " elements found")

# Fill files base
filebase = {}
for item in pathlib.Path(podcast_dir).rglob("*.mp3"):
  # Get filename, album and artist
  head_tail = os.path.split(item)
  filename = head_tail[1]
  filebase[filename] = str(item)
with open("filebase.json", "w", encoding="utf8") as json_file:
  json.dump(filebase, json_file, ensure_ascii=True, indent=2)

# Full list
fullbase = {}
for item in database:
  fullbase[item] = database[item]
#  print("From database: " + str(fullbase[item]))
for item in rssbase:
  if not item in fullbase:
    fullbase[item] = rssbase[item]
#    print("From rssbase: " + str(fullbase[item]))
for item in filebase:
  if not item in fullbase:
    fullbase[item] = filebase[item]
#    print("From filebase: " + str(fullbase[item]))

# Loop over full list
dlbase = {}
tagbase = {}
dltitlelist = []
dllist = []
for item in fullbase:
  if (item in database) and (not item in filebase) and (not item in rssbase):
    # File already listened and not in RSS anymore: remove from database
    print("Removing " + database[item] + " from database")
    database.pop(item)
  elif (not item in database) and (item in filebase):
    # File present but not in database
    print("Resetting " + item + " in database")
    database[item] = filebase[item]
  elif (not item in database) and (not item in filebase) and (item in rssbase):
    # Add to download list
    filepath = os.path.join(podcast_dir, rssbase[item]["artist"], rssbase[item]["album"], item)
    dlbase[item] = rssbase[item]
    dlbase[item]["filepath"] = filepath
    database[item] = filepath
    label = dlbase[item]["artist"] + " - " + dlbase[item]["album"] + " - " + dlbase[item]["title"] + " (" + dlbase[item]["date"] + ")"
    dllist.append((label,item))
  elif (item in database) and (item in filebase) and (item in rssbase):
    # Update tag potentially
    filepath = os.path.join(podcast_dir, rssbase[item]["artist"], rssbase[item]["album"], item)
    tagbase[item] = rssbase[item]
    tagbase[item]["filepath"] = filepath
  elif (not item in database) and (not item in filebase) and (not item in rssbase):
    raise Exception("Item " + item + " should not be in full list")

if len(dllist) > 0:
  # Ask user what should be actually downloaded
  questions = [inquirer.Checkbox("downloadList", message="Select podcasts to download", choices=dllist, default=dllist)]
  answers = inquirer.prompt(questions)

  # Download data
  for item in answers["downloadList"]:
    print("Downloading " + dlbase[item]["filepath"])

    # Make directory
    os.makedirs(os.path.dirname(dlbase[item]["filepath"]), exist_ok=True)

    # Download file
    extension = pathlib.Path(dlbase[item]["url"]).suffix
    result = subprocess.run(['wget', '-O', "tmp" + extension, '-o', 'wget_log', dlbase[item]["url"]])

    if extension == ".mp3":
      # Move file
      os.rename("tmp" + extension, dlbase[item]["filepath"])
    else:
      # Convert file to mp3
      audio = AudioSegment.from_file("tmp" + extension, format=extension.replace(".",""))
      audio.export(dlbase[item]["filepath"], format="mp3")

    # Update mp3 metadata
    with taglib.File(dlbase[item]["filepath"], save_on_exit=True) as song:
     song.tags["ARTIST"] = dlbase[item]["artist"]
     song.tags["ALBUM"] = dlbase[item]["album"]
     song.tags["TITLE"] = dlbase[item]["title"]
     song.tags["TRACKNUMBER"] = "1"
     song.tags["DATE"] = dlbase[item]["date"]
     song.tags["GENRE"] = "Podcast"
else:
  print("No new podcast to download")

#if len(tagbase) > 0:
#  # Ask user tags should be updated
#  questions = [inquirer.List("updateTags", message="Update tags?", choices=["yes", "no"], default="no")]
#  answers = inquirer.prompt(questions)
#  if answers["updateTags"] == "yes":
#    for item in tagbase:
#      print("Updating tag of " + tagbase[item]["filepath"])

#      # Update mp3 metadata
#      with taglib.File(tagbase[item]["filepath"], save_on_exit=True) as song:
#       song.tags["ARTIST"] = tagbase[item]["artist"]
#       song.tags["ALBUM"] = tagbase[item]["album"]
#       song.tags["TITLE"] = tagbase[item]["title"]
#       song.tags["TRACKNUMBER"] = "1"
#       song.tags["DATE"] = tagbase[item]["date"]
#       song.tags["GENRE"] = "Podcast"

# Write database
with open("database.json", "w", encoding ="utf8") as json_file:
  json.dump(database, json_file, ensure_ascii=True, indent=2)
