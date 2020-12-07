import sys
import time
import json
from pathlib import Path
import gtt_updates
import io_lib

BASE_NAME_OUT = "updates_{}.json.gz"

class Update:
    """
    Basic class to hold the updates data
    """
    def __init__(self, up_data):
        news = up_data["vehicle"]
        self.timest = news["timestamp"]
        self.veh_num = news["vehicle"]["label"]
        self.route =  news["trip"]["route_id"]

        self.data = up_data

    def __hash__(self):
        return hash((self.timest, self.veh_num, self.route))
    
    def __eq__(self, other):
        return self.timest == other.timest and self.veh_num == other.veh_num and self.route == other.route

    def __str__(self):
        return f"ts: {self.timest}, veh: {self.veh_num}, route: {self.route}"

def get_parse_updates():
    data = gtt_updates.get_updates()
    print(data.keys())

    return (Update(d) for d in data["entity"])

def main(argv):

    starttime = int(time.time())
    r = get_parse_updates()

    fin_updates = set(r)
    count = 1
    outname = Path(BASE_NAME_OUT.format(starttime))
    while True:
        print(len(fin_updates))
        time.sleep(2)
    #n = set(get_all_updates())

        fin_updates = fin_updates.union(get_parse_updates())
        count += 1
        if count % 3 == 0:
            print("Saving..")
            gen = sorted(fin_updates, key=lambda x: x.timest)

            io_lib.save_json_gzip(outname, [x.data for x in gen])
    
    #print([hash(l) for l in v])
if __name__ == '__main__':
    main(sys.argv)