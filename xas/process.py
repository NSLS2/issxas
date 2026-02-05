from xas.bin import bin, bin_epics_fly_scan
from xas.file_io import (
    load_dataset_from_files,
    create_file_header,
    validate_file_exists,
    validate_path_exists,
    save_interpolated_df_as_file,
    save_binned_df_as_file,
    find_e0,
    save_stepscan_as_file,
    stepscan_remove_offsets,
    stepscan_normalize_xs,
    stepscan_normalize_xia,
    combine_xspress3_channels,
    combine_pil100k_channels,
    combine_xia_channels,
    filter_df_by_valid_keys,
    save_primary_df_as_file,
    save_extended_data_as_file,
    dump_tiff_images,
)
from xas.db_io import (
    load_apb_dataset_from_db,
    translate_apb_dataset,
    load_apb_trig_dataset_from_db,
    load_xs3_dataset_from_db,
    load_pil100k_dataset_from_db,
    load_apb_dataset_only_from_db,
    translate_apb_only_dataset,
    load_xia_dataset_from_db,
)
from xas.interpolate import interpolate, interpolate_with_interp
from scipy.interpolate import interp1d
import pandas as pd
from xas.file_io import _shift_root
from xas.db_io import update_header_start
from xas.metadata import generate_xdi_metadata_from_hdr
from xas.xas_logger import get_logger

# import matplotlib.pyplot as plt
# import numpy as np
import time as ttime
import os

# from isscloudtools.slack import slack_upload_image
# from isscloudtools.cloud_dispatcher import generate_output_figures

from xas.spectrometer import (
    convert_roll_to_energy_for_johann_fly_scan,
    filter_johann_image_kwargs,
    filter_johann_calibration_kwargs,
    interpolate_df_emission_energies_on_common_grid,
)
from xas.image_analysis import reduce_johann_images
from xas.vonhamos import (
    process_von_hamos_scan,
    filter_von_hamos_kwargs,
)  # , save_vh_scan_to_file
import gc

from tiled.client import from_uri

client = from_uri("https://tiled.nsls2.bnl.gov")['iss/sandbox']


def process_interpolate_bin(
    doc,
    db,
    processing_repo="xas",
    draw_func_interp=None,
    draw_func_bin=None,
    cloud_dispatcher=None,
    print_func=None,
    dump_to_tiff=False,
    load_images=False,
    processing_kwargs=None,
    save_image=False,
    camera1=None,
    camera2=None,
):
    logger = get_logger()
    logger.info(
        f"({ttime.ctime()}) Processing has begun -----------------------------------------------"
    )

    if "experiment" in db[doc["run_start"]].start.keys():
        uid = doc["run_start"]
        print(f"processing {uid} in using repo {processing_repo}")
        if processing_repo == "xas":
            process_interpolate_bin_from_uid(
                uid,
                db,
                draw_func_interp=draw_func_interp,
                draw_func_bin=draw_func_bin,
                cloud_dispatcher=cloud_dispatcher,
                print_func=print_func,
                dump_to_tiff=dump_to_tiff,
                load_images=load_images,
                save_image=save_image,
                camera1=camera1,
                camera2=camera2,
                processing_kwargs=processing_kwargs,
            )
    logger.info(
        f"({ttime.ctime()}) Processing has finished -----------------------------------------------"
    )


