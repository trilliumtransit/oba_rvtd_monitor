from datetime import datetime, date, timedelta
from logging.handlers import TimedRotatingFileHandler
import logging
import os
import urllib

from google.transit import gtfs_realtime_pb2
import requests
import transitfeed
from transitfeed import Loader
from transitfeed.gtfsfactory import GetGtfsFactory
from transitfeed.problems import ProblemReporter, TYPE_WARNING

from oba_rvtd_monitor.problems import MonitoringProblemAccumulator
from oba_rvtd_monitor.feedvalidator import HTMLCountingProblemAccumulator
from oba_rvtd_monitor.rvtd_systems import inspect_rvtd_streets_feed


__import__('pkg_resources').declare_namespace(__name__)

BASE_DIR = os.path.split(os.path.dirname(__file__))[0]
DATA_DIR = os.path.join(BASE_DIR, 'data')
DL_DIR = os.path.join(DATA_DIR, 'downloads')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')

# Create the `reports` directory if it doesn't exist
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)

logger = logging.getLogger("gtfs_rt_logger")
logger.setLevel(logging.DEBUG)
 
if not logger.handlers:
    handler = TimedRotatingFileHandler(os.path.join(REPORTS_DIR, 'montior_log.txt'),
                                       when="H",
                                       interval=1,
                                       backupCount=25)
    logger.addHandler(handler)


GTFS_URL = r'http://feed.rvtd.org/googleFeeds/static/google_transit.zip'

GTFS_RT_TRIP = r'http://feed.rvtd.org/googleFeeds/realtime/trip_updates.proto'
GTFS_RT_ALERT = r'http://feed.rvtd.org/googleFeeds/realtime/service_alerts.proto'
GTFS_RT_VEHICLE = r'http://feed.rvtd.org/googleFeeds/realtime/vehicle_positions.proto'

OBA_VEHICLES_URL = r'http://localhost:8080/onebusaway-api-webapp/api/where/vehicles-for-agency/1739.json?key=TEST'

gtfs_file_name = 'google_transit.zip'.format(datetime.now().strftime('%Y-%m-%d'))
# gtfs_file_name = 'google_transit_2015-04-29.zip'.format(datetime.now().strftime('%Y-%m-%d'))
gtfs_file_name = os.path.join(DL_DIR, gtfs_file_name)
    

def download_gtfs():
    '''download the RVTD static GTFS file from their server
    '''
    
    # Create the `downloads` directory if it doesn't exist
    if not os.path.exists(DL_DIR):
        os.makedirs(DL_DIR)    
    
    r = requests.get(GTFS_URL, stream=True)
    with open(gtfs_file_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024): 
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
                

def load_gtfs(problem_reporter=None):
    '''load gtfs into transitfeed
    
    Args:
        problem_reporter (ProblemAccumulatorInterface, default=None): A problem reporter.
    
    Returns:
        gtfs_factory.Schedule: the loaded schedule
    '''
    gtfs_factory = GetGtfsFactory()
    
    loader = gtfs_factory.Loader(gtfs_file_name,
                                 problems=problem_reporter)
    return loader.Load()


def validate_gtfs():
    '''validate the gtfs and write errors html to reports directory
    '''
    
    accumulator = HTMLCountingProblemAccumulator(limit_per_type=50)
    problem_reporter = ProblemReporter(accumulator)
    
    schedule = load_gtfs(problem_reporter)
    schedule.Validate()
    
    # check for trips with a null value for trip_headsign
    for trip in schedule.GetTripList():
        if trip.trip_headsign == 'null':
            problem_reporter.InvalidValue('trip_headsign', 'null', type=TYPE_WARNING)
            
    # write GTFS report to file
    report_name = 'gtfs_validation_{0}.html'.format(datetime.now().strftime('%Y-%m-%d %H.%M'))
    with open(os.path.join(REPORTS_DIR, report_name), 'w') as f:
        accumulator.WriteOutput(gtfs_file_name, f, schedule, transitfeed)
        

