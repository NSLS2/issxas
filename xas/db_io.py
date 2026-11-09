import pandas as pd
import numpy as np
from . import xray
from itertools import product
from copy import deepcopy
from xas.xas_logger import get_logger
import time as ttime


def _get_stream_data_node(hdr, stream_name):
    """Navigate to the data node of a stream once.

    Returns the Tiled data node so callers can read multiple fields without
    re-traversing the node tree (each traversal costs HTTP round-trips).
    Returns None for legacy Brokers, which use hdr.data() instead.
    """
    if hasattr(hdr, 'v2'):
        return hdr.v2[stream_name]['data']
    return None


def _read_field_from_node(node, hdr, stream_name, field):
    """Read one field from a pre-navigated stream data node.

    Pass the node returned by _get_stream_data_node().  Falls back to
    hdr.data() when node is None (legacy Broker).  Always returns ndarray.
    """
    if node is not None:
        return np.asarray(node[field].read())
    values = list(hdr.data(stream_name=stream_name, field=field))
    if len(values) == 1:
        value = values[0]
        if isinstance(value, pd.DataFrame):
            return value.to_records(index=False)
        return np.asarray(value)
    return np.asarray(values)


def _read_tiled_field(hdr, stream_name, field):
    """Read one field, navigating from the run root each time.

    Use _get_stream_data_node() + _read_field_from_node() instead when
    reading multiple fields from the same stream, to avoid re-traversing
    the node tree for every field.
    """
    node = _get_stream_data_node(hdr, stream_name)
    return _read_field_from_node(node, hdr, stream_name, field)


def _read_tiled_records(hdr, stream_name, field, columns):
    values = _read_tiled_field(hdr, stream_name, field)
    if values.dtype.names:
        return pd.DataFrame(values.ravel(), columns=columns)
    return pd.DataFrame(values.reshape(-1, len(columns)), columns=columns)


def _read_records_from_node(node, hdr, stream_name, field, columns):
    values = _read_field_from_node(node, hdr, stream_name, field)
    if values.dtype.names:
        return pd.DataFrame(values.ravel(), columns=columns)
    return pd.DataFrame(values.reshape(-1, len(columns)), columns=columns)


def load_apb_dataset_from_db(db, uid, hdr=None):
    logger= get_logger()
    if hdr is None:
        hdr = db[uid]
    start = dict(hdr.start)
    logger.info(f'({ttime.ctime()}) Retrieving pizzabox data... ')
    # Navigate to apb_stream data node once — avoids re-traversing the Tiled
    # node tree for the second field read (pb9_enc1 uses its own node below).
    apb_node = _get_stream_data_node(hdr, 'apb_stream')
    apb_dataset = _read_records_from_node(
        apb_node, hdr, 'apb_stream', 'apb_stream',
        ['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4']
    ).astype('float64')
    logger.info(f'({ttime.ctime()}) Pizzabox data extracted from DB')
    #to fix the padding
    # looking for teh first negative number in difference dataset
    # apb_dataset = apb_dataset[apb_dataset['timestamp'] > 1]   Lame attempt to clean up padding
    dataset_diff  = np.diff(apb_dataset['timestamp'])

    # array_of_zero_index = np.where(dataset_diff < 0)[0]
    array_of_zero_index = np.where(dataset_diff < -0.01)[0]
    # scan uid = 'ed77df59-48cf-44ed-b09d-861a11d5e4b7'
    # In [32]: apb_dataset['timestamp'][647]
    # Out[32]: 1782911883.0031967
    #
    # In [33]: apb_dataset['timestamp'][648]
    # Out[33]: 1782911883.0083911
    #
    # In [34]: apb_dataset['timestamp'][649]
    # Out[34]: 1782911883.005197 What is going on why recoded timestamp goes backward

    if array_of_zero_index.size == 0:
        padding_index = len(dataset_diff)
    else:
        padding_index = array_of_zero_index[0]
    apb_dataset = apb_dataset[0:padding_index]

    logger.info(f'({ttime.ctime()}) Pizzabox data processed.')

    logger.info(f'({ttime.ctime()}) Retrieving encoder data... ')
    enc_node = _get_stream_data_node(hdr, 'pb9_enc1')
    energy_dataset = _read_records_from_node(
        enc_node, hdr, 'pb9_enc1', 'pb9_enc1',
        ['ts_s', 'ts_ns', 'encoder', 'index', 'state']
    )
    logger.info(f'({ttime.ctime()}) Encoder data received.')
    angle_offset = -float(start['angle_offset'])

    energy_dataset = energy_dataset[energy_dataset['ts_s'] > 1]

    ch_offsets = get_ch_properties(start, 'ch', '_offset')*1e3 #offsets are ib mV but the readings are in uV
    ch_gains = get_ch_properties(start, 'ch', '_amp_gain')

    apb_dataset.iloc[:, 1:] -= ch_offsets
    apb_dataset.iloc[:, 1:] /= 1e6
    apb_dataset.iloc[:, 1:] /= (10**ch_gains)

    return apb_dataset, energy_dataset, angle_offset