def process_interpolate_bin_from_uid(
    uid,
    db,
    draw_func_interp=None,
    draw_func_bin=None,
    cloud_dispatcher=None,
    print_func=None,
    dump_to_tiff=False,
    load_images=False,
    save_interpolated_file=True,
    update_start=None,
    save_image=False,
    camera1=None,
    camera2=None,
    processing_kwargs=None,
):

    logger = get_logger()
    hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind = (
        get_processed_df_from_uid(
            uid,
            db,
            logger=logger,
            draw_func_interp=draw_func_interp,
            draw_func_bin=draw_func_bin,
            print_func=print_func,
            save_interpolated_file=save_interpolated_file,
            update_start=update_start,
            load_images=load_images,
            processing_kwargs=processing_kwargs,
        )
    )
    # save images
    if save_image:
        try:
            base, ext = os.path.splitext(path_to_file)
            if camera1:
                camera1.saveImageAsFile(f"{base}_camera1.jpg")
            if camera2:
                camera2.saveImageAsFile(f"{base}_camera2.jpg")
            logger.info(f"({ttime.ctime()}) Sample images are saved for {path_to_file}")
        except:
            logger.info(
                f"({ttime.ctime()}) Saving sample images failed for {path_to_file}"
            )

    if (processing_kwargs is not None) and ("skip_standard_dat" in processing_kwargs):
        skip_standard_dat = processing_kwargs["skip_standard_dat"]
    else:
        skip_standard_dat = False

    if not skip_standard_dat:
        save_primary_df_as_file(path_to_file, primary_df, comments)

    try:
        dictionary_for_hdf5_file = {**dict(primary_df), **extended_data}
        save_extended_data_as_file(
            path_to_file,
            dictionary_for_hdf5_file,
            data_kind=data_kind,
            metadata_dict=dict(hdr.start),
        )
        # save_extended_data_as_file(path_to_file, extended_data, data_kind=data_kind)
    except Exception as e:
        print(e)
        pass

    if dump_to_tiff:
        if extended_data is not None:
            tiff_files = dump_tiff_images(path_to_file, primary_df, extended_data)
            print(f" >>>>>>>>>>Tiff file {tiff_files}")
            file_list += tiff_files

    # dfgd
    try:
        if cloud_dispatcher is not None:
            # year, cycle, proposal = hdr.start['year'], hdr.start['cycle'], hdr.start['PROPOSAL']
            year, cycle, proposal = (
                hdr.start["year"],
                hdr.start["cycle"],
                hdr.start["proposal"],
            )
            for f in file_list:
                cloud_dispatcher.load_to_dropbox(
                    f, year=year, cycle=cycle, proposal=proposal
                )
                logger.info(
                    f"({ttime.ctime()}) Sending data to the cloud successful for {path_to_file}"
                )
    except Exception as e:
        logger.info(
            f"({ttime.ctime()}) Sending data to the cloud failed for {path_to_file}"
        )
        # raise e


#   clear_db_cache(db)


_legacy_experiment_reg = {"fly_energy_scan_pil100k": "fly_scan"}


