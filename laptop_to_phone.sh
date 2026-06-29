#!/usr/bin/env python

import os
import subprocess
import glob

# Podcast files folder (should be in parser)
if os.path.isdir("/media/benjaminm/BACKUP_SSD/Podcast"):
  src_dir = "/media/benjaminm/BACKUP_SSD/Podcast"
  dst_dir = "/run/user/441385/gvfs/mtp:host=SAMSUNG_SAMSUNG_Android_R58W50AQRWF/Carte SD/Podcast"
if os.path.isdir("/home/benjamin/BACKUP_SSD/Podcast"):
  src_dir = "/home/benjamin/BACKUP_SSD/Podcast"
  dst_dir = "/run/user/1000/gvfs/mtp:host=SAMSUNG_SAMSUNG_Android_R58W50AQRWF/Carte SD/Podcast"

# List mp3 files
src_pods = glob.glob(src_dir + "/*/*/*.mp3")
print("Number of podcasts on laptop: " + str(len(src_pods)))
dst_pods = glob.glob(dst_dir + "/*/*/*.mp3")
print("Number of podcasts on phone: " + str(len(dst_pods)))

# Loop over source podcasts
src_pods_to_transfer = []
for src_file in src_pods:
  dst_file = src_file.replace(src_dir, dst_dir)
  if not os.path.isfile(dst_file):
    src_pods_to_transfer.append(src_file)
print("Files to copy on phone: " + str(len(src_pods_to_transfer)))

# Copy podcasts to destination
for src_file in src_pods_to_transfer:
  dst_file = src_file.replace(src_dir, dst_dir)
  dst_split = os.path.split(dst_file)
  print("- " + dst_split[1])
  os.makedirs(dst_split[0], exist_ok=True)
  result = subprocess.run(['gio', 'copy', src_file, dst_file])

# Loop over destination podcasts
dst_pods_to_transfer = []
for dst_file in dst_pods:
  src_file = dst_file.replace(dst_dir, src_dir)
  if not os.path.isfile(src_file):
    dst_pods_to_transfer.append(dst_file)
print("Files to remove from phone: " + str(len(dst_pods_to_transfer)))

# Remove podcast from destination
for dst_file in dst_pods_to_transfer:
  src_file = dst_file.replace(dst_dir, src_dir)
  src_split = os.path.split(src_file)
  print("- " + src_split[1])
  result = subprocess.run(['gio', 'remove', dst_file])
