import logging
import os
import time

from iti.data.editor import RandomPatchEditor

os.environ['CUDA_VISIBLE_DEVICES'] = "0"

import torch
from torch.utils.data import DataLoader

from iti.data.dataset import KSOFlatDataset, StorageDataset, KSOFilmDataset
from iti.evaluation.callback import PlotBAB, PlotABA, VariationPlotBA, HistoryCallback, ProgressCallback, \
    SaveCallback, NormScheduler
from iti.train.trainer import Trainer, loop

base_dir = "/gss/r.jarolim/prediction/iti/film_v4"
prediction_dir = os.path.join(base_dir, 'prediction')
os.makedirs(prediction_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("{0}/{1}.log".format(base_dir, "info_log")),
        logging.StreamHandler()
    ])

# Init Model
trainer = Trainer(1, 1, norm='in_rs_aff')
trainer.cuda()
trainer.train()
start_it = trainer.resume(base_dir)

# Init Dataset
ccd_dataset = KSOFlatDataset("/gss/r.jarolim/data/kso_general/quality1", 512)
film_dataset = KSOFilmDataset("/gss/r.jarolim/data/filtered_kso_plate", 512)
ccd_storage = StorageDataset(ccd_dataset, '/gss/r.jarolim/data/converted/iti/kso_flat_q1_512', ext_editors=[RandomPatchEditor((256, 256))])
film_storage = StorageDataset(film_dataset, '/gss/r.jarolim/data/converted/iti/kso_film_512', ext_editors=[RandomPatchEditor((256, 256))])

ccd_plot = StorageDataset(ccd_dataset, '/gss/r.jarolim/data/converted/iti/kso_flat_q1_512')
film_plot = StorageDataset(film_dataset, '/gss/r.jarolim/data/converted/iti/kso_film_512')

kso_ccd_iterator = loop(DataLoader(ccd_storage, batch_size=1, shuffle=True, num_workers=8))
kso_film_iterator = loop(DataLoader(film_storage, batch_size=1, shuffle=True, num_workers=8))

# Init Plot Callbacks
history = HistoryCallback(trainer, base_dir)
progress = ProgressCallback(trainer)
save = SaveCallback(trainer, base_dir)
norm_scheduler = NormScheduler(trainer)

plot_settings_A = {"cmap": "gray", "title": "Quality 2", 'vmin': -1, 'vmax': 1}
plot_settings_B = {"cmap": "gray", "title": "Quality 1", 'vmin': -1, 'vmax': 1}

log_iteration = 1000
bab_callback = PlotBAB(ccd_plot.sample(3), trainer, prediction_dir, log_iteration=log_iteration,
                       plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B)
bab_callback.call(0)

aba_callback = PlotABA(film_plot.sample(3), trainer, prediction_dir, log_iteration=log_iteration,
                       plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B)
aba_callback.call(0)

cutout_callback = PlotABA(film_storage.sample(6), trainer, prediction_dir, log_iteration=log_iteration,
                       plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B, plot_id='CUTOUT')
cutout_callback.call(0)

v_callback = VariationPlotBA(ccd_plot.sample(3), trainer, prediction_dir, 4, log_iteration=log_iteration,
                             plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B)

callbacks = [history, progress, save, bab_callback, aba_callback,cutout_callback, v_callback, norm_scheduler]

# Start training
for it in range(start_it, int(1e8)):
    x_a, x_b = next(kso_film_iterator), next(kso_ccd_iterator)
    x_a, x_b = x_a.float().cuda().detach(), x_b.float().cuda().detach()
    #
    trainer.discriminator_update(x_a, x_b)
    trainer.generator_update(x_a, x_b)
    torch.cuda.synchronize()
    #
    for callback in callbacks:
        callback(it)
