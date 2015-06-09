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


def inspect_rvtd_streets_feed(logger=None):
    client = Client(RVTD_STREET_WSDL)
    result = client.service.GetVehicles(1)
        
    with open(os.path.join(REPORTS_DIR, 'mentor_rt_out.txt'), 'w') as f:
        f.write(str(result))
    
    print_or_log('RVTD Streets Webservices', logger)
    for array_of_vehicle_data in result:
        print_or_log('{0} total vehicles in streets vehicles feed'.format(len(array_of_vehicle_data[1])), logger)
        for vehicle in array_of_vehicle_data[1]:
            if vehicle.CurrentWork:
                trip = vehicle.CurrentWork.Trip
                trip_id = trip.Key
                if vehicle.NextStops is None:
                    print_or_log('Streets feed trip_id {0} without NextStops data'.format(trip_id), logger)
    print_or_log('--------', logger)