def get_processed_df_from_uid(
    uid,
    db,
    logger=None,
    draw_func_interp=None,
    draw_func_bin=None,
    print_func=None,
    save_interpolated_file=True,
    update_start=None,
    return_processed_df=False,
    load_images=False,
    processing_kwargs=None,
):

    if print_func is None:
        print_func = print
    if logger is None:
        logger = get_logger()

    # logger = get_logger(print_func=print_func)
    hdr = db[uid]
    if update_start is not None:
        hdr = update_header_start(hdr, update_start)
    experiment = hdr.start["experiment"]
    if experiment in _legacy_experiment_reg.keys():
        experiment = _legacy_experiment_reg[experiment]
    comments = create_file_header(hdr)
    if (processing_kwargs is not None) and ("interp_filename" in processing_kwargs):
        path_to_file = processing_kwargs["interp_filename"]
    else:
        path_to_file = hdr.start["interp_filename"]
    # path_to_file = _shift_root(path_to_file)
    # validate_path_exists(path_to_file)
    # path_to_file = validate_file_exists(path_to_file, file_type='interp')
    e0 = find_e0(hdr)
    data_kind = "default"
    file_list = []
    logger.info(f"({ttime.ctime()}) Processing started for {uid}")
    if experiment == "fly_scan":
        logger.info(f"({ttime.ctime()}) Processing fly scan")
        stream_names = hdr.stream_names
        try:
            # default detectors
            apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
            raw_dict = translate_apb_dataset(apb_df, energy_df, energy_offset)
            logger.info(f"({ttime.ctime()}) Pizzabox and monochromator data processed")
            for stream_name in stream_names:
                if (stream_name == "pil100k_stream") or (
                    stream_name == "pil100k2_stream"
                ):
                    logger.info(f"({ttime.ctime()}) Retrieving trigger data...")
                    pil100k_stream_name = stream_name
                    pil100k_name = stream_name.split("_")[0]
                    apb_trigger_stream_name = f"apb_trigger_{pil100k_name}"

                    apb_trigger_pil100k_timestamps = load_apb_trig_dataset_from_db(
                        db, uid, use_fall=True, stream_name=apb_trigger_stream_name
                    )
                    logger.info(f"({ttime.ctime()}) Trigger data received")
                    logger.info(f"({ttime.ctime()}) Retrieving Pilatus data...")
                    pil100k_dict = load_pil100k_dataset_from_db(
                        db,
                        uid,
                        apb_trigger_pil100k_timestamps,
                        pil100k_stream_name=pil100k_stream_name,
                        load_images=load_images,
                    )
                    logger.info(f"({ttime.ctime()}) Pilatus data received")
                    raw_dict = {**raw_dict, **pil100k_dict}

                elif stream_name == "xs_stream":
                    apb_trigger_xs_timestamps = load_apb_trig_dataset_from_db(
                        db, uid, stream_name="apb_trigger_xs"
                    )
                    xs3_dict = load_xs3_dataset_from_db(
                        db, uid, apb_trigger_xs_timestamps
                    )
                    logger.info(f"({ttime.ctime()}) SDD data received")
                    raw_dict = {**raw_dict, **xs3_dict}
                elif stream_name == "ge_detector_stream":
                    apb_trigger_xia_timestamps = load_apb_trig_dataset_from_db(
                        db, uid, stream_name="apb_trigger_ge_detector"
                    )
                    xia_dict = load_xia_dataset_from_db(
                        db, uid, apb_trigger_xia_timestamps
                    )
                    logger.info(f"({ttime.ctime()}) XIA data received")
                    raw_dict = {**raw_dict, **xia_dict}
                    pass  # WIP for flying Ge detector

            logger.info(f"({ttime.ctime()}) Streams loaded successfully")
        except Exception as e:
            logger.info(f"({ttime.ctime()}) Loading streams failed")
            raise e
        # raise RuntimeError()
        try:
            # print(raw_dict)
            if load_images:
                interpolated_df = interpolate_with_interp(raw_dict)
            else:
                interpolated_df = interpolate(raw_dict)

            logger.info(f"({ttime.ctime()}) Interpolation successful for {uid}")
            if save_interpolated_file:
                client.write_table(
                    interpolated_df,
                    metadata=generate_xdi_metadata_from_hdr(hdr),
                    access_tags=[hdr.start["proposal"]],
                )
        except Exception as e:
            logger.info(f"({ttime.ctime()}) Interpolation failed for {uid}")
            raise e

        try:
            if e0 > 0:
                # rebin_kwargs = filter_rebin_kwargs(processing_kwargs)
                rebin_kwargs = {}
                processed_df = bin(interpolated_df, e0, **rebin_kwargs)
                (path, extension) = os.path.splitext(uid)
                path_to_file = path + ".dat"
                logger.info(f"({ttime.ctime()}) Binning successful for {uid}")

                if draw_func_interp is not None:
                    draw_func_interp(interpolated_df, processed_df)
                if draw_func_bin is not None:
                    draw_func_bin(processed_df, path_to_file)
            else:
                print(f"({ttime.ctime()}) Energy E0 is not defined")
        except Exception as e:
            logger.info(f"({ttime.ctime()}) Binning failed for {path_to_file}")
            raise e

        # save_binned_df_as_file(path_to_file, processed_df, comments)

    elif (experiment == "step_scan") or (experiment == "collect_n_exposures"):
        logger.info(f"({ttime.ctime()}) Processing step scan")
        # path_to_file = validate_file_exists(path_to_file, file_type='interp')
        df = stepscan_remove_offsets(hdr)
        df = stepscan_normalize_xs(df)
        df = stepscan_normalize_xia(df)
        processed_df = filter_df_by_valid_keys(df)

    elif experiment == "epics_fly_scan":
        logger.info(f"({ttime.ctime()}) Processing EPICS fly scan")
        processed_df = get_processed_df_from_uid_for_epics_fly_scan(
            db,
            uid,
            save_interpolated_file=True,
            path_to_file=path_to_file,
            comments=comments,
            load_images=load_images,
            processing_kwargs=processing_kwargs,
        )
    else:
        return

    processed_df = combine_xspress3_channels(processed_df)
    processed_df = combine_xia_channels(processed_df)
    processed_df = combine_pil100k_channels(processed_df)

    if return_processed_df:
        return processed_df

    primary_df, extended_data = split_df_data_into_primary_and_extended(processed_df)

    ### WIP
    if "spectrometer" in hdr.start.keys():
        if hdr.start["spectrometer"] == "von_hamos":
            von_hamos_kwargs = filter_von_hamos_kwargs(processing_kwargs)
            extended_data, comments, file_paths = process_von_hamos_scan(
                primary_df,
                extended_data,
                comments,
                hdr,
                path_to_file,
                db=db,
                **von_hamos_kwargs,
            )
            data_kind = "von_hamos"
            file_list = file_paths
            # save_vh_scan_to_file(path_to_file, vh_scan, comments)
    if (processing_kwargs is not None) and ("skip_standard_dat" in processing_kwargs):
        skip_standard_dat = processing_kwargs["skip_standard_dat"]
    else:
        skip_standard_dat = False

    if not skip_standard_dat:
        file_list.append(path_to_file)
    return hdr, primary_df, extended_data, comments, path_to_file, file_list, data_kind


