import geoip2.database
import dpkt
import socket
import ipaddress
import random
import sys

HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n\
    <kml xmlns="http://www.opengis.net/kml/2.3">\n<Document>\n'
FOOTER = '</Document>\n</kml>\n'


class Position:
    def __init__(self, longtitude, latitude):
        self.longtitude = longtitude
        self.latitude = latitude

    def __str__(self):
        return str(self.longtitude) + ','\
            + str(self.latitude)


class IP:
    def __init__(self, address, position=None):
        self.address = ipaddress.ip_address(address)
        with geoip2.database.Reader('database/GeoLite2-City.mmdb') as reader:
            try:
                response = reader.city(address)
                self.country = response.country.name
                self.city = response.city.name
                self.position = Position(response.location.longitude,
                                         response.location.latitude)
                if response.location.longitude is None:
                    self.country = 'N/A'
                    self.city = 'N/A'
                    self.position = Position(0, 0)
            except:
                if position is None:
                    self.country = 'N/A'
                    self.city = 'N/A'
                    self.position = Position(0, 0)
                else:
                    self.country = 'Home'
                    self.city = 'Home'
                    self.position = position

    def __eq__(self, other):
        if not isinstance(other, IP):
            return False
        return self.address == other.address

    def __str__(self):
        return str(self.address)

    def get_position(self):
        return self.position


class Route:
    def __init__(self, source, destination):
        self.source = source
        self.destination = destination
        self.name = str(destination)
        self.color = hex(random.randint(0, 16777215))
        self.style = str(destination.address).replace('.', '_')

    def get_line(self):
        return str(self.source.get_position()) + ';'\
            + str(self.destination.get_position())

    def get_line_kml(self):
        return str(self.source.get_position()) + '\n'\
            + str(self.destination.get_position())

    def get_name(self):
        return self.name

    def append_name(self, name):
        self.name += '; ' + name

    def __str__(self):
        return f"<Style id=\"{self.style}\">\n\
<LineStyle>\n\
<width>1</width>\n\
<color>{self.color}</color>\n\
</LineStyle>\n\
</Style>\n\
<Placemark>\n\
<name>{self.name}</name>\n\
<extrude>1</extrude>\n\
<tessellate>1</tessellate>\n\
<styleUrl>#{self.style}</styleUrl>\n\
<LineString>\n\
<coordinates>{self.get_line_kml()}</coordinates>\n\
</LineString>\n\
</Placemark>\n\
"


def create_route(ethernet):
    ip = ethernet.data
    source = IP(socket.inet_ntoa(ip.src))
    destination = IP(socket.inet_ntoa(ip.dst))
    return Route(source, destination)


def create_route(source_ip, source_position, destination_ip):
    source = IP(source_ip, source_position)
    destination = IP(destination_ip)
    return Route(source, destination)


def all_routes_from_pcap(file):
    routes = []
    with open(file, 'rb') as f:
        # if pcap then pcap instead of pcapng
        pcap = dpkt.pcapng.Reader(f)
        for _, buffer in pcap:
            ethernet = dpkt.ethernet.Ethernet(buffer)
            if isinstance(ethernet.data, dpkt.ip.IP):
                routes.append(create_route(ethernet))
    return routes


def filter_ip_addresses(file):
    ip_addresses = {}
    with open(file, 'rb') as f:
        # if pcap then pcap instead of pcapng
        pcap = dpkt.pcapng.Reader(f)
        for _, buffer in pcap:
            ethernet = dpkt.ethernet.Ethernet(buffer)
            if isinstance(ethernet.data, dpkt.ip.IP):
                ip = ethernet.data
                source = socket.inet_ntoa(ip.src)
                destination = socket.inet_ntoa(ip.dst)
                ip_addresses[source] = ip_addresses.get(source, 0) + 1
                ip_addresses[destination] = ip_addresses.get(destination, 0) + 1
    return ip_addresses


def create_routes(ip_addresses, home_position):
    routes = []
    sorted_ip_addresses = sorted(ip_addresses.items(),
                                 key=lambda item: item[1], reverse=True)
    ip_addresses = dict(sorted_ip_addresses)
    home_address, _ = sorted_ip_addresses[0]
    ip_addresses.pop(home_address)
    for ip_address in ip_addresses:
        routes.append(create_route(home_address, home_position, ip_address))
    return routes


def merge_routes(routes):
    merged_routes = []
    routes_to_merge = {}
    for route in routes:
        line = route.get_line()
        if line in routes_to_merge:
            routes_to_merge[line].append(route)
        else:
            routes_to_merge[line] = [route]
    for routes_on_line in routes_to_merge.values():
        merged_route = routes_on_line[0]
        for route in routes_on_line[1:]:
            merged_route.append_name(route.get_name())
        merged_routes.append(merged_route)
    return merged_routes


def generate_kml(input_file, home_longtitude, home_latitude):
    home_position = Position(home_longtitude, home_latitude)
    ip_addresses = filter_ip_addresses(input_file)
    routes = create_routes(ip_addresses, home_position)
    routes = merge_routes(routes)
    content = HEADER
    for route in routes:
        content += "\n" + str(route)
    content += FOOTER
    return content


def main():
    if len(sys.argv) < 2:
        print("No input file provided")
        return
    input_file = sys.argv[1]
    output_file = 'output.kml'
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    home_longtitude = 16.3662
    home_latitude = 48.2049
    content = generate_kml(input_file, home_longtitude, home_latitude)
    with open(output_file, 'w') as file:
        file.write(content)


if __name__ == '__main__':
    main()
