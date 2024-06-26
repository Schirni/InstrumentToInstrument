import argparse
import logging
import os

from sunpy.visualization.colormaps import cm

from iti.data.dataset import SDODataset, StorageDataset, STEREODataset
from iti.data.editor import RandomPatchEditor, SliceEditor, BrightestPixelPatchEditor
from iti.train.model import DiscriminatorMode
from iti.trainer import Trainer

parser = argparse.ArgumentParser(description='Train STEREO-To-SDO translations')
parser.add_argument('--base_dir', type=str, help='path to the results directory.')

parser.add_argument('--sdo_path', type=str, help='path to the SDO data.')
parser.add_argument('--stereo_path', type=str, help='path to the STEREO data.')
parser.add_argument('--sdo_converted_path', type=str, help='path to store the converted SDO data.')
parser.add_argument('--stereo_converted_path', type=str, help='path to store the converted STEREO data.')

args = parser.parse_args()
base_dir = args.base_dir

stereo_path = args.stereo_path
stereo_converted_path = args.stereo_converted_path
sdo_path = args.sdo_path
sdo_converted_path = args.sdo_converted_path

prediction_dir = os.path.join(base_dir, 'prediction')
os.makedirs(prediction_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("{0}/{1}.log".format(base_dir, "info_log")),
        logging.StreamHandler()
    ])

# Init Model
trainer = Trainer(4, 4, upsampling=2, discriminator_mode=DiscriminatorMode.CHANNELS, lambda_diversity=0,
                  norm='in_rs_aff', use_batch_statistic=False)
trainer.cuda()

# Init Dataset
test_months = [11, 12]
train_months = list(range(2, 10))

sdo_dataset = SDODataset(sdo_path, resolution=4096, patch_shape=(1024, 1024), months=train_months)
sdo_dataset = StorageDataset(sdo_dataset,
                             sdo_converted_path,
                             ext_editors=[SliceEditor(0, -1),
                                          RandomPatchEditor((512, 512))])

stereo_dataset = StorageDataset(STEREODataset(stereo_path, months=train_months), stereo_converted_path,
                                ext_editors=[BrightestPixelPatchEditor((256, 256)), RandomPatchEditor((128, 128))])

sdo_valid = StorageDataset(SDODataset(sdo_path, resolution=4096, patch_shape=(1024, 1024), months=test_months),
                           sdo_converted_path, ext_editors=[RandomPatchEditor((512, 512)), SliceEditor(0, -1)])
stereo_valid = StorageDataset(STEREODataset(stereo_path, patch_shape=(1024, 1024), months=test_months),
                              stereo_converted_path, ext_editors=[RandomPatchEditor((128, 128))])

plot_settings_A = [
    {"cmap": cm.sdoaia171, "title": "SECCHI 171", 'vmin': -1, 'vmax': 1},
    {"cmap": cm.sdoaia193, "title": "SECCHI 195", 'vmin': -1, 'vmax': 1},
    {"cmap": cm.sdoaia211, "title": "SECCHI 284", 'vmin': -1, 'vmax': 1},
    {"cmap": cm.sdoaia304, "title": "SECCHI 304", 'vmin': -1, 'vmax': 1},
]
plot_settings_B = [
    {"cmap": cm.sdoaia171, "title": "AIA 171", 'vmin': -1, 'vmax': 1},
    {"cmap": cm.sdoaia193, "title": "AIA 193", 'vmin': -1, 'vmax': 1},
    {"cmap": cm.sdoaia211, "title": "AIA 211", 'vmin': -1, 'vmax': 1},
    {"cmap": cm.sdoaia304, "title": "AIA 304", 'vmin': -1, 'vmax': 1},
]

# Start training
trainer.startBasicTraining(base_dir, stereo_dataset, sdo_dataset, stereo_valid, sdo_valid,
                           plot_settings_A, plot_settings_B)
