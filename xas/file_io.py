from datetime import datetime
import os
from subprocess import call
import numpy as np
import pandas as pd
from . import xray
from PIL import Image
import h5py
from xas.metadata import generate_file_header_from_hdr


def _shift_root(fpath):
    if not fpath.startswith('/'):
        fpath = '/' + fpath
    if fpath.startswith('/nsls2/xf08id'):
        print('changing root "/nsls2/xf08id" to "/nsls2/data/iss/legacy/backup"')
        fpath = fpath.replace('/nsls2/xf08id', '/nsls2/data/iss/legacy/backup')
    return fpath


def load_dataset_from_files(db, uid):
    def load_adc_trace(filename=''):
        df=pd.DataFrame()
        keys = ['times', 'timens', 'counter', 'adc']
        if os.path.isfile(filename):
            df_raw = pd.read_table(filename, delim_whitespace=True, comment='#', names=keys, index_col=False)
            df['timestamp'] = df_raw['times'] + 1e-9 * df_raw['timens']
            df['adc'] = df_raw['adc'].apply(lambda x: (int(x, 16) >> 8) - 0x40000 if (int(x, 16) >> 8) > 0x1FFFF else int(x, 16) >> 8) * 7.62939453125e-05
            return df
        else:
            return -1

    def load_enc_trace(filename=''):
        df = pd.DataFrame()
        keys = ['times', 'timens', 'encoder', 'counter', 'di']
        if os.path.isfile(filename):
            df_raw = pd.read_table(filename, delim_whitespace=True, comment='#', names=keys, index_col=False)
            df['timestamp'] = df_raw['times'] + 1e-9 * df_raw['timens']
            df['encoder'] = df_raw['encoder'].apply(lambda x: int(x) if int(x) <= 0 else -(int(x) ^ 0xffffff - 1))
            return df
        else:
            return -1

    def load_trig_trace(filename=''):
        keys = ['times', 'timens', 'encoder', 'counter', 'di']
        if os.path.isfile(filename):
            df = pd.read_table(filename, delim_whitespace=True, comment='#', names=keys,
                               index_col=False)
            df['timestamp'] = df['times'] + 1e-9 * df['timens']
            df = df.iloc[::2]
            return df.iloc[:, [5, 3]]
        else:
            return -1

    arrays = {}
    record = db[uid]
    for stream in record['descriptors']:
        data = pd.DataFrame()
        stream_device = stream['name']
        stream_name = stream['data_keys'][stream['name']]['devname']
        stream_source = stream['data_keys'][stream['name']]['source']
        stream_file = stream['data_keys'][stream['name']]['filename']
        #print(stream_file)

        if stream_source == 'pizzabox-di-file':
            data = load_trig_trace(stream_file)
        if stream_source == 'pizzabox-adc-file':
            #print(stream_device)
            data = load_adc_trace(stream_file)
            stream_offset = f'{stream_device} offset'
            if stream_offset in db[uid]['start']:
                #print("subtracting offset")
                data.iloc[:, 1] = data.iloc[:, 1] - record['start'][stream_offset]
            stream_gain =  f'{stream_device} gain'
            if stream_gain in db[uid]['start']:
                #print("correcting for gain")
                data.iloc[:, 1] = data.iloc[:, 1]/(10**record['start'][stream_gain])


        if stream_source == 'pizzabox-enc-file':
            data = load_enc_trace(stream_file)
            #print(stream_name)
            if stream_name =='hhm_theta':
                data.iloc[:,1] = xray.encoder2energy(data['encoder'], 360000,
                                                       -float(record['start']['angle_offset']))
                stream_name = 'energy'
                #print(stream_name)

        arrays[stream_name] = data

    return arrays

def validate_file_exists(path_to_file,file_type = 'interp'):
    """The function checks if the file exists or not. If exists, it adds an index to the file name.
    """
    if file_type == 'interp':
        prefix = 'r'
    elif file_type == 'bin':
        prefix = 'b'
    if os.path.isfile(path_to_file):
        (path, extension) = os.path.splitext(path_to_file)
        iterator = 2

        while True:

            new_filename = '{}-{}{:04d}{}'.format(path, prefix, iterator,extension)
            if not os.path.isfile(new_filename):
                return new_filename
            iterator += 1
    else:
        return path_to_file

def make_user_dir(path):
    folder_exists = os.path.isdir(path)
    if not folder_exists:
        os.mkdir(path)
        call(['chmod', '777', path])
    return folder_exists

