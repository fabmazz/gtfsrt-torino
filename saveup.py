import sys
import gtt_updates
import time
import json

BASE_NAME_OUT = "updates_{}.json.csv"

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

def get_all_updates():
    data = gtt_updates.get_updates()
    print(data.keys())
    all_up = [Update(d) for d in data["entity"]]

    return all_up

def main(argv):

    starttime = time.time()
    r = get_all_updates()

    v = set(r)
    print(len(v))
    time.sleep(2)
    n = set(get_all_updates())

    v.update(n)

    print(len(v))
    with open(sys.argv[1], "w") as f:
        d= [l.data for l in v]
        json.dump(d, f, indent=3)

    print([hash(l) for l in v])
if __name__ == '__main__':
    main(sys.argv)