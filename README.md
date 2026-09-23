# instruments

Python VISA drivers for the lab instruments used to run experiments on
superconducting circuits (Collège de France / FluxQuantumLab). Wraps
[PyVISA](https://pyvisa.readthedocs.io/) so each instrument (VNAs, source
meters, signal generators, a lock-in, an oscilloscope, a motor controller...)
gets a small Python class with named methods/properties instead of raw SCPI
strings.

For how the package is organized, its known issues, and planned cleanup, see
[`instruments/instruments_overview.md`](instruments/instruments_overview.md),
[`instruments/instruments_improvements.md`](instruments/instruments_improvements.md),
and [`instruments/instruments_refactor.md`](instruments/instruments_refactor.md).

`instruments/RFSoC/` holds unrelated, independently-packaged vendored
projects (QICK, an RFSoC textbook, DSP notebooks) kept here for reference;
it is not part of the installable `instruments` package.

## Requirements

- Python >= 3.8
- A VISA backend — either [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html)
  (install separately, not via pip) or the pure-Python
  [`pyvisa-py`](https://pyvisa-py.readthedocs.io/) backend
  (`pip install pyvisa-py`)
- Everything else (`pyvisa`, `numpy`, `matplotlib`) installs automatically
  with the package — see `requirements.txt` / `pyproject.toml`.

## Install

### On a machine you'll also edit code on (recommended)

Clone the repo once, then install it in **editable mode**. This points the
installed package straight at your working copy, so a `git pull` alone picks
up updates on that machine — no reinstall needed.

```bash
git clone https://github.com/err4re/instruments.git
cd instruments
pip install -e .
```

### On a machine that only needs to use the drivers

```bash
pip install git+https://github.com/err4re/instruments.git
```

This copies the package at install time. To pick up later changes, re-run
the same command (or switch to the editable install above).

## Keeping multiple machines in sync

Each machine keeps its own clone of this repo:

- From wherever you made a change: `git add -u`, `git commit -m "..."`,
  `git push`.
- On every other machine: `git pull`. With an editable install (above),
  that's the only step needed.

If a machine used the non-editable `pip install git+...` instead, re-run
that command after pulling to actually pick up the change.

## Usage

```python
from instruments.znb import Znb
from instruments.configs.znb_config import ZnbLinConfig

vna = Znb("TCPIP0::192.168.1.5::inst0::INSTR")
config = ZnbLinConfig(center_frequency=6e9, span=500e6, bandwidth=1e3,
                       num_points=1001, num_averages=10, power=-30)
vna.set_sweep(config)
freqs, s_data = vna.sweep()
```

Every driver under `instruments/` follows the same pattern: import the
class, instantiate it with a VISA resource string, then call its
methods/properties. See `instruments/instruments_overview.md` for a
driver-by-driver rundown.

## License

MIT — see [LICENSE](LICENSE).
