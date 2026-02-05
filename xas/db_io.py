import pandas as pd
import numpy as np
from . import xray
from itertools import product
from copy import deepcopy
from xas.xas_logger import get_logger
import time as ttime
import h5py


def load_apb_dataset_from_db(db, uid):
    logger= get_logger()
    hdr = db[uid]
    logger.info(f'({ttime.ctime()}) Retrieving pizzabox data... ')
    apb_dataset = db.v2[uid]['apb_stream']['data']['apb_stream'].read()[0]
    logger.info(f'({ttime.ctime()}) Pizzabox data extracted from DB')
    apb_dataset = pd.DataFrame(apb_dataset,
                               columns=['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4'])
    #to fix the padding
    # looking for teh first negative number in difference dataset
    # apb_dataset = apb_dataset[apb_dataset['timestamp'] > 1]   Lame attempt to clean up padding
    dataset_diff  = np.diff(apb_dataset['timestamp'])

    array_of_zero_index = np.where(dataset_diff < 0)[0]

    if array_of_zero_index.size == 0:
        padding_index = len(dataset_diff)
    else:
        padding_index = array_of_zero_index[0]
    apb_dataset = apb_dataset[0:padding_index]


    logger.info(f'({ttime.ctime()}) Pizzabox data processed.')

    logger.info(f'({ttime.ctime()}) Retrieving encoder data... ')
    # apb_dataset = list(hdr.data(stream_name='apb_stream', field='apb_stream'))[0]
    energy_dataset =  db.v2[uid]['pb9_enc1']['data']['pb9_enc1'].read()[0]
    logger.info(f'({ttime.ctime()}) Encoder data received.')
    energy_dataset = pd.DataFrame(energy_dataset,
                                  columns=['ts_s', 'ts_ns', 'encoder', 'index', 'state'])
    angle_offset = -float(hdr['start']['angle_offset'])

    energy_dataset = energy_dataset[energy_dataset['ts_s'] > 1]
    # ch_offset_keys = [key for key in hdr.start.keys() if key.startswith('ch') and key.endswith('_offset')]
    # ch_offsets = np.array([hdr.start[key] for key in ch_offset_keys])

    ch_offsets = get_ch_properties(hdr.start, 'ch', '_offset')*1e3 #offsets are ib mV but the readings are in uV
    ch_gains = get_ch_properties(hdr.start, 'ch', '_amp_gain')

    apb_dataset.iloc[:, 1:] -= ch_offsets
    apb_dataset.iloc[:, 1:] /= 1e6
    apb_dataset.iloc[:, 1:] /= (10**ch_gains)

    return apb_dataset, energy_dataset, angle_offset


def load_apb_dataset_only_from_db(db, uid):
    logger = get_logger()
    hdr = db[uid]
    logger.info(f'({ttime.ctime()}) Retrieving pizzabox data... ')
    apb_dataset = list(hdr.data(stream_name='apb_stream', field='apb_stream'))[0].copy()
    logger.info(f'({ttime.ctime()}) Pizzabox data received.')
    apb_dataset = pd.DataFrame(apb_dataset,
                               columns=['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4'])
    # apb_dataset = list(hdr.data(stream_name='apb_stream', field='apb_stream'))[0]


    ch_offsets = get_ch_properties(hdr.start, 'ch', '_offset')*1e3 #offsets are ib mV but the readings are in uV
    ch_gains = get_ch_properties(hdr.start, 'ch', '_amp_gain')

    apb_dataset.iloc[:, 1:] -= ch_offsets
    apb_dataset.iloc[:, 1:] /= 1e6
    apb_dataset.iloc[:, 1:] /= (10**ch_gains)

    return apb_dataset


def get_ch_properties(hdr_start, start, end):
    ch_keys = [key for key in hdr_start.keys() if key.startswith(start) and key.endswith(end)]
    return np.array([hdr_start[key] for key in ch_keys])



def translate_apb_dataset(apb_dataset, energy_dataset, angle_offset,):
    data_dict= {}
    for column in apb_dataset.columns:
        if column != 'timestamp':
            adc = pd.DataFrame()
            adc['timestamp'] = apb_dataset['timestamp']
            adc['adc'] = apb_dataset[column]

            data_dict[column]=adc

    energy = pd.DataFrame()
    energy['timestamp'] = energy_dataset['ts_s'] + 1e-9 * energy_dataset['ts_ns']
    enc  = energy_dataset['encoder'].apply(lambda x: int(x) if int(x) <= 0 else -(int(x) ^ 0xffffff - 1))


    energy['encoder'] = xray.encoder2energy(enc, 360000, angle_offset)

    data_dict['energy'] = energy
    return data_dict

