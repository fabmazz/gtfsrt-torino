# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import requests
import json
import time


URL="https://mapi.5t.torino.it/routing/v1/routers/mat/index/graphql"
PARAMS = {
	"Content-Type": "application/json; charset=utf-8",
	#"Referer": "https://www.muoversiatorino.it/",
	#"Origin": "https://www.muoversiatorino.it",
	#"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67",
	"DNT" : "1",
	"Host": "mapi.5t.torino.it",

}
def make_request(operationName, variables, query, session:requests.session=None):
    qar={"operationName":operationName,
    "variables":variables,"query":query}
     
    data_req = json.dumps(qar)#query_stop_arrivals#
    
    if session:
        r= session.post(URL,headers=PARAMS,data=data_req)
    else:
        r = requests.post(URL,headers=PARAMS,data=data_req)

    return r

query_trip2="""query TripInfo($tripid: String!){
    trip(id: $tripid){
        gtfsId
        serviceId
        route{
            gtfsId
        }
        pattern{
            code
        }
        tripHeadsign

    }
}
"""

def get_trip_info(gtfs_tripid, session = None): 
    #"gtt:23673879U"
    r = make_request("TripInfo",dict(tripid=gtfs_tripid), query=query_trip2, session=session)
    data = r.json()
    trip = data["data"]["trip"]
    return trip

query_pat="""
    query PatternInfo($field: String!){
    pattern(id: $field){
      name
      code
      semanticHash
      directionId
      headsign
      stops{
        gtfsId
        lat
        lon
      }
      patternGeometry{
        length
        points
      }
    }
}
"""
def get_pattern_info(patternCode, session=None): 
    #"gtt:23673879U"
    r = make_request("PatternInfo",dict(field=patternCode), query=query_pat,session=session)
    data = r.json()
    #
    return data["data"]["pattern"]
