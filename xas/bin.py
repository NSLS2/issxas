"""Gaussian convolution binning for absorption and EPICS fly scans."""

import time as ttime

import numexpr as ne
import numpy as np
import pandas as pd

from . import xray


def get_transition_grid(dE_start, dE_end, E_range, round_up=True):
    if round_up:
        n = np.ceil(2 * E_range / (dE_start + dE_end))
    else:
        n = np.floor(2 * E_range / (dE_start + dE_end))
    delta = (E_range*2/n - 2*dE_start)/(n-1)
    steps = dE_start + np.arange(n)*delta
    return np.cumsum(steps)


def xas_energy_grid(energy_range, e0, edge_start, edge_end, preedge_spacing, xanes_spacing, exafs_k_spacing,
                    E_range_before=15, E_range_after=20, n_before=10, n_after=20):
    """Build the pre-edge, XANES, and EXAFS sampling grid."""
    energy_range_lo = np.min([e0 - 300, np.min(energy_range)])
    energy_range_hi = np.max([e0 + 2500, np.max(energy_range)])

    preedge = np.arange(energy_range_lo, e0 + edge_start, preedge_spacing)

    before_edge = preedge[-1] + get_transition_grid(
        preedge_spacing, xanes_spacing, E_range_before, round_up=False
    )

    edge = np.arange(before_edge[-1], e0+edge_end-E_range_after, xanes_spacing)
    eenergy = xray.k2e(xray.e2k(e0+edge_end, e0), e0)
    post_edge = []

    while eenergy < energy_range_hi:
        kenergy = xray.e2k(eenergy, e0)
        kenergy += exafs_k_spacing
        eenergy = xray.k2e(kenergy, e0)
        post_edge.append(eenergy)

    after_edge = edge[-1] + get_transition_grid(
        xanes_spacing, post_edge[1] - post_edge[0], post_edge[0] - edge[-1], round_up=True
    )
    energy_grid = np.unique(np.concatenate((preedge, before_edge, edge, after_edge, post_edge)))
    energy_grid = energy_grid[(energy_grid >= np.min(energy_range)) & (energy_grid <= np.max(energy_range))]
    return energy_grid


def _generate_convolution_bin_matrix(sample_points, data_x):
    fwhm = _compute_window_width(sample_points)
    delta_en = _compute_window_width(data_x)

    mat = _generate_sampled_gauss_window(
        data_x.reshape(1, -1), fwhm.reshape(-1, 1), sample_points.reshape(-1, 1)
    )
    mat *= delta_en.reshape(1, -1)
    mat /= np.sum(mat, axis=1)[:, None]
    return mat


_GAUSS_SIGMA_FACTOR = 1 / (2 * (2 * np.log(2)) ** .5)


def _generate_sampled_gauss_window(x, fwhm, x0):
    sigma = fwhm * _GAUSS_SIGMA_FACTOR
    a = 1 / (sigma * (2 * np.pi) ** .5)
    data_y = ne.evaluate('a * exp(-.5 * ((x - x0) / sigma) ** 2)')
    return data_y


def _compute_window_width(sample_points):
    '''Given sample points compute windows via approx 1D voronoi

    Parameters
    ----------
    sample_points : array
        Assumed to be monotonic

    Returns
    -------
    windows : array
        Average of distances to neighbors
    '''
    d = np.diff(sample_points)
    fw = (d[1:] + d[:-1]) / 2
    return np.concatenate((fw[0:1], fw, fw[-1:]))


def _bin_columns(dataset, key_base, grid, weights):
    """Apply a shared convolution to scalar channels in one matrix product.

    Detector arrays retain their original shape and DataFrame column position.
    Do not convolve timestamps, which are excluded from the binned output.
    """
    columns = [key for key in dataset if key not in (key_base, 'timestamp')]
    scalar_columns = [key for key in columns if np.ndim(dataset[key].iloc[0]) == 0]
    scalar_results = {}
    if scalar_columns:
        values = dataset[scalar_columns].to_numpy(dtype=np.float64)
        convolved = weights @ values
        scalar_results = dict(zip(scalar_columns, convolved.T))

    result = {key_base: grid}
    for key in columns:
        if key in scalar_results:
            result[key] = scalar_results[key]
        else:
            values = np.stack(dataset[key].to_numpy()).astype(np.float64, copy=False)
            result[key] = list(np.tensordot(weights, values, axes=(1, 0)))
    return pd.DataFrame(result)


def bin(interpolated_dataset, e0, edge_start=-30, edge_end=50, preedge_spacing=5,
        xanes_spacing=-1, exafs_k_spacing=0.04, skip_binning=False, radiation_damage_scan=False):
    """Bin scan channels without modifying the input DataFrame."""
    if skip_binning:
        if radiation_damage_scan:
            print("Processing radiation damage scan....")
            binned_df = interpolated_dataset.sort_values('timestamp')
            binned_df.pop("energy")
            binned_df['timestamp'] = binned_df['timestamp'] - binned_df['timestamp'].min()
            binned_df.rename(columns={'timestamp': 'energy'}, inplace=True)
            return binned_df
        else:
            binned_df = interpolated_dataset.copy()
            col = binned_df.pop("energy")
            n = len(binned_df.columns)
            binned_df.insert(n, col.name, col)
            binned_df = binned_df.sort_values('energy')
    else:
        print(f'({ttime.ctime()}) Binning the data: BEGIN')
        if xanes_spacing == -1:
            if e0 < 14000:
                xanes_spacing = 0.2
            elif e0 < 21000:
                xanes_spacing = 0.3
            elif e0 >= 21000:
                xanes_spacing = 0.4
            else:
                xanes_spacing = 0.3

        interpolated_energy_grid = interpolated_dataset['energy'].values
        binned_energy_grid = xas_energy_grid(
            interpolated_energy_grid, e0, edge_start, edge_end,
            preedge_spacing, xanes_spacing, exafs_k_spacing
        )

        convo_mat = _generate_convolution_bin_matrix(binned_energy_grid, interpolated_energy_grid)
        binned_df = _bin_columns(interpolated_dataset, 'energy', binned_energy_grid, convo_mat)
    binned_df = binned_df.drop('timestamp', axis=1, errors='ignore')
    print(f'({ttime.ctime()}) Binning the data: DONE')
    return binned_df


def bin_epics_fly_scan(interpolated_dataset, key_base=None, step_size=5):
    """Convolve scan channels onto an evenly spaced base-channel grid."""

    interpolated_base_grid = interpolated_dataset[key_base].values
    minimum, maximum = np.min(interpolated_base_grid), np.max(interpolated_base_grid)
    binned_base_grid = np.linspace(minimum, maximum, int((maximum - minimum) / step_size + 1))
    convo_mat = _generate_convolution_bin_matrix(binned_base_grid, interpolated_base_grid)
    binned_df = _bin_columns(interpolated_dataset, key_base, binned_base_grid, convo_mat)
    binned_df = binned_df.drop('timestamp', axis=1, errors='ignore')
    print(f'({ttime.ctime()}) Binning the data: DONE')
    return binned_df
