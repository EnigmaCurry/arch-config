#!/usr/bin/env python2
import os
import logging
logging.basicConfig(level=logging.INFO)

def make_links():
    "Link all the files and directories in ./home to $HOME"
    for fn in os.listdir('home'):
        dst_fn = fn
        if fn.startswith("_"):
            dst_fn = ".%s" % fn[1:]
        try:
            os.symlink(os.path.abspath(os.path.join('home',fn)), os.path.abspath(os.path.join(os.path.expanduser('~'), dst_fn)))
            logging.info('symlinked %s' % dst_fn)
        except OSError:
            pass

if __name__ == "__main__":
    make_links()
