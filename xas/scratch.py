import numpy as np

path = os.path.dirname(path_to_binned)
tiff_storage_path = os.path.join(path, 'tiff_storage')
filename = os.path.basename(path_to_binned)
rixs_processing_file=  os.path.join( tiff_storage_path, filename)
#cloud_dispatcher.load_to_dropbox(path_to_binned)

name = filename.split('.')[0]

tiff_directory = os.path.join( tiff_storage_path, name)
zip_file =
os.system(f"zip eli.zip '{tiff_directory}/*.tif'")


from xas.file_io import load_extended_data_from_file
from PIL import Image

year = '2022'
cycle = '2'
proposal = '309855'
cloud_dispatcher = xlive_gui.cloud_dispatcher

for uid in range(265677, 265858+1):
     hdr = db[uid]
     if 'spectrometer' in hdr.start.keys():
         path_to_file = hdr.start['interp_filename']
         path, f_ext = os.path.split(hdr.start['interp_filename'])
         f, _ = os.path.splitext(f_ext)

         tiff_storage_path = os.path.join(os.path.dirname(path_to_file), 'tiff_storage') + '/'
         scan_name, _ = os.path.splitext(os.path.basename(path_to_file))
         dat_file_fpath = tiff_storage_path + scan_name + '.dat'
         tiff_images_path = tiff_storage_path + scan_name + '/'
         extended_data = load_extended_data_from_file(os.path.join(os.path.dirname(path_to_file), 'extended_data', f + '.h5'))
         if extended_data is not None:
             filepath_list = []
             filename_list = []

             for i, im in enumerate(extended_data['pil100k_image']):
                 image_data = Image.fromarray(im)
                 #
                 tiff_filename = '{}{:04d}{}'.format('image', i + 1, '.tif')
                 tiff_path = tiff_images_path + tiff_filename
                 print(f'TIFF STORAGE: tiff will be saved in {tiff_path}')
                 image_data.save(tiff_path)
                 filepath_list.append(tiff_path)
                 filename_list.append(tiff_filename)

             if zip:
                 # os.system(f"cd '{tiff_images_path}'")
                 zip_file = os.path.splitext(dat_file_fpath)[0] + '-1.zip'
                 # os.system(f"zip '{zip_file}' ./*.tif")
                 if os.path.exists(zip_file):
                     os.remove(zip_file)
                 os.system(f"cd '{tiff_images_path}'; zip '{zip_file}' ./*.tif")
                 filepath_list = [zip_file]

                 for f in filepath_list:
                     cloud_dispatcher.load_to_dropbox(f, year=year, cycle=cycle, proposal=proposal)
                     # logger.info(f'({ttime.ctime()}) Sending data to the cloud successful for {path_to_file}')


             # print(os.path.join(path, 'tiff_storage', f))
             # ext_data = load_extended_data_from_file

###########################
# Yet another attempt at combining the rixs planes

x = xview_gui.widget_data
from xas.file_io import load_binned_df_from_file
rixs_dict = {}


for item in x.list_data.selectedItems():
    fname = os.path.join(x.working_folder, item.text())
    df, header = load_binned_df_from_file(fname)
    print(fname, df.shape)
    uid_idx1 = header.find('Scan.uid:') + 10
    uid_idx2 = header.find('\n', header.find('Scan.uid:'))
    uid = header[uid_idx1: uid_idx2]
    md = db[uid]['start']
    emission_energy = round(md['spectrometer_energy'], 2)
    if emission_energy not in rixs_dict.keys():
        rixs_dict[emission_energy] = [{'energy': df.energy, 'mu' : -df.pil100k_roi1 / df.i0}]
    else:
        rixs_dict[emission_energy].append({'energy': df.energy, 'mu' : -df.pil100k_roi1 / df.i0})

uids = []
for item in x.list_data.selectedItems():
    fname = os.path.join(x.working_folder, item.text())
    df, header = load_binned_df_from_file(fname)
    print(fname, df.shape)
    uid_idx1 = header.find('Scan.uid:') + 10
    uid_idx2 = header.find('\n', header.find('Scan.uid:'))
    uid = header[uid_idx1: uid_idx2]
    uids.append(uid)



some_emission_energy = list(rixs_dict.keys())[0]
energy_in = rixs_dict[some_emission_energy][0]['energy'].values
energy_out = np.sort(list(rixs_dict.keys()))
rixs_data = np.zeros((energy_in.size, energy_out.size))

for i, each_energy_out in enumerate(energy_out):
    each_mu_set = []
    for ds in rixs_dict[each_energy_out]:

        each_mu_set.append(np.interp(energy_in, ds['energy'], ds['mu']))
    rixs_data[:, i] = np.mean(np.array(each_mu_set), axis=0)


ds_norm = xview_gui.project[0]
ds_norm_ka2 = xview_gui.project[11]

xes_norm = np.hstack((ds_norm_ka2.mu[:-2] / np.mean(ds_norm_ka2.mu[-2:]) * np.mean(ds_norm.mu[:2]), ds_norm.mu))

# plt.figure()
# plt.plot(ds_norm_ka2.energy[-2:], ds_norm_ka2.mu[-2:])
# plt.plot(ds_norm.energy[:2], ds_norm.mu[:2])
#
# plt.plot(ds_norm_ka2.energy, ds_norm_ka2.mu / np.mean(ds_norm_ka2.mu[-2:]) * np.mean(ds_norm.mu[:2]))
# plt.plot(ds_norm.energy, ds_norm.mu)

# xes_norm = ds_norm.mu
xes_norm /= xes_norm.max()
rixs_norm = np.mean(rixs_data[energy_in > 8350, :], axis=0)

# xes_8347 = xview_gui.project[1].mu

rixs_data_norm = rixs_data / rixs_norm[None, :] * xes_norm[None, :]
rixs_data_norm /= rixs_data_norm.max()

from xas.spectrometer import convert_rixs_to_energy_transfer

energy_et, rixs_et = convert_rixs_to_energy_transfer(energy_in, energy_out, rixs_data_norm.T)

##
plt.figure(1, clear=True)
plt.plot(energy_in, rixs_data_norm[:, 22]/0.823*1.2, label='RIXS')
plt.plot(herfd_data_energy, herfd_data_ni4, label='HERFD')
plt.legend()
plt.xlim(8325, 8355)

##

plt.figure(1, clear=True)
# plt.contourf(energy_in, energy_out, rixs_data_norm.T, 150, vmin=0, vmax=0.3)
plt.contourf(energy_in, energy_out, np.log10(rixs_data_norm.T), 250, vmin=np.log10(1e-3), vmax=np.log10(1))


plt.figure(2, clear=True)
# plt.contourf(energy_in, energy_out, rixs_data_norm.T, 150, vmin=0, vmax=0.3)
plt.contourf(energy_in, energy_et, np.log10(rixs_et.T), 250, vmin=np.log10(1e-3), vmax=np.log10(1))
# plt.contourf(energy_in, energy_et, rixs_et.T, 250, vmin=0, vmax=0.5)

plt.axis('square')

plt.figure(3, clear=True)
# plt.imshow(np.log10(rixs_et.T), vmin=np.log10(3e-3), vmax=np.log10(1))
plt.plot(energy_et, np.mean(rixs_et[48:52, :], axis=0))
plt.plot(energy_et, np.mean(rixs_et[62:66, :], axis=0))
plt.plot(energy_et, np.mean(rixs_et[78:82, :], axis=0))

plt.figure(4, clear=True)
# plt.plot(energy_out, xes_8347 / xes_8347.max())
plt.plot(energy_out, rixs_data_norm[115, :] / rixs_data_norm[115, :].max())

def save_data_to_files(energy_in, energy_out, rixs_norm, energy_herfd, mu_herfd, filename):
    rixs_matrix = np.block([[0, energy_out[None, :]], [energy_in[:, None], rixs_norm]])
    herfd_matrix = np.vstack((energy_herfd, mu_herfd)).T
    rixs_filename = os.path.join(x.working_folder, f'{filename}_rixs.dat')
    herfd_filename = os.path.join(x.working_folder, f'{filename}_herfd.dat')
    np.savetxt(rixs_filename, rixs_matrix, delimiter='\t')
    np.savetxt(herfd_filename, herfd_matrix, delimiter='\t', header='# energy (eV)\tmu (a.u.)')
    xview_gui.cloud_dispatcher.load_to_dropbox(rixs_filename, year='2022', cycle='2', proposal='310156')
    xview_gui.cloud_dispatcher.load_to_dropbox(herfd_filename, year='2022', cycle='2', proposal='310156')

save_data_to_files(energy_in, energy_out, rixs_data_norm, xview_gui.project[3].energy, xview_gui.project[3].mu, 'DW_NiIII')



herfd_data_energy = xview_gui.project[2].energy
herfd_data_ni4 = xview_gui.project[2].flat
herfd_data_ni3 = xview_gui.project[3].flat
herfd_preedge_ni4 = xview_gui.project[2].pre_edge
herfd_preedge_ni3 = xview_gui.project[3].pre_edge
herfd_postedge_ni4 = xview_gui.project[2].post_edge
herfd_postedge_ni3 = xview_gui.project[3].post_edge

n_out = 22
n_in = 48

# basis_ni4 = np.vstack((rixs_data_norm_ni4[:, n_out], np.ones(energy_in.size))).T
# basis_ni3 = np.vstack((rixs_data_norm_ni3[:, n_out], np.ones(energy_in.size))).T

rixs_data_norm_ni4_bkg_rem = rixs_data_norm_ni4 - np.mean(rixs_data_norm_ni4[energy_in<8325, :], axis=0)[None, :]
rixs_data_norm_ni3_bkg_rem = rixs_data_norm_ni3 - np.mean(rixs_data_norm_ni3[energy_in<8325, :], axis=0)[None, :]

rixs_data_norm_ni4_bkg_rem /= np.interp(energy_in, herfd_data_energy, herfd_postedge_ni4)[:, None]
rixs_data_norm_ni3_bkg_rem /= np.interp(energy_in, herfd_data_energy, herfd_postedge_ni3)[:, None]

scale_ni4, _, _, _ = np.linalg.lstsq(rixs_data_norm_ni4_bkg_rem[:, n_out][:, None],
                                     np.interp(energy_in, herfd_data_energy, herfd_data_ni4), rcond=-1)
scale_ni3, _, _, _ = np.linalg.lstsq(rixs_data_norm_ni3_bkg_rem[:, n_out][:, None],
                                     np.interp(energy_in, herfd_data_energy, herfd_data_ni3), rcond=-1)

rixs_data_norm_scaled_ni4 = rixs_data_norm_ni4_bkg_rem * scale_ni4
rixs_data_norm_scaled_ni3 = rixs_data_norm_ni3_bkg_rem * scale_ni3


plt.figure(5, clear=True)
plt.subplot(221)
plt.contourf(energy_in, energy_out, np.log10(rixs_data_norm_scaled_ni4.T + 1e-3), 250, vmin=np.log10(1e-3), vmax=np.log10(1))
# plt.contourf(energy_in, energy_out, rixs_data_norm_scaled_ni4.T, 250, vmin=0, vmax=1.05, cmap='cubehelix')
plt.title('Ni 4+')
plt.hlines([energy_out[n_out]], energy_in.min(), energy_in.max(), color='w')
plt.vlines([energy_in[n_in]], energy_out.min(), energy_out.max(), color='r')

plt.subplot(222)
plt.contourf(energy_in, energy_out, np.log10(rixs_data_norm_scaled_ni3.T + 1e-3), 250, vmin=np.log10(1e-3), vmax=np.log10(1))
plt.title('Ni 3+')
plt.hlines([energy_out[n_out]], energy_in.min(), energy_in.max(), color='w')
plt.vlines([energy_in[n_in]], energy_out.min(), energy_out.max(), color='r')

plt.subplot(223)
plt.plot(energy_in, rixs_data_norm_scaled_ni4[:, n_out], label='Ni 4+')
plt.plot(herfd_data_energy, herfd_data_ni4, label='Ni 4+ HERFD')

plt.plot(energy_in, rixs_data_norm_scaled_ni3[:, n_out], label='Ni 3+')
plt.plot(herfd_data_energy, herfd_data_ni3, label='Ni 3+ HERFD')
plt.legend()

plt.xlim(8330, 8360)

plt.subplot(224)
plt.plot(energy_out, rixs_data_norm_ni4[n_in, :] * scale_ni4, label='Ni 4+')
plt.plot(energy_out, rixs_data_norm_ni3[n_in, :] * scale_ni3, label='Ni 3+')
plt.legend()


__basis = np.vstack((rixs_data_norm_scaled_ni3[:, n_out],
                     np.interp(energy_in, herfd_data_energy, herfd_data_ni4))).T
__c, _, _, _ = np.linalg.lstsq(__basis, rixs_data_norm_scaled_ni4[:, n_out], rcond=-1)

plt.figure(6, clear=True)

plt.plot(energy_in, rixs_data_norm_scaled_ni4[:, n_out], label='Ni 4+')
plt.plot(energy_in, __basis @ __c, 'r:', label='Ni 4+ fit')

plt.plot(energy_in, rixs_data_norm_scaled_ni3[:, n_out], label='Ni 3+')
plt.plot(herfd_data_energy, herfd_data_ni4, label='Ni 4+ HERFD')


# __alpha = 0.35
# plt.plot(energy_in, (rixs_data_norm_scaled_ni4[:, n_out] - __alpha * rixs_data_norm_scaled_ni3[:, n_out]) / (1 - __alpha), 'r:', label='Ni 4+ recovered')
# plt.plot(herfd_data_energy, herfd_data_ni3, label='Ni 3+ HERFD')
plt.legend()

plt.xlim(8330, 8360)


###################

x = np.arange(0, 1292)
y = np.arange(0, 1292)

_cc = []
for _x, _y in zip(x, y):
    __cc = camera_sp1.calibration.C_dmotdpix(np.array((_x, _y)))
    _cc.append(__cc)

cc = np.array(_cc)

plt.figure(1, clear=True)
plt.plot(cc[:, 0, 0])
plt.plot(cc[:, 1, 0])
plt.plot(cc[:, 0, 1])
plt.plot(cc[:, 1, 1])

########
import copy
from xas.analysis import check_scan
from xas.process import get_processed_df_from_uid
from xas.outliers import outlier_rejection

def get_processed_df_from_uid_advanced(uid, db):
    hdr, df, _, _, _, _, _ = get_processed_df_from_uid(uid, db, save_interpolated_file=False)
    metadata = copy.deepcopy({**hdr.start})


    metadata['mu_good'] = check_scan(df, metadata)
    df['mut'] = -np.log(df["it"] / df["i0"])
    df['mur'] = -np.log(df["ir"] / df["it"])
    df['muf'] = df["iff"] / df["i0"]


    return df, metadata

# pick a sample_uid from scan with uid='5a4ba893-7336-4f9f-b1c6-cf35f3ae9854':
sample_uid = '369ea231-6fbf-4847-a'
uids = list(db.v2.search({'sample_uid': sample_uid}))

dfs, metadatas = [], []

for uid in uids:
    _df, _metadata = get_processed_df_from_uid_advanced(uid, db)
    dfs.append(_df)
    metadatas.append(_metadata)

df_mean, metadata_mean = outlier_rejection(dfs, uids, plot_diagnostics=True)

# ch = 'mut'
# method = 'trimmed_lof'
# for df, uid in zip(dfs, uids):
#     if uid in metadata_mean[ch][method]['inliers']:
#         plt.plot(df['energy'], df[ch], 'k-')
#     else:
#         plt.plot(df['energy'], df[ch], 'b-')
# plt.plot(df_mean['energy'], df_mean[ch][method], 'r-', lw=3)


uid = 'ac830c3a-f227-44c9-ab30-5bf43978e054'
e_nom, e_act, energy_ref_roi, mu_ref_roi, mu_fit = get_energy_offset(uid, db, db_proc, full_return=True)

df, metadata = get_processed_df_from_uid_advanced(uid, db)
plt.figure(2, clear=True)
plt.plot(energy_ref_roi, mu_ref_roi)

plt.plot(energy_ref_roi, mu_fit)

###########
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.use("TkAgg")
from scipy.interpolate import CubicSpline
from xas.file_io import load_binned_df_from_file
from xas.energy_calibration import compute_energy_shift_and_broadening_between_spectra, fine_convolution_grid
path = '/home/charles/Desktop/test_data/bender_scans'
files = \
[
'Bender scan at Pd-K edge - -264 N - 155.61 um.dat',
'Bender scan at Pd-K edge - -289 N - 150.52 um.dat',
'Bender scan at Pd-K edge - -314 N - 145.58 um.dat',
'Bender scan at Pd-K edge - -338 N - 140.62 um.dat',
'Bender scan at Pd-K edge - -363 N - 135.6 um.dat',
'Bender scan at Pd-K edge - -387 N - 130.6 um.dat',
'Bender scan at Pd-K edge - -413 N - 125.67 um.dat'
]

# energy_ref, mu_ref = db_proc.foil_spectrum('Pd', 'K')
df_ref, _ = load_binned_df_from_file(path + '/' + 'Pd K-edge foil energy calibration.dat')
energy_ref = df_ref["energy"]
mu_ref = -np.log(df_ref["ir"] / df_ref["it"])

dfs = []
for f in files:
    _df, _ = load_binned_df_from_file(path + '/' + f)
    _df['mur'] = -np.log(_df['ir'] / _df['it'])
    dfs.append(_df)

# df = dfs[0]
# energy, mu = df["energy"], df["mur"]
# e0 = 24350
# de = 200

# cs = CubicSpline(energy_ref, mu_ref)

# roi_mask = (energy > (e0 - de / 2)) & (energy < (e0 + de / 2))
# energy_roi = energy[roi_mask]
# mu_roi = mu[roi_mask]

# fine_grid_energy_ref = fine_convolution_grid(energy_ref, sigma=0.01)
# fine_grid_mu_ref = cs(fine_grid_energy_ref)

plt.figure(1, clear=True)
for i, df in enumerate(dfs):
    shift, sigma, energy_fit, mu_fit = compute_energy_shift_and_broadening_between_spectra(df['energy'].values, df['mur'].values,
                                                                                           energy_ref - 14.85, mu_ref, e0=24350, de=200)
    print(i, shift, sigma)
    plt.plot(df['energy'].values, df['mur'].values - i, 'k-')
    plt.plot(energy_fit, mu_fit - i, 'r-')

plt.plot(energy_ref, mu_ref * 1.5 + 1, 'k-', lw=1)


##############

# RUN THIS IN NON-TILED ENVIRONMENT
from xas.process import get_processed_df_from_uid
import json
outpath = '/nsls2/data/iss/legacy/Sandbox/database/databroker_output'

def save_xas_data_as_json(uid, db, db_tag='new'):
    hdr = db[uid]
    if 'experiment' in hdr.start.keys():

        hdr, primary_df, _, _, _, _, _ = get_processed_df_from_uid(uid, db, save_interpolated_file=False)
        true_uid = hdr.start.uid
        _start = {**hdr.start}
        _stop = {'time_stop' : hdr.stop.time,
                 'exit_status' : hdr.stop.exit_status}
        metadata ={**_start, **_stop, 'db_tag': db_tag}
        output = {'metadata': metadata, 'data': primary_df.to_dict()}
        print(true_uid)
        fpath = os.path.join(outpath, true_uid)

        with open(fpath, 'w') as f:
            json.dump(output, f)

n1 = 317987
n2 = 321288
for i in range(n1+100, n1 + 300):
    save_xas_data_as_json(i, db, db_tag='new')


##############
# RUN THIS IN TILED ENVIRONMENT
import pandas as pd
import json
import os
from tiled.client import from_profile
outpath = '/nsls2/data/iss/legacy/Sandbox/database/databroker_output'

c_nsls2 = from_profile('nsls2', username='MYUSERNAME')
c = c_nsls2['iss']['sandbox']

def read_xas_data_from_json(fpath):
    with open(fpath, 'r') as f:
        data = json.loads(f.read())
    return data['metadata'], pd.DataFrame(data['data'])

files = [f for f in os.listdir(outpath)]
## _to_do: add muf/mut/mur to the df calculation; also check if mut mur muf are actually good names for the columns
for f in files:

    md, df = read_xas_data_from_json(os.path.join(outpath, f))
    md['mu_quality'] = check_scan(df, md)
    print(f, md['mu_quality'])

    md['tag'] = 'test'
    md['tag_version'] = '0.0'
    md['tag_comment'] = 'test quality check'
    x = c.write_dataframe(df, md)

###############
import xarray as xr
from tiled.client import from_profile
c_nsls2 = from_profile('nsls2', username='username')
c = c_nsls2['iss']['raw']
run = c[-1]
t = run['apb_stream']['data']['apb_stream'].read().squeeze()
data = np.array([list(i) for i in t])
channels = ['i0', 'itrans', 'iref', 'ifluo', 'aux1', 'aux2', 'aux3', 'aux4']
arr = xr.DataArray(data[:, 1:], coords=[data[:, 0], channels], dims=['time', 'channel'])

#####################
from xas.file_io import load_binned_df_from_file

# foil
files = [
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0003 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0004 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0006 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0007 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0008 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0009 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0010 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0011 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0012 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0001-r0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0001-r0003 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0002-r0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil Mn-K XES EXAFS 0003-r0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0003 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0004 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0005 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0006 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0007 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/foil 2 Mn-K XES EXAFS 0008 vh_roi1.dat',
    ]

# LVMO
files = [
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 047) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 046) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 045) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 044) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 043) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 042) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 041) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 040) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 039) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 038) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 037) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 036) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 035) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 034) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 033) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 032) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 031) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 030) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 029) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 028) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 027) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 026) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 025) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 024) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 023) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 022) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 021) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 020) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 019) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 018) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 017) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 016) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 015) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 014) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 013) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 012) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 011) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 010) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 009) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 008) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 007) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 006) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 005) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 004) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 003) Mn-K XES EXAFS 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2023/1/310956/LVMO (pos 002) Mn-K XES EXAFS 0001 vh_roi1.dat',

]

