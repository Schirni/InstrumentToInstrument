import os
import shutil
import warnings
from abc import ABC, abstractmethod
from random import randint

import numpy as np
import pandas
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.visualization import ImageNormalize, LinearStretch, AsinhStretch, LogStretch
from dateutil.parser import parse
from skimage.transform import pyramid_reduce
from sunpy.coordinates import frames
from sunpy.coordinates.sun import angular_radius
from sunpy.map import Map, all_coordinates_from_map, header_helper


class Editor(ABC):

    def convert(self, data, **kwargs):
        result = self.call(data, **kwargs)
        if isinstance(result, tuple):
            data, add_kwargs = result
            kwargs.update(add_kwargs)
        else:
            data = result
        return data, kwargs

    @abstractmethod
    def call(self, data, **kwargs):
        raise NotImplementedError()


sdo_norms = {94: ImageNormalize(vmin=0, vmax=445.5, stretch=AsinhStretch(0.005), clip=True),
             131: ImageNormalize(vmin=0, vmax=981.3, stretch=AsinhStretch(0.005), clip=True),
             171: ImageNormalize(vmin=0, vmax=6457.5, stretch=AsinhStretch(0.005), clip=True),
             193: ImageNormalize(vmin=0, vmax=7757.31, stretch=AsinhStretch(0.005), clip=True),
             304: ImageNormalize(vmin=0, vmax=3756, stretch=AsinhStretch(0.005), clip=True),
             211: ImageNormalize(vmin=0, vmax=6539.8, stretch=AsinhStretch(0.005), clip=True),
             335: ImageNormalize(vmin=0, vmax=915, stretch=AsinhStretch(0.005), clip=True),
             1600: ImageNormalize(vmin=0, vmax=4000, stretch=AsinhStretch(0.005), clip=True),  # TODO
             1700: ImageNormalize(vmin=0, vmax=4000, stretch=AsinhStretch(0.005), clip=True),  # TODO
             6173: ImageNormalize(vmin=-100, vmax=100, stretch=LinearStretch(), clip=True),
             }

soho_norms = {171: ImageNormalize(vmin=0, vmax=3000, stretch=LogStretch(), clip=True),
              195: ImageNormalize(vmin=0, vmax=3000, stretch=LogStretch(), clip=True),
              284: ImageNormalize(vmin=0, vmax=500, stretch=LogStretch(), clip=True),
              304: ImageNormalize(vmin=0, vmax=2000, stretch=LogStretch(), clip=True),
              6173: ImageNormalize(vmin=-100, vmax=100, stretch=LinearStretch(), clip=True),
              }


