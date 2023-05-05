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
import urllib.error
import http.client
from pathlib import Path
from warnings import warn
import requests
import gtt_updates
import io_lib


BASE_NAME_OUT = "updates_{}.json.zstd"
OUT_FOLDER="data"
TIME_SLEEP = 3
HOUR_CUT=4
MAX_UPDATES=130_000

HOURS_REMAKE_SESS = 0.6

def create_mparser():

    parser = argparse.ArgumentParser("Updater saver")

    parser.add_argument("--debug", action="store_true")

    return parser

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

    def get_service_day(self):
        try:
            return self.data["vehicle"]["trip"]["start_date"]
        except:
            return "00000000"

Result = namedtuple("Result", ["data","error"])

def get_parse_updates(session=None, ntries=4):
    gotit = False
    t=0
    while (not gotit and t<ntries):
        try:
            data = gtt_updates.get_updates(session=session)
            gotit = True
        except urllib.error.HTTPError as e:
            print("Got "+e.msg+" , Retrying")
        except http.client.RemoteDisconnected as e:
            print("Remote disconnected, Retrying")

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
    defin = datetime.datetime(now.year, now.month, now.day , HOUR_CUT)
    return defin

def save_ups(fin_set, outname):
    print("Saving...", end=" ")
    t = time.time()
    gen = sorted(fin_set, key=lambda x: x.timest)
    
    #io_lib.save_json_gzip(outname, [x.data for x in gen])
    io_lib.save_json_zstd(outname, [x.data for x in gen])
    tsave = time.time()-t
    print(f"took {tsave:4.3f} s")

def make_filename(outfold):
    this_date = datetime.datetime.today()
    outname = outfold / Path(BASE_NAME_OUT.format(format_date(this_date)))
    return outname

format_date = lambda date : f"{date.year}{date.month:02d}{date.day:02d}{date.hour:02d}{date.minute:02d}"
format_date_sec = lambda date : f"{date.year}{date.month:02d}{date.day:02d}{date.hour:02d}{date.minute:02d}{date.second:02d}"


def main(argv):

    parser=create_mparser()

    args = parser.parse_args(argv[1:])
    debug_run = True if args.debug else False

    m_session = requests.Session()
    starttime = int(time.time())
    tsess = int(starttime)
    ts_cut = get_cut_date().timestamp()
    if ts_cut < starttime:
        ts_cut = get_cut_date(next_day=True).timestamp()
        print("Update changing date")

    firstres=get_parse_updates(m_session)

    fin_updates = set(firstres.data)
    count = 1
    outfold = Path(OUT_FOLDER)
    if not outfold.exists():
        outfold.mkdir(parents=True)
    
    #this_date = datetime.datetime.today()
    FILE_SAVE = make_filename(outfold)
    mtimestamp = int(time.time())
    mdate = datetime.datetime.today()
    try:
        while True:
        
            print(format_date_sec(mdate), "\t", len(fin_updates))

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

            fin_updates = fin_updates.union(set(newres.data))
            mtimestamp = int(time.time())
            mdate = datetime.datetime.today()
            count += 1
            save_too_many = mtimestamp > ts_cut or len(fin_updates) > MAX_UPDATES
            if count % 10 == 0 or save_too_many:
                save_ups(fin_updates, FILE_SAVE)
            if save_too_many:
                ### UPDATE HOUR TO SAVE
                print("Updating saving date")
                if mtimestamp > ts_cut:
                    assert get_cut_date().timestamp() < mtimestamp
                    ts_cut = get_cut_date(next_day=True).timestamp()
                
                FILE_SAVE = make_filename(outfold) #outfold / Path(BASE_NAME_OUT.format(mtimestamp))
                fin_updates = set()
            if time.time() - tsess > HOURS_REMAKE_SESS*3600:
                print("Remaking session")
                m_session = requests.Session()
                tsess = time.time()
    except KeyboardInterrupt:
        print("Caught KeyboardInterrupt")
        save_ups(fin_updates, FILE_SAVE)
    #print([hash(l) for l in v])
if __name__ == '__main__':
    main(sys.argv)