import numpy as np


def split_df_data_into_primary_and_extended(df_orig):
    sec_cols = []
    for c in df_orig.columns:
        if len(df_orig[c][0].shape) > 0:
            sec_cols.append(c)

    if len(sec_cols) > 0:
        extended_data = {}
        df = df_orig.copy()
        for col in sec_cols:
            v = df.pop(col)
            extended_data[col] = np.array([i for i in v])

    else:
        df = df_orig
        extended_data = None
    return df, extended_data


def clear_db_cache(db):
    db._catalog._entries.cache_clear()
    gc.collect()


def process_interpolate_only(doc, db):
    if "experiment" in db[doc["run_start"]].start.keys():
        if db[doc["run_start"]].start["experiment"] == "fly_energy_scan":
            raw_df = load_dataset_from_files(db, doc["run_start"])
            interpolated_df = interpolate(raw_df)
            return interpolated_df


def process_interpolate_unsorted(uid, db):
    raw_df = load_dataset_from_files(db, uid)
    interpolated_df = interpolate(raw_df, sort=False)
    return interpolated_df


def clean_dict(raw_dict):
    clean_raw_dict = {}
    for key in raw_dict.keys():
        df = raw_dict[key]
        zero_idx = df[df["timestamp"] == 0].index.min()
        if zero_idx is None:
            clean_raw_dict[key] = df
        else:
            clean_raw_dict[key] = df.loc[: zero_idx - 1]
    return clean_raw_dict


