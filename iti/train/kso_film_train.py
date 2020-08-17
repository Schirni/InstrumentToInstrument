import logging
import os
import time

os.environ['CUDA_VISIBLE_DEVICES'] = "0"

import torch
from torch.utils.data import DataLoader

from iti.data.dataset import KSODataset, StorageDataset, KSOFilmDataset
from iti.evaluation.callback import PlotBAB, PlotABA, VariationPlotBA, HistoryCallback, ProgressCallback, \
    SaveCallback, LRScheduler
from iti.train.trainer import Trainer, loop

base_dir = "/gss/r.jarolim/prediction/iti/film_v1"
prediction_dir = os.path.join(base_dir, 'prediction')
os.makedirs(prediction_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("{0}/{1}.log".format(base_dir, "info_log")),
        logging.StreamHandler()
    ])

# Init Model
trainer = Trainer(1, 1)
trainer.cuda()
start_it = trainer.resume(base_dir)

# Init Dataset
kso_ccd_dataset = StorageDataset(KSODataset("/gss/r.jarolim/data/kso_general/quality1", 256), '/gss/r.jarolim/data/converted/iti/kso_q1_256_v2')
kso_film_dataset = StorageDataset(KSOFilmDataset("/gss/r.jarolim/data/filtered_kso_plate", 256), '/gss/r.jarolim/data/converted/iti/kso_film_256')

kso_ccd_iterator = loop(DataLoader(kso_ccd_dataset, batch_size=1, shuffle=True, num_workers=8))
kso_film_iterator = loop(DataLoader(kso_film_dataset, batch_size=1, shuffle=True, num_workers=8))

# Init Plot Callbacks
history = HistoryCallback(trainer, base_dir)
progress = ProgressCallback(trainer)
save = SaveCallback(trainer, base_dir)

plot_settings_A = {"cmap": "gray", "title": "Quality 2", 'vmin': -1, 'vmax': 1}
plot_settings_B = {"cmap": "gray", "title": "Quality 1", 'vmin': -1, 'vmax': 1}

log_iteration = 1000
bab_callback = PlotBAB(kso_ccd_dataset.sample(8), trainer, prediction_dir, log_iteration=log_iteration,
                       plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B)
bab_callback.call(0)

aba_callback = PlotABA(kso_film_dataset.sample(8), trainer, prediction_dir, log_iteration=log_iteration,
                       plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B)
aba_callback.call(0)

v_callback = VariationPlotBA(kso_ccd_dataset.sample(8), trainer, prediction_dir, 4, log_iteration=log_iteration,
                             plot_settings_A=plot_settings_A, plot_settings_B=plot_settings_B)

lr_scheduler = LRScheduler(trainer, 30000)

callbacks = [history, progress, save, bab_callback, aba_callback, v_callback, lr_scheduler]

# Init generator stack
trainer.fill_stack([(next(kso_film_iterator).float().cuda().detach(),
                     next(kso_ccd_iterator).float().cuda().detach()) for _ in range(50)])
# Start training
for it in range(start_it, int(1e8)):
    x_a, x_b = next(kso_film_iterator), next(kso_ccd_iterator)
    x_a, x_b = x_a.float().cuda().detach(), x_b.float().cuda().detach()
    end = time.time()
    #
    trainer.discriminator_update(x_a, x_b)
    trainer.generator_update(x_a, x_b)
    torch.cuda.synchronize()
    #
    for callback in callbacks:
        callback(it)