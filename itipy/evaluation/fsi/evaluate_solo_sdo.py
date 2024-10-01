import glob
import collections.abc

import numpy as np
import pandas as pd
from tqdm import tqdm
import sunpy.sun.constants
# hyper needs the four following aliases to be done manually.
collections.Iterable = collections.abc.Iterable
collections.Mapping = collections.abc.Mapping
collections.MutableSet = collections.abc.MutableSet
collections.MutableMapping = collections.abc.MutableMapping
# Now import hyper
from itipy.data.dataset import get_intersecting_files
from itipy.data.editor import NormalizeRadiusEditor, AIAPrepEditor, solo_norm, LoadMapEditor

from itipy.translate import *

from matplotlib import pyplot as plt

from sunpy.map import Map
from astropy import units as u
from astropy.coordinates import SkyCoord
import warnings

warnings.filterwarnings('ignore')

sdo_channels = ['171', '304']
#fsi_files = sorted(glob.glob('/mnt/disks/data/EUI/FSI/test_FSI/**/*.fits', recursive=True))
fsi_files_174 = sorted(glob.glob('/mnt/disks/data/EUI/FSI/*.fits', recursive=True))
fsi_files = get_intersecting_files('/mnt/disks/data/EUI/FSI/test_FSI', ['eui-fsi174-image', 'eui-fsi304-image'])
fsi_files_tot = get_intersecting_files('/mnt/disks/data/EUI/FSI/new_FSI', ['eui-fsi174-image', 'eui-fsi304-image'])
fsi_files_test = get_intersecting_files('/mnt/disks/data', ['eui-fsi174-image', 'eui-fsi304-image'])
aia_files = get_intersecting_files('/mnt/disks/data/SDO/test_SDO', ['171', '304'])
#aia_files = [sorted(glob.glob(os.path.join('/mnt/disks/data/SDO/test_SDO', c, '*.fits'))) for c in sdo_channels]
# aia_171_files = sorted(glob.glob('/mnt/disks/data/SDO/test_SDO/171/*.fits', recursive=True))
# aia_304_files = sorted(glob.glob('/mnt/disks/data/SDO/test_SDO/304/*.fits', recursive=True))
fsi_maps = [Map(f) for f in fsi_files_tot] # rotate north up
stereo_files_tot = get_intersecting_files('/mnt/disks/data', ['171', '195', '284', '304'])


def getFSIData(f):
    s_map, path = LoadMapEditor().call(f)
    s_map = NormalizeRadiusEditor(resolution=1024, fix_irradiance_with_distance=True).call(s_map)
    return s_map

def getAIAData(f):
    s_map = Map(f)
    s_map = NormalizeRadiusEditor(resolution=4096).call(s_map)
    s_map = AIAPrepEditor(calibration='auto').call(s_map)
    #data, _ = MapToDataEditor().call(s_map)
    return s_map

with Pool(90) as p:
    fsi174 = [f for f in tqdm(p.imap(getFSIData, fsi_files_tot[0]), total=len(fsi_files_tot[0]))]
    aia171 = [f for f in tqdm(p.imap(getAIAData, aia_files[0]), total=len(aia_files[0]))]
    fsi304 = [f for f in tqdm(p.imap(getFSIData, fsi_files_test[1]), total=len(fsi_files_test[1]))]
    fsi174 = [np.nanmean(f.data) for f in tqdm(p.imap(getFSIData, fsi_files_tot[0]), total=len(fsi_files_tot[0]))]
    fsi304 = [np.nanmean(f.data) for f in tqdm(p.imap(getFSIData, fsi_files_tot[1]), total=len(fsi_files_tot[1]))]

distances = []
with Pool(8) as p:
    fsi174_distances = [(f.dsun.value / sunpy.sun.constants.au.value) for f in tqdm(p.imap(getFSIData, fsi_files_tot[0]), total=len(fsi_files_tot[0]))]
fsi304_data = [getFSIData(f) for f in tqdm(fsi_files[1])]
aia171_data = [getAIAData(f) for f in tqdm(aia_files[0])]
aia304_data = [getAIAData(f) for f in tqdm(aia_files[1])]

with Pool(8) as p:
    aia171 = [f for f in tqdm(p.imap(getAIAData, aia_files[0]), total=len(aia_files[0]))]

for i in range(len(fsi304)):
    fig = plt.figure(figsize=(50, 50))
    fsi304[i].plot(cmap='sdoaia304', norm=solo_norm['eui-fsi304-image'], origin='lower')
    plt.axis('off')
    plt.title(str(fsi_files_tot[1][i].split('/')[-1].split('.')[0]), fontsize=40)
    plt.savefig('/mnt/disks/data/' + fsi_files_tot[1][i].split('/')[-1].split('.')[0] + '.jpg')
    plt.close()


with Pool(4) as p:
    fsi174_data = [np.nanmean(f.data) for f in tqdm(p.imap(getFSI174Data, fsi_files_174), total=len(fsi_files_174))]
    fsi174 = [f.data for f in tqdm(p.imap(getFSI174Data, fsi_files_174), total=len(fsi_files_174))]

time_fsi = []
longitude_fsi = []
latitude_fsi = []
for i in tqdm(range(len(fsi_files))):
    time_fsi.append(fsi_files[0][i].split('/')[-1].split('T')[0]+ ' ' + fsi_files[0][i].split('/')[-1].split('T')[1][0:8])
    longitude_fsi.append(fsi174[i].heliographic_longitude.value)
    latitude_fsi.append(fsi174[i].heliographic_latitude.value)


time_aia = []
longitude_aia = []
latitude_aia = []
for i in tqdm(range(len(aia171))):
    time_aia.append(aia_files[i].split('/')[-1].split('T')[0]+ ' ' + aia_files[i].split('/')[-1].split('T')[1][0:8])
    longitude_aia.append(aia171[i].heliographic_longitude.value)
    latitude_aia.append(aia171[i].heliographic_latitude.value)


iti_map = []
iti_304_data = []
translator = SolarOrbiterToSDO()
iti_fsi_maps = list(translator.translate([f for f in fsi_files_tot]))

aia_maps171 = [getAIAData(f) for f in tqdm(aia_files[0][:5])]
aia_maps304 = [getAIAData(f) for f in tqdm(aia_files[1][:5])]
fsi174_maps = [getFSIData(f) for f in tqdm(fsi_files_tot[0])]
fsi304_maps = [getFSIData(f) for f in tqdm(fsi_files_tot[1])]

for i in tqdm(range(len(fsi_files[0]))):
    iti171_intensity = np.nanmean(iti_fsi_maps[i][0].data)
    iti304_intensity = np.nanmean(iti_fsi_maps[i][1].data)

for i in tqdm(range(len(fsi_files_new))):
    iti_fsi_maps = list(translator.translate(fsi_files_new[i]))
    iti_map.append(iti_fsi_maps)