def validate_path_exists(path_to_file):
    (path, filename) = os.path.split(path_to_file)
    if not os.path.isdir(path):
        os.mkdir(path)
        call(['chmod', '777', path])


def _get_value_from_hdr_start(hdr, key):
    if key in hdr['start']:
        return hdr['start'][key]
    else:
        return ''

def create_file_header(hdr):
    return generate_file_header_from_hdr(hdr)

def find_e0(hdr):
    # e0 = -1
    try:
        return float(hdr.start['e0'])
    except:
        return -1
    # if 'e0' in hdr.start:
    #     if hdr.start['e0'] is not None:
    #         e0 =
    # return e0


def split_df_data_into_primary_and_extended(df_orig):
    sec_cols = []
    for c in df_orig.columns:
        if len(df_orig[c][0].shape) > 0:
            sec_cols.append(c)

    if len(sec_cols) > 0:
        df = df_orig.copy()
        for col in sec_cols:
            df.pop(col)
        df_sec = df_orig[sec_cols]
    else:
        df = df_orig
        df_sec = None
    return df, df_sec



def save_interpolated_df_as_file(path_to_file, df_orig, comments):
    df, df_sec = split_df_data_into_primary_and_extended(df_orig)
    # TODO: save the interpolated data in df_sec somewhere

    cols = df.columns.tolist()
    fmt = '%17.6f ' + '%12.6e ' + (' '.join(['%12.6e' for i in range(len(cols)-2)]))
    header = '# ' + ' '.join(cols)

    df = df[cols]
    np.savetxt(path_to_file,
               df.values,
               fmt=fmt,
               delimiter=" ",
               header=header,
               comments=comments)

    #print("changing permissions to 774")
    call(['chmod', '774', path_to_file])


# def dump_uid_bundle(base_name, uids, db):
#     path_to_interp_file = db[uids[0]].start()['interp_filename']
#     (path, extension) = os.path.splitext(path_to_interp_file)





def save_binned_df_as_file(path_to_file, df_orig, comments):
    df, df_sec = split_df_data_into_primary_and_extended(df_orig)
    (path, extension) = os.path.splitext(path_to_file)
    path_to_file = path + '.dat'
    path_to_file = validate_file_exists(path_to_file, file_type = 'bin')


    #cols = df.columns.tolist()[::-1]
    cols = df.columns.tolist()
    cols = cols[-1:] + cols[:-1]
    fmt = '%12.6f ' + (' '.join(['%12.6e' for i in range(len(cols) - 1)]))
    header = '  '.join(cols)

    df = df[cols]
    np.savetxt(path_to_file,
               df.values,
               fmt=fmt,
               delimiter=" ",
               header=f'# {header}',
               comments=comments)

    #print("changing permissions to 774")
    call(['chmod', '774', path_to_file])

    if df_sec is not None:
        folder, file = os.path.split(path_to_file)
        folder = os.path.join(folder, 'extended_data')
        filename, _ = os.path.splitext(file)
        path_to_json = os.path.join(folder, filename + '.json')

        try:
            os.mkdir(folder)
        except FileExistsError:
            pass

        df_sec.to_json(path_to_json, orient='records')






def load_interpolated_df_from_file(filename):
    ''' Load interp file and return'''

    if not os.path.exists(filename):
        raise IOError(f'The file {filename} does not exist.')
    header = read_header(filename)
    keys = header[header.rfind('#'):][1:-1].split()
    df = pd.read_csv(filename, sep=r'\s+', comment='#', names=keys, index_col=False)
    if 'energy' in [i.lower() for i in df.columns]: # i am sorry /// Denis
        df = df.sort_values('energy'.lower())
    return df, header

def convert_path_to_file_to_path_to_ext_file(path_to_file, ext_data_path='extended_data'):
    folder, file = os.path.split(path_to_file)
    folder = os.path.join(folder, ext_data_path)
    filename, _ = os.path.splitext(file)
    filename += '.h5'
    return os.path.join(folder, filename)


def load_binned_df_and_extended_data_from_file(path_to_file, ext_data_path='extended_data'):
    df, header = load_binned_df_from_file(path_to_file)
    path_to_ext_file = convert_path_to_file_to_path_to_ext_file(path_to_file, ext_data_path=ext_data_path)
    ext_data = load_extended_data_from_file(path_to_ext_file)
    return df, ext_data, header