def load_apb_dataset_only_from_db(db, uid, hdr=None):
    logger = get_logger()
    if hdr is None:
        hdr = db[uid]
    start = dict(hdr.start)
    logger.info(f'({ttime.ctime()}) Retrieving pizzabox data... ')
    apb_node = _get_stream_data_node(hdr, 'apb_stream')
    apb_dataset = _read_records_from_node(
        apb_node, hdr, 'apb_stream', 'apb_stream',
        ['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4']
    ).astype('float64')
    logger.info(f'({ttime.ctime()}) Pizzabox data received.')

    ch_offsets = get_ch_properties(start, 'ch', '_offset')*1e3 #offsets are ib mV but the readings are in uV
    ch_gains = get_ch_properties(start, 'ch', '_amp_gain')

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


def load_apb_trig_dataset_from_db(db, uid, use_fall=True, stream_name='apb_trigger_xs', hdr=None):
    if hdr is None:
        hdr = db[uid]
    trig_node = _get_stream_data_node(hdr, stream_name)
    data = _read_records_from_node(trig_node, hdr, stream_name, stream_name, ['timestamp', 'transition'])
    _timestamps = data['timestamp'].to_numpy()
    _transitions = data['transition'].to_numpy()

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
def load_xs3_dataset_from_db(db, uid, apb_trig_timestamps, hdr=None):
    if hdr is None:
        hdr = db[uid]
    chan_roi_names = [f'xs_ch{c:02d}_roi{r:02d}' for r, c in product([1, 2, 3, 4], [1, 2, 3, 4])]
    # Navigate to the xs_stream data node once — reading 16 fields from one
    # node avoids 16 separate tree traversals (each ~5 HTTP requests).
    xs_node = _get_stream_data_node(hdr, 'xs_stream')
    t = {field: _read_field_from_node(xs_node, hdr, 'xs_stream', field).ravel() for field in chan_roi_names}
    # n_spectra = t.size
    n_spectra = min(*(values.size for values in t.values()), apb_trig_timestamps.size)
    xs_timestamps = apb_trig_timestamps[:n_spectra]
    # chan_roi_names = [f'CHAN{c}ROI{r}' for c, r in product([1, 2, 3, 4], [1, 2, 3, 4])]
    chan_roi_names = [f'xs_ch{c:02d}_roi{r:02d}' for r, c in product([1, 2, 3, 4], [1, 2, 3, 4])]
    spectra = {}

    for j, chan_roi in enumerate(chan_roi_names):
        # this_spectrum = np.zeros(n_spectra)
        this_spectrum = t[chan_roi][:n_spectra]/100000
        # for i in range(n_spectra):
        # this_spectrum[i] = t[i+1][chan_roi]
        # this_spectrum[i] = t[chan_roi][i + 1]

        spectra[chan_roi] = pd.DataFrame(np.vstack((xs_timestamps, this_spectrum)).T,
                                         columns=['timestamp', chan_roi])

    return spectra