for i in range(5):
    fig, axs = plt.subplots(2, 3, subplot_kw={'projection': aia_maps171[i]}, figsize=(50, 20), dpi=100)
    aia_maps171[i].plot(axes=axs[0, 0], norm=sdo_norms[171])
    fsi174_maps[i].plot(axes=axs[0, 1], norm=solo_norm['eui-fsi174-image'])
    iti_fsi_maps[i][0].plot(axes=axs[0, 2], norm=sdo_norms[171])
    aia_maps304[i].plot(axes=axs[1, 0], norm=sdo_norms[304])
    fsi304_maps[i].plot(axes=axs[1, 1], norm=solo_norm['eui-fsi304-image'])
    iti_fsi_maps[i][1].plot(axes=axs[1, 2], norm=sdo_norms[304])
    axs[0, 0].set_title('AIA 171', fontsize=40)
    axs[0, 1].set_title('FSI 174', fontsize=40)
    axs[0, 2].set_title('ITI 171', fontsize=40)
    plt.savefig('/home/christophschirninger/'+fsi_files_tot[0][i].split('/')[-1].split('.')[0] + '.jpg')



for i in range(len(iti_fsi_maps)):
    fig, axs = plt.subplots(1, 3, figsize=(40, 20))
    axs[0].imshow(fsi174_data[i], cmap='sdoaia171', norm=solo_norm['eui-fsi174-image'], origin='lower')
    axs[0].axis('off')
    axs[0].set_title('Original FSI 174', fontsize=40)
    axs[1].imshow(iti_fsi_maps[i][0].data, cmap='sdoaia171', norm=sdo_norms[171], origin='lower')
    axs[1].axis('off')
    axs[1].set_title('ITI 171', fontsize=40)
    axs[2].imshow(aia171_data[i], cmap='sdoaia171', norm=sdo_norms[171], origin='lower')
    axs[2].axis('off')
    axs[2].set_title('SDO AIA 171', fontsize=40)
    plt.savefig('/home/christophschirninger/FSI_AIA_results/'+fsi_files[0][i].split('/')[-1].split('.')[0] + '.jpg')


for i in range(len(iti_fsi_maps[:5])):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(projection=iti_fsi_maps[i][0])
    iti_fsi_maps[i][0].plot(norm=sdo_norms[171])
    plt.axis('off')
    plt.savefig(str(i)+'.jpg')
    plt.title('ITI 171', fontsize=40)
    plt.savefig('/home/christophschirninger/SPIES_results/ITI171/'+fsi_files_test[1][i].split('/')[-1].split('.')[0] + '.jpg')

for i in range(len(fsi174)):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(projection=fsi174[i])
    fsi174[i].plot(norm=solo_norm['eui-fsi174-image'])
    plt.axis('off')
    plt.title('FSI 174', fontsize=40)
    plt.savefig('/home/christophschirninger/FSI_AIA_results/FSI174/'+fsi_files_test[0][i].split('/')[-1].split('.')[0] + '.jpg')

for i in range(len(aia171_data)):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(projection=aia171_data[i])
    aia171_data[i].plot(norm=sdo_norms[171])
    plt.axis('off')
    plt.title('SDO AIA 171', fontsize=40)
    plt.savefig('/home/christophschirninger/FSI_AIA_results/AIA171/'+aia_files[0][i].split('/')[-1].split('.')[0] + '.jpg')


for i in range(len(iti_fsi_maps)):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(projection=iti_fsi_maps[i][1])
    iti_fsi_maps[i][1].plot(norm=sdo_norms[304])
    plt.axis('off')
    plt.title('ITI 171', fontsize=40)
    plt.savefig('/home/christophschirninger/FSI_AIA_results/ITI304/'+fsi_files[0][i].split('/')[-1].split('.')[0] + '.jpg')

for i in range(len(fsi304)):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(projection=fsi304[i])
    fsi304[i].plot(norm=solo_norm['eui-fsi304-image'])
    plt.axis('off')
    plt.title('FSI 304', fontsize=40)
    plt.savefig('/home/christophschirninger/FSI_AIA_results/FSI304/'+fsi_files_test[1][i].split('/')[-1].split('.')[0] + '.jpg')

for i in range(len(aia304_data)):
    fig = plt.figure(figsize=(20, 20))
    ax = fig.add_subplot(projection=aia304_data[i])
    aia304_data[i].plot(norm=sdo_norms[304])
    plt.axis('off')
    plt.title('SDO AIA 304', fontsize=40)
    plt.savefig('/home/christophschirninger/FSI_AIA_results/AIA304/'+aia_files[0][i].split('/')[-1].split('.')[0] + '.jpg')





aia_171_intensities = []
aia_304_intensities = []
time_aia = []
for i in tqdm(range(len(aia_files[0]))):
    aia_171_intensities.append(aia_171_intensity[i].data.mean())
    aia_304_intensities.append(aia_304_intensity[i].data.mean())
    time_aia.append(aia_files[0][i].split('/')[-1].split('T')[0]+ ' ' + aia_files[0][i].split('/')[-1].split('T')[1][0:8])

fsi_files_time = fsi_files[::2]
iti_171_intensity = []
iti_304_intensity = []
time_fsi = []
for i in tqdm(range(len(fsi_files_tot[0]))):
    iti_171_intensity.append(np.mean(iti_fsi_maps[i][0].data))
    iti_304_intensity.append(np.mean(iti_fsi_maps[i][1].data))
    time_fsi.append(fsi_files_tot[1][i].split('/')[-1].split('T')[0]+ ' ' + fsi_files_tot[0][i].split('/')[-1].split('T')[1][0:8])

fsi_174_intensity = []
fsi_304_intensity = []
for i in tqdm(range(len(fsi_files_tot[0]))):
    fsi_174_intensity.append(np.mean(fsi174[i].data))
    fsi_304_intensity.append(np.mean(fsi304[i].data))


df_fsi_position = pd.DataFrame({'date': time_fsi, 'Longitude': longitude_fsi, 'Latitude': latitude_fsi})
df_fsi_position['date'] = pd.to_datetime(df_fsi_position['date'])

df_aia_position = pd.DataFrame({'date': time_aia, 'Longitude': longitude_aia, 'Latitude': latitude_aia})
df_aia_position['date'] = pd.to_datetime(df_aia_position['date'])

df_fsi174 = pd.DataFrame({'date': time_fsi, 'Intensity': fsi_174_intensity})
df_fsi174['date'] = pd.to_datetime(df_fsi174['date'])
df_fsi174['MovingAverage_FSI174'] = df_fsi174['Intensity'].rolling(66).mean()
df_fsi174['std'] = df_fsi174['Intensity'].std()
df_fsi174['mean'] = df_fsi174['Intensity'].mean()
df_fsi174['std_ma'] = df_fsi174['MovingAverage_FSI174'].std()
df_fsi174['mean_ma'] = df_fsi174['MovingAverage_FSI174'].mean()
df_fsi174['norm'] = (df_fsi174['Intensity'] - df_fsi174['mean']) / df_fsi174['std']
df_fsi174['calibrate'] = (df_fsi174['norm'] * df_aia171['std']) + df_aia171['mean']
df_fsi174['norm_ma'] = (df_fsi174['MovingAverage_FSI174'] - df_fsi174['mean_ma']) / df_fsi174['std_ma']
df_fsi174['calibrate_ma'] = df_fsi174['calibrate'].rolling(20).mean()


