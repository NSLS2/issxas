import numpy as np
import pandas as pd
import pytest

from xas import db_io


class Field:
    def __init__(self, value):
        self.value = value

    def read(self):
        return self.value


class Header:
    def __init__(self, streams, start=None):
        self.v2 = {name: {'data': {key: Field(value) for key, value in fields.items()}}
                   for name, fields in streams.items()}
        self.start = start or {}

    def __getitem__(self, key):
        return getattr(self, key)


@pytest.fixture(autouse=True)
def logger(monkeypatch):
    class Logger:
        def info(self, message):
            pass
    monkeypatch.setattr(db_io, 'get_logger', lambda: Logger())


def test_apb_encoder_and_trigger_structured_fields():
    apb_columns = ['timestamp', 'i0', 'it', 'ir', 'iff', 'aux1', 'aux2', 'aux3', 'aux4']
    apb = np.array([(10, *([1200] * 8)), (11, *([2200] * 8)), (0, *([0] * 8))],
                   dtype=[(name, 'f8') for name in apb_columns])
    enc = np.array([(10, 0, 3, 0, 0), (0, 0, 0, 0, 0)],
                   dtype=[(name, 'i8') for name in ['ts_s', 'ts_ns', 'encoder', 'index', 'state']])
    trigger = np.array([(10., 1), (12., 0), (14., 1), (16., 0), (0., 0)],
                       dtype=[('timestamp', 'f8'), ('transition', 'i4')])
    start = {'angle_offset': 2, **{f'ch{i}_offset': 0.2 for i in range(1, 9)},
             **{f'ch{i}_amp_gain': 1 for i in range(1, 9)}}
    hdr = Header({'apb_stream': {'apb_stream': apb}, 'pb9_enc1': {'pb9_enc1': enc},
                  'apb_trigger_xs': {'apb_trigger_xs': trigger}}, start)
    catalog = {'uid': hdr}
    apb_df, enc_df, offset = db_io.load_apb_dataset_from_db(catalog, 'uid')
    np.testing.assert_allclose(apb_df['i0'], [0.0001])
    assert list(enc_df['encoder']) == [3]
    assert offset == -2
    np.testing.assert_array_equal(db_io.load_apb_trig_dataset_from_db(catalog, 'uid'), [11, 15])


def test_external_rois_and_images_read_independently():
    timestamps = np.array([10., 11.])
    fields = {f'pil100k_roi{i}': np.array([[i, i + 1]]) for i in range(1, 5)}
    fields['pil100k_image'] = np.arange(8).reshape(1, 2, 2, 2)
    hdr = Header({'pil100k_stream': fields})
    result = db_io.load_pil100k_dataset_from_db({'uid': hdr}, 'uid', timestamps, load_images=True)
    np.testing.assert_array_equal(result['pil100k_roi1']['pil100k_roi1'], [1, 2])
    np.testing.assert_array_equal(result['pil100k_image']['pil100k_image'].iloc[0], [[0, 1], [2, 3]])


def test_xspress_and_xia_rois_use_trigger_timestamps():
    xs = {f'xs_ch{c:02d}_roi{r:02d}': np.array([[100000, 200000, 300000]])
          for c in range(1, 5) for r in range(1, 5)}
    ge = {f'ge_detector_channels_mca{c}_R{r}': np.array([[300000, 400000, 500000]])
          for c in range(1, 33) for r in range(4)}
    hdr = Header({'xs_stream': xs, 'ge_detector_stream': ge})
    times = np.array([10., 11.])
    xs_result = db_io.load_xs3_dataset_from_db({'uid': hdr}, 'uid', times)
    ge_result = db_io.load_xia_dataset_from_db({'uid': hdr}, 'uid', times)
    np.testing.assert_array_equal(xs_result['xs_ch01_roi01']['xs_ch01_roi01'], [1, 2])
    np.testing.assert_array_equal(ge_result['ge_detector_channels_mca1_R0']['ge_detector_channels_mca1_R0'], [3, 4])
    np.testing.assert_array_equal(xs_result['xs_ch01_roi01']['timestamp'], times)


def test_legacy_dataframe_records_remain_supported():
    class LegacyHeader:
        def data(self, stream_name, field):
            yield pd.DataFrame({'timestamp': [1., 2.], 'transition': [1, 0]})
    result = db_io.load_apb_trig_dataset_from_db({'uid': LegacyHeader()}, 'uid')
    np.testing.assert_array_equal(result, [1.5])


def test_tiled_and_legacy_trigger_results_match():
    frame = pd.DataFrame({'timestamp': [1., 2., 3., 4., 0.], 'transition': [1, 0, 1, 0, 0]})

    class LegacyHeader:
        def data(self, stream_name, field):
            yield frame

    tiled = Header({'apb_trigger_xs': {'apb_trigger_xs': frame.to_records(index=False)}})
    expected = db_io.load_apb_trig_dataset_from_db({'uid': LegacyHeader()}, 'uid')
    actual = db_io.load_apb_trig_dataset_from_db({'uid': tiled}, 'uid')
    np.testing.assert_array_equal(actual, expected)