def load_xia_dataset_from_db(db, uid, apb_trig_timestamps, hdr=None):
    if hdr is None:
        hdr = db[uid]
    chan_roi_names = [f'ge_detector_channels_mca{i}_R{j}' for i, j in product(range(1,33), range(4))]
    # Navigate to the ge_detector_stream data node once — 128 fields from one node.
    xia_node = _get_stream_data_node(hdr, 'ge_detector_stream')
    t = {field: _read_field_from_node(xia_node, hdr, 'ge_detector_stream', field).ravel() for field in chan_roi_names}
    n_spectra = min(*(values.size for values in t.values()), apb_trig_timestamps.size)
    xs_timestamps = apb_trig_timestamps[:n_spectra]
    # chan_roi_names = [f'ge_detector_channels_mca{i}_R0' for i in range(1, 33)]
    spectra = {}

    for j, chan_roi in enumerate(chan_roi_names):
        this_spectrum = t[chan_roi][:n_spectra]/100000

        spectra[chan_roi] = pd.DataFrame(np.vstack((xs_timestamps, this_spectrum)).T,
                                         columns=['timestamp', chan_roi])

    return spectra




pil100k_legacy_keys_match = {   'pil100k_ROI1': 'pil100k_roi1',
                                'pil100k_ROI2': 'pil100k_roi2',
                                'pil100k_ROI3': 'pil100k_roi3',
                                'pil100k_ROI4': 'pil100k_roi4',
                                'image' : 'pil100k_image'}

def _load_pil100k_dataset_from_db_legacy(db, uid, apb_trig_timestamps, input_type='hdf5', hdr=None):
    if hdr is None:
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


def _load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name='pil100k_stream', load_images=False, hdr=None):
    logger = get_logger()
    if hdr is None:
        hdr = db[uid]
    output = {}
    pil100k_name = pil100k_stream_name.split('_')[0]
    field_list = [f'{pil100k_name}_roi{i}' for i in range(1, 5)]#, 'pil100k_image']

    # Navigate to the pil100k stream data node once for all ROI fields.
    pil_node = _get_stream_data_node(hdr, pil100k_stream_name)
    _t = {field: _read_field_from_node(pil_node, hdr, pil100k_stream_name, field).ravel() for field in field_list}
    n_images = min(*(len(values) for values in _t.values()), len(apb_trig_timestamps))
    _t = {field: values[:n_images] for field, values in _t.items()}
    if load_images:
        logger.info(f'({ttime.ctime()}) Loading Pilatus images...')
        start = ttime.time()
        images = _read_field_from_node(pil_node, hdr, pil100k_stream_name, f'{pil100k_name}_image')
        if images.ndim == 4 and images.shape[0] == 1:
            images = images[0]
        n_images = min(n_images, len(images))
        _t = {field: values[:n_images] for field, values in _t.items()}
        _t[f'{pil100k_name}_image'] = list(images[:n_images])
        print(f"Total time to load Pilatus images: {ttime.time()-start}")
        logger.info(f'({ttime.ctime()}) Pilatus images loading is complete.')
    t = pd.DataFrame(_t)
    # n_images = t.shape[0]
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

def load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name='pil100k_stream', load_images=False, hdr=None):
    try:
        return _load_pil100k_dataset_from_db(db, uid, apb_trig_timestamps, pil100k_stream_name=pil100k_stream_name, load_images=load_images, hdr=hdr)
    except Exception as e:
        print(f'Failed to read pilatus data. Reason: {e}')
        print('Attempting to use legacy loader')
        return _load_pil100k_dataset_from_db_legacy(db, uid, apb_trig_timestamps, input_type='hdf5', hdr=hdr)


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





