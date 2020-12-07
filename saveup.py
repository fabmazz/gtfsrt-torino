import sys
import time
import datetime
from pathlib import Path
import gtt_updates
import io_lib

BASE_NAME_OUT = "updates_{}.json.gz"
TIME_SLEEP = 3
HOUR_CUT=16

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

def get_cut_date(next_day=False):
    now = datetime.datetime.now()
    if next_day:
        now += datetime.timedelta(days=1.)
    defin = datetime.datetime(now.year, now.month, now.day , HOUR_CUT)
    return defin

def save_ups(fin_set, outname):
    print("Saving..")
    gen = sorted(fin_set, key=lambda x: x.timest)

    io_lib.save_json_gzip(outname, [x.data for x in gen])

def main(argv):

    starttime = int(time.time())
    ts_cut = get_cut_date().timestamp()
    if ts_cut < starttime:
        ts_cut = get_cut_date(next_day=True).timestamp()
        print("Update changing date")
    r = get_parse_updates()

    fin_updates = set(r)
    count = 1
    outname = Path(BASE_NAME_OUT.format(starttime))
     
    try:
        while True:
            print(len(fin_updates))
            time.sleep(TIME_SLEEP)
        #n = set(get_all_updates())

            fin_updates = fin_updates.union(set(get_parse_updates()))
            mtimestamp = int(time.time())
            count += 1
            if count % 8 == 0 or mtimestamp > ts_cut:
                save_ups(fin_updates, outname)
            if mtimestamp > ts_cut:
                ### UPDATE HOUR TO SAVE
                print("Updating saving date")
                assert get_cut_date().timestamp() < mtimestamp
                ts_cut = get_cut_date(next_day=True).timestamp()
                outname = Path(BASE_NAME_OUT.format(mtimestamp))
                fin_updates = set()
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt")
        save_ups(fin_updates, outname)
    #print([hash(l) for l in v])
if __name__ == '__main__':
    main(sys.argv)