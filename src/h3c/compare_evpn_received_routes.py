#!/usr/bin/env python

import sys
from optparse import OptionParser


def _get_opt_parser():
    msg_usage = '''%prog -o <origin_file> -l <latest_file>'''
    opt_parser = OptionParser(msg_usage)

    opt_parser.add_option(
        "-o", "--origin_file", action="store", type="string", default=None,
        dest="origin_file",
        help='Path of the file which contains origin route results')

    opt_parser.add_option(
        "-l", "--latest_file", action="store", type="string", default=None,
        dest="latest_file",
        help='Path of the file which contains latest route results')

    return opt_parser


def print_vni_route_prefix(route_prefix, prefix=""):
    print "%s%s" % (prefix, route_prefix)


def print_vni_route_nexthop(nexthop, prefix="", via_prefix=""):
    print "%s    %s via %s" % (prefix, via_prefix, nexthop)


def print_vni_route_best_entry(nexthop, route_prefix, prefix="", via_prefix=""):
    print_vni_route_prefix(route_prefix, prefix=prefix)
    print_vni_route_nexthop(nexthop, prefix,
                            via_prefix="%s best" % via_prefix)


def print_vni_route_backup_entry(nexthop, route_prefix,
                                 prefix="", via_prefix=""):
    print_vni_route_prefix(route_prefix, prefix=prefix)
    print_vni_route_nexthop(nexthop, prefix,
                            via_prefix="%s backup" % via_prefix)


def print_vni_route_entry(route_prefix, vni_route, prefix="", via_prefix=""):
    print_vni_route_prefix(route_prefix, prefix)
    print_vni_route_best_entry(vni_route["best"], prefix, via_prefix)
    for v in vni_route["backup"]:
        print_vni_route_backup_entry(v, prefix, via_prefix)


def print_vni_route_map(vni_route_map, prefix="", via_prefix=""):

    for route_prefix, vni_route in vni_route_map.items():
        print_vni_route_entry(route_prefix, vni_route, prefix, via_prefix)


def print_format_content(route_map, file_path):
    vni_list = route_map.keys()
    vni_list = sorted(vni_list)
    with open(file_path, 'w') as fp:
        for vni in vni_list:
            fp.write("%s\n" % vni)

            vni_route_map = route_map.get(vni)
            if vni_route_map:
                route_prefix_list = vni_route_map.keys()
                route_prefix_list = sorted(route_prefix_list)
                for route_prefix in route_prefix_list:
                    fp.write("    %s\n" % route_prefix)

                    vni_route = vni_route_map[route_prefix]
                    best_nexthop = vni_route["best"]
                    if best_nexthop:
                        fp.write("        best via %s\n" % best_nexthop)
                    backup_nexthop_list = vni_route["backup"]
                    if backup_nexthop_list:
                        for backup_nexthop in backup_nexthop_list:
                            fp.write("        backup via %s\n" % backup_nexthop)
    return 0

def parse_section(section_lines, to_print=False, ingore_best_indicate=True):

    vni_route_map = {}
    route_num = len(section_lines) / 2
    for i in range(0, route_num):
        parts = section_lines[2 * i].split()
        indicate = parts[1]
        is_best = False
        if not ingore_best_indicate:
            if indicate.find(">") != -1:
                is_best = True
        route_prefix = parts[2]

        parts = section_lines[2* i + 1].split()
        nexthop = parts[0]

        if route_prefix not in vni_route_map:
            vni_route_map[route_prefix] = {"best": None, "backup": []}

        if is_best:
            vni_route_map[route_prefix]["best"] = nexthop
        else:
            vni_route_map[route_prefix]["backup"].append(nexthop)

    # sort
    for route_prefix, vni_route in vni_route_map.items():
        vni_route["backup"] = sorted(vni_route["backup"])

    if to_print:
        print_vni_route_map(vni_route_map)

    return vni_route_map


