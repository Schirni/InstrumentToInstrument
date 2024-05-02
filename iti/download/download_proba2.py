import argparse
import logging
import os
import shutil
from datetime import timedelta, datetime
from multiprocessing import Pool
from urllib.request import urlopen
from warnings import simplefilter
from random import sample

import drms
import numpy as np
import pandas as pd
from astropy import units as u
from astropy.io.fits import getheader, HDUList
from dateutil.relativedelta import relativedelta
from sunpy.map import Map
from sunpy.net import Fido, attrs as a
import sunpy_soar
from tqdm import tqdm

class Proba2Downloader:

    def __init__(self, base_path):
        self.base_path = base_path
        self.wavelengths = ["174"]
        self.dirs = ['174']
        [os. makedirs(os.path.join(base_path, dir), exist_ok=True) for dir in self.dirs]

    def downloadDate(self, date):
        files = []
        try:
            # Download SWAP
            for wl in self.wavelengths:
                files += [self.downloadSWAP(date, wl)]
            logging.info('Download complete %s' % date.isoformat())
        except Exception as ex:
            logging.error('Unable to download %s: %s' % (date.isoformat(), str(ex)))
            [os.remove(f) for f in files if os.path.exists(f)]


    def downloadSWAP(self, query_date, wl):
        file_path = os.path.join(self.base_path, str(wl), "%s.fits" % query_date.isoformat("T", timespec='seconds'))
        if os.path.exists(file_path):
            return file_path
        #
        search = Fido.search(a.Time(query_date - timedelta(minutes=15), query_date + timedelta(minutes=15)),
                             a.Instrument('SWAP'), a.Wavelength(174 * u.AA), a.Level(1))
        assert search.file_num > 0, "No data found for %s (%s)" % (query_date.isoformat(), wl)
        search = sorted(search['vso'], key=lambda x: abs(x['Start Time'].datetime - query_date).total_seconds())
        #
        for entry in search:
            files = Fido.fetch(entry, path=self.base_path, progress=False)
            if len(files) != 1:
                continue
            file = files[0]

            # Clean data with header info or add printing meta data info
            #header = Map(file.meta)
            if "lv0" in file:
                os.remove(file)
                continue

            shutil.move(file, file_path)
            return file_path

        raise Exception("No valid file found for %s (%s)!" % (query_date.isoformat(), wl))




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Download Proba2 data')
    parser.add_argument('--download_dir', type=str, help='path to the download directory.')
    parser.add_argument('--n_workers', type=str, help='number of parallel threads.', required=False, default=4)
    parser.add_argument('--start_date', type=str, help='start date in format YYYY-MM-DD.')
    parser.add_argument('--end_date', type=str, help='end date in format YYYY-MM-DD.', required=False, default=datetime.now())

    args = parser.parse_args()
    base_path = args.download_dir
    n_workers = args.n_workers
    start_date = args.start_date
    end_date = args.end_date
    #base_path = '//'

    download_util = Proba2Downloader(base_path=base_path)
    start_date_datetime = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_datetime = datetime.strptime(end_date, "%Y-%m-%d")
    num_months = (end_date_datetime.year - start_date_datetime.year) * 12 + (end_date_datetime.month - start_date_datetime.month)
    month_dates = [start_date_datetime + i * relativedelta(months=1) for i in range(num_months)]
    for d in [start_date_datetime + i * timedelta(days=1) for i in
              range((end_date_datetime - start_date_datetime) // timedelta(days=1))]:
        download_util.downloadDate(d)
