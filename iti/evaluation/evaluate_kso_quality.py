import glob
import os

import numpy as np
import torch
from dateutil.parser import parse
from siqa.data.dataset import AddRadialDistanceEditor
from siqa.model import SIQA
from torch.utils.data import DataLoader
from tqdm import tqdm

from iti.data.dataset import KSOFlatDataset
from iti.train.model import Discriminator

os.environ['CUDA_VISIBLE_DEVICES'] = "0"

from matplotlib import pyplot as plt

# init
base_path = '/gss/r.jarolim/iti/kso_quality_1024_v6'
prediction_path = os.path.join(base_path, 'evaluation')
os.makedirs(prediction_path, exist_ok=True)
# create translator
map_files = list(glob.glob('/gss/r.jarolim/data/kso_general/quality2/*.fts.gz'))
dates = [parse(os.path.basename(f).split('.')[0].replace('_', 'T')) for f in map_files]


dataset = KSOFlatDataset(map_files, 1024, months=[11, 12])
dataset.addEditor(AddRadialDistanceEditor())

# ITI setup
iti_model = torch.load('/gss/r.jarolim/iti/kso_quality_1024_v6/generator_AB.pt')
iti_model.eval()

# SIQA Setup
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
siqa_model = SIQA(input_dim=2, depth=4, dim=32, output_activ='tanh', dim_compression=16)
siqa_model.to(device)
siqa_model.eval()

discriminator = Discriminator(1, 64)
discriminator.to(device)
discriminator.eval()

state = torch.load("/gss/r.jarolim/siqa/siqa_v7/model_state.pt")
start_iteration = state['iteration']
siqa_model.load_state_dict(state['g'])
discriminator.load_state_dict(state['d'])

kso_loss_list = []
iti_loss_list = []
loader = DataLoader(dataset, batch_size=4, shuffle=True, num_workers=8)
with torch.no_grad():
    for i, y in tqdm(enumerate(loader), total=len(loader)):
        y = y.to(device)
        # evaluate KSO
        y_pred, _ = siqa_model(y)
        loss = discriminator.calc_content_loss(y[:, 0:1], y_pred[:, 0:1])
        kso_loss_list.append(loss.detach().cpu().numpy())
        # evaluate ITI
        y_iti = iti_model(y[:, 0:1])
        y_pred, _ = siqa_model(torch.cat([y_iti, y[:, 1:2]], 1))
        loss = discriminator.calc_content_loss(y_iti, y_pred[:, 0:1])
        iti_loss_list.append(loss.detach().cpu().numpy())
        for l, img_iti, img_kso in zip(loss, y_iti, y):
            if l > 0.11:
                fig, ax = plt.subplots(1, 1, figsize=(6, 6))
                ax.imshow(img_kso[0].detach().cpu().numpy(), cmap='gray', vmin=-1, vmax=1)
                ax.set_axis_off()
                fig.tight_layout(0)
                fig.savefig(os.path.join(prediction_path, 'low_kso_%.03f.jpg' % l), dpi=100)
                plt.close(fig)
                fig, ax = plt.subplots(1, 1, figsize=(6, 6))
                ax.imshow(img_iti[0].detach().cpu().numpy(), cmap='gray', vmin=-1, vmax=1)
                ax.set_axis_off()
                fig.tight_layout(0)
                fig.savefig(os.path.join(prediction_path, 'low_iti_%.03f.jpg' % l), dpi=100)
                plt.close(fig)

kso_loss_list = np.concatenate(kso_loss_list)
iti_loss_list = np.concatenate(iti_loss_list)

fig, ax = plt.subplots(1, 1, figsize=(6, 6))
bins = np.linspace(np.min([kso_loss_list, iti_loss_list]), np.max([kso_loss_list, iti_loss_list]), 100)
ax.hist(kso_loss_list, bins=bins, label='KSO', alpha=0.7)
ax.hist(iti_loss_list, bins=bins, label='ITI', alpha=0.7)
ax.set_xlabel('Image Quality Assessment', fontsize=18)
ax.set_ylabel('Number of Observations', fontsize=18)
plt.axvline(0.11, color='red', linestyle='--')
ax.legend(fontsize=18)
fig.tight_layout()
fig.savefig(os.path.join(prediction_path, 'quality_improvement.jpg'), dpi=100)
plt.close(fig)

print('KSO', np.mean(kso_loss_list))
print('ITI', np.mean(iti_loss_list))