def get_processed_df_from_uid_for_epics_fly_scan(
    db,
    uid,
    save_interpolated_file=False,
    path_to_file=None,
    comments=None,
    load_images=False,
    processing_kwargs=None,
):
    hdr = db[uid]
    stream_names = hdr.stream_names
    logger = get_logger()
    # if (hdr.start['spectrometer'] == 'johann'):
    #     load_images = True

    try:
        # default detectors
        # apb_df, energy_df, energy_offset = load_apb_dataset_from_db(db, uid)
        # raw_dict = translate_apb_dataset(apb_df, energy_df, energy_offset)
        raw_dict = {}

        for stream_name in stream_names:
            if stream_name == "apb_stream":
                apb_df = load_apb_dataset_only_from_db(db, uid)
                raw_dict = {**raw_dict, **translate_apb_only_dataset(apb_df)}

            elif (stream_name == "pil100k_stream") or (
                stream_name == "pil100k2_stream"
            ):
                pil100k_stream_name = stream_name
                pil100k_name = stream_name.split("_")[0]
                apb_trigger_stream_name = f"apb_trigger_{pil100k_name}"
                logger.info(f"({ttime.ctime()}) Retrieving trigger data...")
                apb_trigger_pil100k_timestamps = load_apb_trig_dataset_from_db(
                    db, uid, use_fall=True, stream_name=apb_trigger_stream_name
                )
                logger.info(f"({ttime.ctime()}) Trigger data received")
                logger.info(f"({ttime.ctime()}) Retrieving Pilatus data...")
                pil100k_dict = load_pil100k_dataset_from_db(
                    db,
                    uid,
                    apb_trigger_pil100k_timestamps,
                    pil100k_stream_name=pil100k_stream_name,
                    load_images=load_images,
                )
                logger.info(f"({ttime.ctime()}) Pilatus data received")
                raw_dict = {**raw_dict, **pil100k_dict}

            elif stream_name == "xs_stream":
                apb_trigger_xs_timestamps = load_apb_trig_dataset_from_db(
                    db, uid, stream_name="apb_trigger_xs"
                )
                logger.info(f"({ttime.ctime()}) Retrieving SDD data...")
                xs3_dict = load_xs3_dataset_from_db(db, uid, apb_trigger_xs_timestamps)
                logger.info(f"({ttime.ctime()}) SDD data received")
                raw_dict = {**raw_dict, **xs3_dict}

            elif stream_name.endswith("monitor"):
                _stream_name = stream_name[: stream_name.index("monitor") - 1]
                logger.info(f"({ttime.ctime()}) Retrieving monitor data...")
                df = hdr.table(stream_name)
                logger.info(f"({ttime.ctime()}) Monitor data received")
                df["timestamp"] = (
                    df.time.values - np.datetime64("1970-01-01T00:00:00Z")
                ) / np.timedelta64(1, "s")

                interpolator_func = interp1d(
                    df["timestamp"].values,
                    df[_stream_name].values,
                    axis=0,
                    kind="quadratic",
                )
                fine_timestamp = np.linspace(
                    df["timestamp"].min(),
                    df["timestamp"].max(),
                    int((df["timestamp"].max() - df["timestamp"].min()) * 500),
                )
                motor_pos_fine = interpolator_func(fine_timestamp)

                monitor_dict = {
                    _stream_name: pd.DataFrame(
                        {"timestamp": fine_timestamp, _stream_name: motor_pos_fine}
                    )
                }
                raw_dict = {**raw_dict, **monitor_dict}

        # logger.info(f'({ttime.ctime()}) Loading file successful for UID {uid}')
    except Exception as e:
        # logger.info(f'({ttime.ctime()}) Loading file failed for UID {uid}')
        raise e
    try:
        raw_dict = clean_dict(raw_dict)
        interpolated_df = interpolate(raw_dict, sort=False)
        if save_interpolated_file:
            # save_interpolated_df_as_file(path_to_file, interpolated_df, comments)
            client.write_table(
                interpolated_df, metadata=generate_xdi_metadata_from_hdr(hdr)
            )
        # logger.info(f'({ttime.ctime()}) Interpolation successful for {uid}')
    except Exception as e:
        # logger.info(f'({ttime.ctime()}) Interpolation failed for {uid}')
        raise e
    if "spectrometer" in hdr.start:
        if "roi_polygon" in hdr.start["detectors"]["Pilatus 100k New"]["config"]:
            # if 'roi_polygon' in hdr.start['detectors']['Pilatus 100k']['config']:
            # johann_image_kwargs = filter_johann_image_kwargs(processing_kwargs)
            # if (hdr.start['spectrometer'] == 'johann') and (load_images):
            #     interpolated_df = reduce_johann_images(interpolated_df, hdr, **johann_image_kwargs)

            johann_calibration_kwargs = filter_johann_calibration_kwargs(
                processing_kwargs
            )
            if (hdr.start["spectrometer"] == "johann") and (load_images):
                interpolated_df, energy_key = (
                    convert_roll_to_energy_for_johann_fly_scan(
                        interpolated_df, hdr, **johann_calibration_kwargs
                    )
                )
                # return interpolated_df
                if energy_key is not None:
                    interpolated_df = interpolate_df_emission_energies_on_common_grid(
                        interpolated_df, hdr, energy_key=energy_key
                    )
                    step_size = 0.2  # eV
                    processed_df = bin_epics_fly_scan(
                        interpolated_df, key_base="energy", step_size=step_size
                    )
                    return processed_df
    try:
        stream_name = hdr.start["motor_stream_names"][0]
        _stream_name = stream_name[: stream_name.index("monitor") - 1]
        if ("johann" in _stream_name) and (
            ("roll" in _stream_name) or ("yaw" in _stream_name)
        ):
            step_size = 5
        else:
            step_size = 0.1
        processed_df = bin_epics_fly_scan(
            interpolated_df, key_base=_stream_name, step_size=step_size
        )
        # (path, extension) = os.path.splitext(path_to_file)
        # path_to_file = path + '.dat'
        logger.info(f"({ttime.ctime()}) Binning successful")

        # if draw_func_interp is not None:
        #     draw_func_interp(interpolated_df)
        # if draw_func_bin is not None:
        #     draw_func_bin(processed_df, path_to_file)

    except Exception as e:
        logger.info(f"({ttime.ctime()}) Binning failed")
        raise e

    return processed_df