df_fsi304 = pd.DataFrame({'date': time_fsi, 'Intensity': fsi_304_intensity})
df_fsi304['date'] = pd.to_datetime(df_fsi304['date'])
df_fsi304['MovingAverage_FSI304'] = df_fsi304['Intensity'].rolling(4).mean()
df_fsi304['std'] = df_fsi304['Intensity'].std()
df_fsi304['mean'] = df_fsi304['Intensity'].mean()
df_fsi304['std_ma'] = df_fsi304['MovingAverage_FSI304'].std()
df_fsi304['mean_ma'] = df_fsi304['MovingAverage_FSI304'].mean()
df_fsi304['norm'] = (df_fsi304['Intensity'] - df_fsi304['mean']) / df_fsi304['std']
df_fsi304['calibrate'] = (df_fsi304['norm'] * df_aia304['std']) + df_aia304['mean']
df_fsi304['norm_ma'] = (df_fsi304['MovingAverage_FSI304'] - df_fsi304['mean_ma']) / df_fsi304['std_ma']
df_fsi304['calibrate_ma'] = df_fsi304['calibrate'].rolling(15).mean()

df_fsi174_close = pd.DataFrame({'date': time_fsi, 'Intensity': fsi174})
df_fsi174_close['date'] = pd.to_datetime(df_fsi174_close['date'])
df_fsi174_close['MovingAverage_FSI174'] = df_fsi174_close['Intensity'].rolling(330).mean()
df_fsi174_close['std'] = df_fsi174_close['Intensity'].std()
df_fsi174_close['mean'] = df_fsi174_close['Intensity'].mean()
df_fsi174_close['std_ma'] = df_fsi174_close['MovingAverage_FSI174'].std()
df_fsi174_close['mean_ma'] = df_fsi174_close['MovingAverage_FSI174'].mean()
df_fsi174_close['norm'] = (df_fsi174_close['Intensity'] - df_fsi174_close['mean']) / df_fsi174_close['std']
df_fsi174_close['calibrate'] = (df_fsi174_close['norm'] * df_aia171['std']) + df_aia171['mean']
df_fsi174_close['norm_ma'] = (df_fsi174_close['MovingAverage_FSI174'] - df_fsi174_close['mean_ma']) / df_fsi174_close['std_ma']
df_fsi174_close['calibrate_ma'] = df_fsi174_close['calibrate'].rolling(15).mean()

df_fsi304_close = pd.DataFrame({'date': time_fsi, 'Intensity': fsi304})
df_fsi304_close['date'] = pd.to_datetime(df_fsi304_close['date'])
df_fsi304_close['MovingAverage_FSI304'] = df_fsi304_close['Intensity'].rolling(330).mean()
df_fsi304_close['std'] = df_fsi304_close['Intensity'].std()
df_fsi304_close['mean'] = df_fsi304_close['Intensity'].mean()
df_fsi304_close['std_ma'] = df_fsi304_close['MovingAverage_FSI304'].std()
df_fsi304_close['mean_ma'] = df_fsi304_close['MovingAverage_FSI304'].mean()
df_fsi304_close['norm'] = (df_fsi304_close['Intensity'] - df_fsi304_close['mean']) / df_fsi304_close['std']
df_fsi304_close['calibrate'] = (df_fsi304_close['norm'] * df_aia304['std']) + df_aia304['mean']
df_fsi304_close['norm_ma'] = (df_fsi304_close['MovingAverage_FSI304'] - df_fsi304_close['mean_ma']) / df_fsi304_close['std_ma']
df_fsi304_close['calibrate_ma'] = df_fsi304_close['calibrate'].rolling(15).mean()




df_iti_fsi171 = pd.DataFrame({'date': time_fsi, 'Intensity': iti_171_intensity})
df_iti_fsi304 = pd.DataFrame({'date': time_fsi, 'Intensity': iti_304_intensity})
df_iti_fsi171['date'] = pd.to_datetime(df_iti_fsi171['date'])
df_iti_fsi304['date'] = pd.to_datetime(df_iti_fsi304['date'])

df_iti_fsi171_close = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/iti_fsi171_intensity_cycle_close.csv')
df_iti_fsi304_close = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/iti_fsi304_intensity_cycle_close.csv')
df_iti_fsi171_close['date'] = pd.to_datetime(df_iti_fsi171_close['date'])
df_iti_fsi304_close['date'] = pd.to_datetime(df_iti_fsi304_close['date'])

df_aia171 = pd.DataFrame({'date': time_aia, 'Intensity': aia_171_intensity})
df_aia304 = pd.DataFrame({'date': time_aia, 'Intensity': aia_304_intensity})
df_aia171['date'] = pd.to_datetime(df_aia171['date'])
df_aia304['date'] = pd.to_datetime(df_aia304['date'])

df_iti_fsi171['MovingAverage_FSI171'] = df_iti_fsi171['Intensity'].rolling(20).mean()
df_iti_fsi304['MovingAverage_FSI304'] = df_iti_fsi304['Intensity'].rolling(120).mean()
df_iti_fsi171['std'] = df_iti_fsi171['Intensity'].std()
df_iti_fsi304['std'] = df_iti_fsi304['Intensity'].std()
df_iti_fsi171['mean'] = df_iti_fsi171['Intensity'].mean()
df_iti_fsi304['mean'] = df_iti_fsi304['Intensity'].mean()
df_iti_fsi171['std_ma'] = df_iti_fsi171['MovingAverage_FSI171'].std()
df_iti_fsi304['std_ma'] = df_iti_fsi304['MovingAverage_FSI304'].std()
df_iti_fsi171['mean_ma'] = df_iti_fsi171['MovingAverage_FSI171'].mean()
df_iti_fsi304['mean_ma'] = df_iti_fsi304['MovingAverage_FSI304'].mean()

df_iti_fsi171_close['MovingAverage_FSI171'] = df_iti_fsi171_close['Intensity'].rolling(20).mean()
df_iti_fsi304_close['MovingAverage_FSI304'] = df_iti_fsi304_close['Intensity'].rolling(120).mean()


df_aia171['MovingAverage_AIA171'] = df_aia171['Intensity'].rolling(20).mean()
df_aia304['MovingAverage_AIA304'] = df_aia304['Intensity'].rolling(20).mean()
df_aia171['std'] = df_aia171['Intensity'].std()
df_aia304['std'] = df_aia304['Intensity'].std()
df_aia171['mean'] = df_aia171['Intensity'].mean()
df_aia304['mean'] = df_aia304['Intensity'].mean()
df_aia171['std_ma'] = df_aia171['MovingAverage_AIA171'].std()
df_aia304['std_ma'] = df_aia304['MovingAverage_AIA304'].std()
df_aia171['mean_ma'] = df_aia171['MovingAverage_AIA171'].mean()
df_aia304['mean_ma'] = df_aia304['MovingAverage_AIA304'].mean()


# df AIA 171 binning

df_aia171 = pd.read_csv('/mnt/disks/data/SDO/aia_171_intensity_cycle.csv')
df_aia171['date'] = pd.to_datetime(df_aia171['date'])
df_aia171['MovingAverage_AIA171'] = df_aia171['Intensity'].rolling(10).mean() # 4 observation per day = 30 days * 4 = 120
df_aia171['std'] = df_aia171['Intensity'].std()
df_aia171['mean'] = df_aia171['Intensity'].mean()

