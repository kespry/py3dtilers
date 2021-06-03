# Python 3DTiles Tilers 

p3dtiles-tilers is a Python tool and library allowing to build [`3D Tiles`](https://github.com/AnalyticalGraphicsInc/3d-tiles) tilesets out of various geometrical formats e.g. [OBJ](https://en.wikipedia.org/wiki/Wavefront_.obj_file), [GeoJSON](https://en.wikipedia.org/wiki/GeoJSON) or [CityGML through 3dCityDB databases](https://3dcitydb-docs.readthedocs.io/en/release-v4.2.3/)

p3dtiles-tilers uses [`py3dtiles` python library](https://gitlab.com/Oslandia/py3dtiles) for its in memory representation of tilesets

**CLI Features**

* Convert OBJ files to a 3D Tiles tileset 
* Convert GeoJson files to a 3D Tiles tileset 
* Extract CityGML features like buildings, bridges, terrain from [3dCityDB database](https://3dcitydb-docs.readthedocs.io/en/release-v4.2.3/) to a 3D Tiles tileset 

## Installation from sources

To use py3dtilers from sources:

$ apt install git python3 python3-pip virtualenv
$ git clone https://github.com/VCityTeam/py3dtilers
$ cd py3dtilers
$ virtualenv -p python3 venv
$ . venv/bin/activate
(venv)$ pip install -e .
(venv)$ python setup.py install

If you wan to run unit tests:

(venv)$ pip install pytest pytest-benchmark
(venv)$ pytest
...

## CLI Usage