# ###########################################################
# # LOCKARD PROCESSING
# ###########################################################
# # storing table as hdf
# dump_to_hdf = True
# if dump_to_hdf:
#     hdf_fn = os.path.splitext(path_to_file)[0]+'.h5'
#     # hdr = db[uid]
#     t = db[uid].table(fill=True)
#     t.to_hdf(hdf_fn, 'data')
# dump_to_tiff_pushkar = True
# if dump_to_tiff_pushkar:
#     # deal with paths
#     tiff_storage_path = os.path.dirname(path_to_file) + '/tiff_storage/'
#     scan_name = os.path.splitext(os.path.basename(path_to_file))[0]
#     dat_file_fpath = tiff_storage_path + scan_name + '.dat'
#     tiff_images_path = tiff_storage_path + scan_name + '/'
# #
#     try:
#         os.mkdir(tiff_images_path)
#     except FileExistsError:
#         print('Warning Folder exists')
#         return
# #
# #     # deal with images
#     filename_list = []
#     for i, im in enumerate(t['pil100k_image']):
#         image_data = Image.fromarray(im)
# #
#         tiff_filename = '{}{:04d}{}'.format('image', i + 1, '.tiff')
#         tiff_path = tiff_images_path + tiff_filename
#         print(f'TIFF STORAGE: tiff will be saved in {tiff_path}')
#         image_data.save(tiff_path)
#         filename_list.append(tiff_filename)
# #
# #     # deal with table file
#     table_red = df[['hhm_energy', 'apb_ave_ch1_mean', 'apb_ave_ch2_mean', 'apb_ave_ch3_mean', 'apb_ave_ch4_mean']]
#
#     table_red = table_red.rename(
#         columns={'hhm_energy': '# energy', 'apb_ave_ch1': 'i0', 'apb_ave_ch2': 'it', 'apb_ave_ch3': 'ir',
#                  'apb_ave_ch4': 'iff'})
#     # table_red = df
#     table_red['filenames'] = filename_list
#     print(f'TIFF STORAGE: dat will be saved in {dat_file_fpath}')
#     table_red.to_csv(dat_file_fpath, sep='\t', index=False)

