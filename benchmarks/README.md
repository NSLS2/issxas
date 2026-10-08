# Processing benchmark

Run from the repository root after installing `requirements-test.txt`:

```sh
PYTHONPATH=. python benchmarks/benchmark_processing.py --baseline-dir /path/to/old/modules
```

The baseline directory must contain the previous `bin.py` and `interpolate.py`.
Omit `--baseline-dir` to time only the current implementation. Each case warms up
once and reports the median of three runs with one BLAS thread.

Observed in the refactoring environment (Python 3.12, NumPy 2.5.3, pandas 3.0.6,
SciPy 1.18.1), comparing against the original files from this checkout:

| Synthetic workload | Before | After | Speedup |
| --- | ---: | ---: | ---: |
| Scalar interpolation, 200,000 source samples | 52.1 ms | 3.3 ms | 15.6× |
| Image interpolation, 12 frames of 195 × 487 pixels | 1,138.0 ms | 74.5 ms | 15.3× |
| Binning, 12,000 samples and 16 channels | 103.1 ms | 52.5 ms | 2.0× |

These are computation timings, not GUI or beamline throughput measurements.
Results depend on scan dimensions, numerical libraries, and hardware. Image
output keeps its legacy object dtype and integer truncation. Binning still
allocates the dense Gaussian weight matrix; this refactor does not bound its
memory use for very large scans.

The compatibility review inspected the default branches of
[xview](https://github.com/NSLS-II-ISS/xview/tree/9ca42e3f1ef4b02b3aa56202c4ebef6bf9a01867)
and [iss-profile-collection](https://github.com/NSLS2/iss-profile-collection/tree/b2c6b292c51ec4983d041165aff6b6ce641bd13a).
xview rebuilds the entire project list in its `datasets_changed` callback; the
updated `XASProject.load` emits this signal once per nonempty file instead of
once per loaded dataset. No wall-clock GUI speedup is claimed. Project tests
use Qt/Larch stand-ins, and the deployed applications were not launched.
