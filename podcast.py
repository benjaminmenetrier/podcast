#!/usr/bin/env python3

import os
import json
from urllib.request import urlretrieve
from rss_parser import Parser
from requests import get
import pathlib
import subprocess
import datetime
import calendar

# Podcast files folder
podcast_dir=os.path.expanduser('~') + "/Music/PodcastTest"

# Script directory
base_dir=os.path.dirname(os.path.realpath(__file__))

# Make directories
os.makedirs(podcast_dir, exist_ok=True)
os.makedirs(os.path.join(base_dir, "rss"), exist_ok=True)

# Load data base or initialize
if os.path.exists('database.json'):
  database = json.load(open("database.json"))
  with open('database.json.bak', 'w', encoding ='utf8') as json_file: 
  	json.dump(database, json_file, ensure_ascii=True, indent=2) 
else:
  database = {}

# Fill rss base
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
    print(rss)
    exit()
    for item in rss.channel.items:
      url = item.enclosure.attributes['url']    
      itemData = {}
      itemData["title"] = item.title.content.replace("’", "'")
      filename = "".join(x for x in itemData["title"] if x.isalnum())
      itemData["artist"] = artist
      itemData["album"] = album
      itemData["url"] = item.enclosure.attributes['url']
      dateElements = item.pub_date.content.split(" ")
      day = int(dateElements[1])
      month = list(calendar.month_abbr).index(dateElements[2])
      year = int(dateElements[3])
      itemData["date"] = str(datetime.date(year, month, day))
      rssbase[filename] = itemData

# Fill files base
filebase = {}
for item in pathlib.Path(podcast_dir).rglob("*.mp3"):
  # Get filename, album and artist
  head_tail = os.path.split(item)
  filename = head_tail[1]
  filebase[filename] = str(item)

# Full list
fulllist = []
for item in database:
  fulllist.append(item)
for item in rssbase:
  if not item in fulllist:
    fulllist.append(item)
for item in filebase:
  if not item in fulllist:
    fulllist.append(item)  

# Loop over full list
for item in fulllist:
  print("File " + item)
  if (item in database) and (not item in filebase) and (not item in rssbase):
    # File already listened and not in RSS anymore: remove from database
    print("Removing " + database[item] + " from database")
    database.pop(item)
    with open('database.json', 'w', encoding ='utf8') as json_file: 
    	json.dump(database, json_file, ensure_ascii=True, indent=2) 
  elif (not item in database) and (item in filebase):
    # File present but not in database
    print("Resetting " + item + " in database")
    database[item] = filebase[item]
    with open('database.json', 'w', encoding ='utf8') as json_file: 
    	json.dump(database, json_file, ensure_ascii=True, indent=2) 
  elif (not item in database) and (not item in filebase) and (item in rssbase):
    # Download new file, change metadata and add to database
    url = rssbase[item]["url"]
    filepath = os.path.join(podcast_dir, rssbase[item]["artist"], rssbase[item]["album"], item)
    name = input("Download " + rssbase[item]["artist"] + " - " + rssbase[item]["album"] + " - " + rssbase[item]["title"] + " ? [y] ")
    if name == "y":
      print("Downloading " + filepath)
      os.makedirs(os.path.dirname(filepath), exist_ok=True)
      urlretrieve(url, filepath)     
      subprocess.run(["id3v2", "--artist", rssbase[item]["artist"], filepath])
      subprocess.run(["id3v2", "--album", rssbase[item]["album"], filepath])
      subprocess.run(["id3v2", "--song", rssbase[item]["title"], filepath])
      subprocess.run(["id3v2", "--year", rssbase[item]["date"], filepath])
      subprocess.run(["id3v2", "--genre", "Podcast", filepath])
    database[item] = filepath
    with open('database.json', 'w', encoding ='utf8') as json_file: 
    	json.dump(database, json_file, ensure_ascii=True, indent=2) 
  elif (not item in database) and (not item in filebase) and (not item in rssbase):
    raise Exception("Item " + item + " should not be in full list")
