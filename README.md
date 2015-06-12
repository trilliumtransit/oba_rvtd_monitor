# OneBusAway-RVTD Monitor

A set of python scripts to monitor RVTD real time systems, the static GTFS and a local OneBusAway instance.

## Installation

The project is based of off python 2.7, but is best used with the `virtualenv` development scheme.

1. Install Python 2.7
2. Install virtualenv: `$ [sudo] pip install virtualenv`
3. Clone the github project: `$ git clone https://github.com/trilliumtransit/oba_rvtd_monitor.git`
4. Instantiate the virtual python environment for the project using python 2.7: 
  - Windows: `virtualenv --python=C:\Python27\python.exe oba_rvtd_monitor`
  - Linux: `virtualenv -p /path/to/python27 oba_rvtd_monitor`
5. Activate the virtualenv: 
  - Windows: `.\oba_rvtd_monitor\Scripts\activate`
  - Linux: `oba_rvtd_monitor/bin/activate`
6. Browse to project folder `cd oba_rvtd_monitor`
7. Install the python project using develop mode: `python setup.py develop`
8. Create a file called `rvtd_systems.ini` with the following contents (replace with desired ip for streets server):
```
[DEFAULT]
streets_host_name = 1.2.3.4
```

## Usage

If using linux, the files will be in the `bin` folder instead of `Scripts`.  For the following scripts, a new folder called `data` will be created where the gtfs will be downloaded and the monitoring output written to.

### Download GTFS

`Scripts\dl_gtfs.exe`

### Validate GTFS

`Scripts\validate_gtfs.exe`

### Inspect all systems

`Scripts\inspect_gtfs_rt.exe`
