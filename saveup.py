"""
Copyright (C) 2022  Fabio Mazza
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""
from collections import namedtuple
import sys
import time
import datetime
import argparse
from threading import Lock
import urllib.error
import http.client
from pathlib import Path
from warnings import warn
import requests
import gtt_updates
import io_lib, iomsg
import matolib

BASE_NAME_OUT = "updates_{}.msgpack.zstd"
OUT_FOLDER="data"
TIME_SLEEP = 3
HOUR_CUT=(3,45)
MAX_UPDATES=130_000

HOURS_REMAKE_SESS = 0.6

from concurrent.futures import ThreadPoolExecutor, wait

executor = ThreadPoolExecutor(3)

PATTERNS_FUT = []
TRIPS_FUT = []
PATTERNS_LOCK = Lock()
TRIPS_LOCK = Lock()
N_TRIPS_SAVED = 0
def create_mparser():

    parser = argparse.ArgumentParser("Updater saver")

    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no-data", action="store_true",dest="no_data")

    return parser

def download_patternInfo(patterncode):
    global PATTERNS_DOWN
    try:
        pattern = matolib.get_pattern_info(patterncode)

        code = pattern["code"]
        with PATTERNS_LOCK:
            ## use lock
            PATTERNS_DOWN[code] = pattern
        
    except Exception as e:
        print(f"Cannot download pattern {patterncode}, ex: {e}", file=sys.stderr)

def download_tripinfo(gtfsname):
    global DOWNLOADED_TRIPS, TRIPS_DOWN, PATTERNS_DOWN
    
    gtfsid=f"gtt:{gtfsname}"
    if gtfsid=="gtt:NoneU":
        # in some cases the trip is a text 'None'
        return
    if gtfsid in DOWNLOADED_TRIPS:
        ## already downloaded
        return
    try:
        trip_d = matolib.get_trip_info(gtfsid)

        tripelm = dict(gtfsId=trip_d["gtfsId"], serviceId=trip_d["serviceId"], headsign=trip_d["tripHeadsign"],
                               routeId=trip_d["route"]["gtfsId"], patternCode=trip_d["pattern"]["code"])
        with TRIPS_LOCK:
            TRIPS_DOWN.append(tripelm)
            DOWNLOADED_TRIPS.add(gtfsid)

        patCode = tripelm["patternCode"]
        if(patCode not in PATTERNS_DOWN):
            PATTERNS_FUT.append(
                executor.submit(download_patternInfo, patCode)
            )
    except Exception as e:
        ### nothing work
        #print(f"Download info for trip {gtfsid},  gtfsid: {gtfsid}"")
        print(f"Failed to download data for trip {gtfsid}, error: {e}",file=sys.stderr)

def save_patterns_done(patterns_file):
    global PATTERNS_FUT, PATTERNS_DOWN
    res = wait(PATTERNS_FUT)
    with PATTERNS_LOCK:
        PATTERNS_FUT = list(filter(lambda x: not x.done(),PATTERNS_FUT))
        t = time.time()
        io_lib.save_json_zstd(patterns_file,PATTERNS_DOWN, level=5)
        print(f"Saved the patterns in {time.time()-t:.3f} s")

def save_trips_need(trips_file):
    global TRIPS_FUT, TRIPS_DOWN, N_TRIPS_SAVED
    res = wait(TRIPS_FUT)
    with TRIPS_LOCK:
        TRIPS_FUT = list(filter(lambda x: not x.done(),TRIPS_FUT))
        if len(TRIPS_DOWN) > N_TRIPS_SAVED:
            ## save patterns
            t = time.time()
            io_lib.save_json_zstd(trips_file,TRIPS_DOWN, level=6)
            print(f"Saved the trips in {time.time()-t:.3f} s")
            N_TRIPS_SAVED = len(TRIPS_DOWN)


format_date = lambda date : f"{date.year}{date.month:02d}{date.day:02d}{date.hour:02d}{date.minute:02d}"
format_date_day =  lambda date : f"{date.year}{date.month:02d}{date.day:02d}"
format_date_halfmonth =  lambda date : f"{date.year}{date.month:02d}00" if date.day < 15 else f"{date.year}{date.month:02d}15"
format_date_sec = lambda date : f"{date.year}{date.month:02d}{date.day:02d}{date.hour:02d}{date.minute:02d}{date.second:02d}"


get_pattern_fname = lambda outfold: outfold/f"patterns_{format_date_halfmonth(datetime.datetime.now())}.json.zstd"
get_trips_mapname = lambda outfold: outfold/f"trips_{io_lib.format_date_twodays(datetime.datetime.now())}.json.zstd"

#def get_string_name_day()



class Update:
    """
    Basic class to hold the updates data
    """
    def __init__(self, up_data):
        news = up_data["vehicle"]
        tripdat = news["trip"]
        self.timest = news["timestamp"]
        self.veh_num = news["vehicle"]["label"]
        self.route =  tripdat["route_id"]
        self.trip_id = tripdat["trip_id"]
        #self.start_date 

        self.data = {
            "timestamp": self.timest,
            "veh": self.veh_num
        }
        for k in tripdat:
            self.data[k] = tripdat[k]
        for k in news["position"]:
            self.data[k] = news["position"][k]


    def __hash__(self):
        return hash((self.timest, self.veh_num, self.route, self.trip_id))
    
    def __eq__(self, other):
        return self.timest == other.timest and self.veh_num == other.veh_num and self.route == other.route

    def __str__(self):
        return f"ts: {self.timest}, veh: {self.veh_num}, route: {self.route}"

    def get_service_day(self):
        try:
            return self.data["start_date"]
        except:
            print("Update has no start_date")
            return "00000000"

Result = namedtuple("Result", ["data","error"])

def get_parse_updates(session=None, ntries=40):
    gotit = False
    count=0
    while (not gotit and count<ntries):
        try:
            data = gtt_updates.get_updates(session=session)
            gotit = True
        except urllib.error.HTTPError as e:
            print("Got "+e.msg+" , Retrying")
        except http.client.RemoteDisconnected as e:
            print("Remote disconnected, Retrying")
        except Exception as ex:
            print(f"Generic error: {ex}, retrying")
        finally:
            count+=1

    if not gotit:
        warn(f"Cannot get an update after {ntries} trials")
        print(f"Cannot get an update after {ntries} trials")
        return Result(tuple(),"TRIALOUT")

    keys = data.keys()
    if len(keys)>2 or "header" not in keys or "entity" not in keys:
        print(keys)
    
    if "entity" not in keys:
        print("NO PAYLOAD")
        return Result(tuple(), "EMPTY")

    return Result((Update(d) for d in data["entity"]), None)

def get_cut_date(next_day=False):
    now = datetime.datetime.now()
    if next_day:
        now += datetime.timedelta(days=1.)
    defin = datetime.datetime(now.year, now.month, now.day , *HOUR_CUT)
    return defin

def process_updates(ups_set):
    gen = sorted(ups_set, key=lambda x: x.timest)
    return  [x.data for x in gen]

def save_updates_file(increm_list, outname):
    print("Saving...", end=" ")
    t = time.time()
    #gen = sorted(fin_set, key=lambda x: x.timest)
    
    #io_lib.save_json_gzip(outname, [x.data for x in gen])
    #io_lib.save_json_zstd(outname, increm_list)
    iomsg.save_msgpack_zstd(outname, increm_list, level=5)
    #[x.data for x in gen])
    tsave = time.time()-t
    print(f"took {tsave:4.3f} s")

def make_filename(outfold):
    this_date = datetime.datetime.today()
    outname = outfold / Path(BASE_NAME_OUT.format(format_date(this_date)))
    return outname


def main(argv):
    global PATTERNS_DOWN, DOWNLOADED_TRIPS, TRIPS_DOWN

    parser=create_mparser()

    args = parser.parse_args(argv[1:])
    debug_run = True if args.debug else False
    no_data = args.no_data
    if no_data:
        print("Will not download additional data on trips")

    m_session = requests.Session()
    starttime = int(time.time())
    tsess = int(starttime)
    ts_cut = get_cut_date().timestamp()
    if ts_cut < starttime:
        date_next = get_cut_date(next_day=True)
        print("Updating saving date to", date_next)
        ts_cut = date_next.timestamp()
    outfold = Path(OUT_FOLDER)
        
    PATTERNS_FNAME = get_pattern_fname(outfold)
    TRIPS_FNAME = get_trips_mapname(outfold)

    if(PATTERNS_FNAME.exists()):
        PATTERNS_DOWN = io_lib.read_json_zstd(PATTERNS_FNAME)
    else:
        print("No patterns file")
        PATTERNS_DOWN = {}

    if(TRIPS_FNAME.exists()):
        TRIPS_DOWN = io_lib.read_json_zstd(TRIPS_FNAME)
        DOWNLOADED_TRIPS = set(t["gtfsId"] for t in TRIPS_DOWN)
        print(f"Loaded {len(DOWNLOADED_TRIPS)} trips")

    else:
        print("No trips file")
        TRIPS_DOWN = []
        DOWNLOADED_TRIPS = set()

    firstres=get_parse_updates(m_session)

    fin_updates = set(firstres.data)
    UPDATES_OUT = process_updates(fin_updates)
    count = 1
    
    if not outfold.exists():
        outfold.mkdir(parents=True)
    
    #this_date = datetime.datetime.today()
    FILE_SAVE = make_filename(outfold)
    mtimestamp = int(time.time())
    mdate = datetime.datetime.today()

        
    ### begin
    try:
        while True:
        
            print(format_date_sec(mdate), "\t", f"{len(fin_updates)}, tr:{len(TRIPS_DOWN)}, pat:{len(PATTERNS_DOWN)}")

            time.sleep(TIME_SLEEP)
            gotnewdata = False
            last_up_t = time.time()
            while gotnewdata is False:
                try:
                    newres = get_parse_updates(m_session)
                    if newres.error == None:
                        gotnewdata = True
                        last_up_t = time.time()
                    elif newres.error == "TRIALOUT":
                        print("Remake session and retry")
                        m_session = requests.Session()
                        tsess = time.time()
                    else:
                        if newres.error!= "EMPTY": print("ERROR: "+newres.error)
                        else: 
                            time.sleep(2)
                        diff_lup=int(time.time()-last_up_t)
                        if diff_lup > 30:
                            print("last update: "+str(datetime.timedelta(seconds=diff_lup))+" ago")
                except (requests.exceptions.ConnectionError, requests.exceptions.RequestException):
                    print("Error, Remake session")
                    m_session = requests.Session()
                    tsess = time.time()
            ## find ones that have to be added
            ups_add = set(newres.data).difference(fin_updates)
            fin_updates = fin_updates.union(ups_add)
            ## add missing to list
            UPDATES_OUT.extend(process_updates(ups_add))
            ### add updates tripId
            if not no_data:
                for up in ups_add:
                    TRIPS_FUT.append(
                        executor.submit(download_tripinfo, up.trip_id)
                    )

            mtimestamp = int(time.time())
            mdate = datetime.datetime.today()
            count += 1
            rotate_file_save = mtimestamp > ts_cut or len(fin_updates) > MAX_UPDATES
            if count % 10 == 0 or rotate_file_save:
                ## save the updates
                save_updates_file(UPDATES_OUT, FILE_SAVE)
            if count % 15 == 0:
                executor.submit(save_patterns_done, PATTERNS_FNAME)
                #save_patterns_done(PATTERNS_FNAME)
                #save_trips_need(TRIPS_FNAME)
                executor.submit(save_trips_need, TRIPS_FNAME)
                if get_pattern_fname(outfold) != PATTERNS_FNAME:
                    ## update patterns name
                    print("Changing patterns file")
                    PATTERNS_FNAME = get_pattern_fname(outfold)
                    PATTERNS_DOWN = {}
                if get_trips_mapname(outfold) != TRIPS_FNAME:
                    ## update patterns name
                    print("Changing trips file")
                    TRIPS_FNAME = get_trips_mapname(outfold)
                    TRIPS_DOWN = []
                    DOWNLOADED_TRIPS = set()

            if rotate_file_save:
                ### UPDATE HOUR TO SAVE
                if mtimestamp > ts_cut:
                    assert get_cut_date().timestamp() < mtimestamp
                    date_next = get_cut_date(next_day=True)
                    print("Updating saving date to", date_next)
                    ts_cut = date_next.timestamp()
                
                FILE_SAVE = make_filename(outfold) #outfold / Path(BASE_NAME_OUT.format(mtimestamp))
                fin_updates = set()
                UPDATES_OUT = []
            if time.time() - tsess > HOURS_REMAKE_SESS*3600:
                print("Remaking session")
                m_session = requests.Session()
                tsess = time.time()
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt")
        save_updates_file(UPDATES_OUT, FILE_SAVE)
        save_trips_need(TRIPS_FNAME)
        save_patterns_done(PATTERNS_FNAME)
    #print([hash(l) for l in v])
if __name__ == '__main__':
    main(sys.argv)