def parse_file(file_path):

    route_map = {}

    cur_vni = None
    section_lines = []

    with open(file_path) as fp:
        for line in fp:
            line = line.strip()
            if line and line != '\n':

                index = line.find("Route distinguisher:")
                if index != -1:
                    vni = str(line[index + len(
                        "Route distinguisher:"):]).strip()
                    if cur_vni:
                        vni_routes = parse_section(section_lines)
                        route_map[cur_vni] = vni_routes

                    # reset
                    cur_vni = vni
                    section_lines = []

                else:
                    if not cur_vni:
                        continue

                    if line.find("routes") != -1:
                        continue

                    if line.find("Network") != -1:
                        continue

                    section_lines.append(line)

        vni_routes = parse_section(section_lines)
        route_map[cur_vni] = vni_routes

    return route_map


def compare_vni_route_backup(origin_vni_route_backup,
                             latest_vni_route_backup,
                             route_prefix,
                             prefix=""):

    for latest_nexthop in latest_vni_route_backup:
        if latest_nexthop not in origin_vni_route_backup:
            # added
            print_vni_route_backup_entry(latest_nexthop,
                                         route_prefix,
                                         prefix=prefix,
                                         via_prefix="add latest")

    for origin_nexthop in origin_vni_route_backup:
        if origin_nexthop not in latest_vni_route_backup:
            # delete
            print_vni_route_backup_entry(origin_nexthop,
                                         route_prefix,
                                         prefix=prefix,
                                         via_prefix="delete origin")

    return 0


def compare_vni_route(origin_vni_route_map, latest_vni_route_map, prefix=""):

    prefix = "%s    " % prefix

    for route_prefix, latest_vni_route in latest_vni_route_map.items():

        if route_prefix not in origin_vni_route_map:
            # added
            print_vni_route_entry(route_prefix, latest_vni_route,
                                  prefix=prefix,
                                  via_prefix="add latest")
        else:
            # updated
            origin_vni_route = origin_vni_route_map[route_prefix]
            if latest_vni_route["best"] != origin_vni_route["best"]:
                print_vni_route_best_entry(origin_vni_route["best"],
                                           route_prefix=route_prefix,
                                           prefix=prefix,
                                           via_prefix="origin")
                print_vni_route_best_entry(latest_vni_route["best"],
                                           route_prefix=route_prefix,
                                           prefix=prefix,
                                           via_prefix="latest")

            compare_vni_route_backup(origin_vni_route["backup"],
                                     latest_vni_route["backup"],
                                     route_prefix=route_prefix,
                                     prefix=prefix)

    for route_prefix, origin_vni_route in origin_vni_route_map.items():
        if route_prefix not in latest_vni_route_map:
            # deleted route
            print_vni_route_entry(route_prefix, latest_vni_route,
                                  prefix=prefix,
                                  via_prefix="delete origin")

    return 0


def compare_route(origin_file, latest_file):
    origin_route_map = parse_file(origin_file)
    print_format_content(origin_route_map, "%s.bak" % origin_file)

    latest_route_map = parse_file(latest_file)
    print_format_content(latest_route_map, "%s.bak" % latest_file)

    # compare
    prefix = "    "

    for vni, latest_vni_route_map in latest_route_map.items():

        print vni

        if vni not in origin_route_map:
            # added vni
            print_vni_route_map(latest_vni_route_map,
                                prefix=prefix,
                                via_prefix="add latest")
        else:
            # may updated vni
            origin_vni_route_map = origin_route_map[vni]
            compare_vni_route(origin_vni_route_map,
                              latest_vni_route_map,
                              prefix=prefix)

    # deleted
    for vni, origin_vni_route_map in origin_route_map.items():

        if vni not in latest_route_map:
            # deleted vni
            print vni
            print_vni_route_map(latest_vni_route_map,
                                prefix=prefix,
                                via_prefix="delete origin")

    return 0


def main(args):

    parser = _get_opt_parser()
    (options, _) = parser.parse_args(args)

    if not options.origin_file:
        print "please specify origin_file parameter"
        return -1

    if not options.latest_file:
        print "please specify latest_file parameter"
        return -1

    return compare_route(options.origin_file, options.latest_file)


if __name__ == '__main__':
    main(sys.argv[1:])
