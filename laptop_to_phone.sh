#!/bin/bash

# List mp3 files
src_dir="/home/benjaminm/Music/Podcast"
cd "$src_dir"
src_pods=`find . -name *.mp3`

dst_dir="/run/user/441385/gvfs/mtp:host=SAMSUNG_SAMSUNG_Android_R58W50AQRWF/Stockage interne/Podcasts"
cd "$dst_dir"
dst_pods=`find . -name *.mp3`

# Loop over source podcast
echo "Files copied on phone:"
for file in ${src_pods}; do
  echo "${dst_dir}/${file}"
  if ! test -f "${dst_dir}/${file}"; then
    # Copy podcast to destination
    dir="$(dirname "${file}")"
    mkdir -p "${dst_dir}/${dir}"
    gio copy "${src_dir}/${file}" "${dst_dir}/${file}"
  fi
done
IFS=${SAVEIFS}

exit 0
