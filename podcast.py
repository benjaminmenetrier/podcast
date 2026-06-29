#!/usr/bin/env python

import argparse
import calendar
import datetime
import feedparser
import inquirer
import json
import taglib
from pydub import AudioSegment
import os
import pathlib
import re
import subprocess
import unicodedata
import sys

# Podcast files folder (should be in parser)
if os.path.isdir("/media/benjaminm/BACKUP_SSD/Podcast"):
  podcast_dir = "/media/benjaminm/BACKUP_SSD/Podcast"
if os.path.isdir("/home/benjamin/BACKUP_SSD/Podcast"):
  podcast_dir = "/home/benjamin/BACKUP_SSD/Podcast"

# Parser
#parser = argparse.ArgumentParser()
#parser.add_argument("podcast_dir", help="Podcast directory", required=True)

# Parse and print arguments
#args = parser.parse_args()
#print("Parameters:")
#for arg in vars(args):
#    if not arg is None:
#        print(" - " + arg + ": " + str(getattr(args, arg)))

# Make directories
os.makedirs(podcast_dir, exist_ok=True)

# Load data base or initialize
if os.path.exists(os.path.join(podcast_dir, "database.json")):
  database = json.load(open(os.path.join(podcast_dir, "database.json")))
  with open(os.path.join(podcast_dir, "database.json.bak"), "w", encoding ="utf8") as json_file:
    json.dump(database, json_file, ensure_ascii =True, indent=2)
else:
  database = {}

# Fill rss base
print("Processing RSS feeds")
rssbase = {}
for line in open(os.path.join(podcast_dir, "serverlist")):
  li = line.strip()
  if not li.startswith("#"):
    serverlist = line.rstrip().split(" ")
    url = serverlist[0]
    artist = serverlist[1]
    album = serverlist[2]
    print("- Checking " + artist + " - " + album, end=" ... ")
    rss = feedparser.parse(url)

    for item in rss["entries"]:
      itemData = {}
      itemData["title"] = item["title"].replace("’", "'")
      itemData["title"] = item["title"].replace("&#x27;", "'")
      filename = itemData["title"]
      filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
      filename = re.sub(r"[^\w\s-]", "", filename.lower())
      filename = re.sub(r"[-\s]+", "-", filename).strip("-_")
      itemData["artist"] = artist
      itemData["album"] = album
      for link in item["links"]:
        if "audio/" in  link["type"]:
          itemData["url"] = link["href"]
      if not "url" in itemData:
        print("")
        print("Cannot find file url for item: " + str(item))
        exit()
      if "published" in item:
        dateElements = item["published"].split(" ")
        itemData["day"] = int(dateElements[1])
        itemData["month"] = list(calendar.month_abbr).index(dateElements[2])
        itemData["year"] = int(dateElements[3])
        itemData["date"] = str(datetime.date(itemData["year"], itemData["month"], itemData["day"]))
      else:
        itemData["date"] = "NoDate"
      filename = itemData["date"] + "_" + filename + ".mp3"
      rssbase[filename] = itemData
    print(str(len(rss["entries"])) + " elements found")

    if len(rss["entries"]) == 0:
      raise Exception("Cannot read feed: " + url)

# Fill files base
filebase = {}
for item in pathlib.Path(podcast_dir).rglob("*.mp3"):
  # Get filename, album and artist
  head_tail = os.path.split(item)
  filename = head_tail[1]
  filebase[filename] = str(item)
with open(os.path.join(podcast_dir, "filebase.json"), "w", encoding="utf8") as json_file:
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
    dlbase[item]["label"] = dlbase[item]["artist"] + " - " + dlbase[item]["album"] + " - " + dlbase[item]["title"] + " (" + dlbase[item]["date"] + ")"
    dllist.append((dlbase[item]["label"],item))
  elif (item in database) and (item in filebase) and (item in rssbase):
    # Update tag potentially
    filepath = os.path.join(podcast_dir, rssbase[item]["artist"], rssbase[item]["album"], item)
    tagbase[item] = rssbase[item]
    tagbase[item]["filepath"] = filepath
  elif (not item in database) and (not item in filebase) and (not item in rssbase):
    raise Exception("Item " + item + " should not be in full list")

# Write database
with open(os.path.join(podcast_dir, "database.json"), "w", encoding ="utf8") as json_file:
  json.dump(database, json_file, ensure_ascii=True, indent=2)

if len(dllist) > 0:
  # Ask user what should be actually downloaded
  questions = [inquirer.Checkbox("downloadList", message="Select podcasts to download", choices=dllist, default=dllist)]
#  questions = [inquirer.Checkbox("downloadList", message="Select podcasts to download", choices=dllist, default=[])]
  answers = inquirer.prompt(questions)

  # Skip non-downloaded items
  for item in dlbase:
    if not item in answers["downloadList"]:
      print("Skipping " + dlbase[item]["label"])

      # Update database
      database[item] = dlbase[item]["filepath"]

      # Write database
      with open(os.path.join(podcast_dir, "database.json"), "w", encoding ="utf8") as json_file:
        json.dump(database, json_file, ensure_ascii=True, indent=2)

  # Download data
  for item in answers["downloadList"]:
    print("Downloading " + dlbase[item]["label"])

    # Make directory
    os.makedirs(os.path.dirname(dlbase[item]["filepath"]), exist_ok=True)

    # Download file
    extension = pathlib.Path(dlbase[item]["url"]).suffix
    if "?" in extension:
      extension = extension.split('?', 1)[0]
    print('wget -O ' + os.path.join(podcast_dir, "tmp") + extension + ' -o wget_log ' + dlbase[item]["url"])
    result = subprocess.run(['wget', '-O', os.path.join(podcast_dir, "tmp") + extension, '-o', 'wget_log', dlbase[item]["url"]])
    if result.returncode != 0:
      raise Exception("Cannot download: " + dlbase[item]["url"] + ", error code: " + str(result.returncode))

    if extension == ".mp3":
      # Move file
      os.rename(os.path.join(podcast_dir, "tmp") + extension, dlbase[item]["filepath"])
    else:
      # Convert file to mp3
      audio = AudioSegment.from_file(os.path.join(podcast_dir, "tmp") + extension, format=extension.replace(".",""))
      audio.export(dlbase[item]["filepath"], format="mp3")

    # Update mp3 metadata
    with taglib.File(dlbase[item]["filepath"], save_on_exit=True) as song:
      song.tags["ARTIST"] = dlbase[item]["artist"]
      song.tags["ALBUM"] = dlbase[item]["album"]
      song.tags["TITLE"] = dlbase[item]["title"]
      song.tags["TRACKNUMBER"] = "1"
      song.tags["DATE"] = dlbase[item]["date"]
      song.tags["GENRE"] = "Podcast"

    # Update database
    database[item] = dlbase[item]["filepath"]

    # Write database
    with open(os.path.join(podcast_dir, "database.json"), "w", encoding ="utf8") as json_file:
      json.dump(database, json_file, ensure_ascii=True, indent=2)
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