###########################################################
# PUSHKAR PROCESSING
###########################################################
# storing table as hdf
# dump_to_hdf = True
# if dump_to_hdf:
#     hdf_fn = os.path.splitext(path_to_file)[0]+'.h5'
#     hdr = db[uid]
#     t = db[uid].table(fill=True)
#     t.to_hdf(hdf_fn, 'data')
# dump_to_tiff_pushkar = True
# if dump_to_tiff_pushkar:
#     # deal with paths
#     tiff_storage_path = os.path.dirname(path_to_file) + '/tiff_storage/'
#     scan_name = os.path.splitext(os.path.basename(path_to_file))[0]
#     dat_file_fpath = tiff_storage_path + scan_name + '.dat'
#     tiff_images_path = tiff_storage_path + scan_name + '/'
#
#     try:
#         os.mkdir(tiff_images_path)
#     except FileExistsError:
#         print('Warning Folder exists')
#         return
#
#     # deal with images
#     # filename_list = []
#     for i, im in enumerate(t['pil100k_image']):
#         image_data = Image.fromarray(im)
#
#         tiff_filename = '{}{:04d}{}'.format('image', i + 1, '.tif')
#         tiff_path = tiff_images_path + tiff_filename
#         print(f'TIFF STORAGE: tiff will be saved in {tiff_path}')
#         image_data.save(tiff_path)
#         # filename_list.append(tiff_filename)
#
#     # deal with table file
#     table_red = t[['hhm_energy', 'apb_ave_ch1', 'apb_ave_ch2', 'apb_ave_ch3', 'apb_ave_ch4']]
#
#
#     table_red = table_red.rename(
#         columns={'hhm_energy': '# energy', 'apb_ave_ch1': 'i0', 'apb_ave_ch2': 'it', 'apb_ave_ch3': 'ir',
#                  'apb_ave_ch4': 'iff'})
#     # table_red['filenames'] = filename_list
#     print(f'TIFF STORAGE: dat will be saved in {dat_file_fpath}')
#     table_red.to_csv(dat_file_fpath, sep='\t', index=False)


# scratch

# import math
# from xas.math import gauss
# from scipy.optimize import curve_fit
#
#
# def get_image_data():
#     image = bpm_es.image.array_data.read()['bpm_es_image_array_data']['value'].reshape((960,1280))
#     image = image.astype(np.int16)
#     sum_lines = sum(image[:, [i for i in range(line - math.floor(n_lines/2), line + math.ceil(n_lines/2))]].transpose())
#     sum_lines = sum_lines - np.mean(sum_lines[:200])
#     index_max = sum_lines.argmax()
#     max_value = sum_lines.max()
#     min_value = sum_lines.min()
#     sum_lines_t = sum_lines.copy()
#     mask = sum_lines_t>max_value/2
#     idx_to_fit = np.where(mask)
#     sum_lines_t[~mask] = 0
#     x = np.arange(960)
#     coeff, var_matrix = curve_fit(gauss, x[idx_to_fit], sum_lines_t[idx_to_fit], p0=[1, index_max, 5])
#     return sum_lines, sum_lines_t, gauss(x, *coeff)
#
# data1, data1_t, fit1 = get_image_data()
#
# plt.figure()
# plt.plot(data1, label = 'Data 1')
# plt.plot(data1_t, label = 'Data 1 t')
# plt.plot(fit1, label = 'Fit 1')
# plt.legend()
# plt.grid()
#
#
# data2, data1_2, fit2 = get_image_data()
#
# plt.plot(data1, 'k-', label = 'Data 1')
# plt.plot(data1_t, 'k--', label = 'Data 1 t')
# plt.plot(fit1, 'r-', label = 'Fit 1')
