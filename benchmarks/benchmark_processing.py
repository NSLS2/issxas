"""Synthetic processing timings; run from the repo with PYTHONPATH=.

To compare a previous revision, copy its bin.py and interpolate.py into a
directory and pass --baseline-dir DIRECTORY. No beamline services are used.
"""

import argparse
import contextlib
import importlib.util
import io
import logging
from pathlib import Path
from statistics import median
from time import perf_counter

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import xas.bin as current_bin
import xas.interpolate as current_interpolate


def load_baseline(directory, name):
    spec = importlib.util.spec_from_file_location("xas._baseline_" + name, directory / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stream(time, values):
    return pd.DataFrame({"timestamp": time, "value": list(values)})


def measure(function, repeats):
    with contextlib.redirect_stdout(io.StringIO()):
        function()
        durations = []
        for _ in range(repeats):
            start = perf_counter()
            function()
            durations.append(perf_counter() - start)
    return median(durations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    time = np.linspace(0, 10, 5000)
    fast_time = np.linspace(0, 10, 200000)
    scalar_data = {"energy": stream(time, 9000 + time),
                   "i0": stream(fast_time, np.sin(fast_time))}
    image_time = np.arange(12.)
    images = np.random.default_rng(0).integers(0, 10000, size=(12, 195, 487), dtype=np.int32)
    image_data = {"energy": stream(image_time + 0.25, 9000 + image_time),
                  "pil100k2_image": stream(image_time, images)}
    energy = np.linspace(8700, 10000, 12000)
    bin_data = pd.DataFrame({"timestamp": np.arange(12000.), "energy": energy,
                             **{"ch%d" % i: np.sin(energy / (i + 1)) for i in range(16)}})

    versions = {"current": (current_bin, current_interpolate)}
    if args.baseline_dir:
        versions["baseline"] = tuple(load_baseline(args.baseline_dir, name) for name in ("bin", "interpolate"))
    results = {}
    # Hold BLAS threads fixed so channel batching is comparable across machines.
    with threadpool_limits(limits=1):
        for label, (bin_module, interp_module) in versions.items():
            interp_module.get_logger = lambda: logging.getLogger("benchmark")
            cases = {
                "scalar interpolation (200000 -> 4999 samples)": lambda: interp_module.interpolate(scalar_data),
                "image interpolation (12 x 195 x 487)": lambda: interp_module.interpolate_with_interp(image_data),
                "binning (12000 samples, 16 channels)": lambda: bin_module.bin(bin_data, 8979),
            }
            results[label] = {name: measure(function, args.repeats) for name, function in cases.items()}
    for name, duration in results["current"].items():
        message = "%s: %.4f s" % (name, duration)
        if "baseline" in results:
            baseline = results["baseline"][name]
            message += " (baseline %.4f s; %.2fx speedup)" % (baseline, baseline / duration)
        print(message)


if __name__ == "__main__":
    main()
