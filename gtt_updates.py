import sys
import urllib.request
import gtfs_realtime_pb2
import protobuf_json
import json

URL =  "http://percorsieorari.gtt.to.it/das_gtfsrt/vehicle_position.aspx"

def get_updates():
    gtfs_realtime = gtfs_realtime_pb2.FeedMessage()
    req = urllib.request.urlopen(URL)
    data = req.read()
    gtfs_realtime.ParseFromString(data)

    data = protobuf_json.pb2json(gtfs_realtime)
    return data

def main(argv):

    data = get_updates()
    if len(argv) > 1:
        if argv[1] == "show":
            for up in data["entity"]:
                news = up["vehicle"]
                print(news["timestamp"], news["vehicle"]["label"],
                    news["trip"]["route_id"])
        elif argv[1] == "print":
            for up in data["entity"]:
                news = up["vehicle"]
                print(news["vehicle"]["label"])
                print("\t", up.keys())
    else:
        print(json.dumps(data, indent=3))
    return


if __name__ == '__main__':
    main(sys.argv)