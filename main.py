import requests
import time
from subprocess import call
import os
import sys
import re
import grequests
import datetime

the_thing = "ffmpeg -i <input.mp4> -hide_banner -vsync 1 -crf 19 -r 59.94 -vcodec libx264 -preset ultrafast -g 50 -acodec copy <output.mp4>"

cmd_string = "ffmpeg -i 210692252.mp4 -c copy -bsf:a aac_adtstoasc -fflags +genpts fuck.mp4"

the_list = [229480084]


def getRecentVodIds():
    link = "https://api.twitch.tv/kraken/channels/Destiny/videos?client_id=map2eprcvghxg8cdzdy2207giqnn64&broadcast_type=archive"
    r = requests.get(link)
    jsonData = r.json()
    vod_ids = [int(jsonData["videos"][n]["_id"][1:]) for n in range(10)]
    return vod_ids


def checkVod(vod_id):
    with open("completed.txt", "r") as f:
        lines = [line.replace("\n", "") for line in f]
        if str(vod_id) in lines:
            print("\n{} Already downloaded\n".format(vod_id))
            return 0
    file_list = os.listdir()
    if "{}.mp4".format(vod_id) in file_list:
        os.remove("{}.mp4".format(vod_id))
    return 1


def trim_extension_list(vod_id, segment_length):
    ext_list = []
    with open('list.txt', 'r') as f:
        for line in f:
            if str(vod_id) in line:
                times = re.findall(r'(?<=\s)[0-9:\-]+', line)
                for time in times:
                    start_time, end_time = time.split('-')
                    sh, sm, ss = start_time.split(':')
                    eh, em, es = end_time.split(':')
                    start_time_seconds = int(sh)*3600 + int(sm) * 60 + int(ss)
                    end_time_seconds = int(eh)*3600 + int(em) * 60 + int(es)
                    start_segment = int(start_time_seconds / segment_length)
                    end_segment = int(end_time_seconds / segment_length)
                    print(start_segment, end_segment)
                    for i in range(start_segment, end_segment):
                        ext_list.append(i)
    return [str(i) + ".ts" for i in ext_list]


def downloadVod(vod_id):
    check = checkVod(vod_id)
    if check == 0:
        return None
    token, sig = getTwitchApiData(vod_id)
    extension_list, vod_source_quality, segment_length = getUsherApiData(vod_id, token, sig)
    extension_list = trim_extension_list(vod_id, segment_length)
    url_list = [vod_source_quality + extension_list[i] for i in range(len(extension_list))]
    counter = 0
    try:
        os.mkdir("vods\\{}".format(vod_id))
    except FileExistsError:
        pass

    for i in range(0, len(extension_list), 5):
            sys.stdout.write("\r{}/{}".format(i, len(extension_list)))
            divided_url_list = url_list[i:i + 5]
            rs = (grequests.get(u) for u in divided_url_list)
            responses = grequests.map(rs, stream=True)
            for r in responses:
                if os.path.isfile("vods\\{}\\{}.ts".format(vod_id, counter)):
                    counter += 1
                    continue
                with open("vods\\{}\\{}.ts".format(vod_id, counter), "wb") as f:
                    counter += 1
                    for chunk in r.iter_content(chunk_size=255):
                        if chunk:
                            f.write(chunk)

    with open("completed.txt", "a") as f:
        f.write(str(vod_id) + "\n")


def getTwitchApiData(vod_id):
    client_id = "map2eprcvghxg8cdzdy2207giqnn64"
    link = "https://api.twitch.tv/api/vods/{}/access_token?&client_id={}".format(vod_id, client_id)
    r = requests.get(link)
    jsonData = r.json()
    token = jsonData["token"]
    sig = jsonData["sig"]
    return token, sig


def getUsherApiData(vod_id, token, sig):
    link = "http://usher.twitch.tv/vod/{}?nauthsig={}&nauth={}&allow_source=true".format(vod_id, sig, token)
    r = requests.get(link)
    vod_source_quality = re.findall(r'((http)(.+?)(.m3u8))', r.text)[0][0]
    r = requests.get(vod_source_quality)
    extensions = re.findall(r'([0-9]+(.ts))', r.text)
    extension_list = [extensions[i][0] for i in range(len(extensions))]
    segment_length = int(re.findall(r'(?<=#EXT-X-TARGETDURATION:)[0-9]+', r.text)[0])
    vod_data_link = re.findall(r'(http)(.+?)(chunked/)', vod_source_quality)[0]
    vod_data_link = vod_data_link[0] + vod_data_link[1] + vod_data_link[2]
    return extension_list, vod_data_link, segment_length


def main():
    # vod_ids = getRecentVodIds()[::-1]
    vod_ids = the_list
    for vod_id in vod_ids:
        print("\n{} Starting\n".format(vod_id))
        start = time.time()
        downloadVod(vod_id)
        print((time.time() - start)/3600)


main()