def load_binned_df_from_file(filename):
    ''' Load interp file and return'''

    if not os.path.exists(filename):
        raise IOError(f'The file {filename} does not exist.')
    header = read_header(filename)
    keys = header[header.rfind('#'):][1:-1].split()
    df = pd.read_csv(filename, sep=r'\s+', comment='#', names=keys, index_col=False)

    energy_key = None
    for col in df.columns:
        if ('energy' in col.lower()):# or ('e' in col.lower()):
            energy_key = col
            break

    if energy_key:
        df = df.rename(columns={energy_key: 'energy'})
        df = df.sort_values('energy')

    # if 'energy' not in df.columns:
    #     df['energy'] = np.arange(len(df.index))

    return df, header

def read_header(filename):
    header = ''
    line = '#'
    with open(filename) as myfile:
        while line[0] == '#':
            line = next(myfile)
            header += line
    return header[:-len(line)]

def convert_header_to_dict(header):
    lines = header.split('\n')
    lines = [line for line in lines if len(line) > 0]
    lines = [line.replace('# ', '') for line in lines]



#TODO add channels for XIA

stepscan_channel_dict = {
    'hhm_energy': 'energy',
    'motor_emission_energy' : 'energy',
    'johann_emission_energy' : 'energy',
    'apb_ave_ch1_mean': 'i0',
    'apb_ave_ch2_mean': 'it',
    'apb_ave_ch3_mean': 'ir',
    'apb_ave_ch4_mean': 'iff',
    'apb_ave_ch5_mean': 'aux1',
    'apb_ave_ch6_mean': 'aux2',
    'apb_ave_ch7_mean': 'aux3',
    'apb_ave_ch8_mean': 'aux4',
    # 'pil100k_stats1_total': 'pil100_ROI1',
    # 'pil100k_stats2_total': 'pil100_ROI2',
    # 'pil100k_stats3_total': 'pil100_ROI3',
    # 'pil100k_stats4_total': 'pil100_ROI4',
    'pil100k_stats1_total': 'pil100k_roi1',
    'pil100k_stats2_total': 'pil100k_roi2',
    'pil100k_stats3_total': 'pil100k_roi3',
    'pil100k_stats4_total': 'pil100k_roi4',
    'pil100k_image': 'pil100k_image',
    'pil100k2_stats1_total': 'pil100k2_roi1',
    'pil100k2_stats2_total': 'pil100k2_roi2',
    'pil100k2_stats3_total': 'pil100k2_roi3',
    'pil100k2_stats4_total': 'pil100k2_roi4',
    'pil100k2_image': 'pil100k2_image',
    'xs_channel1_rois_roi01_value' : 'xs_ch01_roi01',
    'xs_channel2_rois_roi01_value' : 'xs_ch01_roi02',
    'xs_channel3_rois_roi01_value' : 'xs_ch01_roi03',
    'xs_channel4_rois_roi01_value' : 'xs_ch01_roi04',
    'xs_channel1_rois_roi02_value' : 'xs_ch02_roi01',
    'xs_channel2_rois_roi02_value' : 'xs_ch02_roi02',
    'xs_channel3_rois_roi02_value' : 'xs_ch02_roi03',
    'xs_channel4_rois_roi02_value' : 'xs_ch02_roi04',
    'xs_channel1_rois_roi03_value' : 'xs_ch03_roi01',
    'xs_channel2_rois_roi03_value' : 'xs_ch03_roi02',
    'xs_channel3_rois_roi03_value' : 'xs_ch03_roi03',
    'xs_channel4_rois_roi03_value' : 'xs_ch03_roi04',
    'xs_channel1_rois_roi04_value' : 'xs_ch04_roi01',
    'xs_channel2_rois_roi04_value' : 'xs_ch04_roi02',
    'xs_channel3_rois_roi04_value' : 'xs_ch04_roi03',
    'xs_channel4_rois_roi04_value' : 'xs_ch04_roi04',
    'xs_roi01': 'xs_roi01',
    'xs_roi02': 'xs_roi02',
    'xs_roi03': 'xs_roi03',
    'xs_roi04': 'xs_roi04',
    }


for j in range(1,33):
    for k in range(1):
        key =  f'ge_detector_channels_mca{j}_R{k}'
        value = f'xia_mca_ch{j}_roi{k}'
        stepscan_channel_dict[key]=value

