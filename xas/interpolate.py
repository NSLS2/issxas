"""Align scalar and detector streams to their shared timestamp range."""

import time as ttime

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

from xas.xas_logger import get_logger


def _base_timestamps(dataset, key_base):
    if not dataset or any(frame.empty for frame in dataset.values()):
        raise ValueError("Interpolation requires non-empty streams")
    min_timestamp = max(frame.iloc[0, 0] for frame in dataset.values())
    # Short trigger streams historically do not constrain the upper bound.
    end_times = [frame.iloc[-1, 0] for frame in dataset.values() if len(frame) > 5]
    if not end_times:
        end_times = [frame.iloc[-1, 0] for frame in dataset.values()]
    max_timestamp = min(end_times)
    if key_base is None:
        key_base = max(dataset, key=lambda key: np.median(np.diff(dataset[key].timestamp)))
    timestamps = dataset[key_base].iloc[:, 0].to_numpy()
    timestamps = timestamps[(timestamps >= min_timestamp) & (timestamps <= max_timestamp)]
    # Preserve the historical exclusion of the last overlapping base sample.
    timestamps = timestamps[:-1]
    if not timestamps.size:
        raise ValueError("Streams have too few overlapping timestamps to interpolate")
    return timestamps


def _stream_values(frame):
    values = frame.iloc[:, 1].to_numpy()
    if values.dtype == object:
        values = np.stack(values)
    return values


def _chunk_means(values, count):
    """Vectorize array_split means using its two possible chunk lengths.

    Retaining NumPy's mean reduction avoids changing rounding of epoch-scale
    timestamps, where even small absolute differences affect interpolation.
    """
    size, remainder = divmod(len(values), count)
    split = remainder * (size + 1)
    shape = values.shape[1:]
    groups = []
    if remainder:
        groups.append(values[:split].reshape((remainder, size + 1) + shape).mean(axis=1))
    if count > remainder:
        groups.append(values[split:].reshape((count - remainder, size) + shape).mean(axis=1))
    return np.concatenate(groups, axis=0)


def _downsample(time, values, count):
    """Average the same near-equal chunks as array_split, along time only."""
    reduced_time = _chunk_means(time[1:-1], count)
    reduced_values = _chunk_means(values[1:-1], count)
    return (np.concatenate((time[:1], reduced_time, time[-1:])),
            np.concatenate((values[:1], reduced_values, values[-1:]), axis=0))


def _interpolate_images(time, values, timestamps):
    """Vectorize the legacy per-pixel np.interp path in bounded output chunks.

    Keep its endpoint clamping, input-dtype cast (including integer truncation),
    and object-valued images for compatibility with existing GUI consumers.
    The detector dimensions are taken from the data.
    """
    time = np.asarray(time, dtype=np.float64)
    numeric_values = values.astype(np.float64, copy=False)
    if len(time) == 1:
        return np.repeat(values, len(timestamps), axis=0).astype(object)
    # Search once per timestamp, rather than once per pixel. The rightmost
    # sample wins at duplicate timestamps, matching np.interp.
    lower = np.clip(np.searchsorted(time, timestamps, side='right') - 1, 0, len(time) - 1)
    upper = np.minimum(lower + 1, len(time) - 1)
    upper[timestamps < time[0]] = 0
    result = np.empty((len(timestamps),) + values.shape[1:], dtype=object)
    pixels = int(np.prod(values.shape[1:]))
    chunk_size = max(1, (8 * 1024 * 1024) // max(1, pixels * 8))
    broadcast_shape = (-1,) + (1,) * (values.ndim - 1)
    for start in range(0, len(timestamps), chunk_size):
        stop = start + chunk_size
        lo, hi = lower[start:stop], upper[start:stop]
        query = timestamps[start:stop]
        y_lo, y_hi = numeric_values[lo], numeric_values[hi]
        span = (time[hi] - time[lo]).reshape(broadcast_shape)
        with np.errstate(invalid='ignore'):
            slope = np.divide(y_hi - y_lo, span, out=np.zeros_like(y_lo), where=span != 0)
            interpolated = y_lo + slope * (query - time[lo]).reshape(broadcast_shape)
            # Match np.interp's fallback for equal infinities and missing data.
            interpolated = np.where(np.isnan(interpolated),
                                    y_hi + slope * (query - time[hi]).reshape(broadcast_shape),
                                    interpolated)
            interpolated = np.where(np.isnan(interpolated) & (y_lo == y_hi), y_lo, interpolated)
        exact = (query == time[lo]) | (lo == hi)
        interpolated[exact] = y_lo[exact]
        interpolated[np.isnan(query)] = np.nan
        result[start:stop] = interpolated.astype(values.dtype)
    return result


def _interpolate(dataset, key_base, sort, image_mode, logger=None):
    timestamps = _base_timestamps(dataset, key_base)
    result = {"timestamp": timestamps}
    for key, frame in dataset.items():
        print(f'Interpolating stream {key}...')
        if logger is not None:
            logger.info(f'({ttime.ctime()}) Interpolating stream {key}...')
        time = frame.iloc[:, 0].to_numpy()
        values = _stream_values(frame)
        if image_mode and key == 'pil100k2_image':
            interpolated = _interpolate_images(time, values, timestamps)
        else:
            if len(time) > 5 * len(timestamps):
                time, values = _downsample(time, values, len(timestamps))
            interpolated = interp1d(time, values, axis=0)(timestamps)
        result[key] = interpolated if interpolated.ndim == 1 else list(interpolated)
        print(f'Interpolation of stream {key} is complete')
        if logger is not None:
            logger.info(f'({ttime.ctime()}) Interpolation of stream {key} is complete')
    dataframe = pd.DataFrame(result)
    return dataframe.sort_values('energy') if sort else dataframe


def interpolate(dataset, key_base=None, sort=True):
    """Align streams, averaging oversampled streams before interpolation.

    Array-valued streams are interpolated along their first (time) axis.
    Sorting by energy and the existing timestamp trimming are preserved.
    Input DataFrames are never modified.
    """
    return _interpolate(dataset, key_base, sort, image_mode=False, logger=get_logger())


def interpolate_with_interp(dataset, key_base=None, sort=True):
    """Align streams using the legacy Pilatus image interpolation semantics."""
    return _interpolate(dataset, key_base, sort, image_mode=True)
