import sys
import time
import datetime
import urllib.error
import http.client
from pathlib import Path
import gtt_updates
import io_lib

BASE_NAME_OUT = "updates_{}.json.gz"
TIME_SLEEP = 3
HOUR_CUT=4

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
    gotit = False
    while not gotit:
        try:
            data = gtt_updates.get_updates()
            gotit = True
        except urllib.error.HTTPError as e:
            print("Got "+e.msg+" , Retrying")
        except http.client.RemoteDisconnected as e:
            print("Remote disconnected, Retrying")
    keys = data.keys()
    if len(keys)>2 or "header" not in keys or "entity" not in keys:
        print(keys)
    
    if "entity" not in keys:
        print("NO PAYLOAD")
        return tuple()

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
    mtimestamp = int(time.time())
    try:
        while True:
        
            print(mtimestamp, "\t", len(fin_updates))

            time.sleep(TIME_SLEEP)
        #n = set(get_all_updates())

            fin_updates = fin_updates.union(set(get_parse_updates()))
            mtimestamp = int(time.time())
            count += 1
            save_too_many = mtimestamp > ts_cut or len(fin_updates) > 150000
            if count % 10 == 0 or save_too_many:
                save_ups(fin_updates, outname)
            if save_too_many:
                ### UPDATE HOUR TO SAVE
                print("Updating saving date")
                if mtimestamp > ts_cut:
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