# df AIA 304 binning
df_aia304 = pd.read_csv('/mnt/disks/data/SDO/aia_304_fsi_intensity_cycle.csv')
df_aia304['date'] = pd.to_datetime(df_aia304['date'])
df_aia304['MovingAverage_AIA304'] = df_aia304['Intensity'].rolling(10).mean()
df_aia304['std'] = df_aia304['Intensity'].std()
df_aia304['mean'] = df_aia304['Intensity'].mean()


# df FSI 174 binning
df_fsi174 = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/fsi174_intensity_total.csv')
df_fsi174['date'] = pd.to_datetime(df_fsi174['date'])
df_fsi174['mean'] = df_fsi174['Intensity'].mean()
df_fsi174['std'] = df_fsi174['Intensity'].std()
df_fsi174['norm'] = (df_fsi174['Intensity'] - df_fsi174['mean']) / df_fsi174['std']
df_fsi174['calibrate'] = (df_fsi174['norm'] * df_aia171['std']) + df_aia171['mean']
df_fsi174['calibrate_ma'] = df_fsi174['calibrate'].rolling(30).mean()

# df FSI 304 binning
df_fsi304 = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/fsi304_intensity_total.csv')
df_fsi304['date'] = pd.to_datetime(df_fsi304['date'])
df_fsi304['mean'] = df_fsi304['Intensity'].mean()
df_fsi304['std'] = df_fsi304['Intensity'].std()
df_fsi304['norm'] = (df_fsi304['Intensity'] - df_fsi304['mean']) / df_fsi304['std']
df_fsi304['calibrate'] = (df_fsi304['norm'] * df_aia304['std']) + df_aia304['mean']
df_fsi304['calibrate_ma'] = df_fsi304['calibrate'].rolling(30).mean()


# df itipy 171 binning
df_iti_fsi171 = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/iti_fsi171_intensity_total.csv')
df_iti_fsi171['date'] = pd.to_datetime(df_iti_fsi171['date'])
df_iti_fsi171['MovingAverage_FSI171'] = df_iti_fsi171['Intensity'].rolling(30).mean()

# df itipy 304 binning
df_iti_fsi304 = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/iti_fsi304_intensity_total.csv')
df_iti_fsi304['date'] = pd.to_datetime(df_iti_fsi304['date'])
df_iti_fsi304['MovingAverage_FSI304'] = df_iti_fsi304['Intensity'].rolling(30).mean()


# sdo, fsi orbit
df_aia_position = pd.read_csv('/mnt/disks/data/SDO/aia_position.csv')
df_fsi_position = pd.read_csv('/mnt/disks/data/EUI/FSI/new_FSI/fsi_position.csv')
df_aia_position['date'] = pd.to_datetime(df_aia_position['date'])
df_fsi_position['date'] = pd.to_datetime(df_fsi_position['date'])
df_fsi_position['date_sdo_shift'] = pd.to_datetime(df_fsi_position['date_sdo_shift'])





fig, axs = plt.subplots(1, 1, figsize=(20, 10))
plt.plot(df_iti_fsi304['date'], df_iti_fsi304['Intensity'], label='ITI 304', c='r')
#plt.plot(df_fsi304['date'], df_fsi304['Intensity'], label='FSI 304 baseline ', c='g')
#plt.scatter(df_fsi304_close['date'], df_fsi304_close['calibrate_ma'], label='FSI 304 < 0.7 AU', c='c', s=1)
plt.plot(df_iti_fsi304_close['date'], df_iti_fsi304_close['Intensity'], label='ITI 304 < 0.7 AU', c='k')
plt.plot(df_aia304['date'][6500:], df_aia304['Intensity'][6500:], label='SDO AIA 304', c='b')
#plt.plot(df_aia304['date'], df_aia304['Intensity'], label='moving average', c='r')
plt.plot(df_aia304['date'][6500:], df_aia304['Intensity'][6500:] + df_aia304['Intensity'][6500:].std(), 'b--')
plt.plot(df_aia304['date'][6500:], df_aia304['Intensity'][6500:] - df_aia304['Intensity'][6500:].std(), 'b--')
plt.fill_between(df_aia304['date'][6500:], df_aia304['Intensity'][6500:] + df_aia304['Intensity'][6500:].std(),
                    df_aia304['Intensity'][6500:] - df_aia304['Intensity'][6500:].std(), alpha=0.05, facecolor='blue')
# plt.plot(np.asarray(time), plus_std, 'b--')
# plt.plot(np.asarray(time), minus_std, 'b--',)
# plt.fill_between(np.asarray(new_time), plus_std, minus_std, alpha=0.05, facecolor='blue')
plt.ylabel('Intensity [DN/s]', fontsize=20)
plt.xlabel('Time', fontsize=20)
plt.title('174 Light curve', fontsize=40)
plt.xticks(rotation=45, fontsize=15)
plt.yticks(fontsize=15)
#axs.xaxis.set_major_locator(mdates.DayLocator(interval=50))
# axs.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
plt.legend(fontsize="20")
plt.savefig('aia_fsi_iti_304_lc_test.jpg')

fig, axs = plt.subplots(1, 1, figsize=(20, 10))
plt.scatter(df_iti_fsi171['date'], df_iti_fsi171['MovingAverage_FSI171'], label='ITI 171', c='r', s=1)
plt.scatter(df_fsi174['date'], df_fsi174['calibrate_ma'], label='FSI 174 baseline', c='g', s=1)
plt.scatter(df_fsi174_close['date'], df_fsi174_close['calibrate_ma'], label='FSI 174 < 0.7 AU', c='c', s=1)
plt.scatter(df_iti_fsi171_close['date'], df_iti_fsi171_close['MovingAverage_FSI171'], label='ITI 171 < 0.7 AU', c='k', s=1)
plt.plot(df_aia171['date'][6500:], df_aia171['MovingAverage_AIA171'][6500:], label='SDO AIA 171', c='b')
#plt.plot(df_aia171['date'], df_aia171['MovingAverage_AIA171'], label='moving average', c='r')
plt.plot(df_aia171['date'][6500:], df_aia171['MovingAverage_AIA171'][6500:] + df_aia171['MovingAverage_AIA171'][6500:].std(), 'b--')
plt.plot(df_aia171['date'][6500:], df_aia171['MovingAverage_AIA171'][6500:] - df_aia171['MovingAverage_AIA171'][6500:].std(), 'b--')
plt.fill_between(df_aia171['date'][6500:], df_aia171['MovingAverage_AIA171'][6500:] + df_aia171['MovingAverage_AIA171'][6500:].std(),
                    df_aia171['MovingAverage_AIA171'][6500:] - df_aia171['MovingAverage_AIA171'][6500:].std(), alpha=0.05, facecolor='blue')
plt.ylabel('Intensity [DN/s]', fontsize=20)
plt.xlabel('Time', fontsize=20)
plt.title('171 Light curve', fontsize=40)
plt.xticks(rotation=45, fontsize=15)
plt.yticks(fontsize=15)
#axs.xaxis.set_major_locator(mdates.DayLocator(interval=50))
# axs.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
plt.legend(fontsize="20")
plt.savefig('iti_fsi_aia_171_lc_test.jpg')

############################################################################################################

