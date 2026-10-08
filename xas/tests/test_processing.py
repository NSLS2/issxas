"""Offline numerical contracts for the processing functions used by the GUI."""

import logging

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose, assert_array_equal
from pandas.testing import assert_frame_equal
from scipy.interpolate import interp1d

from xas.bin import (
    _generate_convolution_bin_matrix,
    bin,
    bin_epics_fly_scan,
    xas_energy_grid,
)
from xas.interpolate import _downsample, _interpolate_images, interpolate, interpolate_with_interp


@pytest.fixture(autouse=True)
def local_logger(monkeypatch):
    monkeypatch.setattr("xas.interpolate.get_logger", lambda: logging.getLogger("test"))


def stream(time, values):
    return pd.DataFrame({"timestamp": time, "value": list(values)})


@pytest.mark.parametrize("function", [interpolate, interpolate_with_interp])
@pytest.mark.parametrize("sort", [False, True])
@pytest.mark.parametrize("key_base", [None, "energy"])
def test_scalar_interpolation(function, sort, key_base):
    time = np.arange(10.0)
    fast_time = np.linspace(0, 9, 31)
    dataset = {"energy": stream(time, 100 - time),
               "i0": stream(fast_time, np.sin(fast_time))}
    originals = {key: value.copy(deep=True) for key, value in dataset.items()}
    # The last overlapping base sample is intentionally excluded by the API.
    expected = pd.DataFrame({"timestamp": time[:-1], "energy": 100 - time[:-1],
                             "i0": np.interp(time[:-1], fast_time, np.sin(fast_time))})
    if sort:
        expected = expected.sort_values("energy")
    assert_frame_equal(function(dataset, key_base=key_base, sort=sort), expected)
    for key in dataset:
        assert_frame_equal(dataset[key], originals[key])


@pytest.mark.parametrize("function", [interpolate, interpolate_with_interp])
def test_downsampling_matches_existing_chunk_means(function):
    time = np.arange(10.0)
    fast_time = np.linspace(0, 9, 103)
    values = np.cos(fast_time)
    reduced_time = [fast_time[0]] + [v.mean() for v in np.array_split(fast_time[1:-1], 9)] + [fast_time[-1]]
    reduced_values = [values[0]] + [v.mean() for v in np.array_split(values[1:-1], 9)] + [values[-1]]
    result = function({"energy": stream(time, time), "i0": stream(fast_time, values)})
    assert_allclose(result.i0, np.interp(time[:-1], reduced_time, reduced_values))


def test_array_interpolation():
    time = np.arange(10.0)
    values = np.arange(60.0).reshape(10, 2, 3)
    result = interpolate({"energy": stream(time + 0.25, time),
                          "image": stream(time, values)}, key_base="energy", sort=False)
    assert_allclose(np.stack(result.image), interp1d(time, values, axis=0)(result.timestamp))


@pytest.mark.parametrize("dtype", [np.int32, np.float32, np.float64])
def test_pilatus_interpolation_preserves_legacy_values_and_dtype(dtype):
    time = np.arange(7.0)
    values = (np.arange(7 * 195 * 487).reshape(7, 195, 487) % 123).astype(dtype)
    dataset = {"energy": stream(time + 0.25, time), "pil100k2_image": stream(time, values)}
    result = interpolate_with_interp(dataset, key_base="energy", sort=False)
    flat = values.reshape(7, -1)
    expected = np.empty((len(result), flat.shape[1]), dtype=dtype)
    for pixel in range(flat.shape[1]):
        expected[:, pixel] = np.interp(result.timestamp, time, flat[:, pixel])
    actual = np.stack(result.pil100k2_image)
    assert actual.dtype == object
    assert_array_equal(actual.astype(dtype), expected.reshape(-1, 195, 487))


def dense_reference(sample_points, data_x):
    def widths(points):
        widths = (np.diff(points)[1:] + np.diff(points)[:-1]) / 2
        return np.r_[widths[0], widths, widths[-1]]
    sigma = widths(sample_points)[:, None] / (2 * np.sqrt(2 * np.log(2)))
    weights = np.exp(-0.5 * ((data_x[None, :] - sample_points[:, None]) / sigma) ** 2)
    weights *= widths(data_x)[None, :]
    return weights / weights.sum(axis=1, keepdims=True)


def scan():
    energy = np.linspace(8700, 9600, 301)
    return pd.DataFrame({"timestamp": np.arange(301.0), "energy": energy,
                         "i0": np.sin(energy / 50), "it": np.cos(energy / 50),
                         "image": list(np.arange(1806.0).reshape(301, 2, 3))})


def test_convolution_weights():
    points = np.array([1.0, 1.5, 3, 5, 7])
    data = np.linspace(0, 8, 101)
    assert_allclose(_generate_convolution_bin_matrix(points, data), dense_reference(points, data), atol=1e-16)


