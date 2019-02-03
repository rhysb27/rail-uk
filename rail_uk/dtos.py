from collections import namedtuple

Station = namedtuple('Station', 'name, crs')

HomeStation = namedtuple('HomeStation', 'station, distance')

APIParameters = namedtuple('APIParameters', 'origin, destination, offset')

DepartureInfo = namedtuple('DepartureInfo', 'std, etd, operator, final_dest, in_past, live')