class LoadFITSEditor(Editor):

    def call(self, map_path, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings
            dst = shutil.copy(map_path, os.path.join(os.environ.get("TMPDIR"), os.path.basename(map_path)))
            hdul = fits.open(dst)
            os.remove(dst)
            hdul.verify("fix")
            data, header = hdul[0].data, hdul[0].header
            hdul.close()
        return data, {"header": header}


class LoadMapEditor(Editor):

    def call(self, data, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s_map = Map(data)
            return s_map, {'path': data}


class SubMapEditor(Editor):

    def __init__(self, coords):
        self.coords = coords

    def call(self, map, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings
            return map.submap(SkyCoord(*self.coords, frame=map.coordinate_frame))


class MapToDataEditor(Editor):

    def call(self, map, **kwargs):
        return map.data, {"header": map.meta}


class ContrastNormalizeEditor(Editor):

    def __init__(self, use_median=False, threshold=False):
        self.use_median = use_median
        self.threshold = threshold

    def call(self, data, **kwargs):
        shift = np.median(data, (0, 1), keepdims=True) if self.use_median else np.mean(data, (0, 1), keepdims=True)
        data = (data - shift) / (np.std(data, (0, 1), keepdims=True) + 10e-8)
        if self.threshold:
            data[data > self.threshold] = self.threshold
            data[data < -self.threshold] = -self.threshold
            data /= self.threshold
        return data


class ImageNormalizeEditor(Editor):

    def __init__(self, vmin=0, vmax=1000, stretch=LinearStretch()):
        self.norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=stretch, clip=True)

    def call(self, data, **kwargs):
        data = self.norm(data).data * 2 - 1
        return data


class NormalizeEditor(Editor):

    def __init__(self, norm):
        self.norm = norm

    def call(self, data, **kwargs):
        data = self.norm(data).data * 2 - 1
        return data


class ReshapeEditor(Editor):

    def __init__(self, shape):
        self.shape = shape

    def call(self, data, **kwargs):
        data = data[:self.shape[1], :self.shape[2]]
        return np.reshape(data, self.shape)


class NanEditor(Editor):
    def call(self, data, **kwargs):
        data = np.nan_to_num(data)
        return data


class KSOPrepEditor(Editor):
    def __init__(self, add_rotation=False):
        self.add_rotation = add_rotation

        super().__init__()

    def call(self, kso_map, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings
            kso_map.meta["waveunit"] = "ag"
            kso_map.meta["arcs_pp"] = kso_map.scale[0].value

            if self.add_rotation:
                angle = -kso_map.meta["angle"]
            else:
                angle = 0
            c = np.cos(np.deg2rad(angle))
            s = np.sin(np.deg2rad(angle))

            kso_map.meta["PC1_1"] = c
            kso_map.meta["PC1_2"] = -s
            kso_map.meta["PC2_1"] = s
            kso_map.meta["PC2_2"] = c

            return kso_map

class KSOFilmPrepEditor(Editor):
    def __init__(self, add_rotation=False):
        self.add_rotation = add_rotation

        super().__init__()

    def call(self, data, **kwargs):
        data = data[0]
        h = kwargs['header']
        coord = SkyCoord(0 * u.arcsec, 0 * u.arcsec, obstime=parse(h['DATE_OBS']), observer='earth',
                         frame=frames.Helioprojective)
        header = header_helper.make_fitswcs_header(
            data, coord,
            rotation_angle=h["ANGLE"] * u.deg if self.add_rotation else 0 * u.deg,
            reference_pixel=u.Quantity([h['CENTER_X'], h['CENTER_Y']] * u.pixel),
            scale=u.Quantity([h['CDELT1'], h['CDELT2']] * u.arcsec / u.pix),
            instrument=h["INSTRUME"],
            exposure=h["EXPTIME"] * u.ms,
            wavelength=h["WAVELNTH"] * u.angstrom)

        return Map(data, header)


class AIAPrepEditor(Editor):
    def __init__(self):
        super().__init__()
        self.response = pandas.read_csv(os.path.join('/gss/r.jarolim/data', 'aia_response.csv'),
                                        delim_whitespace=True,
                                        parse_dates=[['year', 'month', 'day']])

    def call(self, s_map, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings
            data = self.getCorrectedMapData(s_map)
            return Map(data, s_map.meta)

    def getCorrectedMapData(self, s_map):
        data = s_map.data
        key = 'aia%d' % s_map.wavelength.value
        correction = self.response[key][
            np.argmin(np.abs(self.response.year_month_day - s_map.date.datetime))] if key in self.response else 1
        correction = correction if correction > 0.03 else 0.03
        data = data / correction / s_map.meta["exptime"]
        data = data.astype(np.float32)
        return data


class NormalizeRadiusEditor(Editor):
    def __init__(self, resolution, padding_factor=0.1):
        self.padding_factor = padding_factor
        self.resolution = resolution
        super(NormalizeRadiusEditor, self).__init__()

    def call(self, s_map, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings
            r_obs_pix = s_map.rsun_obs / s_map.scale[0]  # normalize solar radius
            r_obs_pix = (1 + self.padding_factor) * r_obs_pix
            scale_factor = self.resolution / (2 * r_obs_pix.value)
            s_map = s_map.rotate(recenter=True, scale=scale_factor, missing=s_map.min(), order=3)
            arcs_frame = (self.resolution / 2) * s_map.scale[0].value
            s_map = s_map.submap(SkyCoord([-arcs_frame, arcs_frame] * u.arcsec,
                                          [-arcs_frame, arcs_frame] * u.arcsec,
                                          frame=s_map.coordinate_frame))
            s_map.meta['r_sun'] = s_map.rsun_obs.value / s_map.meta['cdelt1']
            return s_map


class PyramidRescaleEditor(Editor):

    def __init__(self, scale=2):
        self.scale = scale

    def call(self, data, **kwargs):
        if self.scale == 1:
            return data
        data = pyramid_reduce(data, downscale=self.scale)
        return data


class LoadNumpyEditor(Editor):

    def call(self, data, **kwargs):
        return np.load(data)


class StackEditor(Editor):

    def __init__(self, data_sets):
        self.data_sets = data_sets

    def call(self, data, **kwargs):
        return np.concatenate([dp[data] for dp in self.data_sets], 0)


class RemoveOffLimbEditor(Editor):

    def __init__(self, fill_value=0):
        self.fill_value = fill_value

    def call(self, s_map, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # ignore warnings
            hpc_coords = all_coordinates_from_map(s_map)
            r = np.sqrt(hpc_coords.Tx ** 2 + hpc_coords.Ty ** 2) / s_map.rsun_obs
            s_map.data[r > 1] = self.fill_value
            return s_map


class RandomPatchEditor(Editor):
    def __init__(self, patch_shape):
        self.patch_shape = patch_shape

    def call(self, data, **kwargs):
        x = randint(0, data.shape[1] - self.patch_shape[0])
        y = randint(0, data.shape[2] - self.patch_shape[1])
        return data[:, x:x + self.patch_shape[0], y:y + self.patch_shape[1]]