fig, axs = plt.subplots(3, 1, figsize=(40, 20))
axs[0].scatter(df_fsi174['date'][2286:], df_fsi174['calibrate_ma'][2286:], label='FSI 174 baseline', c='g', marker='o', s=4)
axs[0].scatter(df_fsi174_close['date'][585:], df_fsi174_close['calibrate_ma'][585:], c='g', marker='o', s=4)
axs[0].scatter(df_iti_fsi171['date'][1184:], df_iti_fsi171['MovingAverage_FSI171'][1184:], label='ITI 171', c='r', marker='o', s=4)
axs[0].scatter(df_iti_fsi171_close['date'][585:], df_iti_fsi171_close['MovingAverage_FSI171'][585:], c='r', marker='o', s=4)
axs[0].plot(df_aia171['date'][7200:], df_aia171['MovingAverage_AIA171'][7200:], label='SDO AIA 171', c='b')
axs[0].plot(df_aia171['date'][7200:], df_aia171['MovingAverage_AIA171'][7200:] + df_aia171['MovingAverage_AIA171'][7200:].std(), 'b--')
axs[0].plot(df_aia171['date'][7200:], df_aia171['MovingAverage_AIA171'][7200:] - df_aia171['MovingAverage_AIA171'][7200:].std(), 'b--')
axs[0].fill_between(df_aia171['date'][7200:], df_aia171['MovingAverage_AIA171'][7200:] + df_aia171['MovingAverage_AIA171'][7200:].std(),
                    df_aia171['MovingAverage_AIA171'][7200:] - df_aia171['MovingAverage_AIA171'][7200:].std(), alpha=0.05, facecolor='blue')
axs[0].set_ylabel('Intensity [DN/s]', fontsize=30)
axs[0].grid('on')
axs[0].set_xticks([])
axs[0].tick_params(axis='y', labelsize=20)
#axs[0].xlabel('Time', fontsize=20)
axs[0].set_title('171/174 Light curve', fontsize=50)
#plt.xticks(rotation=45, fontsize=15)
#axs[0].set_yticks(fontsize=15)
axs[0].legend(fontsize="20")
axs[1].plot(df_aia171['date'][7200:], np.zeros(len(df_aia171['date'][7200:])), c='white')
axs[1].scatter(df_fsi_position['date'][1880:], df_fsi_position['Latitude'][1880:], label='Solar Orbiter', c='orange', linewidth=3)
axs[1].plot(df_aia_position['date'][1132:1604], df_aia_position['Latitude'][1132:1604], label='SDO', c='b', linewidth=3)
axs[1].grid('on')
axs[1].set_ylabel('Latitude [deg]', fontsize=30)
axs[1].tick_params(axis='y', labelsize=20)
axs[1].set_xticks([])
axs[1].legend(fontsize="20")
#axs[1].xlabel('Time', fontsize=20)
#axs[1].title('Latitude', fontsize=40)
axs[2].plot(df_aia171['date'][7200:], np.ones(len(df_aia171['date'][7200:])), c='white')
axs[2].scatter(df_fsi_position['date'][1880:], df_fsi_position['Longitude'][1880:], label='Solar Orbiter', c='orange', linewidth=3)
axs[2].plot(df_aia_position['date'][1132:1604], df_aia_position['Longitude'][1132:1604], label='SDO', c='b', linewidth=3)
axs[2].set_ylabel('Longitude [deg]', fontsize=30)
axs[2].set_xlabel('Time', fontsize=45)
axs[2].tick_params(axis='y', labelsize=20)
axs[2].tick_params(axis='x', rotation=45, labelsize=25)
axs[2].grid('on')
#axs[2].title('Longitude', fontsize=40)
plt.savefig('fsi_aia_174_lc_position.jpg')


fig, axs = plt.subplots(2, 1, figsize=(40, 20))
axs[0].scatter(df_fsi_position['date'], df_fsi174['calibrate'], label='FSI 174 baseline', c='g', marker='o', s=4)
axs[0].scatter(df_fsi_position['date'], df_iti_fsi171['Intensity'], label='ITI 171', c='r', marker='o', s=4)
axs[0].plot(df_aia171['date'][7000:8660], df_aia171['Intensity'][7000:8660], label='AIA 171', c='b')
axs[0].plot(df_aia171['date'][7000:8660], df_aia171['Intensity'][7000:8660] + df_aia171['std'][7000:8660], 'b--')
axs[0].plot(df_aia171['date'][7000:8660], df_aia171['Intensity'][7000:8660] - df_aia171['std'][7000:8660], 'b--')
axs[0].fill_between(df_aia171['date'][7000:8660], df_aia171['Intensity'][7000:8660] + df_aia171['std'][7000:8660],
                    df_aia171['Intensity'][7000:8660] - df_aia171['std'][7000:8660], alpha=0.05, facecolor='blue')
#axs[0].scatter(df_fsi_position['date'], df_fsi_distance['distance'] + 280, s=100, marker='*', color='gold', zorder=3, label='Solar Orbiter distance < 0.7 AU')
axs[0].set_ylabel('Intensity [DN/s]', fontsize=30)
axs[0].grid('on')
axs[0].set_xticks([])
axs[0].tick_params(axis='y', labelsize=20)
#axs[0].xlabel('Time', fontsize=20)
axs[0].set_title('171/174 Light curve', fontsize=50)
#plt.xticks(rotation=45, fontsize=15)
#axs[0].set_yticks(fontsize=15)
axs[0].legend(loc='upper right', fontsize="30")
axs[1].plot(df_aia171['date'][7000:8660], np.ones(len(df_aia171['date'][7000:8660])), c='white')
axs[1].scatter(df_fsi_position['date'], df_fsi_position['Longitude'], label='Solar Orbiter', c='orange', linewidth=3)
axs[1].plot(df_aia_position['date'][1078:1488], df_aia_position['Longitude'][1078:1488], label='SDO', c='b', linewidth=3)
axs[1].set_ylabel('Longitude [deg]', fontsize=30)
axs[1].set_xlabel('Time', fontsize=45)
axs[1].tick_params(axis='y', labelsize=20)
axs[1].tick_params(axis='x', rotation=45, labelsize=25)
axs[1].legend(fontsize="30", loc='upper left')
axs[1].grid('on')
#axs[2].title('Longitude', fontsize=40)
plt.savefig('fsi_aia_174_lc_position_v2.jpg')


fig, axs = plt.subplots(2, 1, figsize=(40, 20))
axs[0].scatter(df_fsi_position['date'], df_fsi304['calibrate'], label='FSI 304', c='g', marker='o', s=4)
axs[0].scatter(df_fsi_position['date'], df_iti_fsi304['Intensity'], label='ITI 304', c='r', marker='o', s=4)
axs[0].plot(df_aia304['date'][7000:8660], df_aia304['MovingAverage_AIA304'][7000:8660], label='SDO AIA 304', c='b')
axs[0].plot(df_aia304['date'][7000:8660], df_aia304['MovingAverage_AIA304'][7000:8660] + df_aia304['std'][7000:8660], 'b--')
axs[0].plot(df_aia304['date'][7000:8660], df_aia304['MovingAverage_AIA304'][7000:8660] - df_aia304['std'][7000:8660], 'b--')
axs[0].fill_between(df_aia304['date'][7000:8660], df_aia304['MovingAverage_AIA304'][7000:8660] + df_aia304['std'][7000:8660],
                    df_aia304['MovingAverage_AIA304'][7000:8660] - df_aia304['std'][7000:8660], alpha=0.05, facecolor='blue')
