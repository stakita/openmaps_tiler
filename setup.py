from setuptools import setup, find_packages

setup(
    name = 'openstreetmaps_tiler',
    author = 'Simon Takita',
    version = '0.1',
    package_dir = {'openstreetmaps_tiler': 'openstreetmaps_tiler'},
    packages = ['openstreetmaps_tiler', 'openstreetmaps_tiler.scripts'],
    install_requires = [
        'docopt',
        'Pillow',
        'opencv-python',
        'numpy',
        'sh',
        'xmltodict',
    ],
    entry_points = {
        'console_scripts': [
            'create_overview_video = openstreetmaps_tiler.scripts.create_overview_video:main',
            'create_chase_video = openstreetmaps_tiler.scripts.create_chase_video:main',
            'tile_download = openstreetmaps_tiler.scripts.tile_download:main',
        ]
    }
)