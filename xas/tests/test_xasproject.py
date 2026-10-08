"""Dataset/project contracts, isolating the optional Qt and Larch dependencies.

The stand-ins exercise local data handling and notification counts; they do not
validate Qt event delivery or Larch's normalization algorithms.
"""

import importlib.util
from pathlib import Path
import pickle
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal


@pytest.fixture
def project_module(monkeypatch):
    qt = ModuleType("PyQt5")
    qt.QtCore = SimpleNamespace(QObject=object, pyqtSignal=lambda *args: None)
    larch = ModuleType("larch")
    larch.Group = SimpleNamespace
    larch.Interpreter = object
    xafs = ModuleType("larch.xafs")
    for name in ("pre_edge", "autobk", "mback", "xftf"):
        setattr(xafs, name, Mock(side_effect=AssertionError("Unexpected Larch call")))
    for name, module in (("PyQt5", qt), ("larch", larch), ("larch.xafs", xafs)):
        monkeypatch.setitem(sys.modules, name, module)
    path = Path(__file__).parents[1] / "xasproject.py"
    spec = importlib.util.spec_from_file_location("_test_xasproject", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("e0", [2., [2.], np.array([2.]), np.array([[2.]])])
def test_flatten_preserves_preedge_and_corrects_postedge(project_module, e0):
    dataset = project_module.XASDataSet(energy=np.arange(6.), process=False)
    dataset.e0 = e0
    dataset.norm = np.array([0., 0.1, 0.2, 1.1, 1.2, 1.3])
    dataset.pre_edge = np.zeros(6)
    dataset.post_edge = np.array([2., 2., 2., 2.2, 2.4, 2.6])
    dataset.edge_step = 2.
    norm = dataset.norm.copy()
    dataset.flatten()
    assert_allclose(dataset.flat, [0., 0.1, 0.2, 1., 1., 1.])
    assert_array_equal(dataset.norm, norm)
    assert not np.shares_memory(dataset.flat, dataset.norm)


def test_flatten_without_postedge_retains_existing_behavior(project_module, capsys):
    dataset = project_module.XASDataSet(energy=np.arange(3.), process=False)
    dataset.e0 = 5.
    dataset.flatten()
    assert "Skipping flatten calculation" in capsys.readouterr().out
    assert not hasattr(dataset, "flat")


def test_load_appends_all_datasets_before_notifying_gui(project_module, tmp_path):
    path = tmp_path / "project.pkl"
    with path.open("wb") as handle:
        pickle.dump(["scan-1", "scan-2", "scan-3"], handle)
    project = project_module.XASProject()
    project.datasets.append("existing")
    project.datasets_changed = Mock()
    snapshots = []
    project.datasets_changed.emit.side_effect = lambda data: snapshots.append(list(data))
    project.load(path)
    assert project.datasets == ["existing", "scan-1", "scan-2", "scan-3"]
    assert snapshots == [["existing", "scan-1", "scan-2", "scan-3"]]
    project.datasets_changed.emit.assert_called_once_with(project.datasets)


def test_save_load_roundtrip(project_module, tmp_path):
    project = project_module.XASProject()
    project.datasets.extend([{"name": "scan", "energy": [1, 2, 3]}])
    path = tmp_path / "project.pkl"
    project.save(path)
    loaded = project_module.XASProject()
    loaded.datasets_changed = Mock()
    loaded.load(path)
    assert loaded.datasets == project.datasets


def test_empty_project_load_does_not_notify(project_module, tmp_path):
    path = tmp_path / "empty.pkl"
    with path.open("wb") as handle:
        pickle.dump([], handle)
    project = project_module.XASProject()
    project.datasets_changed = Mock()
    project.load(path)
    project.datasets_changed.emit.assert_not_called()
