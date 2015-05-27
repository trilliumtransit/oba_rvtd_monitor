from setuptools import setup, find_packages
 
setup(
    name='oba_rvtd_monitor',
    packages=find_packages(),
    install_requires=[
        'requests>=2.5.3',
        'transitfeed>=1.2.14',
        'gtfs-realtime-bindings>=0.0.4',
        'suds>=0.4'
    ],
    entry_points={
        'console_scripts': [
            'dl_gtfs=oba_rvtd_monitor:download_gtfs',
            'validate_gtfs=oba_rvtd_monitor:validate_gtfs',
            'inspect_gtfs_rt=oba_rvtd_monitor:inspect_gtfs_rt',
            'inspect_rvtd_streets=oba_rvtd_monitor.rvtd_systems:inspect_rvtd_streets_feed'
        ]
    }
)