axs[0].scatter(df_fsi_position['date'], df_fsi_distance['distance'] + 80, s=100, marker='*', color='gold', zorder=3, label='Solar Orbiter distance < 0.7 AU')
axs[0].set_ylabel('Intensity [DN/s]', fontsize=30)
axs[0].grid('on')
axs[0].set_xticks([])
axs[0].tick_params(axis='y', labelsize=20)
#axs[0].xlabel('Time', fontsize=20)
axs[0].set_title('304 Light curve', fontsize=50)
#plt.xticks(rotation=45, fontsize=15)
#axs[0].set_yticks(fontsize=15)
axs[0].legend(loc='upper right', fontsize="30")
axs[1].plot(df_aia304['date'][7000:8660], np.ones(len(df_aia304['date'][7000:8660])), c='white')
axs[1].scatter(df_fsi_position['date_sdo_shift'], df_fsi_position['Longitude'], label='Solar Orbiter', c='orange', linewidth=3)
axs[1].plot(df_aia_position['date'][1078:1488], df_aia_position['Longitude'][1078:1488], label='SDO', c='b', linewidth=3)
axs[1].set_ylabel('Longitude [deg]', fontsize=30)
axs[1].set_xlabel('Time', fontsize=45)
axs[1].tick_params(axis='y', labelsize=20)
axs[1].tick_params(axis='x', rotation=45, labelsize=25)
axs[1].legend(fontsize="30", loc='upper left')
axs[1].grid('on')
#axs[2].title('Longitude', fontsize=40)
plt.savefig('fsi_aia_304_lc_position_v2.jpg')




fig, axs = plt.subplots(1, 1, figsize=(20, 10))
plt.scatter(df_fsi304['date'], df_fsi304['calibrate_ma'], label='FSI 304 baseline', c='g', marker='o', s=4)
plt.scatter(df_fsi304_close['date'], df_fsi304_close['calibrate_ma'], label='FSI 304 < 0.7 AU', c='r', marker='o', s=4)
plt.scatter(df_iti_fsi304['date'], df_iti_fsi304['MovingAverage_FSI304'], label='ITI 304', c='k', marker='o', s=4)
plt.scatter(df_iti_fsi304_close['date'], df_iti_fsi304_close['MovingAverage_FSI304'], label='ITI 304 < 0.7 AU', c='c', marker='o', s=4)
plt.plot(df_aia304['date'][6500:], df_aia304['MovingAverage_AIA304'][6500:], label='SDO AIA 304', c='b')
plt.plot(df_aia304['date'][6500:], df_aia304['MovingAverage_AIA304'][6500:] + df_aia304['MovingAverage_AIA304'][6500:].std(), 'b--')
plt.plot(df_aia304['date'][6500:], df_aia304['MovingAverage_AIA304'][6500:] - df_aia304['MovingAverage_AIA304'][6500:].std(), 'b--')
plt.fill_between(df_aia304['date'][6500:], df_aia304['MovingAverage_AIA304'][6500:] + df_aia304['MovingAverage_AIA304'][6500:].std(),
                    df_aia304['MovingAverage_AIA304'][6500:] - df_aia304['MovingAverage_AIA304'][6500:].std(), alpha=0.05, facecolor='blue')
plt.ylabel('Intensity [DN/s]', fontsize=20)
plt.xlabel('Time', fontsize=20)
plt.title('304 Light curve', fontsize=40)
plt.xticks(rotation=45, fontsize=15)
plt.yticks(fontsize=15)
plt.legend(fontsize="20")
plt.savefig('fsi_aia_304_lc_cycle.jpg')

############################################################################################################


fig, axs = plt.subplots(1, 1, figsize=(20, 10))
plt.plot(df_fsi174['date'], df_fsi174['calibrate'], label='FSI 174 1 AU', c='k')
plt.plot(df_aia171['date'][2735:], df_aia171['MovingAverage_AIA171'][2735:], label='AIA 171', c='b')
plt.plot(df_aia171['date'][2735:], df_aia171['MovingAverage_AIA171'][2735:] + df_aia171['MovingAverage_AIA171'][2735:].std(), 'b--')
plt.plot(df_aia171['date'][2735:], df_aia171['MovingAverage_AIA171'][2735:] - df_aia171['MovingAverage_AIA171'][2735:].std(), 'b--')
plt.fill_between(df_aia171['date'][2735:], df_aia171['MovingAverage_AIA171'][2735:] + df_aia171['MovingAverage_AIA171'][2735:].std(),
                    df_aia171['MovingAverage_AIA171'][2735:] - df_aia171['MovingAverage_AIA171'][2735:].std(), alpha=0.05, facecolor='blue')
plt.ylabel('Intensity', fontsize=20)
plt.xlabel('Time', fontsize=20)
plt.title('171/174 Light curve', fontsize=40)
plt.xticks(rotation=45, fontsize=15)
plt.yticks(fontsize=15)
#axs.xaxis.set_major_locator(mdates.DayLocator(interval=50))
# axs.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
plt.legend(fontsize="20")
plt.savefig('FSI_AIA_b6_lc_scaled_1AU_ma.jpg')

for i in range(len(fsi_files_304)):
    fig = plt.figure(figsize=(50, 20))
    ax = fig.add_subplot(projection=fsi_maps[0])
    fsi_304_maps_exp[i].plot(axes=ax, norm=solo_norm['eui-fsi304-image'])
    ax.axis('off')
    ax.set_title('Original - FSI 304', fontsize=40)
    plt.savefig(time_fsi[i] + '_FSI_304.jpg')


### Crop maps
fig = plt.figure(figsize=(50, 20))
ax = fig.add_subplot(projection=iti_map[0][0][1])
iti_map[0][0][1].plot(axes=ax, norm=sdo_norms[304])
ax.axis('off')
ax.set_title('ITI', fontsize=40)
coords = SkyCoord(Tx=(-380, 220) * u.arcsec,
                  Ty=(200, 800) * u.arcsec,
                  frame=iti_map[0][0][1].coordinate_frame)
iti_map[0][0][1].draw_quadrangle(coords, axes=ax, color='red', linewidth=5)
plt.savefig('iti_fsi_304_rectangle.jpg')

top_right = SkyCoord(Tx=-380 * u.arcsec, Ty=200 * u.arcsec, frame=iti_map[0][0][1].coordinate_frame)
bottom_left = SkyCoord(Tx=220 * u.arcsec, Ty=800 * u.arcsec, frame=iti_map[0][0][1].coordinate_frame)
fig = plt.figure(figsize=(50, 20))
ax = fig.add_subplot(projection=iti_map[0][0][1])
iti_map[0][0][1].submap(bottom_left, top_right=top_right).plot(axes=ax, norm=sdo_norms[304])
ax.axis('off')
ax.set_title('ITI', fontsize=40)
plt.savefig('iti_fsi_304_submap.jpg')



fig = plt.figure(figsize=(50, 20))
ax = fig.add_subplot(projection=fsi_304_map_exp)
fsi_304_map_exp.plot(axes=ax, norm=solo_norm['eui-fsi304-image'])
ax.axis('off')
ax.set_title('ITI', fontsize=40)
coords = SkyCoord(Tx=(-485, 115) * u.arcsec,
                  Ty=(125, 725) * u.arcsec,
                  frame=fsi_304_map_exp.coordinate_frame)