for j in range(1,33):
    for k in range(1):
        key =  f'ge_detector_scas_dxp{j}_counts'
        value = f'xia_sca_ch{j}_roi{k}'
        stepscan_channel_dict[key]=value

for k in range(1):
    key = f'xia_mca_roi{k}'
    stepscan_channel_dict[key]=key

for k in range(1):
    key = f'xia_sca_roi{k}'
    stepscan_channel_dict[key]=key

xia_mca_channel_list = []
for j in range(1,33):
    for k in range(1):
        xia_mca_channel_list.append(f'xia_mca_ch{j}_roi{k}')

xia_sca_channel_list = []
for j in range(1,33):
    for k in range(1):
        xia_sca_channel_list.append(f'xia_sca_ch{j}_roi{k}')


# ge_detector_channels_mca_list = {k:f"ge_detector_channles_mca{j}_R{k}" for j, k in product(range(1,33), range(4))}
ge_detector_channels_mca_dict = {}
for i in range(4):
    ge_detector_channels_mca_dict[i] = []
    for j in range(1,33):
        ge_detector_channels_mca_dict[i].append(f"ge_detector_channels_mca{j}_R{i}")



xs_channel_list = [
    'xs_ch01_roi01',
    'xs_ch02_roi01',
    'xs_ch03_roi01',
    'xs_ch04_roi01',
    'xs_ch01_roi02',
    'xs_ch02_roi02',
    'xs_ch03_roi02',
    'xs_ch04_roi02',
    'xs_ch01_roi03',
    'xs_ch02_roi03',
    'xs_ch03_roi03',
    'xs_ch04_roi03',
    'xs_ch01_roi04',
    'xs_ch02_roi04',
    'xs_ch03_roi04',
    'xs_ch04_roi04']

xs_channel_comb_dict = {'xs_roi01' : ['xs_ch01_roi01',
                                      'xs_ch02_roi01',
                                      'xs_ch03_roi01',
                                      'xs_ch04_roi01'],
                        'xs_roi02' : ['xs_ch01_roi02',
                                      'xs_ch02_roi02',
                                      'xs_ch03_roi02',
                                      'xs_ch04_roi02'],
                        'xs_roi03' : ['xs_ch01_roi03',
                                      'xs_ch02_roi03',
                                      'xs_ch03_roi03',
                                      'xs_ch04_roi03'],
                        'xs_roi04' : ['xs_ch01_roi04',
                                      'xs_ch02_roi04',
                                      'xs_ch03_roi04',
                                      'xs_ch04_roi04'],
                        }


xia_mca_comb_dict = {'xia_mca_roi0': [f'xia_mca_ch{i}_roi0' for i in range(1,33)],
                    }
xia_sca_comb_dict = {'xia_sca_roi0': [f'xia_sca_ch{i}_roi0'for i in range(1,33)] }

xia_raw_channel_list =[]

for j in range(1,33):
    for k in range(1):
        xia_raw_channel_list.append(f'ge_detector__channels_mca{j}_R{k}')
for j in range(1,33):
        xia_raw_channel_list.append(f'ge_detector_scas_dxp{j}_counts')


pil100k_channel_list = [
    'pil100k_roi1',
    'pil100k_roi2',
    'pil100k_roi3',
    'pil100k_roi4'
]
pil100k_channel_comb_dict = {'herfd' : ['pil100k_roi2',
                                        'pil100k_roi3',
                                        'pil100k_roi4'],
                            }

def stepscan_remove_offsets(hdr, fill=True):
    try:
        df = hdr.table(fill=True)
    except:
        df = hdr.table()

    for channel_name, _ in stepscan_channel_dict.items():
        if (channel_name in df.columns) and channel_name.startswith('apb'):
            offset = hdr.descriptors[0]["configuration"]['apb_ave']['data'][channel_name.replace("_mean", "_offset")]
            df[channel_name] = df[channel_name] - offset
    return df


def stepscan_normalize_xs(df):
    for channel_name in xs_channel_list:
        if channel_name in df.columns:
            df[channel_name] = df[channel_name] / df['xs_settings_acquire_time']
    return df

def stepscan_normalize_xia(df):
    for channel_name in xia_raw_channel_list:
        if channel_name in df.columns:
            df[channel_name] = df[channel_name] / df['ge_detector_settings_actual_time']
    return df