@pytest.mark.parametrize("mode", ["xas", "epics"])
def test_binning_matches_dense_reference(mode):
    dataset = scan()
    original = dataset.copy(deep=True)
    if mode == "xas":
        grid = xas_energy_grid(dataset.energy.values, 8979, -30, 50, 5, 0.2, 0.04)
        result = bin(dataset, 8979)
    else:
        grid = np.linspace(8700, 9600, 181)
        result = bin_epics_fly_scan(dataset, key_base="energy", step_size=5)
    weights = dense_reference(grid, dataset.energy.values)
    assert list(result) == ["energy", "i0", "it", "image"]
    assert_allclose(result.energy, grid)
    for key in ["i0", "it"]:
        assert_allclose(result[key], weights @ dataset[key].values, atol=1e-14)
    assert_allclose(np.stack(result.image), np.tensordot(weights, np.stack(dataset.image), axes=(1, 0)))
    assert_frame_equal(dataset, original)


def test_radiation_damage_scan():
    dataset = scan().iloc[::-1].copy()
    original = dataset.copy(deep=True)
    result = bin(dataset, 8979, skip_binning=True, radiation_damage_scan=True)
    assert "timestamp" not in result
    assert_array_equal(result.energy, np.arange(301))
    assert_frame_equal(dataset, original)


def test_skip_binning_does_not_mutate_gui_data():
    dataset = scan().iloc[::-1].copy()
    original = dataset.copy(deep=True)
    result = bin(dataset, 8979, skip_binning=True)
    expected = original.drop(columns="timestamp")
    energy = expected.pop("energy")
    expected["energy"] = energy
    assert_frame_equal(result, expected.sort_values("energy"))
    assert_frame_equal(dataset, original)


@pytest.mark.parametrize("function", [interpolate, interpolate_with_interp])
def test_array_downsampling_preserves_detector_shape(function):
    time = np.arange(10.0)
    fast_time = np.linspace(0, 9, 103)
    images = np.arange(618.0).reshape(103, 2, 3)
    result = function({"energy": stream(time, time), "image": stream(fast_time, images)})
    reduced_time = np.r_[fast_time[0], [v.mean() for v in np.array_split(fast_time[1:-1], 9)], fast_time[-1]]
    reduced_images = np.concatenate((images[:1], [v.mean(axis=0) for v in np.array_split(images[1:-1], 9)], images[-1:]))
    assert_allclose(np.stack(result.image), interp1d(reduced_time, reduced_images, axis=0)(time[:-1]))


@pytest.mark.parametrize("time", [np.arange(6.0), np.array([0., 1., 1., 2., 3., 3.]), np.array([1.])])
def test_image_interpolation_clamping_duplicates_and_arbitrary_shape(time):
    values = np.arange(len(time) * 6.0).reshape(len(time), 2, 3)
    queries = np.array([-1., 0., 0.25, 1., 2.5, 3., 6.])
    actual = _interpolate_images(time, values, queries).astype(float)
    for row in range(2):
        for col in range(3):
            assert_allclose(actual[:, row, col], np.interp(queries, time, values[:, row, col]))


@pytest.mark.parametrize("dataset", [{}, {"energy": stream([], [])},
                                    {"energy": stream(np.arange(7.), np.arange(7.)),
                                     "i0": stream(np.arange(10., 17.), np.arange(7.))}])
def test_empty_or_disjoint_streams_raise_clear_errors(dataset):
    with pytest.raises(ValueError, match="non-empty|overlapping"):
        interpolate(dataset)


def test_short_streams():
    result = interpolate({"energy": stream(np.arange(4.), np.arange(4.))})
    assert_array_equal(result.timestamp, np.arange(3.))


@pytest.mark.parametrize("size", [101, 102, 103])
@pytest.mark.parametrize("dtype", [np.float32, np.float64, np.int32])
def test_downsampling_rounding_with_epoch_timestamps(size, dtype):
    time = 1.8e9 + np.linspace(0, 0.01, size)
    values = np.random.default_rng(10).uniform(-100, 100, size).astype(dtype)
    actual_time, actual_values = _downsample(time, values, 10)
    expected_time = np.r_[time[0], [v.mean() for v in np.array_split(time[1:-1], 10)], time[-1]]
    expected_values = np.r_[values[0], [v.mean() for v in np.array_split(values[1:-1], 10)], values[-1]]
    assert_array_equal(actual_time, expected_time)
    assert_array_equal(actual_values, expected_values)


@pytest.mark.parametrize("dtype", [np.int32, np.float32, np.float64])
def test_image_interpolation_random_values_match_numpy(dtype):
    rng = np.random.default_rng(15)
    time = 1.8e9 + np.cumsum(rng.uniform(0.001, 0.1, 20))
    values = rng.uniform(-1000, 1000, (20, 2, 3)).astype(dtype)
    queries = np.r_[time, np.linspace(time[0] - 1, time[-1] + 1, 100)]
    actual = _interpolate_images(time, values, queries).astype(dtype)
    for row in range(2):
        for col in range(3):
            expected = np.interp(queries, time, values[:, row, col]).astype(dtype)
            assert_array_equal(actual[:, row, col], expected)


def test_image_interpolation_nonfinite_values_match_numpy():
    time = np.arange(6.)
    values = np.array([[1., np.nan], [np.nan, 2.], [3., 3.], [np.inf, -np.inf],
                       [np.inf, -np.inf], [5., 5.]])
    queries = np.r_[np.linspace(-1, 7, 33), np.nan]
    actual = _interpolate_images(time, values, queries).astype(float)
    for column in range(2):
        assert_allclose(actual[:, column], np.interp(queries, time, values[:, column]))