fsi_304_map_exp.draw_quadrangle(coords, axes=ax, color='red', linewidth=5)
plt.savefig('fsi_304_rectangle.jpg')

top_right = SkyCoord(Tx=-485 * u.arcsec, Ty=125 * u.arcsec, frame=fsi_304_map_exp.coordinate_frame)
bottom_left = SkyCoord(Tx=115 * u.arcsec, Ty=725 * u.arcsec, frame=fsi_304_map_exp.coordinate_frame)
fig = plt.figure(figsize=(50, 20))
ax = fig.add_subplot(projection=fsi_304_map_exp)
fsi_304_map_exp.submap(bottom_left, top_right=top_right).plot(axes=ax, norm=solo_norm['eui-fsi304-image'])
ax.axis('off')
ax.set_title('ITI', fontsize=40)
plt.savefig('fsi_304_submap.jpg')


fig = plt.figure(figsize=(50, 20))
ax = fig.add_subplot(projection=aia_map_exp)
aia_map_exp.plot(axes=ax, norm=sdo_norms[304])
ax.axis('off')
ax.set_title('ITI', fontsize=40)
coords = SkyCoord(Tx=(-440, 100) * u.arcsec,
                  Ty=(90, 630) * u.arcsec,
                  frame=aia_map_exp.coordinate_frame)
aia_map_exp.draw_quadrangle(coords, axes=ax, color='red', linewidth=5)
plt.savefig('aia_304_rectangle.jpg')

top_right = SkyCoord(Tx=-440 * u.arcsec, Ty=90 * u.arcsec, frame=aia_map_exp.coordinate_frame)
bottom_left = SkyCoord(Tx=100 * u.arcsec, Ty=630 * u.arcsec, frame=aia_map_exp.coordinate_frame)
fig = plt.figure(figsize=(50, 20))
ax = fig.add_subplot(projection=aia_map_exp)
aia_map_exp.submap(bottom_left, top_right=top_right).plot(axes=ax, norm=sdo_norms[304])
ax.axis('off')
ax.set_title('ITI', fontsize=40)
plt.savefig('aia_304_submap.jpg')




### Spacecraft position
fig, axs = plt.subplots(2, 1, figsize=(40, 20))
axs[0].scatter(df_fsi_position['date_sdo_shift'], df_fsi_position['Latitude'], label='Solar Orbiter', c='orange', linewidth=3)
axs[0].plot(df_aia_position['date'][1078:1488], df_aia_position['Latitude'][1078:1488], label='SDO', c='b', linewidth=3)
axs[0].set_ylabel('Latitude [deg]', fontsize=30)
axs[0].grid('on')
axs[0].set_xticks([])
axs[0].tick_params(axis='y', labelsize=30)
#axs[0].xlabel('Time', fontsize=20)
#axs[0].set_title('Latitude', fontsize=50)
axs[1].plot(df_aia171['date'][7000:8660], np.ones(len(df_aia171['date'][7000:8660])), c='white')
axs[1].scatter(df_fsi_position['date_sdo_shift'], df_fsi_position['Longitude'], label='Solar Orbiter', c='orange', linewidth=3)
axs[1].plot(df_aia_position['date'][1078:1488], df_aia_position['Longitude'][1078:1488], label='SDO', c='b', linewidth=3)
axs[1].set_ylabel('Longitude [deg]', fontsize=30)
axs[1].set_xlabel('Time', fontsize=45)
axs[1].tick_params(axis='y', labelsize=30)
axs[1].tick_params(axis='x', rotation=45, labelsize=25)
axs[1].legend(fontsize="30", loc='upper left')
axs[1].grid('on')
#axs[2].title('Longitude', fontsize=40)
plt.savefig('Solo_SDO_position_shift.jpg')



### MAE and Cross correlation comparison with binning
df_aia171_solo = pd.DataFrame({'date': df_aia171['date'][7006:8629], 'Intensity': df_aia171['Intensity'][7006:8629]})
df_fsi174_shift = pd.DataFrame({'date': df_fsi_position['date_sdo_shift'], 'Intensity': df_fsi174['Intensity']})
df_fsi174_bin_mean = df_fsi174_shift.set_index('date').groupby(pd.Grouper(freq='5D')).median()
df_fsi174_bin_mean_calibrate = ((df_fsi174_bin_mean['Intensity'].values - df_fsi174['mean'][0]) / df_fsi174['std'][0]) * df_aia171['std'][0] + df_aia171['mean'][0]
df_aia171_bin_mean = df_aia171_solo.set_index('date').groupby(pd.Grouper(freq='5D')).median()
df_iti_fsi171 = pd.DataFrame({'date': df_fsi_position['date_sdo_shift'], 'Intensity': df_iti_fsi171['Intensity']})
df_iti_fsi171_bin_mean = df_iti_fsi171.set_index('date').groupby(pd.Grouper(freq='5D')).median()

plt.figure(figsize=(20, 10))
plt.plot(df_fsi174_bin_mean.index, df_fsi174_bin_mean_calibrate, label='FSI 174', c='g')
plt.plot(df_aia171_bin_mean.index, df_aia171_bin_mean['Intensity'].values, label='SDO AIA 171', c='b')
plt.plot(df_iti_fsi171_bin_mean.index, df_iti_fsi171_bin_mean['Intensity'].values, label='ITI 171', c='r')
plt.savefig('iti_fsi_aia_171_lc_bin.jpg')



df_aia304_solo = pd.DataFrame({'date': df_aia304['date'][7006:8629], 'Intensity': df_aia304['Intensity'][7006:8629]})
df_fsi304_shift = pd.DataFrame({'date': df_fsi_position['date_sdo_shift'], 'Intensity': df_fsi304['Intensity']})
df_fsi304_bin_mean = df_fsi304_shift.set_index('date').groupby(pd.Grouper(freq='5D')).median()
df_fsi304_bin_mean_calibrate = ((df_fsi304_bin_mean['Intensity'].values - df_fsi304['mean'][0]) / df_fsi304['std'][0]) * df_aia304['std'][0] + df_aia304['mean'][0]
df_aia304_bin_mean = df_aia304_solo.set_index('date').groupby(pd.Grouper(freq='5D')).median()
df_iti_fsi304 = pd.DataFrame({'date': df_fsi_position['date_sdo_shift'], 'Intensity': df_iti_fsi304['Intensity']})
df_iti_fsi304_bin_mean = df_iti_fsi304.set_index('date').groupby(pd.Grouper(freq='5D')).median()


plt.figure(figsize=(20, 10))
plt.plot(df_fsi304_bin_mean.index, df_fsi304_bin_mean_calibrate, label='FSI 304', c='g')
plt.plot(df_aia304_bin_mean.index, df_aia304_bin_mean['Intensity'].values, label='SDO AIA 304', c='b')
plt.plot(df_iti_fsi304_bin_mean.index, df_iti_fsi304_bin_mean['Intensity'].values, label='ITI 304', c='r')
plt.savefig('iti_fsi_aia_304_lc_bin.jpg')