def combine_xspress3_channels(df):
    if xs_channel_list[0] in df.columns:
        aug_df = {}
        for k, chs in xs_channel_comb_dict.items():
            aug_df[k] = np.sum(df[chs].values, axis=1)
        aug_df = pd.DataFrame(aug_df)
        cols = [c for c in df.columns if c not in xs_channel_list]
        cols = cols + list(xs_channel_comb_dict.keys()) + xs_channel_list
        df = pd.concat((df, aug_df), axis=1)
        df = df[cols]
    return df

def combine_xia_channels(df):
    if xia_mca_channel_list[0] in df.columns:
        aug_df = {}
        for k, chs in xia_mca_comb_dict.items():
            aug_df[k] = np.sum(df[chs].values, axis=1)
        aug_df = pd.DataFrame(aug_df)
        cols = [c for c in df.columns if c not in xia_mca_channel_list]
        cols = cols + list(xia_mca_comb_dict.keys()) + xia_mca_channel_list
        df = pd.concat((df, aug_df), axis=1)

    if xia_sca_channel_list[0] in df.columns:
        aug_df = {}
        for k, chs in xia_sca_comb_dict.items():
            aug_df[k] = np.sum(df[chs].values, axis=1)
        aug_df = pd.DataFrame(aug_df)
        cols = [c for c in df.columns if c not in xia_sca_channel_list]
        cols = cols + list(xia_sca_comb_dict.keys()) + xia_mca_channel_list
        df = pd.concat((df, aug_df), axis=1)

    elif ge_detector_channels_mca_dict[0][0] in df.columns:
        aug_df = {}
        for channel, item in ge_detector_channels_mca_dict.items():
            _name = f"mca_R{channel}_sum"
            aug_df[_name] = df[item].sum(axis=1)
        aug_df = pd.DataFrame(aug_df)
        df = pd.concat((df, aug_df), axis=1)


        # for k, chs in ge_detector_channels_mca_list.items():
        #     aug_df[k] = np.sum(df[chs].values, axis=1)
        # aug_df = pd.DataFrame(aug_df)
        # cols = [c for c in df.columns if c not in xia_sca_channel_list]
        # cols = cols + list(xia_sca_comb_dict.keys()) + xia_mca_channel_list
        # df = pd.concat((df, aug_df), axis=1)
    return df




def combine_pil100k_channels(df):
    if pil100k_channel_list[0] in df.columns:
        aug_df = {}
        for k, chs in pil100k_channel_comb_dict.items():
            aug_df[k] = np.sum(df[chs].values, axis=1)
        aug_df = pd.DataFrame(aug_df)
        cols = [c for c in df.columns if c not in pil100k_channel_list]
        cols = cols + list(pil100k_channel_comb_dict.keys()) + pil100k_channel_list
        df = pd.concat((df, aug_df), axis=1)
        df = df[cols]
    return df


def filter_df_by_valid_keys(df):
    d = {}
    for key, new_key in stepscan_channel_dict.items():
        if key in df.columns:
            d[new_key] = [i.squeeze() for i in df[key].values]
    return pd.DataFrame(d)


def write_df_to_file(path_to_file, df, comments):
    cols = df.columns.tolist()

    fmt = '%12.6f ' + (' '.join(['%12.6e' for i in range(len(cols) - 1)]))
    header = '  '.join(cols)

    # df = df[cols]
    np.savetxt(path_to_file,
               df.values,
               fmt=fmt,
               delimiter=" ",
               header=f'# {header}',
               comments=comments)
    call(['chmod', '774', path_to_file])


def save_stepscan_as_file(path_to_file, df, comments):
    # assuming stepscan_channel_dict keys and values are ordered as above
    # select all columns from df with names in stepscan_channel_dict.keys()
    # and rename

    # valid_keys = set(stepscan_channel_dict.keys()) & set(df.columns)
    # valid_keys = [key for key in stepscan_channel_dict.keys() if key in df.columns]
    # data = df[valid_keys]
    df_upd = filter_df_by_valid_keys(df)
    # data.columns = [stepscan_channel_dict[k] for k in data.columns]
    write_df_to_file(path_to_file, df_upd, comments)
    return df_upd


def save_primary_df_as_file(path_to_file, df, comments):
    write_df_to_file(path_to_file, df, comments)