def translate_apb_only_dataset(apb_dataset):
    data_dict = {}
    for column in apb_dataset.columns:
        if column != 'timestamp':
            adc = pd.DataFrame()
            adc['timestamp'] = apb_dataset['timestamp']
            adc['adc'] = apb_dataset[column]

            data_dict[column] = adc

    return data_dict


def load_apb_trig_dataset_from_db(db, uid, use_fall=True, stream_name='apb_trigger_xs'):

    hdr = db[uid]
    # t = hdr.table(stream_name=stream_name, fill=True)
    data = list(hdr.data(stream_name=stream_name, field=stream_name))[0]
    _timestamps = np.array([f[0] for f in data])
    _transitions = np.array([f[1] for f in data])

    timestamps = _timestamps[_timestamps > 0]
    mask = _timestamps != 0

    transitions = _transitions[mask]

    # timestamps, transitions = data[:, 0], data[:, 1]
    # timestamps = t[stream_name][1]['timestamp'].values
    # transitions = t[stream_name][1]['transition'].values

    if use_fall:
        # shift = 0
        if transitions[0] == 0:
            #     shift = timestamps[1] - timestamps[0]
            timestamps = timestamps[1:]
            transitions = transitions[1:]
        # print('dfhdshdahda')
        rises = timestamps[0::2]
        falls = timestamps[1::2]
        n_0 = np.sum(transitions == 0)
        n_1 = np.sum(transitions == 1)
        n_all = np.min([n_0, n_1])
        apb_trig_timestamps = (rises[:n_all] + falls[:n_all]) / 2 #- shift
        # apb_trig_timestamps = (timestamps[transitions == 1][:n_all] + timestamps[transitions == 0][:n_all])/2

    else:
        n_0 = np.sum(transitions == 0)
        n_1 = np.sum(transitions == 1)
        n_all = np.min([n_0, n_1])
        rises = timestamps[transitions == 1]
        apb_trig_timestamps = rises[:n_all] + np.mean(np.diff(rises))/2
    return apb_trig_timestamps

# this is old
def load_xs3_dataset_from_db_legacy(db, uid, apb_trig_timestamps):
    hdr = db[uid]
    t = hdr.table(stream_name='xs_stream', fill=True)['xs_stream']
    # n_spectra = t.size
    n_spectra = min(t.size, apb_trig_timestamps.size)
    xs_timestamps = apb_trig_timestamps[:n_spectra]
    chan_roi_names = [f'CHAN{c}ROI{r}' for c, r in product([1, 2, 3, 4], [1, 2, 3, 4])]
    spectra = {}

    for j, chan_roi in enumerate(chan_roi_names):
        this_spectrum = np.zeros(n_spectra)

        for i in range(n_spectra):
            this_spectrum[i] = t[i+1][chan_roi]

        spectra[chan_roi] = pd.DataFrame(np.vstack((xs_timestamps, this_spectrum)).T, columns=['timestamp', chan_roi])

    return spectra

# this is compatible with new handlers
def load_xs3_dataset_from_db(db, uid, apb_trig_timestamps):
    hdr = db[uid]
    t = hdr.table(stream_name='xs_stream', fill=True)
    # n_spectra = t.size
    n_spectra = min(t['xs_ch01_roi01'][1].size, apb_trig_timestamps.size)
    xs_timestamps = apb_trig_timestamps[:n_spectra]
    # chan_roi_names = [f'CHAN{c}ROI{r}' for c, r in product([1, 2, 3, 4], [1, 2, 3, 4])]
    chan_roi_names = [f'xs_ch{c:02d}_roi{r:02d}' for r, c in product([1, 2, 3, 4], [1, 2, 3, 4])]
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



def load_xia_dataset_from_db(db, uid, apb_trig_timestamps):
    hdr = db[uid]
    t = hdr.table(stream_name='ge_detector_stream', fill=True)
    n_spectra = min(t['ge_detector_channels_mca1_R0'][1].size, apb_trig_timestamps.size)
    xs_timestamps = apb_trig_timestamps[:n_spectra]
    chan_roi_names = [f'ge_detector_channels_mca{i}_R{j}' for i, j in product(range(1,33), range(4))]
    # chan_roi_names = [f'ge_detector_channels_mca{i}_R0' for i in range(1, 33)]
    spectra = {}

    for j, chan_roi in enumerate(chan_roi_names):
        this_spectrum = t[chan_roi][1][:n_spectra]/100000

        spectra[chan_roi] = pd.DataFrame(np.vstack((xs_timestamps, this_spectrum)).T,
                                         columns=['timestamp', chan_roi])

    return spectra




