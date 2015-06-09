import ConfigParser
import os

from suds.client import Client


BASE_DIR = os.path.split(os.path.dirname(__file__))[0]
DATA_DIR = os.path.join(BASE_DIR, 'data')
DL_DIR = os.path.join(DATA_DIR, 'downloads')
REPORTS_DIR = os.path.join(DATA_DIR, 'reports')
RVTD_SETTINGS = ConfigParser.ConfigParser()
RVTD_SETTINGS.read(os.path.join(BASE_DIR, 'rvtd_systems.ini'))
RVTD_STREETS_HOSTNAME = RVTD_SETTINGS.get('DEFAULT', 'streets_host_name')
RVTD_STREET_WSDL = "http://{0}/streets/WCF/FixedRouteRealTimeWebService.svc?wsdl".format(RVTD_STREETS_HOSTNAME)

# Create the `reports` directory if it doesn't exist
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)
    

def print_or_log(s, logger):
    if logger:
        logger.debug(s)
    else:
        print(s)


def inspect_rvtd_streets_feed(active_trip_ids, logger=None):
    client = Client(RVTD_STREET_WSDL)
    result = client.service.GetVehicles(1)
        
    with open(os.path.join(REPORTS_DIR, 'mentor_rt_out.txt'), 'w') as f:
        f.write(str(result))
    
    print_or_log('RVTD Streets Webservices', logger)
    streets_trip_ids = []
    streets_trips_without_next_stops = []
    for array_of_vehicle_data in result:
        print_or_log('{0} total vehicles in streets vehicles feed'.format(len(array_of_vehicle_data[1])), logger)
        for vehicle in array_of_vehicle_data[1]:
            if vehicle.CurrentWork:
                trip = vehicle.CurrentWork.Trip
                trip_id = trip.Key
                streets_trip_ids.append(trip_id)
                if vehicle.NextStops is None:
                    streets_trips_without_next_stops.append(trip_id)
    
    print_or_log('{0} total vehicles with current work'.format(len(streets_trip_ids)), logger)
    
    streets_missing_active_trips = []
    for trip_id in active_trip_ids:
        if trip_id not in streets_trip_ids:
            streets_missing_active_trips.append(trip_id)
            
    invalid_streets_trip_ids = []
    for trip_id in streets_trip_ids:
        if trip_id not in active_trip_ids:
            invalid_streets_trip_ids.append(trip_id)
            
    print_or_log('{0} total active trips not in Streets Webservice'.format(len(streets_missing_active_trips)), logger)
    print_or_log('{0} total vehicles without next stops data'.format(len(streets_trips_without_next_stops)), logger)
    print_or_log('{0} total vehicles with invalid trip ids'.format(len(invalid_streets_trip_ids)), logger)
                 
    for trip_id in streets_missing_active_trips:
        print_or_log('active trip id {0} not in Streets Webservice'.format(trip_id), logger)
            
    for trip_id in streets_trips_without_next_stops:
        print_or_log('Streets feed trip_id {0} without NextStops data'.format(trip_id), logger)
        
    for trip_id in invalid_streets_trip_ids:
        print_or_log('Streets feed trip_id {0} is invalid'.format(trip_id), logger)
    
    print_or_log('--------', logger)
