import geoip2.database
import dpkt
import socket
import ipaddress
import random
import sys

HEADER: str = '<?xml version="1.0" encoding="UTF-8"?>\n\
    <kml xmlns="http://www.opengis.net/kml/2.3">\n<Document>\n'
FOOTER: str = '</Document>\n</kml>\n'


class Position:
    def __init__(self, longtitude: float, latitude: float):
        self.longtitude: float = longtitude
        self.latitude: float = latitude

    def __str__(self) -> str:
        return str(self.longtitude) + ','\
            + str(self.latitude)


class IP:
    def __init__(self,
                 address: ipaddress.IPv4Address | ipaddress.IPv6Address,
                 position: Position = None):
        self.address = ipaddress.ip_address(address)
        with geoip2.database.Reader('database/GeoLite2-City.mmdb') as reader:
            try:
                response = reader.city(address)
                self.country: str = response.country.name
                self.city: str = response.city.name
                self.position: Position = Position(response.location.longitude,
                                                   response.location.latitude)
                if response.location.longitude is None:
                    self.country: str = 'N/A'
                    self.city: str = 'N/A'
                    self.position: Position = Position(0, 0)
            except Exception:
                if position is None:
                    self.country: str = 'N/A'
                    self.city: str = 'N/A'
                    self.position: Position = Position(0, 0)
                else:
                    self.country: str = 'Home'
                    self.city: str = 'Home'
                    self.position: Position = position

    def __eq__(self, other: any) -> bool:
        if not isinstance(other, IP):
            return False
        return self.address == other.address

    def __str__(self) -> str:
        return str(self.address)

    def get_position(self) -> Position:
        return self.position


class Route:
    def __init__(self, source: IP, destination: IP):
        self.source: IP = source
        self.destination: IP = destination
        self.name: str = str(destination)
        self.color: str = hex(random.randint(0, 16777215))
        self.style: str = str(destination.address).replace('.', '_')

    def get_line(self) -> str:
        return str(self.source.get_position()) + ';'\
            + str(self.destination.get_position())

    def get_line_kml(self) -> str:
        return str(self.source.get_position()) + '\n'\
            + str(self.destination.get_position())

    def get_name(self) -> str:
        return self.name

    def append_name(self, name: str) -> None:
        self.name += '; ' + name

    def __str__(self) -> str:
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


def create_route(ethernet: dpkt.ethernet.Ethernet) -> Route:
    ip: dpkt.ip.IP = ethernet.data
    source: IP = IP(socket.inet_ntoa(ip.src))
    destination: IP = IP(socket.inet_ntoa(ip.dst))
    return Route(source, destination)


def create_route(source_ip, source_position, destination_ip) -> Route:
    source: IP = IP(source_ip, source_position)
    destination: IP = IP(destination_ip)
    return Route(source, destination)


def all_routes_from_pcap(file) -> list[Route]:
    routes: list[Route] = []
    with open(file, 'rb') as f:
        # if pcap then pcap instead of pcapng
        pcap: dpkt.pcapng.Reader = dpkt.pcapng.Reader(f)
        for _, buffer in pcap:
            ethernet: dpkt.ethernet.Ethernet = dpkt.ethernet.Ethernet(buffer)
            if isinstance(ethernet.data, dpkt.ip.IP):
                routes.append(create_route(ethernet))
    return routes


def filter_ip_addresses(file: str) -> dict[str, int]:
    ip_addresses: dict[str, int] = {}
    with open(file, 'rb') as f:
        # if pcap then pcap instead of pcapng
        pcap: dpkt.pcapng.Reader = dpkt.pcapng.Reader(f)
        for _, buffer in pcap:
            ethernet: dpkt.ethernet.Ethernet = dpkt.ethernet.Ethernet(buffer)
            if isinstance(ethernet.data, dpkt.ip.IP):
                ip: dpkt.ip.IP = ethernet.data
                source: str = socket.inet_ntoa(ip.src)
                destination: str = socket.inet_ntoa(ip.dst)
                ip_addresses[source] = ip_addresses.get(source, 0) + 1
                ip_addresses[destination] = ip_addresses.get(destination, 0) + 1
    return ip_addresses


def create_routes(ip_addresses: dict[str, int],
                  home_position: Position) -> list[Route]:
    routes: list[Route] = []
    sorted_ip_addresses: list[str] = sorted(ip_addresses.items(),
                                            key=lambda item: item[1],
                                            reverse=True)
    ip_addresses: dict[str, int] = dict(sorted_ip_addresses)
    home_address, _ = sorted_ip_addresses[0]
    for ip_address in ip_addresses[1:]:
        routes.append(create_route(home_address, home_position, ip_address))
    return routes


def merge_routes(routes: list[Route]) -> list[Route]:
    merged_routes: list[Route] = []
    routes_to_merge: dict[str, list[Route]] = {}
    for route in routes:
        line: str = route.get_line()
        if line in routes_to_merge:
            routes_to_merge[line].append(route)
        else:
            routes_to_merge[line] = [route]
    for routes_on_line in routes_to_merge.values():
        merged_route: Route = routes_on_line[0]
        for route in routes_on_line[1:]:
            merged_route.append_name(route.get_name())
        merged_routes.append(merged_route)
    return merged_routes


def generate_kml(input_file: str,
                 home_longtitude: float,
                 home_latitude: float) -> str:
    home_position: Position = Position(home_longtitude, home_latitude)
    ip_addresses: dict[str, int] = filter_ip_addresses(input_file)
    routes: list[Route] = create_routes(ip_addresses, home_position)
    routes = merge_routes(routes)
    content: str = HEADER
    for route in routes:
        content += "\n" + str(route)
    content += FOOTER
    return content


def main() -> None:
    if len(sys.argv) < 2:
        print("No input file provided")
        return
    input_file: str = sys.argv[1]
    output_file: str = 'output.kml'
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    home_longtitude: float = 16.3662
    home_latitude: float = 48.2049
    content: str = generate_kml(input_file, home_longtitude, home_latitude)
    with open(output_file, 'w') as file:
        file.write(content)


if __name__ == '__main__':
    main()
