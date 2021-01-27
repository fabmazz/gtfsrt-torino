import sys
import json
import time
import requests
import protobuf_json

import gtfs_realtime_pb2

URL =  "http://percorsieorari.gtt.to.it/das_gtfsrt/vehicle_position.aspx"


def get_updates(session=None):
    gtfs_realtime = gtfs_realtime_pb2.FeedMessage()
    if session is not None:
        c = session.get(URL)
    else:
        c = requests.get(URL)
    #req = urllib.request.urlopen(URL)
    #data = req.read()
    gtfs_realtime.ParseFromString(c.content)

    data = protobuf_json.pb2json(gtfs_realtime)
    return data

def get_up_obj(url=None,printout=False):
    if url is None:
        url = URL
    gtfs_realtime = gtfs_realtime_pb2.FeedMessage()
    req = urllib.request.urlopen(url)
    data = req.read()
    if printout:
        print(data)
    gtfs_realtime.ParseFromString(data)

    return gtfs_realtime

def check_update(up):
    mid = up["id"]
    in_id = up["vehicle"]["vehicle"]["id"]
    return mid == in_id


def main(argv):

    data = get_updates()
    if len(argv) > 1:
        if argv[1] == "show":
            for up in data["entity"]:
                news = up["vehicle"]
                print(news["timestamp"], news["vehicle"]["label"],
                    news["trip"]["route_id"])
                print("\t", up.keys())

        elif argv[1] == "checkid":
            all_good = True
            for up in data["entity"]:
                all_good = all_good and check_update(up)
            print("IDs are the same field: ", all_good)


    else:
        print(json.dumps(data, indent=3))
    return


if __name__ == '__main__':
    main(sys.argv)