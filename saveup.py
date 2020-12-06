import sys
import gtt_updates

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

    def __str__(self):
        return f"ts: {self.timest}, veh: {self.veh_num}, route: {self.route}"

def get_all_updates():
    data = gtt_updates.get_updates()

    all_up = [Update(d) for d in data["entity"]]

    return all_up

def main(argv):

    r = get_all_updates()

    v = set(r)

    for x in r:
        print(x)

    print(len(r), len(v))

if __name__ == '__main__':
    main(sys.argv)