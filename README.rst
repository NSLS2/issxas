===============================
XAS
===============================

.. image:: https://img.shields.io/travis/elistavitski/xas.svg
        :target: https://travis-ci.org/elistavitski/xas

.. image:: https://img.shields.io/pypi/v/xas.svg
        :target: https://pypi.python.org/pypi/xas


Calculation tools for X-ray absorption spectroscopy at NSLS II

* Free software: 3-clause BSD license
* Documentation: (COMING SOON!) https://elistavitski.github.io/xas.

Features
--------

* Timestamp alignment of scalar and detector-image streams.
* Gaussian convolution binning for XAS and EPICS fly scans.
* Beamline data loading, calibration, and analysis utilities.

Offline tests and benchmarks
----------------------------

Run numerical processing tests without a database, Qt, or beamline filesystem::

    python -m pip install -r requirements-test.txt
    python -m pytest xas/tests -q

Run synthetic timings with a fixed BLAS thread count::

    PYTHONPATH=. python benchmarks/benchmark_processing.py

For a before/after comparison, export the previous revision's ``xas/bin.py``
and ``xas/interpolate.py`` to a directory and pass ``--baseline-dir DIRECTORY``.
These timings cover computation only; GUI, database, and file I/O latency must
be measured in the deployed environment. The root ``test.py`` is a separate
integration script that connects to the NSLS-II Tiled service and writes output.

Processing compatibility
------------------------

The interpolation and binning entry points retain their public signatures,
column ordering, energy sorting, and array-valued DataFrame cells. Interpolation
still excludes the final overlapping timestamp. ``interpolate_with_interp``
retains the Pilatus path's integer truncation and object image dtype while
accepting detector dimensions from the input instead of requiring 195 x 487.

Binning no longer reorders the caller's DataFrame when ``skip_binning=True``.
Interpolation reports empty or nonoverlapping streams with ``ValueError`` and
also supports scans whose streams all contain at most five samples. Gaussian
weights and energy-grid generation retain the existing numerical model;
batching channel products can cause ordinary floating-point rounding differences.

The xview-facing ``XASDataSet.flatten`` handles scalar and single-element edge
energies and corrects the normalized spectrum above the edge without modifying
``norm``. ``XASProject.load`` still appends saved datasets, but emits one
``datasets_changed`` signal after the complete load, avoiding repeated GUI
refreshes. Its tests isolate Qt and Larch with stand-ins; a deployed GUI smoke
test is still needed to validate event delivery and full normalization.