pil100k_legacy_keys_match = {   'pil100k_ROI1': 'pil100k_roi1',
                                'pil100k_ROI2': 'pil100k_roi2',
                                'pil100k_ROI3': 'pil100k_roi3',
                                'pil100k_ROI4': 'pil100k_roi4',
                                'image' : 'pil100k_image'}

def _load_pil100k_dataset_from_db_legacy(db, uid, apb_trig_timestamps, input_type='hdf5'):
    hdr = db[uid]
    spectra = {}
    if input_type == 'tiff':
        t = hdr.table(stream_name='pil100k_stream', fill=True)['pil100k_stream']
        # n_images = t.shape[0]
        n_images = min(t.size, apb_trig_timestamps.size)
        pil100k_timestamps = apb_trig_timestamps[:n_images]

        image_array = np.array([i for i in t])
        rois = hdr.start['roi']


        for j in range(4):
            x, y, dx, dy = rois[j]
            this_spectrum = np.sum(image_array[:, y: (y + dy), x: (x + dx)], axis=(1,2)) # NOTE : flipped X and Y

            spectra[f'pil100k_ROI{j+1}'] = pd.DataFrame(np.vstack((pil100k_timestamps, this_spectrum)).T, columns=['timestamp', f'pil100k_ROI{j+1}'])
    elif input_type == 'hdf5':
        t = hdr.table(stream_name='pil100k_stream', fill=True)['pil100k_stream']
        # n_images = t.shape[0]
        n_images = min(t.size, apb_trig_timestamps.size)
        pil100k_timestamps = apb_trig_timestamps[:n_images]
        keys = t[1].tolist().keys()
        # keys = [k for k in t[1].keys() if ('roi' in k.lower())] # do only those with roi in the name
        output = {}
        for key in keys:
            arr = [t[i+1].tolist()[key] for i in range(n_images)]
            upd_key = pil100k_legacy_keys_match[key]
            output[upd_key] = pd.DataFrame({'timestamp': pil100k_timestamps, upd_key: arr})
        return output


def _load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name='pil100k_stream', load_images=False):
    logger = get_logger()
    hdr = db[uid]
    output = {}
    # t = hdr.table(stream_name='pil100k_stream', fill=True)
    pil100k_name = pil100k_stream_name.split('_')[0]
    field_list = [f'{pil100k_name}_roi{i}' for i in range(1, 5)]#, 'pil100k_image']

    _t = {field : list(hdr.data(stream_name=pil100k_stream_name, field=field))[0] for field in field_list}
    #WIP
    if load_images:
        logger.info(f'({ttime.ctime()}) Loading Pilatus images...')
        # _t[f'{pil100k_name}_image'] = [i for i in list(hdr.data(stream_name=pil100k_stream_name, field=f'{pil100k_name}_image'))[0]]
        start = ttime.time()
        path_hdf5_file = ["/"+doc['resource_path'] for name, doc in hdr.documents() if name == 'resource' and doc['spec'] == "PIL100k_HDF5"][0]
        with h5py.File(path_hdf5_file, 'r') as f:
            arry = f['entry/data/data'][()]
        _t[f'{pil100k_name}_image'] = list(arry)
        print(f"Total time to load Pilatus images: {ttime.time()-start}")
        logger.info(f'({ttime.ctime()}) Pilatus images loading is complete.')
    t = pd.DataFrame(_t)
    # n_images = t.shape[0]
    n_images = min(t[f'{pil100k_name}_roi1'].size, apb_trig_timestamps.size)
    pil100k_timestamps = apb_trig_timestamps[:n_images]
    keys = [k for k in t.keys() if (k != 'time') ]#and (k != 'pil100k_image')]
    t = t[:n_images]
    for j, key in enumerate(keys):
        output[key] = pd.DataFrame(np.vstack((pil100k_timestamps, t[key])).T, columns=['timestamp', f'{key}'])
    return output


# def _load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name='pil100k_stream', load_images=False):
#     logger = get_logger()
#     hdr = db[uid]
#     output = {}
#     # t = hdr.table(stream_name='pil100k_stream', fill=True)
#     pil100k_name = pil100k_stream_name.split('_')[0]
#     field_list = [f'{pil100k_name}_roi{i}' for i in range(1, 5)]#, 'pil100k_image']
#
#     _t = {field : list(hdr.data(stream_name=pil100k_stream_name, field=field))[0] for field in field_list}
#     #WIP
#     if load_images:
#         logger.info(f'({ttime.ctime()}) Loading Pilatus images...')
#         start = ttime.time()
#         _t[f'{pil100k_name}_image'] = [i for i in list(hdr.data(stream_name=pil100k_stream_name, field=f'{pil100k_name}_image'))[0]]
#         print(f"Total time to load Pilatus images: {ttime.time()-start}")
#         logger.info(f'({ttime.ctime()}) Pilatus images loading is complete.')
#     t = pd.DataFrame(_t)
#     # n_images = t.shape[0]
#     n_images = min(t[f'{pil100k_name}_roi1'].size, apb_trig_timestamps.size)
#     pil100k_timestamps = apb_trig_timestamps[:n_images]
#     keys = [k for k in t.keys() if (k != 'time') ]#and (k != 'pil100k_image')]
#     t = t[:n_images]
#     for j, key in enumerate(keys):
#         output[key] = pd.DataFrame(np.vstack((pil100k_timestamps, t[key])).T, columns=['timestamp', f'{key}'])
#     return output