def save_metadata_dict_to_h5(h5file, group_name, data_dict):
    def write_item(group, key, value):
        if isinstance(value, dict):
            subgroup = group.require_group(key)
            for subkey, subval in value.items():
                write_item(subgroup, subkey, subval)
        elif isinstance(value, (list, tuple)):
            try:
                arr = np.array(value)
                group.create_dataset(key, data=arr)
            except Exception:
                group.create_dataset(key, data=str(value))
        elif isinstance(value, str):
            dt = h5py.string_dtype(encoding='utf-8')
            group.create_dataset(key, data=value, dtype=dt)
        elif value is None:
            dt = h5py.string_dtype(encoding='utf-8')
            group.create_dataset(key, data="None", dtype=dt)
        else:
            group.create_dataset(key, data=value)

    group = h5file.require_group(group_name)
    for key, value in data_dict.items():
        if key in group:
            del group[key]
        write_item(group, key, value)

def save_extended_data_as_file(path_to_file, extended_data, data_kind='default', ext_data_path='extended_data', metadata_dict=None):
    if extended_data is not None:
        folder, file = os.path.split(path_to_file)
        folder = os.path.join(folder, ext_data_path)
        filename, _ = os.path.splitext(file)
        filename += '.h5'
        try:
            os.mkdir(folder)
        except FileExistsError:
            pass
        path_to_ext_file = os.path.join(folder, filename)
        with h5py.File(path_to_ext_file, 'a') as f:
            f['data_kind'] = data_kind
            save_metadata_dict_to_h5(f, 'metadata', metadata_dict)
            for k, v in recursively_parse_dict(extended_data):
                f[k] = v

def recursively_parse_dict(data_dict):
    for k, v in data_dict.items():
        if type(v) == dict:
            for sub_k, sub_v in recursively_parse_dict(v):
                yield f'{k}/{sub_k}', sub_v
        else:
            yield k, v

def recuresively_parse_h5(f):
    output = {}
    if type(f) == h5py._hl.dataset.Dataset:
        return f[()]
    else:
        for k in f.keys():
            v = recuresively_parse_h5(f[k])
            if k not in output.keys():
                output[k] = {}
            output[k] = v
        return output


def load_extended_data_from_file(path_to_ext_file):
    try:
        with h5py.File(path_to_ext_file, 'r') as f:
            extended_data = recuresively_parse_h5(f)
        return extended_data
    except Exception as e:
        print(e)
        return None

def dump_tiff_images(path_to_file, df, extended_data, df_red=None, tiff_storage_path='/tiff_storage/', zip=True):
    # print(f'Extended data shape  {extended_data.shape}')
    if 'pil100k2_image' in extended_data.keys():
        # deal with paths
        tiff_storage_path = os.path.dirname(path_to_file) + tiff_storage_path

        scan_name, _ = os.path.splitext(os.path.basename(path_to_file))
        dat_file_fpath = tiff_storage_path + scan_name + '.dat'
        tiff_images_path = tiff_storage_path + scan_name + '/'

        try:
            print('Creating a directory tiff_storage')
            os.mkdir(tiff_storage_path)
        except FileExistsError:
            print('Failed to create directory tiff_storage')
            pass

        try:
            print('Creating a directory tiff_images')
            os.mkdir(tiff_images_path)
        except FileExistsError:
            print('These tiff images were saved already')
            return

        filename_list = []
        filepath_list = []
        for i, im in enumerate(extended_data['pil100k2_image']):
            image_data = Image.fromarray(im)
            #
            tiff_filename = '{}{:04d}{}'.format('image', i + 1, '.tif')
            tiff_path = tiff_images_path + tiff_filename
            print(f'TIFF STORAGE: tiff will be saved in {tiff_path}')
            image_data.save(tiff_path)
            filepath_list.append(tiff_path)
            filename_list.append(tiff_filename)

        if zip:
            print('Creating a zip file')
            zip_file = os.path.splitext(dat_file_fpath)[0]+'.zip'
            os.system(f"cd '{tiff_images_path}'; zip '{zip_file}' ./*.tif")
            # os.system(f"zip '{zip_file}' '{tiff_images_path}'/*.tif")
            filepath_list = [zip_file]

        if df_red is None:
            df_red = pd.concat([df[c] for c in ['energy', 'i0', 'it', 'ir', 'iff'] if c in df.columns], axis=1)

        df_red['filenames'] = filename_list
        print(f'TIFF STORAGE: dat will be saved in {dat_file_fpath}')
        df_red.to_csv(dat_file_fpath, sep='\t', index=False)
        filepath_list.append(dat_file_fpath)
        return filepath_list