# LMO

files = [
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 412) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 411) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 410) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 409) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 408) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 407) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 406) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 405) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 404) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 403) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 402) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 400) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 399) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 398) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 397) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 396) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 395) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 394) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 393) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 392) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 391) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 390) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 389) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 388) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 387) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 386) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 385) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 384) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 383) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 382) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 381) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 380) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 379) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 378) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 377) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 376) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 375) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 374) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 373) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 372) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 371) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 370) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 369) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 368) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 367) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 366) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 365) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 364) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 363) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 362) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 361) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 360) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 359) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 358) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 357) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 356) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 355) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 354) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 353) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 352) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 351) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 350) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 349) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 348) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 347) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 346) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 345) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 344) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 343) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 342) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 341) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 340) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 339) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 338) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 337) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 336) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 335) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 334) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 333) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 332) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 331) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 330) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 329) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 328) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 327) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 326) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 324) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 323) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 322) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 321) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 320) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 319) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 318) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 317) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 316) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 315) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 314) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 313) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 312) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 311) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 310) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 309) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 308) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 307) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 306) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 305) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 304) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 303) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 302) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 300) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 299) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 298) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 297) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 296) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 295) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 294) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 293) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 292) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 291) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 290) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 289) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 288) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 287) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 286) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 285) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 284) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 283) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 282) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 281) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 280) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 279) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 278) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 277) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 276) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 275) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 274) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 273) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 272) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 271) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 270) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 269) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 268) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 267) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 266) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 265) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 264) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 263) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 262) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 261) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 260) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 259) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 258) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 257) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 256) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 254) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 253) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 252) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 251) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 250) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 249) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 248) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 247) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 246) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 245) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 244) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 243) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 242) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 241) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 240) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 239) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 238) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 237) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 236) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 235) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 234) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 233) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 232) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 231) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 230) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 229) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 228) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 227) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 226) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 225) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 224) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 223) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 222) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 221) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 220) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 219) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 218) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 217) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 216) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 214) Mn-K XES EXAFS 0001-r0002 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 213) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 212) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 211) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 210) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 209) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 208) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 207) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 206) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 205) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 204) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 203) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 202) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 200) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 199) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 198) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 197) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 196) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 195) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 194) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 193) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 192) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 191) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 189) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 188) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 187) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 186) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 185) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 184) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 183) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 182) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 181) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 180) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 179) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 178) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 177) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 176) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 175) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 174) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 173) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 172) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 171) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 170) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 169) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 168) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 167) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 166) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 165) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 164) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 163) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 162) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 161) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 160) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 159) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 158) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 157) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 156) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 155) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 154) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 153) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 152) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 151) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 150) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 149) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 148) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 147) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 146) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 145) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 144) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 143) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 142) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 141) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 140) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 139) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 138) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 137) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 135) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 134) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 133) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 132) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 131) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 130) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 129) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 128) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 127) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 126) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 125) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 124) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 123) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 122) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 121) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 120) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 119) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 118) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 117) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 116) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 115) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 114) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 113) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 112) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 111) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 110) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 109) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 108) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 107) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 106) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 105) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 104) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 103) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 102) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 101) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 100) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 099) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 098) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 097) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 096) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 095) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 094) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 093) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 092) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 091) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 090) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 089) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 088) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 087) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 086) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 085) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 084) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 083) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 082) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 081) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 080) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 079) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 078) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 077) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 076) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 075) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 074) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 073) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 072) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 071) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 070) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 069) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 068) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 067) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 066) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 065) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 064) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 063) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 062) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 061) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 060) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 059) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 058) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 057) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 056) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 055) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 054) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 053) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 052) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 051) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 050) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 049) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 048) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 047) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 046) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 045) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 044) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 043) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 042) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 041) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 040) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 039) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 038) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 037) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 036) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 035) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 034) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 033) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 032) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 031) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 030) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 029) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 028) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 027) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 026) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 025) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 024) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 023) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 022) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 021) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 020) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 019) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 018) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 017) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 016) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 015) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 014) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 013) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 012) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 011) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 010) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 009) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 008) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 007) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 006) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 005) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 004) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 003) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 002) Mn-K XES EXAFS 0001 vh_roi1.dat',
 '/nsls2/data/iss/legacy/processed/2023/1/310956/LMO (pos 001) Mn-K XES EXAFS 0001 vh_roi1.dat'
]


rixs = []
for f in files:
    print(f)
    df, _ = load_binned_df_from_file(f)
    # print(energy_in.size)
    bla = df.columns.tolist()
    _rixs = -df[bla[1::2]].values / df[bla[2::2]].values
    if _rixs.shape[1] == 504:
        rixs.append(_rixs)

energy_out = df['energy'].values
energy_in = np.array([float('.'.join(i.split('_')[2:4])) for i in bla[1::2]])
rixs = np.array(rixs) / 1e6

rixs_av = np.mean(rixs, axis=0)

plt.figure(1, clear=True)
plt.contourf(energy_out, energy_in, rixs_av.T, 50)

n_out = [230, 245]
plt.vlines(energy_out[n_out], energy_in.min(), energy_in.max(), colors='r')


herfds = rixs_av[n_out, :].T
herfds -= np.mean(herfds[20:60, :], axis=0)[None, :]
herfds /= np.mean(herfds[400:, :], axis=0)[None, :]

plt.figure(2, clear=True)
plt.plot(energy_in, herfds)


e_in_min = 6570
e_out_min = 6472.5
e_out_max = 6494.5

e_out_glitch_mask = (energy_out <= 6477.25) | (energy_out >= 6477.75)

e_in_mask = energy_in >= e_in_min
e_out_mask = (energy_out >= e_out_min) & (energy_out <= e_out_max) & e_out_glitch_mask

rixs_av_roi = rixs_av[np.ix_(e_out_mask, e_in_mask)]
uu, ss, vvT = np.linalg.svd(rixs_av_roi)
vv = vvT.T


plt.figure(3, clear=True)
plt.subplot(221)
plt.contourf(energy_out[e_out_mask], energy_in[e_in_mask], rixs_av_roi.T, 50, vmin=rixs_av_roi.min(), vmax=rixs_av_roi.max()*0.5)

i_cmp = [0, 1, 2]

plt.subplot(222)
plt.semilogy(ss, 'ks-')

plt.subplot(223)
plt.plot(energy_out[e_out_mask], uu[:, i_cmp])

plt.subplot(224)
plt.plot(energy_in[e_in_mask], vv[:, i_cmp])
#########




print(f'with APB and SHUTTER: {np.mean([1.6482348442077637, 1.7039844989776611, 1.6537742614746094, 1.7817823886871338, 1.7271864414215088])}')
print(f'with APB: {np.mean([1.213865041732788, 1.268347978591919, 1.3224411010742188, 1.2643957138061523, 1.3515892028808594])}')
print(f'without APB: {np.mean([1.0586943626403809, 1.1041831970214844, 1.0835952758789062, 1.1153781414031982, 1.138744592666626])}')


######

from xas.db_io import load_apb_dataset_from_db, load_apb_trig_dataset_from_db




def plot_trace_for_uid(uid, offset=0):
    hdr = db[uid]
    t_apb = hdr.table(stream_name='apb_stream', fill=True).apb_stream[1]
    t_trig = hdr.table(stream_name='apb_trigger_pil100k', fill=True).apb_trigger_pil100k[1]

    t_min = t_apb[:, 0].min()

    apb_trace = t_apb[:, 6] / 1e6
    apb_trace2 = t_apb[:, 5] / 1e6
    # apb_trace -= np.percentile(apb_trace, 1)
    # apb_trace /= np.percentile(apb_trace, 99)


    # plt.plot(t_apb[:, 0], t_apb[:, 5] / 1e6)
    plt.plot(t_apb[:, 0] - t_min, apb_trace - offset, '-')
    plt.plot(t_apb[:, 0] - t_min, apb_trace2 - offset, '-')
    # plt.plot(t_trig[:, 0] - t_min, t_trig[:, 1] - offset, 'r-')



y_shift = 1.25
plt.figure(1, clear=True)
for i, uid in enumerate(uids):
    plot_trace_for_uid(uid, offset=i*y_shift)
    plt.text(0.2, -i*y_shift + y_shift*0.25, f'({i+1}) {uid}', ha='center', va='center')

# plt.legend()
plt.xlim(0, 1)

plot_trace_for_uid(-1, 0)

############

uids = ['452dc667-f81a-4daf-be60-e6e7d486211d',
        '2c5c0b8f-01e9-4e22-8748-d582dc75e8c0',
        'd178dd6b-531a-4780-8fa4-101a7b8569b8',
        '262acc5b-2941-4284-b01e-ba7bcb4a2122',
        '3572f520-1777-417e-a0b6-685ff8267761',
        '3a8af009-5213-40e7-9340-0de79b34551d',
        '87ec51b5-3848-4dfe-ba27-320418258ffe',
        '4e00831c-9163-4715-9f32-e413ec1b889a',
        'b4090950-b187-4416-b611-ca0d3ec8c8c7',
        'e23bcf19-d8c0-4fac-997f-d0f7dfe1296b'
        ]
# uid = '452dc667-f81a-4daf-be60-e6e7d486211d'

plt.figure(1, clear=True)

for i, uid in enumerate(uids):
    hdr = db[uid]

    stream_name='apb_trigger_pil100k'
    data_trig_raw = list(hdr.data(stream_name=stream_name, field=stream_name))[0]

    # from xas.db_io import load_apb_dataset_from_db, load_apb_trig_dataset_from_db
    df_apb, _, _ = load_apb_dataset_from_db(db, uid)

    derived_timestamps_trig = load_apb_trig_dataset_from_db(db, uid, stream_name=stream_name)

    t_apb = df_apb.timestamp.values
    s_apb = df_apb.aux2.values

    s_apb -= s_apb.min()
    s_apb /= s_apb.max()

    plt.plot(data_trig_raw[:, 0] - t_apb.min(), data_trig_raw[:, 1] - i * 1.15)
    plt.plot(t_apb - t_apb.min(), s_apb - i * 1.15)
    plt.vlines(derived_timestamps_trig.tolist() - t_apb.min(), 0 - i * 1.15, 1.1 - i * 1.15, colors='k')


##########


unique_samples = get_unique_values_for_metadata_key(node, 'sample_name')
unique_scans = get_unique_values_for_metadata_key(node, 'scan_name')
# unique_quality = get_unique_values_for_metadata_key(node, 'scan_quality')

denis_tree = {}

for _sample in unique_samples:
    denis_tree[_sample] = {}
    for _scan in unique_scans:
        denis_tree[_sample][_scan] = {}
        # for _quality_i, _quality in enumerate(unique_quality):
        print(_sample, _scan,)
        _node = node.search(Key('sample_name') == _sample).search(Key('scan_name') == _scan)
        # _uid_indexes = list(range(len(_uids)))
        denis_tree[_sample][_scan] = {'node': _node}#, 'index': _uid_indexes, 'checkbox_id': []}




#########
from matplotlib import pyplot as plt
plt.ion()



# plt.figure(1, clear=True)
# for i in range(10):
#     # df = load_apb_dataset_from_tiled(run)
#     # plt.plot(df.timestamp, df.i0)
#     df = read_hhm_encoder_dataset_from_tiled(run)
#     plt.plot(df.timestamp, df.energy)


apb_df = load_apb_dataset_from_tiled(run)



energy_df = load_hhm_encoder_dataset_from_tiled(run)

apb_dict = translate_dataset(apb_df)
energy_dict = translate_dataset(energy_df, columns=['energy'])

raw_dict = {**apb_dict, **energy_dict}

dataset = raw_dict

interpolated_dataset = interpolate(dataset)

rebinned_dataset = rebin(interpolated_dataset, run.metadata['start']['e0'])

# interpolated_dataset = {}
key= 'mufluor'
df = dataset[key]
# df['timestamp_bin'] = pd.cut(df['timestamp'], bins=timestamp_edges, labels=timestamp)
# df_mean = df.groupby('timestamp_bin').mean(numeric_only=False)
# interpolated_dataset[key] = df_mean[key]

plt.figure(1, clear=True)
# plt.plot(df['timestamp'], df[key], '.-')
# plt.plot(interpolated_dataset['timestamp'], interpolated_dataset[key], '.')
plt.plot(rebinned_dataset['timestamp'], rebinned_dataset[key] - rebinned_dataset['iff'] / rebinned_dataset['i0'], '.-')
# plt.plot(rebinned_dataset['timestamp'], , '.-')


####

plt.figure(1, clear=True)
plt.plot(apb_df['timestamp'], apb_df['mufluor'])
# plt.plot(apb_df['timestamp'], apb_df['iff'] / apb_df['i0'])

######

# plt.figure(1, clear=True)
# for i, (k, ds) in enumerate(raw_dict.items()):
#     plt.plot(ds.timestamp.values, np.ones(ds.timestamp.values.size) - i)

# imports

from ophyd import EpicsSignal
import time as ttime
import numpy as np
import matplotlib.pyplot as plt
plt.ion()

# ophyd signals
apb_fa_filename_bin = EpicsSignal('XF:08IDB-CT{PBA:1}:FA:Stream:Bin:File-SP', name='apb_filename_bin')
apb_fa_filename_txt = EpicsSignal('XF:08IDB-CT{PBA:1}:FA:Stream:Txt:File-SP', name='apb_filename_txt')
apb_fa_stream = EpicsSignal('XF:08IDB-CT{PBA:1}:FA:Stream-SP', name='apb_stream')

apb_trig_filename = EpicsSignal('XF:08IDB-CT{PBA:1}:Pulse:2:Filename-SP', name='apb_trig_filename')
apb_trig_stream = EpicsSignal('XF:08IDB-CT{PBA:1}:Pulse:2:Stream:Mode-SP', name='apb_trig_stream')
apb_trig_acquire = EpicsSignal('XF:08IDB-CT{PBA:1}:Pulse:2:Mode-SP', name='apb_trig_acquire')

def set_filenames(n):
    fname = f'/nsls2/data/iss/legacy/raw/apb/2023/04/05/trigger_test2_{n:02d}'
    fname_fa_bin = fname + '_fa.bin'
    fname_fa_txt = fname + '_fa.txt'
    apb_fa_filename_bin.put(fname_fa_bin)
    apb_fa_filename_txt.put(fname_fa_txt)

    fname_trig = fname + '_trig.bin'
    apb_trig_filename.put(fname_trig)
    return fname_fa_bin, fname_trig

def acquisition_sequence():
    ttime.sleep(0.2) # small delay before start to let the file PVs to write
    apb_fa_stream.put(1)
    ttime.sleep(1) # sleep a bit to ensure that streaming actually begins

    apb_trig_stream.put(1)
    ttime.sleep(0.5) # small delay to ensure that streaming of trigger is commenced before pulsing begins
    apb_trig_acquire.put(2)

    ttime.sleep(1) # let it run for a bit

    apb_fa_stream.put(0)
    apb_trig_stream.put(0)
    apb_trig_acquire.put(0)
    ttime.sleep(0.5) # small delay to ensure that files finish writing

# def acquisition_sequence():
#     ttime.sleep(0.2) # small delay before start to let the file PVs to write
#
#     apb_trig_acquire.put(1)  #Set Pulser acquire state to “FA”
#
#     ttime.sleep(0.2) # small delay before start set Pulser acquire state to “FA”
#
#     apb_trig_stream.put(1)   #Enable Pulser streaming to file.  Nothing will happen until FA streaming starts
#
#     ttime.sleep(0.2) # small delay before start set Pulser streaming to “Enable”
#     apb_fa_stream.put(1)  #Start the FA streaming.  This will immediately start the Pulser streaming as well.
#
#     ttime.sleep(3) # let it run for a bit
#
#     apb_fa_stream.put(0)
#     apb_trig_stream.put(0)
#     apb_trig_acquire.put(0)
#     ttime.sleep(0.5) # small delay to ensure that files finish writing

# def acquisition_sequence():
#     ttime.sleep(0.2) # small delay before start to let the file PVs to write
#
#     apb_trig_stream.put(1) #Enable Pulser Streaming.  Pulser is still OFF.
#     ttime.sleep(0.2) # small delay to ensure that streaming is Enabled.
#     apb_trig_acquire.put(2)  #Turn Pulser ON. Pulser transitions will be streamed to file.
#
#     ttime.sleep(0.2) # small delay to ensure that streaming is running.
#     apb_fa_stream.put(1) #Turn FA streaming ON
#
#     ttime.sleep(3) # let it run for a bit
#
#     apb_fa_stream.put(0)
#     apb_trig_stream.put(0)
#     apb_trig_acquire.put(0)
#     ttime.sleep(0.5) # small delay to ensure that files finish writing


