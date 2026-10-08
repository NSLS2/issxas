"""Numerical contracts against the real Larch API used by both GUIs."""

import numpy as np
from numpy.testing import assert_allclose

from xas.xasproject import XASDataSet


def test_fourier_components_and_requested_window_are_preserved():
    energy = np.linspace(8700., 9900., 601)
    mu = .0001 * (energy - 8700) + 1 / (1 + np.exp(-(energy - 8979) / 2))
    ds = XASDataSet(energy=energy, mu=mu, md={"e0": 8979})
    ds.kmax_ft = 7
    ds.kweight = 1
    ds.extract_ft()
    assert ds.kmax_ft == 7
    assert_allclose(ds.chir_im, ds.chir.imag)
    assert_allclose(ds.chir_re, ds.chir.real)
    ds.extract_ft_force({"window_type": "hanning", "tapering": 1, "r_weight": 2})
    assert_allclose(ds.chir_im, ds.chir.imag)
    assert_allclose(ds.chir_re, ds.chir.real)


def test_nominal_actual_converter_interpolates_both_directions():
    from xas.fitting import Nominal2ActualConverterWithLinearInterpolation

    converter = Nominal2ActualConverterWithLinearInterpolation()
    converter.append_point(10, 11)
    converter.append_point(20, 23)
    assert_allclose(converter.nom2act(15), 17)
    assert_allclose(converter.act2nom(17), 15)