def read_pilatus_data_from_documents(hdr=None, stream_name=None):
    docs = hdr.documents

    pass

def load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name='pil100k_stream', load_images=False):
    try:
        return _load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name=pil100k_stream_name, load_images=load_images)
    except Exception as e:
        print(f'Failed to read pilatus data. Reason: {e}')
        print('Attempting to use legacy loader')
        return _load_pil100k_dataset_from_db_legacy(db, uid, apb_trig_timestamps, input_type='hdf5')


class MockHeader:
    def __init__(self, start: dict, stop: dict, stream_names: list):
        self.start = start
        self.stop = stop
        self.stream_names = stream_names

    @classmethod
    def from_header(cls, hdr):
        start = dict(hdr.start)
        stop = dict(hdr.stop)
        stream_names = hdr.stream_names
        return cls(start, stop, stream_names)

    def update_start(self, update_dict):
        for k, v in update_dict.items():
            self.start[k] = v

def update_header_start(hdr, update_start_dict):
    new_hdr = MockHeader.from_header(hdr)
    new_hdr.update_start(update_start_dict)
    return new_hdr

def get_all_uids_for_proposal(db, year, cycle, proposal, keys=['experiment']):
    year = str(year)
    cycle = str(cycle)
    proposal = str(proposal)
    runs = db.v2.search({'year': year, 'cycle' : cycle, 'PROPOSAL' : proposal})

    uids = []
    for uid in runs:
        start = runs[uid].metadata['start']
        if all((k in start.keys()) for k in keys):
            uids.append(uid)
    return uids


def get_fly_uids_for_proposal(db, year, cycle, proposal):
    year = str(year)
    cycle = str(cycle)
    proposal = str(proposal)
    runs = db.v2.search({'year': year, 'cycle' : cycle, 'PROPOSAL' : proposal, 'experiment' : 'fly_scan'})
    return list(runs)

from collections import OrderedDict
import pandas as pd
def get_uid_tree_for_proposal(db, year, cycle, proposal):
    year = str(year)
    cycle = str(cycle)
    proposal = str(proposal)
    runs = db.v2.search({'year': year, 'cycle': cycle, 'PROPOSAL': proposal})

    uid_df = []
    for uid in runs:
        start = runs[uid].metadata['start']
        if 'experiment' in start.keys():
            uid_dict = {'scan_group_uid' : None,
                        'uid' : uid,
                        'experiment' : start['experiment'],
                        'name': start['interp_filename'],
                        'kind' : 'default'}
            if 'scan_group_uid' in start.keys():
                uid_dict['scan_group_uid'] = start['scan_group_uid']
            uid_df.append(uid_dict)
    uid_df = pd.DataFrame(uid_df)
    uid_df['grouped'] = False

    output = []
    for i, row in uid_df.iterrows():
        if not row['grouped']:
            if ((row['scan_group_uid'] is None) or
                ((uid_df['scan_group_uid'] == row['scan_group_uid']).sum() == 1)):
                output_row = row.to_dict()
                output_row.pop('scan_group_uid')
                output_row.pop('grouped')
            else:
                output_row = {'scan_group_uid' : row['scan_group_uid']}
                uids_loc = uid_df[uid_df['scan_group_uid'] == row['scan_group_uid']]
                uids_loc = uids_loc.drop(['scan_group_uid', 'grouped'], axis=1)
                output_row['uids'] = uids_loc.to_dict(orient='records')
            output.append(output_row)
            uid_df[uid_df['scan_group_uid'] == row['scan_group_uid']]['grouped'] = True

    return output







    #
    #
    # return uid_list


def plot_normalized(x, y, factor=1):
    x = np.array(x)
    y = np.array(y)

    y_norm = (y - y.min())/factor
    plt.plot(x, y_norm)


def plot_normalized_scan(db, uid, factor=1):
    hdr = db[uid]
    x = list(hdr.data('hhm_energy'))
    y = list(hdr.data('pil100k_stats1_total'))
    plot_normalized(x, y, factor)