def concat_date_and_seconds(today, seconds_after_midnight):
    dt = datetime(today.year, today.month, today.day)
    return dt + timedelta(seconds=seconds_after_midnight)


def inspect_gtfs_rt():
    
    # load schedule
    accumulator = HTMLCountingProblemAccumulator(limit_per_type=50)
    problem_reporter = ProblemReporter(accumulator)
    schedule = load_gtfs(problem_reporter)
    
    # get service ids for today
    today = date.today()
    service_periods_today = schedule.GetServicePeriodsActiveEachDate(today, today + timedelta(days=1))[0]
    service_ids_today = []
    for service in service_periods_today[1]:
        service_ids_today.append(service.service_id)
    
    # get a list of trips active at this time
    now = datetime.now()
    ten_minutes_from_now = now + timedelta(minutes=10)
    ten_minutes_ago = now - timedelta(minutes=10)
    active_trips = []
    active_trip_ids = []
    for trip in schedule.GetTripList():
        if trip.service_id in service_ids_today:
            trip_start = trip.GetStartTime()
            trip_start = concat_date_and_seconds(today, trip_start)
            trip_end = trip.GetEndTime()
            trip_end = concat_date_and_seconds(today, trip_end)
            if trip_start < ten_minutes_from_now and trip_end > ten_minutes_ago:
                active_trips.append(dict(trip_id=trip.trip_id,
                                         trip_start=trip_start,
                                         trip_end=trip_end))
                active_trip_ids.append(trip.trip_id)            
            
    # get the gtfs-rts
    
    # get the gtfs-rt trip update
    feed = gtfs_realtime_pb2.FeedMessage()
    response = urllib.urlopen(GTFS_RT_TRIP)
    feed.ParseFromString(response.read())
    
    # calculate which trips are in gtfs-rt and which ones have stop_time_updates
    trip_ids_in_gtfs_rt = []
    trip_ids_with_stop_time_update = []
    for entity in feed.entity:
        if entity.HasField('trip_update'):
            trip_id = entity.trip_update.trip.trip_id
            if trip_id not in trip_ids_in_gtfs_rt:
                trip_ids_in_gtfs_rt.append(trip_id)
                
            try:
                if len(entity.trip_update.stop_time_update) > 0:
                    if trip_id not in trip_ids_with_stop_time_update:
                        trip_ids_with_stop_time_update.append(trip_id)
            except:
                pass
            
    # get the gtfs-rt service alerts
    feed = gtfs_realtime_pb2.FeedMessage()
    response = urllib.urlopen(GTFS_RT_ALERT)
    feed.ParseFromString(response.read())
    
    service_alerts = []
    
    for entity in feed.entity:
        service_alerts.append(str(entity))
        
    # get the gtfs-rt vehicle positions
    feed = gtfs_realtime_pb2.FeedMessage()
    response = urllib.urlopen(GTFS_RT_VEHICLE)
    feed.ParseFromString(response.read())
    
    vehicles = []
    vehicles_with_trip = []
    
    for entity in feed.entity:
        vehicles.append(entity.id)
        if entity.vehicle.trip.trip_id:
            vehicles_with_trip.append(entity)
            
    # get OneBusAway vehicle positions
    oba_vehicles_result = requests.get(OBA_VEHICLES_URL)
    oba_vehicles = oba_vehicles_result.json()['data']['list']
    oba_vehicles_trip_ids = []
    oba_vehicles_with_invalid_trip_id = []
    oba_vehicles_without_trip_id = []
    oba_missing_active_trips = []
    for vehicle in oba_vehicles:
        if vehicle['tripId'] == '':
            oba_vehicles_without_trip_id.append(vehicle)
        else:
            trip_id_stripped = vehicle['tripId'].replace('1739_', '', 1)
            oba_vehicles_trip_ids.append(trip_id_stripped)
            if trip_id_stripped not in active_trip_ids:
                oba_vehicles_with_invalid_trip_id.append(vehicle)
                
    # calculate active trip ids not present in OBA
    for trip_id in active_trip_ids:
        if trip_id not in oba_vehicles_trip_ids:
            oba_missing_active_trips.append(trip_id)

    # examine vehicles with trip ids for valid trip id and status
    vehicles_with_invalid_trip_id = []
    vehicles_with_stop_id = []
    vehicle_tripids_with_trip_but_no_stop_id = []
    for entity in vehicles_with_trip:
        if entity.vehicle.trip.trip_id not in active_trip_ids:
            vehicles_with_invalid_trip_id.append(entity)
        if entity.vehicle.stop_id:
            vehicles_with_stop_id.append(entity)
        else:
            vehicle_tripids_with_trip_but_no_stop_id.append(entity.vehicle.trip.trip_id)    
    
    # determine missing active trip ids from vehicles
    missing_trip_ids_from_vehicles = []
    for trip_id in active_trip_ids:
        vehicle_found = False
        for entity in vehicles_with_trip:
            if entity.vehicle.trip.trip_id == trip_id:
                vehicle_found = True
                break
        
        if not vehicle_found:
            missing_trip_ids_from_vehicles.append(trip_id)
                    
    # prepare error reporting
    logger.debug('------------------------------------------------------')
    logger.debug(now.strftime('%Y-%m-%d %H:%M'))
    logger.debug('--------')
    logger.debug('GTFS')
    logger.debug('{0} total active trip ids'.format(len(active_trip_ids)))
    
    for trip in active_trips:
        logger.debug('trip_id: {0} start: {1} end: {2}'.format(trip['trip_id'],
                                                               trip['trip_start'].strftime('%H:%M'),
                                                               trip['trip_end'].strftime('%H:%M')))
        
    logger.debug('--------')
    logger.debug('GTFS-RT Trip Updates')
    logger.debug('{0} total trips in gtfs-rt'.format(len(trip_ids_in_gtfs_rt)))
    logger.debug('{0} total trips in gtfs-rt with stop time updates'.format(len(trip_ids_with_stop_time_update)))
    
    # determine trips without trip updates
    for trip_id in active_trip_ids:
        if trip_id not in trip_ids_in_gtfs_rt:
            logger.debug('active trip id {0} not in gtfs-rt'.format(trip_id))
            
    # determine trip updates without stop times
    for trip_id in trip_ids_in_gtfs_rt:
        if trip_id not in trip_ids_with_stop_time_update:
            logger.debug('trip id {0} in gtfs-rt trip update without stop_time_updates'.format(trip_id))
            
    # service alerts
    logger.debug('--------')
    logger.debug('GTFS-RT Service Alerts:')
    logger.debug('{0} total service alerts'.format(len(service_alerts)))
    logger.debug('--------')
    
    # vehicles stuff
    logger.debug('GTFS-RT Vehicles')
    logger.debug('{0} total vehicles'.format(len(vehicles)))
    logger.debug('{0} total vehicles with trip data'.format(len(vehicles_with_trip)))
    logger.debug('{0} total vehicles with invalid trip_id'.format(len(vehicles_with_invalid_trip_id)))
    logger.debug('{0} total active trip_ids missing from vehicles'.format(len(missing_trip_ids_from_vehicles)))
    logger.debug('{0} total vehicles with stop id'.format(len(vehicles_with_stop_id)))
    
    for trip_id in vehicle_tripids_with_trip_but_no_stop_id:
        logger.debug('vehicle with trip_id {0} without stop info'.format(trip_id))
    
    logger.debug('--------')   
        
    inspect_rvtd_streets_feed(active_trip_ids, logger)
    
    logger.debug('OneBusAway')
    logger.debug('{0} total vehicles'.format(len(oba_vehicles)))
    logger.debug('{0} total vehicles with invalid trip_id'.format(len(oba_vehicles_with_invalid_trip_id)))
    logger.debug('{0} total vehicles without trip_id'.format(len(oba_vehicles_without_trip_id)))
    logger.debug('{0} active trips missing from vehicles'.format(len(oba_missing_active_trips)))
    for trip_id in oba_missing_active_trips:
        logger.debug('active trip id {0} not in OBA'.format(trip_id))
    logger.debug('--------')    
