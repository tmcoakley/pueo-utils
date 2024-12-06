#!/usr/bin/env python3

import pickle
import subprocess
from pathlib import Path
from datetime import date
import argparse

parser = argparse.ArgumentParser(description="Create the version pickle for pueo.sqfs")
parser.add_argument('outpath', help='Path to the pueo.sqfs /usr/local/share')

args = parser.parse_args()

destPickle = args.outpath + '/share/version.pkl'

def get_git_revision_short_hash() -> str:
    hash = None
    try:
        hash = subprocess.check_output(['git','rev-parse','--short','HEAD']).decode().strip()
    except Exception as e:
        pass
    return hash

ver = Path("PUEO_SQFS_VERSION").read_text().strip('\n')

pueo_sqfs = {}
pueo_sqfs['version'] = ver
pueo_sqfs['hash'] = get_git_revision_short_hash()
pueo_sqfs['date'] = str(date.today())

with open(destPickle, "wb") as f:
    pickle.dump(pueo_sqfs, f)