mae_fsi174_baseline = np.nanmean(np.abs(df_fsi174_bin_mean_calibrate[:-1] - df_aia171_bin_mean['Intensity'].values))
mae_iti171 = np.nanmean(np.abs(df_iti_fsi171_bin_mean['Intensity'].values[:-1] - df_aia171_bin_mean['Intensity'].values))
mae_fsi174_original = np.nanmean(np.abs(df_fsi174_bin_mean['Intensity'].values[:-1] - df_aia171_bin_mean['Intensity'].values))

mae_fsi174_baseline_pc = mae_fsi174_baseline / df_aia171_bin_mean['Intensity'].values.max() * 100
mae_fsi174_original_pc = mae_fsi174_original / df_aia171_bin_mean['Intensity'].values.max() * 100
mae_iti171_pc = mae_iti171 / df_aia171_bin_mean['Intensity'].values.max() * 100


cond = ~np.isnan(df_fsi174_bin_mean_calibrate[:-1]) & ~np.isnan(df_aia171_bin_mean['Intensity'].values)
cc_fsi174_baseline = np.corrcoef(df_fsi174_bin_mean_calibrate[:-1][cond], df_aia171_bin_mean['Intensity'].values[cond])
cc_fsi174_original = np.corrcoef(df_fsi174_bin_mean['Intensity'].values[:-1][cond], df_aia171_bin_mean['Intensity'].values[cond])
cc_iti171 = np.corrcoef(df_iti_fsi171_bin_mean['Intensity'].values[:-1][cond], df_aia171_bin_mean['Intensity'].values[cond])




mae_fsi304_baseline = np.nanmean(np.abs(df_fsi304_bin_mean_calibrate[:-1] - df_aia304_bin_mean['Intensity'].values))
mae_iti304 = np.nanmean(np.abs(df_iti_fsi304_bin_mean['Intensity'].values[:-1] - df_aia304_bin_mean['Intensity'].values))
mae_fsi304_original = np.nanmean(np.abs(df_fsi304_bin_mean['Intensity'].values[:-1] - df_aia304_bin_mean['Intensity'].values))

mae_fsi304_baseline_pc = mae_fsi304_baseline / df_aia304_bin_mean['Intensity'].values.max() * 100
mae_fsi304_original_pc = mae_fsi304_original / df_aia304_bin_mean['Intensity'].values.max() * 100
mae_iti304_pc = mae_iti304 / df_aia304_bin_mean['Intensity'].values.max() * 100

cond = ~np.isnan(df_fsi304_bin_mean_calibrate[:-1]) & ~np.isnan(df_aia304_bin_mean['Intensity'].values)
cc_fsi304_baseline = np.corrcoef(df_fsi304_bin_mean_calibrate[:-1][cond], df_aia304_bin_mean['Intensity'].values[cond])
cc_fsi304_original = np.corrcoef(df_fsi304_bin_mean['Intensity'].values[:-1][cond], df_aia304_bin_mean['Intensity'].values[cond])
cc_iti304 = np.corrcoef(df_iti_fsi304_bin_mean['Intensity'].values[:-1][cond], df_aia304_bin_mean['Intensity'].values[cond])

# Make a nice print statement for this results
print(f'MAE FSI 174 baseline: {mae_fsi174_baseline:.2f} and in %: {mae_fsi174_baseline_pc:.2f}%')
print(f'MAE FSI 174 original: {mae_fsi174_original:.2f} and in %: {mae_fsi174_original_pc:.2f}%')
print(f'MAE ITI 171: {mae_iti171:.2f} and in %: {mae_iti171_pc:.2f}%')
print(f'CrossCorrelation FSI 174 baseline: {cc_fsi174_baseline[0, 1]:.2f}')
print(f'CrossCorrelation FSI 174 original: {cc_fsi174_original[0, 1]:.2f}')
print(f'CrossCorrelation ITI 171: {cc_iti171[0, 1]:.2f}')

print(f'MAE FSI 304 baseline: {mae_fsi304_baseline:.2f} and in %: {mae_fsi304_baseline_pc:.2f}%')
print(f'MAE FSI 304 original: {mae_fsi304_original:.2f} and in %: {mae_fsi304_original_pc:.2f}%')
print(f'MAE ITI 304: {mae_iti304:.2f} and in %: {mae_iti304_pc:.2f}%')
print(f'CrossCorrelation FSI 304 baseline: {cc_fsi304_baseline[0, 1]:.2f}')
print(f'CrossCorrelation FSI 304 original: {cc_fsi304_original[0, 1]:.2f}')
print(f'CrossCorrelation ITI 304: {cc_iti304[0, 1]:.2f}')

plt.figure(figsize=(20, 10))
plt.plot(df_fsi304_bin_mean_calibrate[:-1][cond], label='FSI 304', c='g')
plt.plot(df_aia304_bin_mean['Intensity'].values[cond], label='SDO AIA 304', c='b')
plt.plot(df_iti_fsi304_bin_mean['Intensity'].values[:-1][cond], label='ITI 304', c='r')
plt.savefig('iti_fsi_aia_304_lc_bin_cc.jpg')


plt.figure(figsize=(20, 10))
#plt.scatter(df_fsi174_fix['date'], df_fsi174_fix['Intensity'], label='Fix irradiance with distance')
plt.scatter(df_fsi174['date'], df_fsi174['Intensity'], label='Original irradiance')
plt.legend()
plt.savefig('fsi_174_fix_irradiance.jpg')



iti171_intensity = []
iti304_intensity = []
for i in tqdm(range(len(iti_fsi_maps))):
    iti171_intensity.append(np.nanmean(iti_fsi_maps[i][0].data))
    iti304_intensity.append(np.nanmean(iti_fsi_maps[i][1].data))

time_fsi = []
for i in range(len(iti_fsi_maps)):
    time_fsi.append(fsi_files_tot[0][i].split('/')[-1].split('T')[0]+ ' ' + fsi_files_tot[0][i].split('/')[-1].split('T')[1][0:8])

iti171 = pd.DataFrame({'date': time_fsi, 'Intensity': iti171_intensity})
iti171['date'] = pd.to_datetime(iti171['date'])
iti304 = pd.DataFrame({'date': time_fsi, 'Intensity': iti304_intensity})
iti304['date'] = pd.to_datetime(iti304['date'])

aia171_intensity = pd.read_csv('/mnt/disks/data/SDO/intensity_aia171_cycle.csv')
aia304_intensity = pd.read_csv('/mnt/disks/data/SDO/intensity_aia304_cycle.csv')
aia171_intensity['Date'] = pd.to_datetime(aia171_intensity['Date'])
aia304_intensity['Date'] = pd.to_datetime(aia304_intensity['Date'])

fig, axs = plt.subplots(1, 1, figsize=(20, 10))
plt.scatter(aia171_intensity['Date'][3200:], aia171_intensity['Intensity'][3200:], label='SDO AIA 171', c='b')
plt.scatter(iti171['date'], iti171['Intensity'], label='ITI 304', c='r')
plt.savefig('ITI_AIA_lc_171_test.jpg')

fig, axs = plt.subplots(1, 1, figsize=(20, 10))
plt.scatter(aia304_intensity['Date'][3200:], aia304_intensity['Intensity'][3200:], label='SDO AIA 304', c='b')
plt.scatter(iti304['date'], iti304['Intensity'], label='ITI 304', c='r')
plt.savefig('ITI_AIA_lc_304_test.jpg')