# data readout
def read_fa_data(fpath):
    raw_data = np.fromfile(fpath, dtype=np.int32)

    columns = ['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4']
    num_columns = len(columns) + 1
    raw_data = raw_data.reshape((raw_data.size // num_columns, num_columns))

    derived_data = np.zeros((raw_data.shape[0], raw_data.shape[1] - 1))
    derived_data[:, 0] = raw_data[:, -2] + raw_data[:, -1] * 8.0051232 * 1e-9  # Unix timestamp with nanoseconds
    for i in range(num_columns - 2):
        derived_data[:, i + 1] = raw_data[:, i]  # ((raw_data[:, i] ) - Offsets[i]) / Gains[i]

    return derived_data

def read_trig_data(fpath):
    raw_data = np.fromfile(fpath, dtype=np.int32)
    raw_data = raw_data.reshape((raw_data.size // 3, 3))

    derived_data = np.zeros((raw_data.shape[0], 2))
    derived_data[:, 0] = raw_data[:, 1] + raw_data[:, 2] * 8.0051232 * 1e-9  # Unix timestamp with nanoseconds
    derived_data[:, 1] = raw_data[:, 0]
    return derived_data

def get_data(fname_fa_bin, fname_trig):
    data_fa = read_fa_data(fname_fa_bin)
    data_trig = read_trig_data(fname_trig)

    time_fa = data_fa[:, 0]
    signal_fa = data_fa[:, 6]
    t_min = time_fa.min()

    time_trig = data_trig[:, 0]
    signal_trig = data_trig[:, 1]
    return (time_fa - t_min), signal_fa, (time_trig - t_min), signal_trig


# def acquire_data(n=3):
n = 1
plt.figure(1, clear=True)
for i in range(n):
    fname_fa_bin, fname_trig = set_filenames(i + 1)
    acquisition_sequence()
    offset = i * 1.15
    time_fa, signal_fa, time_trig, signal_trig = get_data(fname_fa_bin, fname_trig)
    signal_fa_ = (signal_fa - np.percentile(signal_fa, 1)) / (np.percentile(signal_fa, 99) - np.percentile(signal_fa, 1))
    plt.plot(time_fa, signal_fa_ - offset)
    plt.plot(time_trig, signal_trig - offset)


plt.figure(2)
plt.plot(time_fa, signal_fa*1e-6)

processed_scans = list(range(352382, 354132))
uids = list(db.v2.search({'proposal': '311347'}))

# scan_md = [[db[uid].start['time'], db[uid].start['scan_id']] for uid in uids]
# scan_ids = [db[uid].start['scan_id'] for uid in uids]

# for uid in uids:
for i in range(389939, 389963):
#     try:
    hdr = db[uid]
    if hdr.start['scan_id'] not in processed_scans:
        try:
            process_interpolate_bin(hdr.stop, db)
        except Exception as e:
            print(e)

############

offset = 0
def elasic_plot_func(x, y, x_fit, y_fit, Ecen, fwhm, roi_label='', roi_color='k'):
    global offset
    plt.plot(x, y - offset, '.', color=roi_color)
    plt.plot(x_fit, y_fit - offset, '-', color=roi_color)
    offset += 0.1

motor_pos_elastic = []
fwhm_elastic = []
max_elastic = []

plt.figure(1, clear=True)
offset = 0
for uid in range(389939, 389963 + 1):
    _fwhm, _max= analyze_linewidth_fly_scan(db, uid, x_key='energy', rois=[1], plot_func=elasic_plot_func)
    # _fwhm = analyze_elastic_fly_scan(db, uid, rois=[1], plot_func=elasic_plot_func)
    fwhm_elastic.append(_fwhm)
    max_elastic.append(_max)
    motor_pos_elastic.append(db[uid].start['tweak_motor_position'])

motor_pos_emission = []
fwhm_emission = []
max_emission = []
plt.figure(2, clear=True)
offset = 0
for uid in range(389461, 389485 + 1):
# for uid in range(389456, 389485 + 1):
    _fwhm, _max = analyze_linewidth_fly_scan(db, uid, rois=[1], plot_func=elasic_plot_func)
    fwhm_emission.append(_fwhm)
    max_emission.append(_max)
    motor_pos_emission.append(db[uid].start['tweak_motor_position'])



_, ax1 = plt.subplots(1, num=3, clear=True)
ax2 = ax1.twinx()
# ax3 = ax1.twinx()
# ax4 = ax1.twinx()

def my_plot_func(ax=ax1, marker='.', color='k', sign=1):
    def _bla(x, y, x_min, y_fit):
        _y = np.array(y) * sign
        _y_fit = np.array(y_fit) * sign
        ax.plot(x, _y, color + marker)
        ax.plot(x, _y_fit, color + '-')
        ax.vlines([x_min], np.min(_y), np.max(_y), colors=color)
    return _bla

get_optimal_crystal_alignment_position(motor_pos_elastic, fwhm_elastic, plot_func=my_plot_func(ax=ax1, marker='o', color='b', sign=1))
get_optimal_crystal_alignment_position(motor_pos_emission, fwhm_emission, plot_func=my_plot_func(ax=ax2, marker='o', color='r', sign=1))
# get_optimal_crystal_alignment_position(motor_pos_elastic, -np.array(max_elastic), plot_func=my_plot_func(ax=ax3, marker='s', color='b', sign=-1))
# get_optimal_crystal_alignment_position(motor_pos_emission, -np.array(max_emission), plot_func=my_plot_func(ax=ax4, marker='s', color='r', sign=-1))



total_img = []

elastic_scan = {}
for uid in range(389939, 389963):
    df = get_processed_df_from_uid(uid, db, save_interpolated_file=False, return_processed_df=True)

    hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind
    hdr = db[uid]
    x = hdr.start['tweak_motor_position']
    t = hdr.table(stream_name='pil100k_stream', fill=True)
    scan = []
    for img in t.pil100k_image[1]:
        scan.append(np.sum(img[85:120, 194:265]))
        if uid in [389939, 389950, 389962]:
            total_img.append(img)
    elastic_scan[x] = scan

bla = np.mean(np.array(total_img), axis=0)
plt.figure(2, clear=True)
plt.imshow(bla, vmin=0.04, vmax=0.07)


# data['Ecen'] = []
data['fwhm'] = []
# data['I_cor'] = []
# data['I_fit'] = []
# data['I_fit_raw'] = []
# data['E_scan'] = []
for uid in range(389939, 389963):
    Ecen0, fwhm0 = estimate_center_and_width_of_peak(E, I)
    Ecen, fwhm, I_cor, I_fit, I_fit_raw = fit_gaussian(E, I, Ecen0, fwhm0)
    # Ecen, fwhm, I_cor, I_fit, I_fit_raw, E_scan = analyze_elastic_fly_scan(db, uid=uid)
    # data['Ecen'].append(Ecen)
    data['fwhm'].append(fwhm)
    # data['I_cor'].append(I_cor)
    # data['I_fit'].append(I_fit)
    # data['I_fit_raw'].append(I_fit_raw)
    # data['E_scan'].append(E_scan)







#Elastic scan plot

data = {}
# data['x'] = []
for uid in range(389939, 389963):
    hdr = db[uid]
    x_val = hdr.start['tweak_motor_position']
    fwhm = analyze_elastic_fly_scan(db, uid=uid)
    data[x_val] = fwhm

fig, ax = plt.subplots(1,1, figsize=(4,6))

ax.plot(data.keys(), data.values(), '-ro')
ax.set_xlabel(r'R (mm)', size=12)
ax.set_ylabel(r'FWHM (eV)', size=12)
# ax.set_yticks(np.arange(1.52, 1.9, 0.05))

path = '/home/xf08id/Documents/Spectrometer_paper/'

plt.savefig(path + 'elastic.png', bbox_inches='tight', dpi=600)


#Emission cuk

#main = 389556, 389485
#aux2 = 389487, 389539
#aux3 = 389540, 389593

data_m = {}
for uid in range(389456, 389485):
    hdr = db[uid]
    x_val = hdr.start['tweak_motor_position']
    fwhm, _ = analyze_linewidth_fly_scan(db, uid=uid)
    data_m[x_val] = fwhm

data_2 = {}
for uid in range(389487, 389539):
    hdr = db[uid]
    if 'tweak_motor_position' in hdr.start.keys():
        _x = hdr.start['spectrometer_config']['bragg_registration']['pos_act']['motor_cr_assy_x'][0]
        x_val = hdr.start['tweak_motor_position']
        x_val = (x_val/1000) + _x
        x_key = 'johann_aux2_crystal_motor_cr_aux2_roll'
        fwhm, _ = analyze_linewidth_fly_scan(db, uid=uid, x_key=x_key)
        data_2[x_val] = fwhm
    else:
        pass

data_3 = {}
for uid in range(389540, 389593):
    hdr = db[uid]
    if 'tweak_motor_position' in hdr.start.keys():

        _x = hdr.start['spectrometer_config']['bragg_registration']['pos_act']['motor_cr_assy_x'][0]
        x_val = hdr.start['tweak_motor_position']
        x_val = (x_val/1000) + _x
        x_key = 'johann_aux3_crystal_motor_cr_aux3_roll'
        fwhm, _ = analyze_linewidth_fly_scan(db, uid=uid, x_key=x_key)
        data_3[x_val] = fwhm
    else:
        pass

fig, ax = plt.subplots(1,1, figsize=(6,4))

ax.plot(data_m.keys(), data_m.values(), '-ro', label='main')
ax.plot(data_2.keys(), data_2.values(), '-bo', label='aux2')
ax.plot(data_3.keys(), data_3.values(), '-go', label='aux3')

ax.set_xlabel(r'R (mm)', size=12)
ax.set_ylabel(r'FWHM (a.u.)', size=12)
# ax.set_yticks(np.arange(1.52, 1.9, 0.05))
ax.legend()

path = '/home/xf08id/Documents/Spectrometer_paper/'

plt.savefig(path + 'emission_cuk.png', bbox_inches='tight', dpi=600)

#herfd main 389700, 389724
#herfd aux2 389725, 389778
#herfd aux3 389779, 389832
#herfd aux4 389834, 389878
#herfd aux5 389880, 389938

X = []
for uid in range(389700, 389725):
    hdr = db[uid]
    x_val = hdr.start['tweak_motor_position']
    X.append(x_val)
    df = get_processed_df_from_uid(uid, db=db)
    np.savetxt(path + f'Main x {x_val:.3f}.dat', np.column_stack((df[1]['energy'], df[1]['i0'], df[1]['pil100k_roi1'])))

np.savetxt(path + f"Main x value.dat", np.column_stack((X)))

X = []
for uid in range(389725, 389779):
    hdr = db[uid]
    if 'tweak_motor_position' in hdr.start.keys():
        # _x = hdr.start['spectrometer_config']['bragg_registration']['pos_act']['motor_cr_assy_x'][0]
        _x = 986.700040041
        x_val = hdr.start['tweak_motor_position']
        x_val = (x_val / 1000) + _x
        X.append(x_val)
        df = get_processed_df_from_uid(uid, db=db)
        np.savetxt(path + f'Aux2 x {x_val:.3f}.dat', np.column_stack((df[1]['energy'], df[1]['i0'], df[1]['pil100k_roi1'])))
    else:
        pass
np.savetxt(path + f"Aux2 x value.dat", np.column_stack((X)))


X = []
for uid in range(389779, 389832):
    hdr = db[uid]
    if 'tweak_motor_position' in hdr.start.keys():
        # _x = hdr.start['spectrometer_config']['bragg_registration']['pos_act']['motor_cr_assy_x'][0]
        _x = 986.700040041
        x_val = hdr.start['tweak_motor_position']
        x_val = (x_val / 1000) + _x
        X.append(x_val)
        df = get_processed_df_from_uid(uid, db=db)
        np.savetxt(path + f'Aux3 x {x_val:.3f}.dat', np.column_stack((df[1]['energy'], df[1]['i0'], df[1]['pil100k_roi1'])))
    else:
        pass
np.savetxt(path + f"Aux3 x value.dat", np.column_stack((X)))

X = []
for uid in range(389834, 389878):
    hdr = db[uid]
    if 'tweak_motor_position' in hdr.start.keys():
        # _x = hdr.start['spectrometer_config']['bragg_registration']['pos_act']['motor_cr_assy_x'][0]
        _x = 986.700040041
        x_val = hdr.start['tweak_motor_position']
        x_val = (x_val / 1000) + _x
        X.append(x_val)
        df = get_processed_df_from_uid(uid, db=db)
        np.savetxt(path + f'Aux4 x {x_val:.3f}.dat', np.column_stack((df[1]['energy'], df[1]['i0'], df[1]['pil100k_roi1'])))
    else:
        pass
np.savetxt(path + f"Aux4 x value.dat", np.column_stack((X)))

X = []
for uid in range(389880, 389938):
    hdr = db[uid]
    if 'tweak_motor_position' in hdr.start.keys():
        # _x = hdr.start['spectrometer_config']['bragg_registration']['pos_act']['motor_cr_assy_x'][0]
        _x = 986.700040041
        x_val = hdr.start['tweak_motor_position']
        x_val = (x_val / 1000) + _x
        X.append(x_val)
        df = get_processed_df_from_uid(uid, db=db)
        np.savetxt(path + f'Aux5 x {x_val:.3f}.dat', np.column_stack((df[1]['energy'], df[1]['i0'], df[1]['pil100k_roi1'])))
    else:
        pass
np.savetxt(path + f"Aux5 x value.dat", np.column_stack((X)))

def get_timestamps_for_pbs(uid, db):
    hdr = db[uid]
    t_apb = hdr.table(stream_name='apb_stream', fill=True)
    t_enc = hdr.table(stream_name='pb9_enc1', fill=True)
    time_enc = t_enc['pb9_enc1'][1][:, 0] + t_enc['pb9_enc1'][1][:, 1]*1e-9
    time_apb = t_apb['apb_stream'][1][:, 0]
    return time_apb, time_enc


time_apb_sn, time_enc_sn =  get_timestamps_for_pbs('86011010-7b40-4987-abd0-106f8b31a86d', db)
time_apb_in, time_enc_in =  get_timestamps_for_pbs('a159e8ca-b4ed-4dde-b0ed-a2e6f4875067', db) # Sep 2023
# time_apb_in, time_enc_in =  get_timestamps_for_pbs('8d45c349', db) # June 2023

plt.figure(1, clear=True)
plt.plot(time_enc_sn - time_enc_sn[0], '.-')
plt.plot(time_enc_in - time_enc_in[0], '.-')


_, time_enc_in_now =  get_timestamps_for_pbs('a159e8ca-b4ed-4dde-b0ed-a2e6f4875067', db) # Sep 2023
_, time_enc_in_old = get_timestamps_for_pbs('8d45c349', db) # June 2023

plt.figure(1, clear=True)
plt.plot(time_enc_in_now - time_enc_in_now[0], '.-')
plt.plot(time_enc_in_old - time_enc_in_old[0], '.-')



# _, time_enc_cu_now =  get_timestamps_for_pbs('73761037-9d85-435b-a4a8-bb168baa73a0', db)
_, time_enc_cu_now =  get_timestamps_for_pbs('e6bbc310-aa06-4f87-8edc-bd1864088a38', db)
# _, time_enc_cu_now =  get_timestamps_for_pbs('e018c7bb-37ba-4a7d-8d9c-185ad579b7ab', db)
_, time_enc_cu_old = get_timestamps_for_pbs('3d265b3a', db)

plt.figure(1, clear=True)
plt.plot(time_enc_cu_now - time_enc_cu_now[0], '.-')
plt.plot(time_enc_cu_old - time_enc_cu_old[0], '.-')


R = 500

hkl1 = [1, 1, 1]
hkl2 = [1, 1, 0]
cos_alpha = np.dot(hkl1, hkl2)/np.linalg.norm(hkl1)/np.linalg.norm(hkl2)
alpha = np.arccos(cos_alpha)
alpha_deg = np.rad2deg(alpha)

bragg_deg = 90 - alpha_deg + 2.15
print(f'{bragg_deg=}, {alpha_deg=}')

bragg = np.deg2rad(bragg_deg)

# bragg = np.deg2rad(45)
# alpha = np.deg2rad(45) # 0*np.deg2rad(np.rad2deg(np.arccos(np.sqrt(2/3))))
crystal_x = R * np.sin(bragg + alpha) * np.sin(bragg - alpha)
crystal_y = R * np.sin(bragg + alpha) * np.cos(bragg - alpha)
det_x = 0
det_y = 2 * R * np.sin(bragg) * np.cos(bragg)
K_x = R * np.sin(bragg)**2 - R/2
K_y = R * np.sin(bragg)*np.cos(bragg)

phi = np.deg2rad(np.linspace(0, 360, 361))
KK_x = R/2 * np.cos(phi) + K_x
KK_y = R/2 * np.sin(phi) + K_y

plt.figure(1, clear=True)
plt.plot(0, 0, 'ko')

plt.plot(crystal_x, crystal_y, 'bo')
plt.plot(det_x, det_y, 'go')
plt.plot([0, crystal_x, det_x], [0, crystal_y, det_y], 'k-')

plt.plot(K_x, K_y, 'mo')
plt.plot(KK_x, KK_y, 'm-')

plt.xlim(-500, 1000)
plt.ylim(-500, 1000)
plt.axis('equal')


from xas.process import process_interpolate_bin_from_uid, get_processed_df_from_uid
from xas.file_io import save_extended_data_as_file

uids = [ 'd6b89a0d-1cf5-4b0b-8695-bc84cb5007e5',
         '318cec96-5213-4773-baf2-da50cae02f2d',
         '138e62df-c191-4831-9249-a5d252e8b6e8',
         '4989c59b-76a0-46dd-8723-51fd6f1ff6e5',
         'abaa4995-9bd1-4a5b-9b2d-4338ea30ab12',
         'b5d1704b-8c99-4f71-884f-14204166ab7b',
         '119523cd-0aae-4964-af3d-140458a51bcd',
         '4f94bb97-166e-4194-b145-bab39479bbf1',
         '23bfef24-7602-4a65-b761-cd9617152716',
         '8e71ee10-c9a3-4c49-9c59-11f169ca94d9' ]


# uids = list(range(42213, 42321 + 1))[4:]
uids = list(range(42304, 42321 + 1))
for i, uid in enumerate(uids):
    try:
        print('workding on', uid, db[uid].start.name, 'progress:', i / len(uids) * 100)
    except:
        pass
    if 'experiment' not in db[uid].start:
        continue
    hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db,
                                                                              logger=None,
                                                                              draw_func_interp=None,
                                                                              draw_func_bin=None,
                                                                              print_func=None,
                                                                              save_interpolated_file=False,
                                                                              update_start=None,
                                                                              load_images=True)

    path_to_file = hdr.start['interp_filename'][:-3] + 'dat'
    # extended_data['pil100k_image'] = extended_data['pil100k_image'].astype(np.float32)
    save_extended_data_as_file(path_to_file, extended_data, data_kind=data_kind)



###
np.random.seed(1)

x = np.arange(100)
s = np.exp(-((x - 50)/ (np.sqrt(2) * 5))**2) * 7
noise1 = np.random.randn(100) * (np.sqrt(55)/np.sqrt(500))
noise2 = np.random.randn(100) * (np.sqrt(55/10)/np.sqrt(180))


plt.figure(1, clear=True)
plt.plot(x, s + noise1)
plt.plot(x, s + noise2)



####
from xas.file_io import load_binned_df_from_file


files = ['/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0001 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0003 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0004 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0005 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0006 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0007 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0008 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0009 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0010 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0001-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0002-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0004-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0003-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0005-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0006-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0007-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0008-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0009-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0010-r0002 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0011 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0012 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0013 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0014 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0015 vh_roi1.dat',
         # '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0016 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0017 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0018 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0019 vh_roi1.dat',
         '/nsls2/data/iss/legacy/processed/2024/1/309462/24-2254 reduced Pt-L3 RIXS 10s 0020 vh_roi1.dat',]

files = [
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0003 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0004 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0005 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0006 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0007 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0008 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0009 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0010 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0011 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0012 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0013 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0017 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0018 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0019 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0020 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0021 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0022 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0023 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0024 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0025 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0026 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0027 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0030 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0031 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0032 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-24102 (pos 001) Pt-L3 RIXS 10s 0001-r0033 vh_roi1.dat',
]


files = [
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0002 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0003 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0004 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0005 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0006 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0007 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0008 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0009 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0010 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0011 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0012 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0016 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0017 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0018 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0019 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0020 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0021 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0022 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0023 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0024 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0025 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0026 vh_roi1.dat',
# '/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0027 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0030 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0031 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0032 vh_roi1.dat',
'/nsls2/data/iss/legacy/processed/2024/1/309462/23-63961 (pos 001) Pt-L3 RIXS 10s 0001-r0033 vh_roi1.dat',
]

rxes_list = []

for file in files:
    df, _ = load_binned_df_from_file(file)
    _energy_in = df.energy.values
    _energy_out = np.array([float('.'.join(i.split('_')[-2:])) for i in df.columns[1::2].tolist()])
    _counts = df.values[:, 1::2]
    _i0 = df.values[:, 2::2]
    rxes_list.append({'energy_in': _energy_in, 'energy_out': _energy_out, 'intensity': _counts / (_i0 / np.median(_i0, axis=1)[:, None])})

energy_in = _energy_in
energy_out = _energy_out
rxes = np.mean(np.array([_rxes['intensity'] for _rxes in rxes_list]), axis=0)

plt.figure(2, clear=True)
plt.contourf(energy_out, energy_in, rxes, 251, vmin=0, vmax=70)




# rxes_242254 = {'energy_out': energy_out, 'energy_in': energy_in, 'rxes': rxes}
# rxes_2324102 = {'energy_out': energy_out, 'energy_in': energy_in, 'rxes': rxes}
rxes_2363961 = {'energy_out': energy_out, 'energy_in': energy_in, 'rxes': rxes}


plt.figure(1, clear=True)
plt.contourf(rxes_242254['energy_out'], rxes_242254['energy_in'], rxes_242254['rxes'], 251, vmin=0, vmax=70)
plt.title('24-2254')

plt.figure(2, clear=True)
plt.contourf(rxes_2324102['energy_out'], rxes_2324102['energy_in'], rxes_2324102['rxes'], 251, vmin=0, vmax=70)
plt.title('23-24102')

plt.figure(3, clear=True)
plt.contourf(rxes_2363961['energy_out'], rxes_2363961['energy_in'], rxes_2363961['rxes'], 251, vmin=0, vmax=70)
plt.title('23-63961')


#########

mask = np.zeros(img.shape, dtype=bool)
mask[:, 59::61] = True
mask[:, 60::61] = True
mask[:, 61::61] = True
mask[96:99, :] = True

vsize, hsize = mask.shape
hpix, vpix = np.meshgrid(np.arange(hsize), np.arange(vsize))

hpix_arr = hpix.reshape(vsize * hsize)
vpix_arr = vpix.reshape(vsize * hsize)
mask_arr = mask.reshape(vsize * hsize)

dr = np.sqrt((hpix_arr[mask_arr][:, None] - hpix_arr[~mask_arr][None, :])**2 + (vpix_arr[mask_arr][:, None] - vpix_arr[~mask_arr][None, :])**2)
index_closest = np.argmin(dr, axis=1)

img_mask_arr = img.reshape(vsize * hsize)[mask_arr]
img_closeset_arr = img.reshape(vsize * hsize)[index_closest]

# mask_closest = np.zeros(img.shape, dtype=bool)
# for idx in index_closest:
#     vp = vpix_arr[~mask_arr][idx]
#     hp = hpix_arr[~mask_arr][idx]
#     # print(vp, hp)
#     mask_closest[vp, hp] = True


img_cor = img.copy()
img_cor[mask] *= 0.96
# img_cor[mask_closest] *= 10

plt.figure(1, clear=True)
plt.subplot(211)
plt.imshow(img, vmin=3, vmax=10)

plt.subplot(212)
plt.imshow(img_cor, vmin=3, vmax=10)

plt.figure(2, clear=True)
plt.plot(img_closeset_arr, img_closeset_arr / img_mask_arr, 'k.')
# plt.axis('square')



hhm_y_precise = {}
hhm_y_precise['uid'] = []
hhm_y_precise['value'] = []
def find_optimal_hhm_Y_values():
    energy_tab = [ 4900,  5100,  5500,  6000,  7000,  8000,  9000, 10000, 11000, 12000, 13000, 15000, 17500, 20000]
    # energy_tab = [9000]
    for energy in energy_tab:
        yield from bps.mv(hhm.energy, energy)
        yield from prepare_beamline_plan(energy, move_cm_mirror = True, move_hhm_y = True)
        yield from quick_pitch_optimization()
        yield from bp.relative_scan([bpm_fm], hhm.y_precise, -0.5, 0.5, 21)


        hdr = db[-1]
        hhm_y_precise['uid'].append(hdr.start['uid'])
        t = hdr.table()
        index = np.argmax(t['bpm_fm_stats1_total'])
        hhm_y_precise['value'].append(t['hhm_y_precise'][index+1])





#2024-09-19

[9.937850000000001,
 9.57315,
 9.467450000000001,
 9.3162,
 9.177100000000001,
 9.08755,
 9.025,
 8.978050000000001,
 8.9411,
 8.9609,
 8.88475,
 8.84365,
 8.85205,
 8.816450000000001]


uids =['d0166c48-ebcf-4647-820f-f10f53e768f8',
 '93b12235-e1ba-4ef4-93e7-7ea558450f0d',
 '3e49c021-69de-4011-937f-0637a56ddf40',
 'ebfafa6f-5ef5-4820-a77f-8f0b9436959e',
 '9f8e8399-a0af-4099-ae57-b89f4e9687cf',
 '021337a6-693c-4a0f-a529-5246e574f941',
 '8a21ec71-c4ae-4a95-94ee-6b8e6e5b24c4',
 '6ec12c6d-492e-44d1-93c9-9876a1b53f96',
 '922fa456-e258-43c6-b6ba-b498f6f61bf9',
 '7794afc8-4dd0-4591-98ff-c576df92790e',
 'c7354f86-c247-4ad4-858f-2d0e7043f326',
 '496d2087-10dd-4ff1-83f1-7ab7410d8bd2',
 '1baf04d6-a8e3-4a6b-882d-e31ca3a5b75a',
 'db7bb3d2-866d-47d4-a1fd-463d94c46416']

with open('inclinometer_data.json') as jd:
    d = json.load(jd)

d = {'motor_det_th1': {'0': -27,
  '1': -24,
  '2': -21,
  '3': -18,
  '4': -15,
  '5': -12,
  '6': -9,
  '7': -6,
  '8': -3,
  '9': 0,
  '10': 3,
  '11': 6,
  '12': 9,
  '13': 12,
  '14': 15,
  '15': 18,
  '16': 21,
  '17': 24,
  '18': 27,
  '19': 30,
  '20': 33,
  '21': 36,
  '22': 39,
  '23': 42,
  '24': 45,
  '25': 48,
  '26': 51,
  '27': 54,
  '28': 57,
  '29': 60,
  '30': 63,
  '31': 66,
  '32': 69},
 'motor_det_inc1': {'0': 14653,
  '1': 14388,
  '2': 14119,
  '3': 13855,
  '4': 13575,
  '5': 13316,
  '6': 13047,
  '7': 12782,
  '8': 12514,
  '9': 12244,
  '10': 11980,
  '11': 11705,
  '12': 11436,
  '13': 11172,
  '14': 10903,
  '15': 10639,
  '16': 10370,
  '17': 10106,
  '18': 9836,
  '19': 9567,
  '20': 9303,
  '21': 9039,
  '22': 8774,
  '23': 8505,
  '24': 8241,
  '25': 7972,
  '26': 7707,
  '27': 7438,
  '28': 7164,
  '29': 6900,
  '30': 6631,
  '31': 6366,




plt.figure();
plt.plot(d['motor_det_th1'].keys(), d['motor_det_th1'].values())


plt.figure();
plt.plot(d['motor_det_th1'].keys(), d['motor_det_inc1'].values())


id = 'fb1129d8-0a05-45fc-85d0-6844af4c5e50'
fb=f'/nsls2/data/iss/legacy/raw/apb/2024/10/31/{id}.txt'
raw_data = np.fromfile(fp, dtype=np.int32)
columns = ['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4']
num_columns = len(columns) + 1  # TODO: figure out why 1
reshaped = raw_data[2:].reshape((raw_data.size // num_columns, num_columns))
derived_data = np.zeros((reshaped.shape[0], reshaped.shape[1] - 1))
derived_data[:, 0] = reshaped[:, -2] + reshaped[:, -1] * 8.0051232 * 1e-9  # Unix timestamp with nanoseconds
for i in range(num_columns - 2):
    derived_data[:, i + 1] = reshaped[:, i]  #
df = pd.DataFrame(data=derived_data, columns=columns)

class XmapMCA(Device):
    val = Cpt(EpicsSignal, "VAL")
    R0low = Cpt(EpicsSignal, "R0LO")
    R0high = Cpt(EpicsSignal, "R0HI")
    R0 = Cpt(EpicsSignal, "R0")
    R0nm = Cpt(EpicsSignal, "R0NM")

def make_channels(channels):
    chn_dict = OrderedDict()
    for channel in channels:
        attrStr = f"mca{channel:1d}"
        chn_dict[attrStr] = (XmapMCA, f"mca{channel:1d}.", dict())
        attrStr = f"preamp{channel:1d}_gain"
        chn_dict[attrStr] = (EpicsSignal, f"dxp{channel:1d}.PreampGain", dict())

    return chn_dict

# def make_mcas(mcas):
#     mca_dict = OrderedDict()
#     for mca in mcas:
#         attrStr = f"mca{mca:1d}"
#         mca_dict[attrStr] = (EpicsSignal, f"mca{mca:1d}.VAL", dict())
#
#     return mca_dict


class GeDetector(Device):
    ch = DDC(make_mcas(range(1, 33)))
    start = Cpt(EpicsSignal, "StartAll")

ge_detector = GeDetector("XF:08IDB-ES{GE-Det:1}", name="ge_detector")

from xas.process import load_apb_dataset_from_db
a = load_apb_dataset_from_db(db, -1)
plt.figure();
plt.plot(a[0]['timestamp'])


def get_processed_df_from_uid_for_epics_fly_scan(db, uid, save_interpolated_file=False, path_to_file=None,
                                                 comments=None, load_images=False, processing_kwargs=None):
    hdr = db[uid]
    stream_names = hdr.stream_names
    logger = get_logger()

    # if (hdr.start['spectrometer'] == 'johann'):
    #     load_images = True

    # try:
    # default detectors
    # apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
    # raw_dict = translate_apb_dataset(apb_df, energy_df, energy_offset)
    raw_dict = {}

    for stream_name in stream_names:
        if stream_name == 'apb_stream':
            apb_df = load_apb_dataset_only_from_db(db, uid)
            raw_dict = {**raw_dict, **translate_apb_only_dataset(apb_df)}

        elif (stream_name == 'pil100k_stream') or (stream_name == 'pil100k2_stream'):
            pil100k_stream_name = stream_name
            pil100k_name = stream_name.split('_')[0]
            apb_trigger_stream_name = f'apb_trigger_{pil100k_name}'
            logger.info(f'({ttime.ctime()}) Retrieving trigger data...')
            apb_trigger_pil100k_timestamps = load_apb_trig_dataset_from_db(db, uid, use_fall=True,
                                                                           stream_name=apb_trigger_stream_name)
            logger.info(f'({ttime.ctime()}) Trigger data received')
            logger.info(f'({ttime.ctime()}) Retrieving Pilatus data...')
            pil100k_dict = load_pil100k_dataset_from_db(db, uid, apb_trigger_pil100k_timestamps,
                                                        pil100k_stream_name=pil100k_stream_name,
                                                        load_images=load_images)
            logger.info(f'({ttime.ctime()}) Pilatus data received')
            raw_dict = {**raw_dict, **pil100k_dict}

        elif stream_name == 'xs_stream':
            apb_trigger_xs_timestamps = load_apb_trig_dataset_from_db(db, uid, stream_name='apb_trigger_xs')
            logger.info(f'({ttime.ctime()}) Retrieving SDD data...')
            xs3_dict = load_xs3_dataset_from_db(db, uid, apb_trigger_xs_timestamps)
            logger.info(f'({ttime.ctime()}) SDD data received')
            raw_dict = {**raw_dict, **xs3_dict}

        elif stream_name.endswith('monitor'):
            _stream_name = stream_name[:stream_name.index('monitor') - 1]
            logger.info(f'({ttime.ctime()}) Retrieving monitor data...')
            df = hdr.table(stream_name)
            logger.info(f'({ttime.ctime()}) Monitor data received')
            df['timestamp'] = (df.time.values - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')

            interpolator_func = interp1d(df['timestamp'].values, df[_stream_name].values, axis=0, kind='quadratic')
            fine_timestamp = np.linspace(df['timestamp'].min(), df['timestamp'].max(),
                                         int((df['timestamp'].max() - df['timestamp'].min()) * 500))
            motor_pos_fine = interpolator_func(fine_timestamp)

            monitor_dict = {_stream_name: pd.DataFrame({'timestamp': fine_timestamp,
                                                        _stream_name: motor_pos_fine})}
            raw_dict = {**raw_dict, **monitor_dict}

        # logger.info(f'({ttime.ctime()}) Loading file successful for UID {uid}')
    # except Exception as e:
    #     # logger.info(f'({ttime.ctime()}) Loading file failed for UID {uid}')
    #     raise e
    # try:
    return raw_dict
    interpolated_df = interpolate(raw_dict, sort=False)
    if save_interpolated_file:
        save_interpolated_df_as_file(path_to_file, interpolated_df, comments)
        # logger.info(f'({ttime.ctime()}) Interpolation successful for {uid}')
    # except Exception as e:
    #     # logger.info(f'({ttime.ctime()}) Interpolation failed for {uid}')
    #     raise e
    if 'spectrometer' in hdr.start:
        if 'roi_polygon' in hdr.start['detectors']['Pilatus 100k New']['config']:
            # if 'roi_polygon' in hdr.start['detectors']['Pilatus 100k']['config']:
            # johann_image_kwargs = filter_johann_image_kwargs(processing_kwargs)
            # if (hdr.start['spectrometer'] == 'johann') and (load_images):
            #     interpolated_df = reduce_johann_images(interpolated_df, hdr, **johann_image_kwargs)

            johann_calibration_kwargs = filter_johann_calibration_kwargs(processing_kwargs)
            if (hdr.start['spectrometer'] == 'johann') and (load_images):
                interpolated_df, energy_key = convert_roll_to_energy_for_johann_fly_scan(interpolated_df, hdr,
                                                                                         **johann_calibration_kwargs)
                # return interpolated_df
                if energy_key is not None:
                    interpolated_df = interpolate_df_emission_energies_on_common_grid(interpolated_df, hdr,
                                                                                      energy_key=energy_key)
                    step_size = 0.2  # eV
                    processed_df = bin_epics_fly_scan(interpolated_df, key_base='energy', step_size=step_size)
                    return processed_df
    # try:
    stream_name = hdr.start['motor_stream_names'][0]
    _stream_name = stream_name[:stream_name.index('monitor') - 1]
    if ('johann' in _stream_name) and (('roll' in _stream_name) or ('yaw' in _stream_name)):
        step_size = 5
    else:
        step_size = 0.1
    processed_df = bin_epics_fly_scan(interpolated_df, key_base=_stream_name, step_size=step_size)
    # (path, extension) = os.path.splitext(path_to_file)
    # path_to_file = path + '.dat'
    logger.info(f'({ttime.ctime()}) Binning successful')

    # if draw_func_interp is not None:
    #     draw_func_interp(interpolated_df)
    # if draw_func_bin is not None:
    #     draw_func_bin(processed_df, path_to_file)

    # except Exception as e:
    #     logger.info(f'({ttime.ctime()}) Binning failed')
    #     raise e

    return processed_df

    def clean_dict(raw_dict):
        clean_raw_dict = {}
        for key in raw_dict.keys():
            df = raw_dict[key]
            zero_idx = df[df['timestamp'] == 0].index.min()
            if zero_idx is None:
                clean_raw_dict[key] = df
            else:
                clean_raw_dict[key] = df.loc[:zero_idx - 1]
        return clean_raw_dict

    uid2 = 'f0dc13a9-e87b-448f-a875-dea91d54ab7b'

    a = get_processed_df_from_uid_for_epics_fly_scan(db, uid2)
    n = a['i0']['timestamp']
    plt.figure();
    plt.plot(n)





#processing of Ge detector data from XIA map


import numpy as np
import time
import sys
import os
import h5py
import matplotlib.pyplot as plt


def aslong(d):
    """unravels and converts array of int16 (int) to int32 (long)"""
    # need to unravel the array!!!
    d = d.astype(np.int16).ravel()
    d.dtype = np.int32
    return d


class xMAPBufferHeader(object):
    def __init__(self, buff):
        self.tag0 = buff[0]  # Tag word 0
        self.tag1 = buff[1]  # Tag word 1
        self.headerSize = buff[2]  # Buffer header size
        #  Mapping mode (1=Full spectrum, 2=Multiple ROI, 3=List mode)
        self.mappingMode = buff[3]
        self.runNumber = buff[4]  # Run number
        # Sequential buffer number, low word first
        self.bufferNumber = aslong(buff[5:7])[0]
        self.bufferID = buff[7]  # 0=A, 1=B
        self.numPixels = buff[8]  # Number of pixels in buffer
        # Starting pixel number, low word first
        self.startingPixel = aslong(buff[9:11])[0]
        self.moduleNumber = buff[11]
        self.channelID = np.array(buff[12:20]).reshape((4, 2))
        self.channelSize = buff[20:24]
        self.bufferErrors = buff[24]
        self.userDefined = buff[32:64]
        self.listMode = buff[64]
        self.wordsPerEvent = buff[65]
        self.totalEvents = aslong(buff[66:68])[0]
        self.specialRecords = aslong(buff[68:70])[0]

    def report(self):
        print(["{}={}".format(field, getattr(self, field)) for field in ['mappingMode',
                                                                         'runNumber', 'bufferNumber', 'bufferID',
                                                                         'numPixels',
                                                                         'startingPixel', 'moduleNumber', 'channelSize',
                                                                         'totalEvents']])


class xMAPMCAPixelHeader(object):
    def __init__(self, buff):
        self.tag0 = buff[0]
        self.tag1 = buff[1]
        self.headerSize = buff[2]
        # Mapping mode (1=Full spectrum, 2=Multiple ROI, 3=List mode)
        self.mappingMode = buff[3]
        self.pixelNumber = aslong(buff[4:6])[0]
        self.blockSize = aslong(buff[6:8])[0]
        self.channelSize = buff[10:13]


class xMAPData(object):
    def __init__(self, npix, nmod, nchan):
        ndet = 4 * nmod
        self.firstPixel = 0
        self.numPixels = 0
        self.counts = np.zeros((npix, ndet, nchan), dtype='i2')
        self.realTime = np.zeros((npix, ndet), dtype='i8')
        self.liveTime = np.zeros((npix, ndet), dtype='i8')
        self.inputCounts = np.zeros((npix, ndet), dtype='i4')
        self.outputCounts = np.zeros((npix, ndet), dtype='i4')


CLOCKTICK = 0.320  # xmap clocktick = 320 ns


def decode_xmap_buffers(array_data):
    # array_data will normally be 3d:
    #  shape = (narrays, nmodules, buffersize)
    # but nmodules and narrays could be 1, so that
    # array_data could be 1d or 2d.
    #
    # here we force the data to be 3d
    shape = array_data.shape
    if len(shape) == 1:
        array_data.shape = (1, 1, shape[0])
    elif len(shape) == 2:
        array_data.shape = (1, shape[0], shape[1])

    narrays, nmodules, buffersize = array_data.shape
    modpixs = int(max(124, array_data[0, 0, 8]))
    npix_total = 0
    # real / live times are returned in microseconds.
    for array in range(narrays):
        for module in range(nmodules):
            d = array_data[array, module, :]
            bh = xMAPBufferHeader(d)
            dat = d[256:].reshape(modpixs, int((d.size - 256) / modpixs))
            # converting buffer from flat to

            npix = bh.numPixels
            if module == 0:
                npix_total += npix
                if array == 0:
                    # first time through, (array,module)=(0,0) we
                    # read mapping mode, set up how to slice the
                    # data, and build data arrays in xmapdat
                    mapmode = dat[0, 3]
                    if mapmode == 1:  # mapping, full spectra
                        nchans = d[20]
                        data_slice = slice(256, 8448)
                    elif mapmode == 2:  # ROI mode
                        # Note:  nchans = number of ROIS !!
                        nchans = max(d[264:268])
                        data_slice = slice(64, 64 + 8 * nchans)
                    xmapdat = xMAPData(narrays * modpixs, nmodules, nchans)
                    print(narrays * modpixs, nmodules, nchans)
                    xmapdat.firstPixel = bh.startingPixel

            # acquisition times and i/o counts data are stored
            # as longs in locations 32:64
            t_times = aslong(dat[:npix, 32:64]).reshape(npix, 4, 4)
            mod_slice = slice(module * 4, module * 4 + 4)
            p1 = npix_total - npix
            p2 = npix_total
            xmapdat.realTime[p1:p2, mod_slice] = t_times[:, :, 0]
            xmapdat.liveTime[p1:p2, mod_slice] = t_times[:, :, 1]
            xmapdat.inputCounts[p1:p2, mod_slice] = t_times[:, :, 2]
            xmapdat.outputCounts[p1:p2, mod_slice] = t_times[:, :, 3]

            # the data, extracted as per data_slice and mapmode
            t_data = dat[:npix, data_slice]
            if mapmode == 2:
                t_data = aslong(t_data)
            xmapdat.counts[p1:p2, mod_slice, :] = t_data.reshape(npix, 4, nchans)

    xmapdat.numPixels = npix_total
    xmapdat.counts = xmapdat.counts[:npix_total]
    xmapdat.realTime = CLOCKTICK * xmapdat.realTime[:npix_total]
    xmapdat.liveTime = CLOCKTICK * xmapdat.liveTime[:npix_total]
    xmapdat.inputCounts = xmapdat.inputCounts[:npix_total]
    xmapdat.outputCounts = xmapdat.outputCounts[:npix_total]
    return xmapdat

#####################################################################
fname = '077c7dc4-70ef-4e60-8807_000000.h5'

folder_path = "/nsls2/data/iss/legacy/Sandbox/epics/raw/dxp/2025/02/11/"
f = h5py.File(folder_path + fname, 'r')
data = f['entry']['data']['data'][:]
a=decode_xmap_buffers(data)



path = '/nsls2/data/iss/legacy/Sandbox/epics/'
filename = 'mock2_003.h5'

f = h5py.File(path + filename, 'r')
data = f['entry']['data']['data']

array = decode_xmap_buffers(data).counts


import h5py
from matplotlib import pyplot as plt
#from decode_xmap_buffers import decode_xmap_buffers
import os


folder_path = "/nsls2/data/iss/legacy/Sandbox/epics/raw/dxp/2025/02/11/"

#folder_path = r"C:/nsls/test_006.h5"

#files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]


plt.figure()
for nn in range(20:25):
    d=b[:,nn,0]
    d=d-np.average(d[-10:])
    d=d/np.max(d)
    plt.plot(d, legend =  str(nn))
plt.legend()

files = ["4d5f0594-8243-44e4-bfbe_000000.h5"]

for fname in files:
#    fname = r"C:/nsls/test_006.h5"
    if not str(fname).endswith("h5"):
        continue
    print(folder_path + fname)
    f = h5py.File(folder_path + fname, 'r')
    data = f['entry']['data']['data'][:]
    decoded_data, mapmode = decode_xmap_buffers(data)
    print(decoded_data.counts.shape)
    print(f"{mapmode=}")


frames = 1
plt.figure()
for i in range(frames):
    for j in range(32):
        plt.plot(array[i][j])
plt.show()plt

# inclinometer values 2025-01-13
d = {'motor_det_th1': {'0': -27,
  '1': -24,
  '2': -21,
  '3': -18,
  '4': -15,
  '5': -12,
  '6': -9,
  '7': -6,
  '8': -3,
  '9': 0,
  '10': 3,
  '11': 6,
  '12': 9,
  '13': 12,
  '14': 15,
  '15': 18,
  '16': 21,
  '17': 24,
  '18': 27,
  '19': 30,
  '20': 33,
  '21': 36,
  '22': 39,
  '23': 42,
  '24': 45,
  '25': 48,
  '26': 51,
  '27': 54,
  '28': 57,
  '29': 60,
  '30': 63,
  '31': 66,
  '32': 69},
 'motor_det_inc1': {'0': 14667,
  '1': 14398,
  '2': 14133,
  '3': 13864,
  '4': 13594,
  '5': 13325,
  '6': 13056,
  '7': 12791,
  '8': 12522,
  '9': 12258,
  '10': 11994,
  '11': 11725,
  '12': 11455,
  '13': 11191,
  '14': 10922,
  '15': 10657,
  '16': 10389,
  '17': 10119,
  '18': 9855,
  '19': 9586,
  '20': 9317,
  '21': 9052,
  '22': 8788,
  '23': 8519,
  '24': 8255,
  '25': 7986,
  '26': 7721,
  '27': 7452,
  '28': 7188,
  '29': 6918,
  '30': 6649,
  '31': 6385,
  '32': 6116}}

d = {'motor_det_th1': {'0': -27,
  '1': -24,
  '2': -21,
  '3': -18,
  '4': -15,
  '5': -12,
  '6': -9,
  '7': -6,
  '8': -3,
  '9': 0,
  '10': 3,
  '11': 6,
  '12': 9,
  '13': 12,
  '14': 15,
  '15': 18,
  '16': 21,
  '17': 24,
  '18': 27,
  '19': 30,
  '20': 33,
  '21': 36,
  '22': 39,
  '23': 42,
  '24': 45,
  '25': 48,
  '26': 51,
  '27': 54,
  '28': 57,
  '29': 60,
  '30': 63,
  '31': 66,
  '32': 69},
 'motor_det_inc1': {'0': 14667,
  '1': 14402,
  '2': 14133,
  '3': 13869,
  '4': 13599,
  '5': 13330,
  '6': 13061,
  '7': 12791,
  '8': 12527,
  '9': 12253,
  '10': 11988,
  '11': 11720,
  '12': 11455,
  '13': 11186,
  '14': 10922,
  '15': 10652,
  '16': 10388,
  '17': 10119,
  '18': 9850,
  '19': 9581,
  '20': 9317,
  '21': 9039,
  '22': 8783,
  '23': 8519,
  '24': 8250,
  '25': 7986,
  '26': 7716,
  '27': 7453,
  '28': 7183,
  '29': 6914,
  '30': 6650,
  '31': 6381,
  '32': 6116}}



fpath = "/nsls2/data/iss/legacy/xf08id/settings/json/"

with open(fpath + 'test.json', 'w') as f:
    json.dump(d, f)




2025-06-17

d = {'motor_det_th1': {'0': -27,
  '1': -24,
  '2': -21,
  '3': -18,
  '4': -15,
  '5': -12,
  '6': -9,
  '7': -6,
  '8': -3,
  '9': 0,
  '10': 3,
  '11': 6,
  '12': 9,
  '13': 12,
  '14': 15,
  '15': 18,
  '16': 21,
  '17': 24,
  '18': 27,
  '19': 30,
  '20': 33,
  '21': 36,
  '22': 39,
  '23': 42,
  '24': 45,
  '25': 48,
  '26': 51,
  '27': 54,
  '28': 57,
  '29': 60,
  '30': 63,
  '31': 66,
  '32': 69},
 'motor_det_inc1': {'0': 14668,
  '1': 14403,
  '2': 14134,
  '3': 13870,
  '4': 13600,
  '5': 13330,
  '6': 13061,
  '7': 12792,
  '8': 12527,
  '9': 12229,
  '10': 11988,
  '11': 11720,
  '12': 11455,
  '13': 11186,
  '14': 10922,
  '15': 10652,
  '16': 10388,
  '17': 10119,
  '18': 9850,
  '19': 9581,
  '20': 9317,
  '21': 9039,
  '22': 8783,
  '23': 8519,
  '24': 8250,
  '25': 7986,
  '26': 7716,
  '27': 7453,
  '28': 7183,
  '29': 6914,
  '30': 6650,
  '31': 6381,
  '32': 6116}}




    theta = 80
    R = 500
    _th = np.deg2rad(theta)
    crystal_x = R/np.sin(_th)
    detector_y = 2 * R * np.cos(_th)
    detector_x = 2 * R * np.cos(_th) * np.cos(_th) / np.sin(_th)

    print(f'Crystal at distance {crystal_x =} mm')
    print(f'Detector at distance {detector_x = } mm')
    print(f'Detector at height {detector_y = } mm')

    import matplotlib.pyplot as plt

    circle1 = plt.Circle((0, 0), 7, color='r')
    circle2 = plt.Circle((-crystal_x,0), 7, color='blue')
    circle3 = plt.Circle((-detector_x, detector_y), 7, color='g', clip_on=False)

    fig, ax = plt.subplots()  # note we must use plt.subplots, not plt.subplot
    ax.set_xlim(-750,10)
    ax.set_ylim(-10, 750)
    ax.set_aspect('equal', adjustable='box')

    # (or if you have an existing figure)
    # fig = plt.gcf()
    # ax = fig.gca()

    ax.add_patch(circle1)
    ax.add_patch(circle2)
    ax.add_patch(circle3)


    circle1 = plt.Circle((0, 0), 7, color='r')
    circle2 = plt.Circle((-508,0), 7, color='blue')
    circle3 = plt.Circle((-34, 184), 7, color='g', clip_on=False)

    fig, ax = plt.subplots()  # note we must use plt.subplots, not plt.subplot
    ax.set_xlim(-750,10)
    ax.set_ylim(-10, 750)
    ax.set_aspect('equal', adjustable='box')

    # (or if you have an existing figure)
    # fig = plt.gcf()
    # ax = fig.gca()

    ax.add_patch(circle1)
    ax.add_patch(circle2)
    ax.add_patch(circle3)

pseudo_dict = {'det_pitch':10.61 , 'det_x': 34.52, 'det_y': 10.6144}



a = 337.38 #mm
b = 302.50 #mm
c = 234.55 #mm

alpha = 42.55 - theta

def calculate_arc(theta):
    a = 337.38  # mm
    b = 302.50  # mm
    c = 234.55  # mm
    alpha = 42.55 - theta
    return  c - np.sqrt(a**2 + b**2 - 2*a*b*np.cos(np.deg2rad(alpha)))


{'motor_det_x': 164.8610169497468,
 'motor_det_th1': 32.604633125382826,
 'motor_det_th2': -53.80463312538281}



def get_energy_offset(uid, db,  dE=25, plot_fun=None, attempts=20, sleep_time=2, full_return=False):
    print('running get_energy_offset')
    start = db[uid].start
    fname_raw = start['interp_filename']
    if fname_raw.endswith('.raw'):
        fname_bin = fname_raw[:-4] + '.dat'



    df, file_hdr = load_binned_df_from_file(fname_bin)
    scan_uid = [line for i, line in enumerate(file_hdr.split('\n# ')) if line.startswith('Scan.uid')][0].split(': ')[1]
    print(f"Computing energy shift for {os.path.split(fname_bin)[1]} (uid: '{scan_uid}')")
                # print('bla')

    try:
        energy = df['energy'].values
        _mu = -np.log(df['ir'] / df['it']).values
        ds = XASDataSet(mu=_mu, energy=energy)
        mu = ds.flat

        element = start['element']
        edge = start['edge']
        e0 = float(start['e0'])

        # energy_ref, mu_ref = db_proc.foil_spectrum(element, edge) ## unsorted array of energy and mu
        #
        # _foil_spectrum_tuple = db_proc.foil_spectrum(element, edge)
        # _dataframe_foil = pd.DataFrame(np.column_stack(_foil_spectrum_tuple))
        # _dataframe_foil = _dataframe_foil.sort_values(0)
        #
        # energy_ref = np.array(_dataframe_foil[0])
        # mu_ref = np.array(_dataframe_foil[1])

        _energy_ref, _mu_ref = get_foil_spectrum(element, edge)
        energy_ref = np.array(_energy_ref)
        mu_ref = np.array(_mu_ref)
        mask = (energy_ref >= (e0 - dE)) & (energy_ref <= (e0 + dE))

        energy_shift_coarse = energy_ref[np.argmin(np.abs(mu_ref - 0.5))] - energy[np.argmin(np.abs(mu - 0.5))]
        energy += energy_shift_coarse
        energy_ref_roi = energy_ref[mask]
        mu_ref_roi = mu_ref[mask]
        shift, mu_fit = compute_shift_between_spectra(energy, mu, energy_ref_roi, mu_ref_roi)
        e_cor = e0 + shift - energy_shift_coarse
        if plot_fun is not None:
            # mu = np.interp(energy_ref_roi, energy, mu)
            plot_fun(energy_ref_roi, mu_ref_roi, mu_fit)

    except Exception as e:
        print(f'[Energy Calibration] Error: {e}')
        e0, e_cor, energy_ref_roi, mu_ref_roi, mu_fit = None, None, None, None, None

    if full_return:
        return e0, e_cor, energy_ref_roi, mu_ref_roi, mu_fit
    else:
        return e0, e_cor




def get_attenuation_value(thickness:int  = 0, **kwargs):
    # Adding reference foil element list
    with open(f'{ROOT_PATH_SHARED}/settings/json/attenuator.json') as fp:
        attenuators_list = json.load(fp)

    current_attenuator_position = int(attenuator_motor.pos.user_readback.get())
    positions_list = [item['position'] for item in attenuators_list]
    attenuation_str_list = [item['position'] for item in attenuators_list]

    if position in positions_list:
        indx = thickness_str_list.index(thickness_str)
        yield from mv(attenuator_motor.pos, attenuators_list[indx]['position'])
    else:
        yield from mv(attenuator_motor.pos, 0)




 'xia_ch1_roi0': 'ge_detector_channels_mca1_R0'='ge_detector_channels_mca1_R0',
 'xia_ch2_roi0': 'ge_detector_channels_mca2_R0',
 'xia_ch3_roi0': 'ge_detector_channels_mca3_R0',
 'xia_ch4_roi0': 'ge_detector_channels_mca4_R0',
 'xia_ch5_roi0': 'ge_detector_channels_mca5_R0',
 'xia_ch6_roi0': 'ge_detector_channels_mca6_R0',
 'xia_ch7_roi0': 'ge_detector_channels_mca7_R0',
 'xia_ch8_roi0': 'ge_detector_channels_mca8_R0',
 'xia_ch9_roi0': 'ge_detector_channels_mca9_R0',
 'xia_ch10_roi0': 'ge_detector_channels_mca10_R0',
 'xia_ch11_roi0': 'ge_detector_channels_mca11_R0',
 'xia_ch12_roi0': 'ge_detector_channels_mca12_R0',
 'xia_ch13_roi0': 'ge_detector_channels_mca13_R0',
 'xia_ch14_roi0': 'ge_detector_channels_mca14_R0',
 'xia_ch15_roi0': 'ge_detector_channels_mca15_R0',
 'xia_ch16_roi0': 'ge_detector_channels_mca16_R0',
 'xia_ch17_roi0': 'ge_detector_channels_mca17_R0',
 'xia_ch18_roi0': 'ge_detector_channels_mca18_R0',
 'xia_ch19_roi0': 'ge_detector_channels_mca19_R0',
 'xia_ch20_roi0': 'ge_detector_channels_mca20_R0',
 'xia_ch21_roi0': 'ge_detector_channels_mca21_R0',
 'xia_ch22_roi0': 'ge_detector_channels_mca22_R0',
 'xia_ch23_roi0': 'ge_detector_channels_mca23_R0',
 'xia_ch24_roi0': 'ge_detector_channels_mca24_R0',
 'xia_ch25_roi0': 'ge_detector_channels_mca25_R0',
 'xia_ch26_roi0': 'ge_detector_channels_mca26_R0',
 'xia_ch27_roi0': 'ge_detector_channels_mca27_R0',
 'xia_ch28_roi0': 'ge_detector_channels_mca28_R0',
 'xia_ch29_roi0': 'ge_detector_channels_mca29_R0',
 'xia_ch30_roi0': 'ge_detector_channels_mca30_R0',
 'xia_ch31_roi0': 'ge_detector_channels_mca31_R0',
 'xia_ch32_roi0': 'ge_detector_channels_mca32_R0'}


'ge_detector_channels_mca1_val',
 'ge_detector_channels_mca1_R0low',
 'ge_detector_channels_mca1_R0high',
 'ge_detector_channels_mca1_R0',
 'ge_detector_channels_mca1_R0nm',
 'ge_detector_channels_mca2_val',
 'ge_detector_channels_mca2_R0low',
 'ge_detector_channels_mca2_R0high',
 'ge_detector_channels_mca2_R0',
 'ge_detector_channels_mca2_R0nm',
 'ge_detector_channels_mca3_val',
 'ge_detector_channels_mca3_R0low',
 'ge_detector_channels_mca3_R0high',
 'ge_detector_channels_mca3_R0',
 'ge_detector_channels_mca3_R0nm',
 'ge_detector_channels_mca4_val',
 'ge_detector_channels_mca4_R0low',



bragg = 80
def calc(bragg):
    h = 550* np.sin(np.deg2rad(69))
    R=500
    L1=550
    L2=91

    Xc = R/np.cos(np.deg2rad(90-bragg))
    Yc = 0
    y = R*np.sin(np.deg2rad(90-bragg))
    c = R/np.tan(np.deg2rad(bragg))
    Xd = 2 * c * np.cos(np.deg2rad(bragg))
    Yd = 2 * c * np.sin(np.deg2rad(bragg))

    Xj = Xd-L2*np.cos(np.deg2rad(90-bragg))
    Yj = Yd+L2*np.sin(np.deg2rad(90-bragg))


    theta1 = (np.arcsin((h-Yd)/L1))

    Xg = Xj+L1*np.cos(theta1)
    Yg = h

    plt.figure();
    plt.plot(0,0,'or');
    plt.plot(F,0,'xr');
    plt.plot(Xc,Yc,'xb');
    plt.plot(Xd,Yd,'ob');
    plt.plot(Xj,Yj,'ob');
    plt.plot(Xg,Yg,'ob');
    plt.plot([0,Xc ],[0,Yc], 'b:')
    plt.plot([Xd,Xc ],[Yd,Yc], 'b:')
    plt.plot([Xd,0 ],[Yd,0], 'b:')
    plt.plot([Xd,Xj ],[Yd,Yj], 'b')
    plt.plot([Xg,Xj ],[Yg,Yj], 'b')
    plt.plot([0, 500], [h,h], 'b:')


    plt.axis('equal')

channels = np.array([ 1,  2,  3,  5,  7,  8,  9, 10, 11, 12, 13, 14, 15, 16, 17,
       18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31])
def process_ge_detctor_data(uid):
    t = db[uid].table()

    length = len(t['time'])
    array = np.zeros(length)
    for channel in channels:
        pass


energy = [8020, 8030, 8050, 8070]
pixel = [338, 293, 217, 139]

from scipy.interpolate import interp1d

interp1d(
    x,
    y,
    kind='linear',
    axis=-1,
    copy=True,
    bounds_error=None,
    fill_value=nan,
    assume_sorted=False,
)

spectra = []
uids = []
images = []
horz_cuts = []
def perform_crystal_x_scan(range=2, acq_time=1,step = 0.2):
    current_cr_x = vonhamos_motors.assm_x.user_readback.get()
    cr_x_array = np.arange(current_cr_x - range/2, (current_cr_x + range/2) + 0.1, step)


    for cr_x in cr_x_array:
        yield from bps.mv(vonhamos_motors.assm_x, cr_x)
        uid = (yield from pil2_count(acq_time=acq_time))
        uids.append(uid)
        _img=pil100k2.image.array_data.get()
        _img = _img.reshape(195,487)
        images.append(_img)
        roi = _img[80:100,150:380]
        horz_cuts.append(np.average(roi, axis=1))
        spectra.append(np.average(roi, axis=0))
    yield from bps.mv(vonhamos_motors.assm_x,  current_cr_x)
    return uids, spectra, horz_cuts,images


spectra = []
uids = []
images = []
horz_cuts = []
pos_array = np.array()
def perform_crystal_yaw_scan(range=6, acq_time=1,step = 0.5):
    motor = vonhamos_motors.arc
    current_pos = motor.user_readback.get()
    pos_array = np.arange(current_pos - range/2, (current_pos + range/2) + 0.1, step)


    for pos in pos_array:
        yield from bps.mv(motor, pos)
        uid = (yield from pil2_count(acq_time=acq_time))
        uids.append(uid)
        _img=pil100k2.image.array_data.get()
        _img = _img.reshape(195,487)
        images.append(_img)
        roi = _img[80:100,150:380]
        horz_cuts.append(np.average(roi, axis=1))
        spectra.append(np.average(roi, axis=0))
    yield from bps.mv(motor,  current_pos)
    return uids, spectra, horz_cuts,images






    def compute_arc_motion(self, bragg=90):
        a = 337.38  # mm
        b = 302.50  # mm
        c = 234.55  # mm
        alpha = 42.55 - bragg
        return c - np.sqrt(a ** 2 + b ** 2 - 2 * a * b * np.cos(np.deg2rad(alpha)))

    #79.38



from lmfit.models import GaussianModel as gauss
from lmfit.models import LorentzianModel as lorenz
def fit_gauss_normalize_center(x, y, no_of_points=10):
    dat = y - np.sum(y[:no_of_points])/no_of_points
    pars = gauss().guess(data=dat, x=x)
    out = gauss().fit(dat, pars, x=x)
    return x-out.params.valuesdict()['center'], dat/out.params.valuesdict()['height'], out.best_fit/out.params.valuesdict()['height'], out

def fit_lorent_normalize_center(x, y, no_of_points=10):
    dat = y - np.sum(y[:no_of_points])/no_of_points
    pars = lorenz().guess(data=dat, x=x)
    out = lorenz().fit(dat, pars, x=x)
    return x-out.params.valuesdict()['center'], dat/out.params.valuesdict()['height'], out.best_fit/out.params.valuesdict()['height'], out



plt.figure()
fwhms = []
for i, spec in enumerate(spectra):
    a = np.arange(len(spec))
    x, y,z, t = fit_lorent_normalize_center(a, spec)
    plt.plot(x,y+i)
    plt.plot(x,z+i)
    fwhms.append(t.values['fwhm']*0.25)


plt.figure()
fwhms = []
for i, spec in enumerate(horz_cuts):
    a = np.arange(0, len(spec))
    x, y,z, t = fit_gauss_normalize_center(a, spec)
    plt.plot(x,y+i)
    plt.plot(x,z+i)
    fwhms.append(t.values['fwhm']*0.25)

16-6690-4e10-aae0-bfa9aa7f668b''4b150416-6690-4e10-aae0-bfa9aa7f668b'

spectra = []
horz_cuts = []
for image in images:
    roi = image[80:100,190:270]
    horz_cuts.append(np.average(roi, axis=1))
    spectra.append(np.average(roi, axis=0))




spectra = []
uids = []
images = []
horz_cuts = []
pos_array = []
def perform_crystal_roll_scan(range=20, acq_time=1,step = 0.5):
    motor = vonhamos_motors.crystal_pitch
    current_pos = motor.user_readback.get()
    pos_array = np.arange(current_pos - range/2, (current_pos + range/2) + 0.1, step)

    for pos in pos_array:
        yield from bps.mv(motor, pos)
        uid = (yield from pil2_count(acq_time=acq_time))
        uids.append(uid)
        _img=pil100k2.image.array_data.get()
        _img = _img.reshape(195,487)
        images.append(_img)
        roi = _img[80:100,150:380]
        horz_cuts.append(np.average(roi, axis=1))
        spectra.append(np.average(roi, axis=0))
    yield from bps.mv(motor,  current_pos)
    return uids, spectra, horz_cuts,images



images = []
def perform_crystal_roll_scan_stupid(range=10, step = 0.5):
    motor = vonhamos_motors.crystal_pitch
    current_pos = motor.user_readback.get()
    pos_array = np.arange(current_pos - range/2, (current_pos + range/2) + 0.1, step)

    for pos in pos_array:
        motor.set(pos)
        ttime.sleep(0.5)
        _img=pil100k2.image.array_data.get()
        images.append(_img)
        ttime.sleep(0.5)
    motor.set(current_pos)

spectra = []
horz_cuts = []
for image in images:
    image = image.reshape(195,487)
    roi = image[90:110,140:380]
    horz_cuts.append(np.average(roi, axis=1))
    spectra.append(np.average(roi, axis=0))

plt.figure()
for i, spec in enumerate(spectra):
    plt.plot(spec, label = str(i))

plt.legend()


plt.figure()



spectra_array = spectra[0:10]
length = len(spectra_array)

for i, spec, pos in zip(np.arange(10), spectra[:10], pos_array[:10]):
    plt.plot(spec, label = f"{pos:.2f}")
plt.legend()

folder_path = "/nsls2/data/iss/legacy/Sandbox/epics/raw/dxp/2025/02/12/"

import glob
import os

list_of_files = glob.glob(folder_path+ '/*') # * means all if need specific format then *.csv
latest_file = max(list_of_files, key=os.path.getctime)
print(latest_file)
fname = latest_file.split('/')[-1]
f = h5py.File(folder_path + fname, 'r')
data = f['entry']['data']['data'][:]
a=decode_xmap_buffers(data)
b=a.counts
c=b[:,:,0]
plt.figure()
for ii in range(32):
    plt.plot(c[:,ii]-np.average(c[-10:,ii]))



ge_flyscan_uid = 'b441983c-f26b-47a9-a332-c938af5bd928'




def load_xia_dataset_from_db(db, uid, apb_trig_timestamps):
    hdr = db[uid]
    t = hdr.table(stream_name='ge_detector_stream', fill=True)
    # n_spectra = t.size
    n_spectra = min(t['ge_detector_channels_mca1_R0'][1].size, apb_trig_timestamps.size)
    xs_timestamps = apb_trig_timestamps[:n_spectra]
    # chan_roi_names = [f'CHAN{c}ROI{r}' for c, r in product([1, 2, 3, 4], [1, 2, 3, 4])]
    chan_roi_names = [f'ge_detector_channels_mca{i}_R0' for i in range(1,33)]
    # chan_roi_names = [f'xs_ch{c:02d}_roi{r:02d}' for r, c in product([1, 2, 3, 4], [1, 2, 3, 4])]
    spectra = {}

    for j, chan_roi in enumerate(chan_roi_names):
        # this_spectrum = np.zeros(n_spectra)
        this_spectrum = t[chan_roi][1][:n_spectra]/100000
        # for i in range(n_spectra):
        # this_spectrum[i] = t[i+1][chan_roi]
        # this_spectrum[i] = t[chan_roi][i + 1]

        spectra[chan_roi] = pd.DataFrame(np.vstack((xs_timestamps, this_spectrum)).T,
                                         columns=['timestamp', chan_roi])

    return spectra



### calib scan for 10 energy points
####

from scipy.ndimage import rotate

uid = '283c2f60-46b5-47bd-bd23-36e6dc2fbedd'

uid = '5211435a-7751-44de-885b-a2de32c1d33a'
hdr = db[uid]
t = hdr.table(fill=True)
from scipy.ndimage import rotate
image_stack = []
for img in t['pil100k2_image'][:]:
    rot = rotate(img[0][77:95, :], angle=-1.2, order=3)
    image_stack.append(rot)
image_stack = np.array(image_stack)

def run_calibration_on_slice(uid, slice_array=[100, 200, 0, 300], slice=False):
    hdr = db[uid]
    t = hdr.table(fill=True)




rotation = rotate(image_stack, angle=-0.5)

image = t['pil100k2_image'][1:].sum(axis=0)[0]

from xas.process import get_processed_df_from_uid, process_interpolate_bin
uid = 'ed806cad-9d61-4bbe-b1ba-06c885fc0e87'

hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db, load_images=True)

hdr = db[uid]
doc = hdr.stop

process_interpolate_bin(doc, db, load_images=True, dump_to_tiff=True)

from xas.process import process_interpolate_bin
def create_tiff_images(last_few_scans=10):
    for scan in range(1, last_few_scans+1, 1):
        hdr = db[-scan]
        doc = hdr.stop
        try:
            process_interpolate_bin(doc, db, load_images=True, dump_to_tiff=True)
        except:
            pass



from xas.process import get_processed_df_from_uid, process_interpolate_bin


hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db, load_images=True)
pil_images =  extended_data['pil100k2_image']

specs = []
energy = primary_df['energy']
for image in pil_images:
    specs.append(np.average(image[70:100, 200:500], axis=0))
Y =  energy
X = np.array(range(len(specs[0])))
Z= np.array(specs)
X_mesh, Y_mesh = np.meshgrid(X, Y)

plt.figure(figsize=(8, 6))
contour = plt.contourf(X_mesh, Y_mesh, Z, cmap='viridis')
plt.colorbar(contour, label='Values')
plt.xlabel('X Coordinate')
plt.ylabel('Incident energy')
plt.title('Contour Plot from Excel Data')
plt.show()


x = xview_gui.widget_data

from xas.file_io import load_binned_df_from_file
from xas.process import process_interpolate_bin
uids = []
for item in x.list_data.selectedItems():
    fname = os.path.join(x.working_folder, item.text())
    df, header = load_binned_df_from_file(fname)
    print(fname, df.shape)
    uid_idx1 = header.find('Scan.uid:') + 10
    uid_idx2 = header.find('\n', header.find('Scan.uid:'))
    uid = header[uid_idx1: uid_idx2]
    uids.append(uid)

def create_tiff_images(uids):
    for uid in uids:
        hdr = db[uid]
        doc = hdr.stop
        process_interpolate_bin(doc, db, load_images=True, dump_to_tiff=True, cloud_dispatcher=True)


create_tiff_images(uids)


uid = 'bb4b2fd0-70c2-416d-8fde-2af9954b0948'

def process_rixs_images(uids, calib_pixel=None, calib_energy=None):
    rixs = []
    energy = []
    for uid in uids:
        hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db, load_images=True)
        energy.append(primary_df['energy'])

        xes = []
        for img in extended_data['pil100k2_image']:
            xes.append(img[77:95,  :].sum(axis=0))

        rixs.append(np.array(xes))

    energy = np.array(energy)
    rixs = np.array(rixs)

    return energy, rixs, calib_pixel, calib_energy



ENERGY, RIXS, CALIB_PIXEL, CALIB_ENERGY = process_rixs_images(uids, calib_pixel=pix, calib_energy=energy)


import threading
import time

results_rixs = []
results_energy = []
lock = threading.Lock()


def worker(thread_id, uid):
    hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db,
                                                                                                             load_images=True)

    xes = []
    for img in extended_data['pil100k2_image']:
        xes.append(img[77:95, :].sum(axis=0))

    with lock:
        results_rixs.append(np.array(xes))
        results_energy.append(np.array(primary_df['energy']))


threads = []
start = time.time()
for i, uid in enumerate(uids):
    thread = threading.Thread(target=worker, args=(i, uid))
    threads.append(thread)
    thread.start()

for thread in threads:
    thread.join()

end = time.time()
print(f"Total time is {end-start}s")

print("Finished")

####################multiprocessing


import multiprocessing
import time


def worker(thread_id, uid, results_rixs, results_energy):
    hdr = db[uid]
    t = hdr.table(stream_name='pil100k2_stream', fill=True)
    # hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db, load_images=True)

    # xes = []
    # for img in extended_data['pil100k2_image']:
    #     xes.append(img[77:95, :].sum(axis=0))

    xes = []
    for img in t['pil100k2_image'][1]:
        xes.append(img[77:95, :].sum(axis=0))

    results_rixs.append(np.array(xes))
    # results_energy.append(np.array(primary_df['energy']))


if __name__ == "__main__":
    manager = multiprocessing.Manager()
    results_rixs = manager.list()
    results_energy = manager.list()
    processes = []

    start = time.time()
    for i, uid in enumerate(uids[:5]):
        process = multiprocessing.Process(target=worker, args=(i, uid, results_rixs, results_energy))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    end = time.time()
    print(f"Total time is {end-start}s")

    print("Finished")



start = time.time()
for uid in uids[20:25]:
    hdr = db[uid]
    t = hdr.table(stream_name='pil100k2_stream', fill=True)
end = time.time()
print(f"Total time is {end-start}s")




start = ttime.time()
hdr = db['06f76dde-c1dc-43e1-874e-d2043aff53de']
uid = hdr.start['uid']
from xas.file_io import (load_dataset_from_files, create_file_header, validate_file_exists, validate_path_exists,
                      save_interpolated_df_as_file, save_binned_df_as_file, find_e0, save_stepscan_as_file,
                      stepscan_remove_offsets, stepscan_normalize_xs, stepscan_normalize_xia,combine_xspress3_channels, combine_pil100k_channels,
                      combine_xia_channels,
                      filter_df_by_valid_keys, save_primary_df_as_file, save_extended_data_as_file, dump_tiff_images)
from xas.db_io import load_apb_dataset_from_db, translate_apb_dataset, load_apb_trig_dataset_from_db, load_xs3_dataset_from_db, load_pil100k_dataset_from_db, load_apb_dataset_only_from_db, translate_apb_only_dataset, load_xia_dataset_from_db
apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
raw_dict = translate_apb_dataset(apb_df, energy_df, energy_offset)
raw_dict
apb_trigger_pil100k_timestamps = load_apb_trig_dataset_from_db(db, uid, use_fall=True,
                                                                                   stream_name='apb_trigger_pil100k2')
pil100k_dict = load_pil100k_dataset_from_db(db, uid, apb_trigger_pil100k_timestamps,
                                                                pil100k_stream_name='pil100k2_stream',
                                                                load_images=True)
raw_dict = {**raw_dict, **pil100k_dict}
raw_dict
raw_dict.keys()
interpolated_dataset = {}
dataset = raw_dict
min_timestamp = max([dataset.get(key).iloc[0, 0] for key in dataset])
max_timestamp = min([dataset.get(key).iloc[len(dataset.get(key)) - 1, 0] for key in
                         dataset if len(dataset.get(key).iloc[:, 0]) > 5])
key_base = None
if key_base is None:
    all_keys = []
    time_step = []
    for key in dataset.keys():
        all_keys.append(key)
        # time_step.append(np.mean(np.diff(dataset[key].timestamp)))
        time_step.append(np.median(np.diff(dataset[key].timestamp)))
    key_base = all_keys[np.argmax(time_step)]
timestamps = dataset[key_base].iloc[:,0]

condition = timestamps < min_timestamp
timestamps = timestamps[np.sum(condition):]

condition = timestamps > max_timestamp
timestamps = timestamps[: (len(timestamps) - np.sum(condition) - 1)]

interpolated_dataset['timestamp'] = timestamps.values
timestamps = dataset[key_base].iloc[:,0]
condition = timestamps < min_timestamp
timestamps = timestamps[np.sum(condition):]
condition = timestamps > max_timestamp
timestamps = timestamps[: (len(timestamps) - np.sum(condition) - 1)]
interpolated_dataset['timestamp'] = timestamps.values
key = 'pil100k2_image'
time = dataset.get(key).iloc[:, 0].values
val = dataset.get(key).iloc[:, 1].values
if len(dataset.get(key).iloc[:, 0]) > 5 * len(timestamps):
    time = [time[0]] + [np.mean(array) for array in np.array_split(time[1:-1], len(timestamps))] + [time[-1]]
    val = [val[0]] + [np.mean(array) for array in np.array_split(val[1:-1], len(timestamps))] + [val[-1]]

end = ttime.time()
print(f'Total duration {end-start}')


start = ttime.time()
val_interp = interpolator_func(timestamps)
end = ttime.time()
print(f'Total duration {end-start}')


for j in range(len(s)):
    s[j] = s[j].astype(np.int16)


b_interp = np.ndarray((len(timestamps), b.shape[1],b.shape[2]))
start = ttime.time()
for ii in range(195):
    for jj in range(487):
        b_interp[:, ii,jj] = np.interp(timestamps, time.astype(np.float64), b[:,ii, jj])
end = ttime.time()
print(f'Total duration {end-start}')

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
import time as ttime


def interpolate_gpt(dataset, key_base=None, sort=True):


    # Compute min and max timestamps more efficiently
    min_timestamp = max(dataset[key].iloc[0, 0] for key in dataset)
    max_timestamp = min(dataset[key].iloc[-1, 0] for key in dataset if len(dataset[key]) > 5)

    # Determine key_base based on the max median time step
    if key_base is None:
        key_base = max(dataset, key=lambda k: np.median(np.diff(dataset[k].iloc[:, 0])))

    timestamps = dataset[key_base].iloc[:, 0].values
    timestamps = timestamps[(timestamps >= min_timestamp) & (timestamps <= max_timestamp)]

    interpolated_dataset = {'timestamp': timestamps}

    for key, data in dataset.items():
        print(f'({ttime.ctime()} Interpolating stream {key}...')
        #logger.info(f'({ttime.ctime()}) Interpolating stream {key}...')

        time = data.iloc[:, 0].values
        val = data.iloc[:, 1].values

        if len(time) > 5 * len(timestamps):
            time = [time[0]] + [np.mean(array) for array in np.array_split(time[1:-1], len(timestamps))] + [time[-1]]
            val = [val[0]] + [np.mean(array) for array in np.array_split(val[1:-1], len(timestamps))] + [val[-1]]

        interpolator_func = interp1d(time, val, axis=0, assume_sorted=True, bounds_error=False,
                                     fill_value="extrapolate")
        interpolated_dataset[key] = interpolator_func(timestamps)
        print(f'{ttime.ctime()} Interpolation of stream {key} is complete')
        #logger.info(f'({ttime.ctime()}) Interpolation of stream {key} is complete')

    interpolated_dataframe = pd.DataFrame(interpolated_dataset)

    return interpolated_dataframe.sort_values('energy') if sort else interpolated_dataframe



start = ttime.time()
interpolator_func(timestamps)
print(f"total time {ttime.time()-start}")

#___________________________________________________________________________________________
def interpolate(dataset, key_base = None, sort=True):
    #logger = get_logger()

    interpolated_dataset = {}
    min_timestamp = max([dataset.get(key).iloc[0, 0] for key in dataset])
    max_timestamp = min([dataset.get(key).iloc[len(dataset.get(key)) - 1, 0] for key in
                         dataset if len(dataset.get(key).iloc[:, 0]) > 5])
    if key_base is None:
        all_keys = []
        time_step = []
        for key in dataset.keys():
            all_keys.append(key)
            # time_step.append(np.mean(np.diff(dataset[key].timestamp)))
            time_step.append(np.median(np.diff(dataset[key].timestamp)))
        key_base = all_keys[np.argmax(time_step)]
    timestamps = dataset[key_base].iloc[:,0]

    condition = timestamps < min_timestamp
    timestamps = timestamps[np.sum(condition):]

    condition = timestamps > max_timestamp
    timestamps = timestamps[: (len(timestamps) - np.sum(condition) - 1)]

    interpolated_dataset['timestamp'] = timestamps.values

    for key in dataset.keys():
        print(f'Interpolating stream {key}...')
        #logger.info(f'({ttime.ctime()}) Interpolating stream {key}...')

        time = dataset.get(key).iloc[:, 0].values
        val = dataset.get(key).iloc[:, 1].values
        if len(dataset.get(key).iloc[:, 0]) > 5 * len(timestamps):
            time = [time[0]] + [np.mean(array) for array in np.array_split(time[1:-1], len(timestamps))] + [time[-1]]
            val = [val[0]] + [np.mean(array) for array in np.array_split(val[1:-1], len(timestamps))] + [val[-1]]
            # interpolated_dataset[key] = np.array([timestamps, np.interp(timestamps, time, val)]).transpose()

        # interpolated_dataset[key] = np.array([timestamps, np.interp(timestamps, time, val)]).transpose()
        interpolator_func = interp1d(time, np.array([v for v in val]), axis=0)
        if key != 'pil100k2_image':
            val_interp = interpolator_func(timestamps)

        else:
            print(val.shape)
            print(val[0].shape)
            reshaped_val = np.stack(val, axis=0)  # Shape: (x, y, z)
            print(reshaped_val.shape)
            interpolator = interp1d(time, reshaped_val, kind='linear', axis=0, fill_value='extrapolate',
                                    assume_sorted=True)

            # Interpolate for new timestamps
            interpolated_images = interpolator(timestamps)
            val_interp = np.array(np.split(interpolated_images, interpolated_images.shape[0], axis=0), dtype=object).squeeze()
            print(val_interp.shape)
            print(val_interp[0].shape)
        if len(val_interp.shape) == 1:
            interpolated_dataset[key] = val_interp
        else:
            interpolated_dataset[key] = [v for v in val_interp]
        print(f'Interpolation of stream {key} is complete')
        #logger.info(f'({ttime.ctime()}) Interpolation of stream {key} is complete')

    intepolated_dataframe = pd.DataFrame(interpolated_dataset)
    if sort:
        return intepolated_dataframe.sort_values('energy')
    else:
        return intepolated_dataframe


def interpolate_with_interp(dataset, key_base=None, sort=True):
    # logger = get_logger()

    interpolated_dataset = {}
    min_timestamp = max([dataset.get(key).iloc[0, 0] for key in dataset])
    max_timestamp = min([dataset.get(key).iloc[len(dataset.get(key)) - 1, 0] for key in
                         dataset if len(dataset.get(key).iloc[:, 0]) > 5])
    if key_base is None:
        all_keys = []
        time_step = []
        for key in dataset.keys():
            all_keys.append(key)
            # time_step.append(np.mean(np.diff(dataset[key].timestamp)))
            time_step.append(np.median(np.diff(dataset[key].timestamp)))
        key_base = all_keys[np.argmax(time_step)]
    timestamps = dataset[key_base].iloc[:, 0]

    condition = timestamps < min_timestamp
    timestamps = timestamps[np.sum(condition):]

    condition = timestamps > max_timestamp
    timestamps = timestamps[: (len(timestamps) - np.sum(condition) - 1)]

    interpolated_dataset['timestamp'] = timestamps.values

    for key in dataset.keys():
        print(f'Interpolating stream {key}...')
        # logger.info(f'({ttime.ctime()}) Interpolating stream {key}...')
        if key == 'pil100k2_image':
            time = dataset.get(key).iloc[:, 0].values.astype(np.float64)
            val = np.stack(dataset.get(key).iloc[:, 1].values)

            if len(dataset.get(key).iloc[:, 0]) > 5 * len(timestamps):
                time = [time[0]] + [np.mean(array) for array in np.array_split(time[1:-1], len(timestamps))] + [time[-1]]
                val = [val[0]] + [np.mean(array) for array in np.array_split(val[1:-1], len(timestamps))] + [val[-1]]

                interpolated_dataset[key] = np.array([timestamps, np.interp(timestamps, time, val, left=None, right=None)]).transpose()
        else:

            time = dataset.get(key).iloc[:, 0].values
            val = dataset.get(key).iloc[:, 1].values
            if len(dataset.get(key).iloc[:, 0]) > 5 * len(timestamps):
                time = [time[0]] + [np.mean(array) for array in np.array_split(time[1:-1], len(timestamps))] + [
                    time[-1]]
                val = [val[0]] + [np.mean(array) for array in np.array_split(val[1:-1], len(timestamps))] + [val[-1]]
                interpolated_dataset[key] = np.array([timestamps, np.interp(timestamps, time, val)]).transpose()

        interpolated_dataset[key] = np.array([timestamps, np.interp(timestamps, time, val)]).transpose()
        # interpolator_func = interp1d(time, np.array([v for v in val]), axis=0)
        # val_interp = interpolator_func(timestamps)
        # if len(val_interp.shape) == 1:
        #     interpolated_dataset[key] = val_interp
        # else:
        #     interpolated_dataset[key] = [v for v in val_interp]
        # print(f'Interpolation of stream {key} is complete')
        # logger.info(f'({ttime.ctime()}) Interpolation of stream {key} is complete')

    intepolated_dataframe = pd.DataFrame(interpolated_dataset)
    if sort:
        return intepolated_dataframe.sort_values('energy')
    else:
        return intepolated_dataframe




##### Jenny VHS Processing after generating all the tif and h5 files for getting the RIXS plan ########

path_hdf5 = '/nsls2/data/iss/legacy/processed/2025/1/314438/extended_data/'
path_data = '/nsls2/data/iss/legacy/processed/2025/1/314438/'

key_data = "*stepscan*-r0002.dat"
key_hdf5 = "*stepscan*r0002*.h5"

import glob
from larch.io import read_ascii
import h5py
from xas.vonhamos import *

def create_dict_for_pixel_to_energy(path_hdf5=None,
                                    path_data=None,
                                    key_data=None,
                                    key_hdf5=None):

    dictionary = {}

    h5_files = [f for f in sorted(glob.glob(path_hdf5 + key_hdf5))]
    data_files = [f for f in sorted(glob.glob(path_data + key_data))]

    for h5_f, da_f in zip(h5_files, data_files):
        data = read_ascii(da_f)
        data_h5 = h5py.File(h5_f)

        arr = []
        for img in data_h5['pil100k2_image']:
            arr.append(img[80:100, :])

        arr = np.array(arr)
        dictionary[os.path.basename(h5_f)] = {}

        _, _, pixel, energy = run_calibration(arr, data.energy, output_diagnostics=False)

        dictionary[os.path.basename(h5_f)]['energy'] = energy
        dictionary[os.path.basename(h5_f)]['pixel'] = pixel

    return dictionary


calib_dict = create_dict_for_pixel_to_energy(path_hdf5=path_hdf5, path_data=path_data, key_data=key_data, key_hdf5=key_hdf5)


key_hdf5 = "Fe_Acetate*RIXS*.h5"
key_data = "Fe_Acetate*s_RIXS*0001.dat"


h5_files = [f for f in sorted(glob.glob(path_hdf5 + key_hdf5))]
data_files = [f for f in sorted(glob.glob(path_data + key_data))]


MONO_EN = []
RIXS = []
EMISSION = []

for hd_f, da_f in zip(h5_files, data_files):
    data = read_ascii(da_f)
    if len(data.i0) < 326:
        continue
    data_h5 = h5py.File(hd_f)
    print(f"{hd_f = } {da_f = }")
    XES= [img[80:100, :].sum(axis=0)/data.i0[i] for i, img in enumerate(data_h5['pil100k2_image'])]
    MONO_EN.append(data.energy)
    EMISSION.append(calib_dict['Fe_Acetate (pos 005) Fe-K calib stepscan 0001-r0002.h5']['energy'])
    RIXS.append(np.array(XES))

data_files = [f for f in sorted(glob.glob('Fe Acetate *s_RIXS*0001.dat'))]


plt.figure()
for key in calib_dict.keys():
    en = calib_dict[key]['energy']
    pix = calib_dict[key]['pixel']
    plt.plot(en, pix, label=key)

plt.legend()

en = 0
flu = 0
for da_f in data_files:
    data = read_ascii(da_f)
    if len(data.i0) < 326:
        continue
    flu = flu + data.pil100k2_roi3/data.i0


en = np.array(en)
flu = flu.array(en)



h5_files = [f for f in sorted(glob.glob(path_h5 + key_h5))]


for i, f in enumerate(hdf5_files, start=6):
    name_current = os.path.basename(f)[16:19]

    print(f"{i} = {name_current}")


h5_files = ['DT372_RIXS (pos 005) Fe-K calib stepscan 0001-r0002.h5',
'DT373_RIXS (pos 005) Fe-K calib stepscan 0001-r0002.h5',
'Fe2Co_Acetate (pos 001) Fe-K calib stepscan 0001-r0002.h5',
'Fe2Co_Mil100 (pos 002) Fe-K calib stepscan 0001-r0002.h5',
'Fe2Co_MOF74 (pos 001) Fe-K calib stepscan 0001-r0002.h5',
'Fe2Ni_acetate (pos 002) Fe-K calib stepscan 0001-r0002.h5',
'Fe2Ni_Mil100 (pos 002) Fe-K calib stepscan 0001-r0002.h5',
'Fe2Ni_MOF74 (pos 001) Fe-K calib stepscan 0001-r0002.h5',
'Fe2NiOAc_RIXS (pos 001) Fe-K calib stepscan 0001-r0002.h5',
'Fe_Acetate (pos 001) Fe-K calib stepscan 0001-r0002.h5',
'Fe_Acetate (pos 005) Fe-K calib stepscan 0001-r0002.h5',
'FeBTC (pos 002) Fe-K calib stepscan 0001-r0002.h5',
'Fe_Mil100 (pos 003) Fe-K calib stepscan 0001-r0002.h5',
'FeMil100_RIXS (pos 001) Fe-K calib stepscan 0001-r0002.h5',
'Fe_MOF74 (pos 002) Fe-K calib stepscan 0001-r0002.h5',
'TCNQ_FeBTC (pos 002) Fe-K calib stepscan 0001-r0002.h5']

h5_files = [path_h5+file for file in h5_files]

for i, f in enumerate(files_h5):
    new_name = os.path.basename(f).split('(')[1].split(')')[0].split(" ")[1]
    old_name = os.path.basename(files_h5[i-1]).split('(')[1].split(')')[0].split(" ")[1]
    if new_name == old_name:
        print(new_name)


files = [f for f in sorted(glob.glob("*s_RIXS*.h5"))]

keys_h5 = ['DT372_RIXS*s_RIXS*.h5',
'DT373_RIXS*s_RIXS*.h5',
'Fe2Co_Acetate*s_RIXS*.h5',
'Fe2Co_Mil100*s_RIXS*.h5',
'Fe2Co_MOF74*s_RIXS*.h5',
'Fe2Ni_acetate*s_RIXS*.h5',
'Fe2Ni_Mil100*s_RIXS*.h5',
'Fe2Ni_MOF74*s_RIXS*.h5',
'Fe2NiOAc_RIXS*s_RIXS*.h5',
'Fe_Acetate*s_RIXS*.h5',
'FeBTC*s_RIXS*.h5',
'Fe_Mil100*s_RIXS*.h5',
'FeMil100_RIXS*s_RIXS*.h5',
'Fe_MOF74*s_RIXS*.h5',
'TCNQ_FeBTC*s_RIXS*.h5']


keys_data = ['DT372_RIXS*s_RIXS*0001.dat',
'DT373_RIXS*s_RIXS*0001.dat',
'Fe2Co_Acetate*s_RIXS*0001.dat',
'Fe2Co_Mil100*s_RIXS*0001.dat',
'Fe2Co_MOF74*s_RIXS*0001.dat',
'Fe2Ni_acetate*s_RIXS*0001.dat',
'Fe2Ni_Mil100*s_RIXS*0001.dat',
'Fe2Ni_MOF74*s_RIXS*0001.dat',
'Fe2NiOAc_RIXS*s_RIXS*0001.dat',
'Fe_Acetate*s_RIXS*0001.dat',
'FeBTC*s_RIXS*0001.dat',
'Fe_Mil100*s_RIXS*0001.dat',
'FeMil100_RIXS*s_RIXS*0001.dat',
'Fe_MOF74*s_RIXS*0001.dat',
'TCNQ_FeBTC*s_RIXS*0001.dat']

group_hdf5 = {}
group_data = {}

path_hdf5 = '/nsls2/data/iss/legacy/processed/2025/1/314438/extended_data/'
path_data = '/nsls2/data/iss/legacy/processed/2025/1/314438/'

for key_d, key_h5 in zip(keys_data, keys_h5):
    group_hdf5[key_h5] = [f for f in sorted(glob.glob(path_hdf5+key_h5))]
    group_data[key_d] = [f for f in sorted(glob.glob(path_data+key_d))]
    print(f"{len(group_data[key_d]) = } {len(group_hdf5[key_h5]) = } {key_d}")


group_rixs = {}
for key_d, key_h5, cal_key in zip(group_data.keys(), group_hdf5.keys(), calib_dict.keys()):
    RIXS = []
    MONO_EN = []
    EMISSION = []

    for hd_f, da_f in zip(group_hdf5[key_h5], group_data[key_d]):
        print(f"{hd_f} {da_f}")
        data = read_ascii(da_f)
        if len(data.i0) < 326 or 'pil100k2_roi3' not in data.array_labels:
            print("-----------------EXCEPTION-------------")
            continue
        data_h5 = h5py.File(hd_f)
        print(f"{hd_f = } {da_f = }")
        XES = [img[80:100, :].sum(axis=0) / data.i0[i] for i, img in enumerate(data_h5['pil100k2_image'])]
        MONO_EN.append(data.energy)
        EMISSION.append(calib_dict[cal_key]['energy'])
        RIXS.append(np.array(XES))

    group_rixs[key_d] = {}
    group_rixs[key_d]['rixs'] = np.array(RIXS).sum(axis=0)
    group_rixs[key_d]['energy'] = np.array(MONO_EN).sum(axis=0)/len(MONO_EN)
    group_rixs[key_d]['EMISSION'] = np.array(EMISSION).sum(axis=0)/len(EMISSION)



from tiled.client import from_uri
from databroker.queries import TimeRange, Key
c = from_uri("https://tiled.nsls2.bnl.gov")["iss"]["raw"]
date_limited_c = c.search(TimeRange(since="2025-01-01", until="2025-03-19"))
proposal_limited_c = date_limited_c.search(Key("proposal") == "309462")
scan_limited_c = proposal_limited_c.search(Key("experiment") == "fly_scan")
b=list(scan_limited_c)
for uid in b:
    dt = datetime.datetime.fromtimestamp(db[uid].start['time'], tz=datetime.timezone.utc)
    eastern = pytz.timezone('US/Eastern')
    loc_dt = dt.astimezone(eastern)
    fmt = '%Y-%m-%d %H:%M:%S %Z%z'
    loc_dt.strftime(fmt)
    print(f"{loc_dt} {uid}")


dt = datetime.datetime.fromtimestamp(hdr.start['time'], tz=datetime.timezone.utc)
eastern = pytz.timezone('US/Eastern')
loc_dt = dt.astimezone(eastern)
fmt = '%Y-%m-%d %H:%M:%S %Z%z'
loc_dt.strftime(fmt)
print(loc_dt)

print(datetime.datetime.fromtimestamp('9f88d2c7-a7ee-4287-a7fc-dddd904293df', tz=datetime.timezone.utc))

import datetime
import pytz
datetime.datetime.fromtimestamp(db[b[-1]].start['time'])
dt

proposal_limited_c = proposal_limited_c.search(Key("experiment") == "fly_scan")
proposal_limited_c
date_limited_c = c.search(TimeRange(since="2025-01-01", until="2025-03-19"))
%history

uid = '9193b2b0-d6d5-48d2-bb04-a4669c8cbe1f'

from databroker import Broker
db = Broker.named('iss')
import time
uid = 'c43c49b2-f72e-4928-ac01-1bf3ba3a3ddb'
uid = '4c1a60ed-b202-4c82-b97d-41aecb667b57'
uid = '4afc89ba-f544-4070-b52e-16fb94aac4a9'
uid = '18a11286-7e64-4d18-9d91-5440dd7b2495'
hdr = db[uid]
start = time.time()
t = hdr.table(stream_name='pil100k2_stream', fill=True)
print(f"{time.time()-start}")

path = None

with open(path) as f:
    data = h

data = h5py.File(path)
start = time.time()
arr = np.array(data['entry']['data']['data'])
print(f"{time.time()-start}")

start = time.time()
with h5py.File(path1, 'r') as f:
    dset = f['/entry/data/data']
    array = dset[()]
print(f"{time.time()-start}")


import time
RE.msg_hook = bluesky.utils.ts_msg_hook
def motor_move(motor, pos):
    start = time.time()
    yield from bps.mv(motor, pos)
    print(f"Total time {time.time()-start}sec")
RE(motor_move(hhm.energy, 9000))


import time as ttime
from xas.process import process_interpolate_bin
uid = '9193b2b0-d6d5-48d2-bb04-a4669c8cbe1f'
hdr = db[uid]
start = ttime.time()
process_interpolate_bin(hdr.stop, db, load_images=True)
print(f"{ttime.time()-start}")



hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = get_processed_df_from_uid(uid, db, load_images=True)


for uid in uids:
    start = ttime.time()
    hdr = db[uid]
    process_interpolate_bin(hdr.stop, db, load_images=True)
    print(f"{ttime.time() - start}")

dictionary = {}
for elem in elements:
    dictionary[elem] = {}
    _dict = xraydb.xray_edges(elem)
    for key in _dict.keys():
        if _dict[key].energy > 4700 and _dict[key].energy < 32000:
            dictionary[elem][key] = _dict[key].energy


for element in qas_foils:
    for edge in xraydb.xray_edges(element):
        energy = xraydb.xray_edges(element)[edge].energy
        if (energy >= 4500) and (energy <= 32000):
            _qas_foil_data.append({'element': element,
                          'edge':edge,
                          'energy':energy})




old = pd.read_csv('old_pressure_data1', parse_dates=[0], sep='\t', skiprows=16)
new = pd.read_csv('new_pressure_data3', parse_dates=[0], sep='\t', skiprows=16)

plt.figure()

time_old = old.iloc[:, 0].astype('int64') // 1E9
time_old = time_old - time_old[0]

time_new = new.iloc[:, 0].astype('int64') // 1E9
time_new = time_new - time_new[0]

plt.plot(time_old, old.iloc[:, 1])
plt.plot(time_new, new.iloc[:, 1])


new = pd.read_csv('new_pressure_data_5', parse_dates=[0], sep='\t', skiprows=16)
time_new = new.iloc[:, 0].astype('int64') // 1E9
time_new = time_new - time_new[0]

plt.figure()
plt.plot(time_new[1:], new.iloc[:, 1][1:])
plt.plot(time_new[1:], 3E-3/np.sqrt(time_new[1:]))



columns = ['timestamp', 'ps_level', 'ps_pressure', 'bath_level', 'bath_pressure',
           'accu_level', 'accu_pressure', 'p1', 'p2', 't1', 't2', 't3', 't4', 'rate', 'temp_flow_meter']

old = pd.read_csv('Cryo_data', parse_dates=[0], sep='\t', comment='#', names=columns)
time_old = old['timestamp'].astype('int64') // 1E9

timestamp = time_old - time_old[0]


plt.figure()
plt.plot(timestamp, old['ps_level'], label='PS Level')
plt.plot(timestamp, old['bath_level'], label='Bath Level')
plt.plot(timestamp, old['accu_level'], label='Accumulator Level')
plt.xlabel("Time (sec)")
plt.ylabel("Level (%)")
plt.xlim(280000, 340000)
plt.legend()

plt.figure()
plt.plot(timestamp, old['ps_pressure'], label='PS Pressure')
plt.plot(timestamp, old['bath_pressure'], label='Bath Pressure')
plt.plot(timestamp, old['accu_pressure'], label='Accumulator Pressure')
plt.xlabel("Time (sec)")
plt.ylabel("Pressure (kPa)")
plt.xlim(280000, 340000)
plt.legend()



plt.figure()
plt.plot(timestamp, old['p1'], label='Supply LN2 Pressure')
plt.plot(timestamp, old['p2'], label='Return LN2 Pressure')
plt.xlabel("Time (sec)")
plt.ylabel("Pressure (kPa)")
plt.xlim(280000, 340000)
plt.legend()


plt.figure()
plt.plot(timestamp, old['t1'], label='T1')
plt.plot(timestamp, old['t2'], label='T2')
plt.plot(timestamp, old['t3'], label='T3')
plt.plot(timestamp, old['t4'], label='T4')
plt.xlabel("Time (sec)")
plt.ylabel("Temperature (K)")
plt.xlim(280000, 340000)
plt.ylim(75, 85)17100
plt.legend()

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Cursor

# Create some sample data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create a figure and an axes object
fig, ax = plt.subplots()

# Plot the data
ax.plot(x, y)

# Create the Cursor widget
# The 'ax' argument specifies the axes to attach the cursor to.
# 'horizOn' and 'vertOn' control whether horizontal and vertical lines are shown.
# 'color' and 'linewidth' customize the appearance of the lines.
cursor = Cursor(ax, horizOn=True, vertOn=True, color='red', linewidth=1)

# Display the plot
plt.show()


von_hamos_geometry.crystal = "Ge"
von_hamos_geometry.e2bragg(8900) = 80.02740605090814

von_hamos_geometry.compute_geometry_for_energy(8900)
(507.67054619950966, 30.450391642263536, 173.17709884065675, 9.97259394909186)
cr_x, det_x, det_y, theta

von_hamos_geometry.compute_arc_motion(bragg=80.02740605090814)
26.349880385574153

von_hamos_det_arm._forward({'det_pitch':80.02740605090814, 'det_x':30.450391642263536, 'det_y':173.17709884065675})
{'motor_det_x': 203.77061970977343,
 'motor_det_th1': 36.16126864517311,
 'motor_det_th2': -46.133862594264976}


bender_positions = [1.42,
 1.83,
 2.24,
 2.65,
 3.06,
 3.47,
 3.88,
 4.29,
 4.7,
 5.11,
 5.52,
 5.93,
 6.34,
 6.75,
 7.16,
 7.57,
 7.98,
 8.39,
 8.8,
 9.21,
 9.63,
 10.04,
 10.45,
 10.86,
 11.27,
 11.68,
 12.09,
 12.5,
 12.91,
 13.32,
 13.73,
 14.14,
 14.55,
 14.96,
 15.37,
 15.78,
 16.19,
 16.6,
 17.01,
 17.42]

plans = bender_scan_plan_bundle(element='Cu', edge='K', bender_positions=bender_positions)
plan_processor.add_plans(plans)

#4900,  5100,  5500,  6000,  7000,  8000,  9000, 10000, 11000, 12000, 13000, 15000, 17500, 20000, 26000]


###################################
########## hhm_y_precise tabulation 2025-10-30
#########################################
{energy:[4950, 5100, 5500, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 15000, 17500, 20000, 26000, 31000],
 uid:['9d8973fe-cb65-4b26-b15b-357be7586668',
      '0cc86d17-031a-4b4e-b47c-ba78f4424881',
      'cd5f43b2-09b3-4583-a6ec-54ef696791b4',
      '9196b604-b76f-4813-8f32-896503ea274f',
      '265c9bd1-4f44-4b31-8610-b8cb3af28c49',
      'b44b7661-231f-4062-af44-729fcb9020ca',
      '58bad7c0-313a-4035-bd6f-38f76b6fdec0',
       '96aa3c29-82f5-4944-9e18-4ccc662d22a6',
       '472da164-24ce-49f8-a938-468a5108e756',
        '765485e5-3fe6-40ff-b32d-ee1c1abade71',
'711e5f0a-bb59-40a8-9ce4-89d0f0cd60a4',
'711e5f0a-bb59-40a8-9ce4-89d0f0cd60a4',
'fef3865c-4cd0-4360-976c-d079dbbd6488'
'37973463-a254-4c8f-9ad0-4efa7d3acb52',
'3b79c065-9bf0-444d-a0d0-9f9bbbed22a2'
'b0d6fec1-80d2-47a6-af0b-760ad7d9e973'

      ],
 value:[8.657, 8.606, 8.457, 8.36, 8.243, 8.143, 8.097, 8.044, 8.046, 7.995, 7.937, 7.930, 7.922, 7.940, 7.920]}

uids = [
'b0d6fec1-80d2-47a6-af0b-760ad7d9e973',
'37973463-a254-4c8f-9ad0-4efa7d3acb52',
'28234a63-6c58-4b0f-bdb6-a6ca6f2cae14',
'8e307546-5e32-4dfe-9972-148235f7b06a',
'711e5f0a-bb59-40a8-9ce4-89d0f0cd60a4',
'765485e5-3fe6-40ff-b32d-ee1c1abade71',
'472da164-24ce-49f8-a938-468a5108e756',
'96aa3c29-82f5-4944-9e18-4ccc662d22a6',
'58bad7c0-313a-4035-bd6f-38f76b6fdec0',
'b44b7661-231f-4062-af44-729fcb9020ca',
'265c9bd1-4f44-4b31-8610-b8cb3af28c49',
'9196b604-b76f-4813-8f32-896503ea274f',
'cd5f43b2-09b3-4583-a6ec-54ef696791b4',
'0cc86d17-031a-4b4e-b47c-ba78f4424881',
'9d8973fe-cb65-4b26-b15b-357be7586668',]


'711e5f0a-bb59-40a8-9ce4-89d0f0cd60a4'


uids = [
'8e307546-5e32-4dfe-9972-148235f7b06a' #15000
'28234a63-6c58-4b0f-bdb6-a6ca6f2cae14' #17500
'fef3865c-4cd0-4360-976c-d079dbbd6488' #20000
'37973463-a254-4c8f-9ad0-4efa7d3acb52' #26000
'b0d6fec1-80d2-47a6-af0b-760ad7d9e973' #31000
]

uids = np.arange(-1, -200, -1)
for uid in uids:
    hdr = db[uid]
    dictionary = hdr.start
    try:
        if dictionary['motors'][0] == 'hhm_y_precise':
            print(dictionary['uid'])
    except Exception as e:
        print(e)
uids = [
'b0d6fec1-80d2-47a6-af0b-760ad7d9e973',
'37973463-a254-4c8f-9ad0-4efa7d3acb52',
'fef3865c-4cd0-4360-976c-d079dbbd6488',
'28234a63-6c58-4b0f-bdb6-a6ca6f2cae14',
'1761d3a0-c004-44ca-9ce9-f1140c26dd1a'
'8e307546-5e32-4dfe-9972-148235f7b06a',
'711e5f0a-bb59-40a8-9ce4-89d0f0cd60a4',
'765485e5-3fe6-40ff-b32d-ee1c1abade71',
'472da164-24ce-49f8-a938-468a5108e756',
'96aa3c29-82f5-4944-9e18-4ccc662d22a6',
'58bad7c0-313a-4035-bd6f-38f76b6fdec0',
'b44b7661-231f-4062-af44-729fcb9020ca',
'265c9bd1-4f44-4b31-8610-b8cb3af28c49',
'9196b604-b76f-4813-8f32-896503ea274f',
'cd5f43b2-09b3-4583-a6ec-54ef696791b4',
'0cc86d17-031a-4b4e-b47c-ba78f4424881',
'9d8973fe-cb65-4b26-b15b-357be7586668'
]


uids = [
# '811390d3-da27-47e6-9d27-a56bc0e51a32',
# '2c5e8b96-d637-4fb8-9c71-aea94ac7b229',
'711e5f0a-bb59-40a8-9ce4-89d0f0cd60a4',
'5e9a5e41-9686-44da-a1f4-51f212ba3805']


plt.figure()
s = []
for i, uid in enumerate(uids):
    print(uid)
    hdr = db[uid]
    t = hdr.table()
    plt.plot(t['hhm_y_precise'], t['bpm_fm_stats1_total'], label=str(i))
    arg = np.argmax(t['bpm_fm_stats1_total'])
    s.append(t['hhm_y_precise'][arg])

plt.legend()


def create_zip(self):
    _, _current_user = self.user_manager.current_user()
    proposal = (_current_user['runs'][-1]['proposal'])

    year = self.RE.md['year']
    cycle = self.RE.md['cycle']
    proposal = self.RE.md['proposal']
    PI = self.RE.md['PI']
    email_address = self.lineEdit_email.text()
    # working_directory = f'/nsls2/xf08id/users/{year}/{cycle}/{proposal}'
    working_directory = f'{ROOT_PATH}/{USER_PATH}/{year}/{cycle}/{proposal}'
    zip_file = f'{working_directory}/{proposal}.zip'
    id = str(uuid.uuid4())[0:5]
    zip_id_file = f'{proposal}-{id}.zip'

    if os.path.exists(zip_file):
        os.remove(zip_file)

    # os.system(f'zip {zip_file} {working_directory}/*.* ')

    print('Creating a zip file')
    os.system(f"cd '{working_directory}'; zip '{zip_id_file}' *.dat")

    message = create_html_message(
        'staff08id@gmail.com',
        email_address,
        f'ISS beamline data for Proposal {proposal}\n',
        f' <p> Dear {PI},</p> <p>You can download the results of your experiment from JupyterHub by following the steps below: </p>'
        f'<p> 1. Go to https://jupyter.nsls2.bnl.gov and log in using your BNL credentials. </p>'
        f'<p> 2. Click on "Start My Server" to launch a new server or relaunch an already active server. </p>'
        f'<p> 3. In the "Server Options" window, select "Scientific Python" as the job profile, then click "Start".</p>'
        f'<p> 4. In the File menu, select "Open from Path..." </p>'
        f'<p> 5. Copy and paste the following path (without quotation marks): "{working_directory}" </p>'
        f'<p> 6. Right-click on the zip file named {zip_id_file} and download it to your PC. </p> '
        f'<p> Sincerely, </p> <p> ISS Staff </p>'
    )

    draft = upload_draft(self.parent.gmail_service, message)
    sent = send_draft(self.parent.gmail_service, draft)
    print('Email sent for zip files')


uid = 'db4997cb-9e39-462c-9c58-454999ace698'
uid1 = 'c6501f5f-61d1-43cd-b62e-fa5421c83789'

hdr = db['db4997cb-9e39-462c-9c58-454999ace698']
hdr1 = db['c6501f5f-61d1-43cd-b62e-fa5421c83789']


from xas.file_io import (load_dataset_from_files, create_file_header, validate_file_exists, validate_path_exists,
                      save_interpolated_df_as_file, save_binned_df_as_file, find_e0, save_stepscan_as_file,
                      stepscan_remove_offsets, stepscan_normalize_xs, stepscan_normalize_xia,combine_xspress3_channels, combine_pil100k_channels,
                      combine_xia_channels,
                      filter_df_by_valid_keys, save_primary_df_as_file, save_extended_data_as_file, dump_tiff_images)
from xas.db_io import load_apb_dataset_from_db, translate_apb_dataset, load_apb_trig_dataset_from_db, load_xs3_dataset_from_db, load_pil100k_dataset_from_db, load_apb_dataset_only_from_db, translate_apb_only_dataset, load_xia_dataset_from_db
from xas.interpolate import interpolate, interpolate_with_interp

apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
raw_dict = translate_apb_dataset(apb_df, energy_df, energy_offset)

t = hdr.table(stream_name='pb9_enc1', fill=True)
t1 = hdr.table(stream_name='pb9_enc1', fill=True)

plt.figure()
plt.plot(t['pb9_enc1'][1]['ts_s']+t['pb9_enc1'][1]['ts_ns'], t['pb9_enc1'][1]['encoder'])


plt.figure()
plt.plot(raw_dict['energy']['timestamp']-raw_dict['energy']['timestamp'][0], raw_dict['energy']['encoder'])
plt.plot(raw_dict1['energy']['timestamp']-raw_dict1['energy']['timestamp'][0], raw_dict1['energy']['encoder'])


apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
raw_dict1 = translate_apb_dataset(apb_df, energy_df, energy_offset)


uid2 = 'b28a5efa-daa6-4b1a-ac6b-a47c24bef538'
uid3 = 'c5028810-ecf0-4c84-9112-6de064c60c49'

apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid2)
raw_dict2 = translate_apb_dataset(apb_df, energy_df, energy_offset)
apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid3)
raw_dict3 = translate_apb_dataset(apb_df, energy_df, energy_offset)


plt.figure()
plt.plot(raw_dict2['energy']['timestamp']-raw_dict2['energy']['timestamp'][0], raw_dict2['energy']['encoder'])
plt.plot(raw_dict3['energy']['timestamp']-raw_dict3['energy']['timestamp'][0], raw_dict3['energy']['encoder'])


def plot_beamdamage_scans(uid=-1):
    hdr = db[uid]
    t = hdr.t



def plot_scan(uid=-1):
    hdr = db[uid]
    t = hdr.table()
    plt.plot(t['hhm_energy'], np.log(t['bpm_fm_stats1_total']))



### March 30, 2026

#### Inclinometer data from -27 to 69 degree
d = {'motor_det_th1': {'0': -27,
  '1': -24,
  '2': -21,
  '3': -18,
  '4': -15,
  '5': -12,
  '6': -9,
  '7': -6,
  '8': -3,
  '9': 0,
  '10': 3,
  '11': 6,
  '12': 9,
  '13': 12,
  '14': 15,
  '15': 18,
  '16': 21,
  '17': 24,
  '18': 27,
  '19': 30,
  '20': 33,
  '21': 36,
  '22': 39,
  '23': 42,
  '24': 45,
  '25': 48,
  '26': 51,
  '27': 54,
  '28': 57,
  '29': 60,
  '30': 63,
  '31': 66,
  '32': 69},
 'motor_det_inc1': {'0': 14646,
  '1': 14381,
  '2': 14113,
  '3': 13848,
  '4': 13578,
  '5': 13309,
  '6': 13040,
  '7': 12770,
  '8': 12507,
  '9': 12237,
  '10': 11968,
  '11': 11700,
  '12': 11436,
  '13': 11166,
  '14': 10902,
  '15': 10632,
  '16': 10362,
  '17': 10094,
  '18': 9829,
  '19': 9560,
  '20': 9291,
  '21': 9026,
  '22': 8757,
  '23': 8493,
  '24': 8223,
  '25': 7960,
  '26': 7691,
  '27': 7421,
  '28': 7157,
  '29': 6888,
  '30': 6618,
  '31': 6355,
  '32': 6085}}

#### Inclinometer data from 69 to -27 degree

d = {'motor_det_th1': {'0': -27,
  '1': -24,
  '2': -21,
  '3': -18,
  '4': -15,
  '5': -12,
  '6': -9,
  '7': -6,
  '8': -3,
  '9': 0,
  '10': 3,
  '11': 6,
  '12': 9,
  '13': 12,
  '14': 15,
  '15': 18,
  '16': 21,
  '17': 24,
  '18': 27,
  '19': 30,
  '20': 33,
  '21': 36,
  '22': 39,
  '23': 42,
  '24': 45,
  '25': 48,
  '26': 51,
  '27': 54,
  '28': 57,
  '29': 60,
  '30': 63,
  '31': 66,
  '32': 69},
 'motor_det_inc1': {'0': 14621,
  '1': 14351,
  '2': 14081,
  '3': 13818,
  '4': 13548,
  '5': 13294,
  '6': 13035,
  '7': 12765,
  '8': 12501,
  '9': 12232,
  '10': 11962,
  '11': 11699,
  '12': 11430,
  '13': 11160,
  '14': 10896,
  '15': 10626,
  '16': 10363,
  '17': 10094,
  '18': 9824,
  '19': 9555,
  '20': 9291,
  '21': 9021,
  '22': 8757,
  '23': 8488,
  '24': 8223,
  '25': 7955,
  '26': 7685,
  '27': 7422,
  '28': 7152,
  '29': 6882,
  '30': 6619,
  '31': 6350,
  '32': 6085,}}


plt.plot(t['apb_stream'][1]['timestamp'],t['apb_stream'][1]['i0'])

junk_uids = []
for uid in uids:
    try:
        apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
        print(len(apb_df['timestamp']))
    except Exception as ex:
        junk_uids.append(uid)
        print(ex)



data = np.arange(0, 720, 1)
sin = 500 + np.sin(data*np.pi/180)
noise = np.random.normal(0, 0.2, sin.shape)

noisy_signal = sin+noise
plt.figure()
plt.plot(data, noisy_signal)

# Mingzhao Liu 'PROPOSAL': '309093' 'year': '2021''cycle': '3'
from tiled.client import from_uri
from tiled.queries import Key

catalog = from_uri("https://tiled.nsls2.bnl.gov")
c = catalog['iss']['raw']

results = c.search(Key("start.PROPOSAL") == '309093').search(Key("start.experiment") == 'fly_energy_scan_apb')


plt.figure()
scan_ids = [167590, 167600, 167608, 167617, 167625]
scaling = [1, 1, 1, 1, 1]
for sids, sca in zip(scan_ids, scaling):
    hdr = db[sids]
    t = hdr.table()
    plt.plot(t['hhm_energy'], t['apb_ave_ch1']*sca)
plt.yscale(u'log')

scan_ids = [167590, 167600, 167608, 167617, 167625]
uids = []
for scan_id in scan_ids:
    hdr = db[scan_ids[id]]
    t = hdr.start
    t.uid
    t.scan_id
    uids.append(t.uid)

voltages = list(np.arange(0, 1651, 1))
RE(bp.list_scan([apb_ave], wps1.hv302, voltages))
def voltage_scan(voltages=None):
    for volt in voltages:
        yield from bps.abs_set(wps1.hv302, volt)
        yield from sleep(5)
        yield from bp.count([apb_ave])



from ophyd.status import DeviceStatus
import threading
class WPS_Scan(Device):
    setpoint = Cpt(EpicsSignal, 'HV:u302}V-Set')
    readback = Cpt(EpicsSignalRO, 'HV:u302}V-Sense', name='wps_i0_plate')
    hv302 = Cpt(DeviceWithNegativeReadBack, 'HV:u302}')

    def __init__(self, prefix, WPS_scan_id=None, **kwargs):
        super().__init__(prefix, **kwargs)
        self.WPS_scan_id = WPS_scan_id

        if self.WPS_scan_id is None:
            self.WPS_scan_id = 'WPS_scan'

    def set(self, value):
        status = DeviceStatus(self)

        def _move():
            self.setpoint.put(value, wait=True)
            time.sleep(4)
            status.set_finished()

        threading.Thread(target=_move, daemon=True).start()
        return status

    def read(self):
        return {self.WPS_scan_id: {'value':self.readback.get(), 'timestamp': time.time()}}

    def describe(self):
        return {self.WPS_scan_id: {'source': 'PV-Sense', 'dtype': 'number', 'shape': []}}

    def stop(self, *, success=False):
        self.setpoint.stop()

    def is_moving(self):
        return False

    def read_configuration(self):
        return {}

    def describe_configuration(self):
        return {}


wps_i0 = WPS_Scan('XF:08IDB-OP{WPS:01-', name='wps_i0', WPS_scan_id='WPS_scan_i0')


def voltage_plataue():
    He =  np.array([90, 85, 80, 75]) * 0.05
    N2 = np.array([10, 15, 20, 25]) * 0.05
    absorptions = [4, 6.4, 8.5, 10]
    voltages = np.arange(40, 1651, 20)
    uids = []
    for n2, he, absorp in zip(N2, He, absorptions):
        yield from bps.abs_set(wps_i0.hv302, 40, wait=True)
        print(f"Setting up the voltage to safe value...............")
        print(f"Setting up the flow for {n2 = } and {he = } with absorption {absorp = }")
        yield from bps.abs_set(gas_he.flow, he, wait=True)
        yield from bps.abs_set(gas_n2.flow, n2, wait=True)
        yield from sleep(180)
        print(f"Gases change is now complete.........................")
        dictionary = {'gases': {'N2': n2, 'He': he}, 'absorption': absorp}
        uid = yield from bp.list_scan([apb_ave], wps_i0, voltages.tolist(), md=dictionary)
        uids.append(uid)
    return uids


uids = []
plt.figure()
for uid in uids:
    hdr = db[uid]
    t = hdr.table()
    plt.plot(t['WPS_scan_i0'], t['apb_ave_ch1_mean'], label=hdr.start['absorption'])
plt.legend()

uids = ['3fd0b682-865e-4f63-99a2-54fea7de6374',
        '59c0c591-351e-44e5-b963-78e41e64eeae',
        '9648432a-d6a0-4b5b-986d-2168864c94b4',
        'd27ef2ac-5755-4cc7-8a03-296348a97c49',
        '5ee3bbe2-754e-4239-86ee-a6f295f723c5']

plt.figure()
scaling = [2.8, 1.6, 0.8, 0.35, 0.35]
for sids, sca in zip(uids, scaling):
     hdr = db[sids]
     t = hdr.table()
     plt.plot(t['hhm_energy'], t['apb_ave_ch1']*sca)
plt.yscale(u'log')



x = xview_gui.widget_project
indexes = x.list_project.selectedIndexes()
plt.figure()
for index in indexes:
    ds = x.parent.project[index.row()]
    plt.plot(ds.energy, ds.flat)



from xas.file_io import load_binned_df_from_file
uids = []
for item in x.list_data.selectedItems():
    fname = os.path.join(x.working_folder, item.text())
    df, header = load_binned_df_from_file(fname)
    print(fname, df.shape)
    uid_idx1 = header.find('Scan.uid:') + 10
    uid_idx2 = header.find('\n', header.find('Scan.uid:'))
    uid = header[uid_idx1: uid_idx2]
    uids.append(uid)

key_entry = ['johann_main_crystal_motor_cr_main_roll', 'johann_aux2_crystal_motor_cr_aux2_roll']
crystals = ['main', 'aux2']
LUT = {}
LUT['energy'] = [12645, 12647, 12649, 12651, 12653, 12655, 12657, 12659, 12661, 12663, 12665]

for key, crystal in zip(key_entry, crystals):
    a, b, c, d = analyze_linewidth_fly_scan(db, uid, rois=[3], x_key=key)
    LUT[crystal] = [analyze_linewidth_fly_scan(db, uid, rois=[3], x_key=key)[3] for uid in uids]

uids = ['39789757-f641-4700-80ef-154f5b6777cc',
 '10cb5a41-f0f5-45c9-9df9-17cdd166791b',
 '9ae36c3b-2cbf-4825-86b9-aa720e203832',
 'c9fb03df-e8e6-4842-9989-9e783b4ad231',
 'c7d45773-7cb4-4a74-ab34-2c8e7e7994d2',
 'd07c86fb-7690-4889-a471-912a4e298dbb',
 'bc8be569-972d-419f-991e-d9e9d3496442',
 'fd6952fd-19f3-49db-ae5c-db44dd4a3242',
 '4d7c6a26-8f05-499c-a214-f5f27f4e1d5e',
 '54fa862e-2c93-45df-8949-d16bd9f47791',
 'c6f05973-fcd1-4a05-8998-f51c7e489acd']




LUT = {'energy': [12645,
  12647,
  12649,
  12651,
  12653,
  12655,
  12657,
  12659,
  12661,
  12663,
  12665],
 'main': [391.03828296195616,
  346.63276492027194,
  297.507765089212,
  257.41481295206256,
  210.48700891990129,
  167.68929223470892,
  122.2701657391274,
  77.58315356326722,
  34.90837617712876,
  -9.266794183172324,
  -52.36098466240465],
 'aux2': [-139.86769560126348,
  -184.35425182515647,
  -223.85633039533477,
  -273.4855059364299,
  -312.02386792549106,
  -354.5198600978057,
  -400.71462093588144,
  -445.1025316180406,
  -487.98200720920715,
  -531.9647608349758,
  -573.0856089412798]}

from xas.spectrometer import convert_roll_to_energy_for_johann_fly_scan
from xas.process import get_processed_df_from_uid


path = '/nsls2/auto-storage/iss/legacy/processed/2026/2/317954/roll_to_energy/'

def get_clean_dataframe(dataframe=None, crystal='main'):
    dataframe = dataframe.copy()
    crystals = ['main', 'aux2', 'aux3', 'aux4', 'aux5']
    crystals_that_requires_to_be_removed = [cry for cry in crystals if cry != crystal]
    for cry in crystals_that_requires_to_be_removed:
        energy_base = f"energy_{cry}"
        if energy_base in dataframe.columns:
            dataframe.pop(energy_base)
    # print(dataframe.columns)
    energy_base = f"energy_{crystal}"
    col = dataframe.pop(energy_base)
    dataframe.insert(0, energy_base, col)
    return dataframe


for uid in uids:
    print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{uid}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    _, df, _, _, _, file, _ = get_processed_df_from_uid(uid, db, save_interpolated_file=False)
    print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{file[0]}<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    hdr = db[uid]
    interpolated_df, energy_key = convert_roll_to_energy_for_johann_fly_scan(df, hdr, LUT=LUT)
    filename = os.path.basename(file[0])
    crystals = ['main', 'aux2']
    for crystal in crystals:
        energy_base = f"energy_{crystal}"
        file_name = f"{crystal}_" + filename[:-4]  + ".dat"
        dataframe = get_clean_dataframe(interpolated_df, crystal)
        np.savetxt(path + file_name, dataframe.to_numpy(), header=" ".join(dataframe.columns))



df['timestamp'] = (df.time.values - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
interpolator_func = interp1d(df['timestamp'].values, df[_stream_name].values, axis=0, kind='quadratic')
fine_timestamp = np.linspace(df['timestamp'].min(), df['timestamp'].max(), int((df['timestamp'].max() - df['timestamp'].min()) * 500))
motor_pos_fine = interpolator_func(fine_timestamp)



monitor_dict = {_stream_name : pd.DataFrame({'timestamp': fine_timestamp,
                                               _stream_name: motor_pos_fine})}


for uid in uids:
    print(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>{uid}<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
    hdr = db[uid]
    t = hdr.table(stream_name='apb_stream', fill=True)
    print(t['apb_stream'][1]['timestamp'])
    print(np.where(t['apb_stream'][1]['timestamp'] < 0))


from xas.db_io import load_apb_dataset_from_db, translate_apb_dataset, load_apb_trig_dataset_from_db, load_xs3_dataset_from_db, load_pil100k_dataset_from_db, load_apb_dataset_only_from_db, translate_apb_only_dataset, load_xia_dataset_from_db
from xas.process import clean_dict
from xas.interpolate import interpolate
raw_dict = {}
apb_df = load_apb_dataset_only_from_db(db, uid)
raw_dict = {**raw_dict, **translate_apb_only_dataset(apb_df)}
stream_name = 'pil100k2_stream'
pil100k_stream_name = 'pil100k2_stream'
pil100k_name = stream_name.split('_')[0]
apb_trigger_stream_name = f'apb_trigger_{pil100k_name}'
apb_trigger_pil100k_timestamps = load_apb_trig_dataset_from_db(db, uid, use_fall=True, stream_name=apb_trigger_stream_name)
pil100k_dict = load_pil100k_dataset_from_db(db, uid, apb_trigger_pil100k_timestamps,
                                                              pil100k_stream_name=pil100k_stream_name,
                                                              load_images=False)
raw_dict = {**raw_dict, **pil100k_dict}
raw_dict = clean_dict(raw_dict)
interpolated_df = interpolate(raw_dict, sort=False)


###################################################################
XF:08IDA-UT{Cryo:1}PS-I #Phase seperator level
XF:08IDA-UT{Cryo:1}Acc-I # Accumulator level
XF:08IDA-UT{Cryo:1}LN2Bath-I # Bath level
XF:08ID-UT{LN2-Vlv}Pos-Sts # LN2 supply valve PV
caput XF:08ID-UT{LN2-Vlv}Cmd:Opn-Cmd 1 #to open the valve
caput XF:08ID-UT{LN2-Vlv}Cmd:Cls-Cmd 1 # to close the valve

import time
import datetime
from ophyd import (Device, Component as Cpt,
                   EpicsSignal, EpicsSignalRO, DeviceStatus)

_time_fmtstr = '%Y-%m-%d %H:%M:%S'
class CryoLevel(Device):
    ps_level = Cpt(EpicsSignal, "PS-I")
    accu_level = Cpt(EpicsSignal, "Acc-I")
    bath_level = Cpt(EpicsSignal, "LN2Bath-I")

cryo_level = CryoLevel('XF:08IDA-UT{Cryo:1}', name = 'cryo_level')

class TwoButtonShutter(Device):
    # TODO: this needs to be fixed in EPICS as these names make no sense
    # the value coming out of the PV does not match what is shown in CSS
    RETRY_PERIOD = 0.5
    MAX_ATTEMPTS = 10
    open_cmd = Cpt(EpicsSignal, 'Cmd:Opn-Cmd', string=True)
    open_val = 'Open'

    close_cmd = Cpt(EpicsSignal, 'Cmd:Cls-Cmd', string=True)
    close_val = 'Not Open'

    status = Cpt(EpicsSignalRO, 'Pos-Sts', string=True)
    fail_to_close = Cpt(EpicsSignalRO, 'Sts:FailCls-Sts', string=True)
    fail_to_open = Cpt(EpicsSignalRO, 'Sts:FailOpn-Sts', string=True)
    enabled_status = Cpt(EpicsSignalRO, 'Enbl-Sts', string=True)

    # user facing commands
    open_str = 'Open'
    close_str = 'Close'

    def set(self, val):
        if self._set_st is not None:
            raise RuntimeError(f'trying to set {self.name}'
                               ' while a set is in progress')

        cmd_map = {self.open_str: self.open_cmd,
                   self.close_str: self.close_cmd}
        target_map = {self.open_str: self.open_val,
                      self.close_str: self.close_val}

        cmd_sig = cmd_map[val]
        target_val = target_map[val]

        st = DeviceStatus(self)
        if self.status.get() == target_val:
            st._finished()
            return st

        self._set_st = st
        print(self.name, val, id(st))
        enums = self.status.enum_strs

        def shutter_cb(value, timestamp, **kwargs):
            try:
                value = enums[int(value)]
            except (ValueError, TypeError):
                # we are here because value is a str not int
                # just move on
                ...
            if value == target_val:
                self._set_st = None
                self.status.clear_sub(shutter_cb)
                st._finished()

        cmd_enums = cmd_sig.enum_strs
        count = 0

        def cmd_retry_cb(value, timestamp, **kwargs):
            nonlocal count
            try:
                value = cmd_enums[int(value)]
            except (ValueError, TypeError):
                # we are here because value is a str not int
                # just move on
                ...
            count += 1
            if count > self.MAX_ATTEMPTS:
                cmd_sig.clear_sub(cmd_retry_cb)
                self._set_st = None
                self.status.clear_sub(shutter_cb)
                st._finished(success=False)
            if value == 'None':
                if not st.done:
                    time.sleep(self.RETRY_PERIOD)
                    cmd_sig.set(1)

                    ts = datetime.datetime.fromtimestamp(timestamp) \
                        .strftime(_time_fmtstr)
                    if count > 2:
                        msg = '** ({}) Had to reactuate shutter while {}ing'
                        print(msg.format(ts, val if val != 'Close'
                                         else val[:-1]))
                else:
                    cmd_sig.clear_sub(cmd_retry_cb)

        cmd_sig.subscribe(cmd_retry_cb, run=False)
        self.status.subscribe(shutter_cb)
        cmd_sig.set(1)

        return st

    def stop(self, *, success=False):
        import time
        prev_st = self._set_st
        if prev_st is not None:
            while not prev_st.done:
                time.sleep(.1)
        self._was_open = (self.open_val == self.status.get())
        st = self.set('Close')
        while not st.done:
            time.sleep(.5)

    def resume(self):
        import time
        prev_st = self._set_st
        if prev_st is not None:
            while not prev_st.done:
                time.sleep(.1)
        if self._was_open:
            st = self.set('Open')
            while not st.done:
                time.sleep(.5)

    def unstage(self):
        self._was_open = False
        return super().unstage()

    def __init__(self, *args, **kwargs):
        self._was_open = False
        super().__init__(*args, **kwargs)
        self._set_st = None
        self.read_attrs = ['status']

ln2_valve = TwoButtonShutter('XF:08ID-UT{LN2-Vlv}', name='ln2_valve')



import pandas as pd

import pandas as pd

data = {
    'Edge': [
        'Ti-K', 'V-K', 'Cr-K', 'Mn-K', 'Fe-K', 'Co-K', 'Ni-K', 'Cu-K', 'Zn-K',
        'W-L3', 'Ir-L3', 'Au-L3', 'Rb-K', 'Zr-K', 'Nb-K*', 'Mo-K', 'Ru-K*',
        'Rh-K*', 'Pd-K', 'Ag-K*', 'Cd-K*', 'In-K', 'Sn-K*', 'Sb-K*', 'Te-K'
    ],
    'Energy (eV)': [
        4950, 5465, 5989, 6539, 7112, 7709, 8333, 8979, 9659,
        10207, 11215, 11919, 15200, 17988, 18986, 20000, 22117,
        23220, 24350, 25514, 26711, 27940, 29200, 30491, 31814
    ],
    'Vertical pos (mm)': [
        0.628, 0.629, 0.629, 0.633, 0.635, 0.636, 0.636, 0.636, 0.636,
        0.636, 0.636, 0.636, 0.735, 0.785, 0.821, 0.792, 0.822,
        0.824, 0.776, 0.827, 0.727, 0.776, 0.923, 0.727, 0.889
    ],
    'I0': [
        6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 7, 8
    ],
    'It': [
        7, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 7, 8
    ],
    'Ir': [
        7, 7, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 7, 8
    ],
    'HHM Pitch (um)': [
        504.80, 504.21, 503.67, 503.12, 502.68, 502.55, 502.10, 501.77, 501.48,
        501.30, 500.98, 501.03, 499.87, 499.67, 498.53, 499.63, 498.27,
        498.25, 499.08, 498.13, 497.99, 499.04, 497.55, 497.82, 499.31
    ],
    'HHM Roll (um)': [
        473.50, 473.50, 474.00, 474.00, 474.50, 473.00, 473.00, 473.00, 473.00,
        473.50, 473.50, 472.50, 473.00, 474.00, 474.00, 474.00, 475.00,
        476.00, 482.00, 480.00, 480.00, 482.00, 484.00, 484.00, 482.00
    ],
    'HHM Y (mm)': [
        8.949, 8.793, 8.704, 8.610, 8.566, 8.499, 8.453, 8.403, 8.407,
        8.358, 8.357, 8.334, 8.230, 8.194, 8.239, 8.193, 8.222,
        8.234, 8.245, 8.233, 8.223, 8.200, 8.239, 8.255, 8.249
    ],
    'BPM ES exp time': [
        0.085, 0.085, 0.160, 0.140, 0.120, 0.130, 0.140, 0.140, 0.140,
        0.170, 0.185, 0.170, 0.235, 0.220, 0.200, 0.220, 0.225,
        0.230, 0.230, 0.230, 0.230, 0.230, 0.230, 0.230, 0.380
    ],
    'Table high': [
        45.942, 45.992, 45.996, 45.987, 46.004, 46.001, 46.036, 46.006, 45.990,
        46.064, 46.067, 46.184, 45.908, 45.805, 45.797, 45.747, 45.824,
        45.793, 45.768, 45.789, 45.805, 45.792, 45.715, 45.811, 45.517
    ]
}

# Convert to pandas DataFrame
df = pd.DataFrame(data)

df = pd.DataFrame(data).dropna().reset_index(drop=True)



columns = [['HHM Pitch (um)', 'HHM Roll (um)', 'HHM Y (mm)'],
           ['I0','It','Ir'],
           ['Vertical pos (mm)', 'BPM ES exp time', 'Table high']
           ]

def get_interpolation(energy_value, energy_array, value_array):
    f = interpolate.interp1d(energy_array, value_array, kind='cubic', fill_value='extrapolate')
    return f(energy_value)

energy = np.arange(5000, 32100, 100)

fig, ax = plt.subplots(3,3, figsize=(15,12))
for i in range(3):
    for j in range(3):
        interp = [get_interpolation(e, df['Energy (eV)'], df[columns[i][j]]) for e in energy]
        poly = np.polyfit(df['Energy (eV)'],df[columns[i][j]], deg=3)
        fit = np.polyval(poly, energy)
        ax[i,j].plot(df['Energy (eV)'], df[columns[i][j]], label=columns[i][j])
        ax[i,j].plot(energy, interp, color = 'r', label='interpolated data')
        ax[i,j].plot(energy, fit, color = 'b', label="poly fit 3 deg")
        ax[i,j].legend()
        ax[i,j].set_title(columns[i][j])
        ax[i,j].set_xlabel('Energy (eV)')
        ax[i,j].set_ylabel(columns[i][j])
plt.tight_layout()

def get_interpolation(energy_value, energy_array, value_array):
    f = interpolate.interp1d(energy_array, value_array, kind='cubic', fill_value='extrapolate')
    return f(energy_value)