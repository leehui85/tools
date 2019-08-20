#!/usr/bin/env python

import sys
from optparse import OptionParser

sys.path.append("/pitrix/lib/pitrix-bots")
sys.path.append("/pitrix/lib/pitrix-common")

from api.constants import STATUS_CEASED, STATUS_DELETED
from db.constants import TB_IMAGE
from utils.global_conf import get_db
from utils.misc import exec_cmd
from bot import context


def _get_opt_parser():
    msg_usage = '''%prog [-d]'''
    opt_parser = OptionParser(msg_usage)

    opt_parser.add_option(
        "-d", "--dry", action="store", type="int", default=1,
        dest="dry",
        help='''1: just print info''')

    return opt_parser


def clean_deleted_images(dry=1):

    get_image_name_cmd = 'find /pitrix/images-repo -type f -name "img*" | xargs -I {} basename {}'
    ret = exec_cmd(get_image_name_cmd)
    if ret is None or ret[0] != 0:
        return -1

    image_id_set = set()
    if ret[1]:
        for line in ret[1].splitlines():
            parts = line.split('.')
            if len(parts) == 2:
                image_id = parts[0]
                image_id_set.add(image_id)

    image_ids = list(image_id_set)
    total = len(image_id_set)
    step = 100

    ctx = context.instance()
    ctx.pg = get_db("zone")
    condition = {
        "status": [STATUS_DELETED, STATUS_CEASED]
    }

    to_delele_image_ids = []
    for begin in range(0, total, step):
        end = min(begin + step, total)
        condition["image_id"] = image_ids[begin:end]
        ret = ctx.pg.base_get(TB_IMAGE, condition, ["image_id"])
        if ret:
            for image in ret:
                to_delele_image_ids.append(image["image_id"])

    for image_id in to_delele_image_ids:
        if dry:
            print "clean image [%s]" % image_id
        else:

            rm_cmd = "rm -f /pitrix/images-repo/{prefix}/{image_id}*".\
                format(prefix=image_id[4:6], image_id=image_id)
            exec_cmd(rm_cmd)

            rm_cmd = "rm -f /pitrix/images-repo/{prefix}/archive/{image_id}*".\
                format(prefix=image_id[4:6], image_id=image_id)
            exec_cmd(rm_cmd)

    print "done"


def main(args):

    parser = _get_opt_parser()
    (options, _) = parser.parse_args(args)
    return clean_deleted_images(dry=options.dry)


if __name__ == '__main__':
    main(sys.argv[1:])
