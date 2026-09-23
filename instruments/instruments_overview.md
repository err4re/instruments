# Instruments Overview

This document maps out how the `instruments` package works. It covers only the
lab-instrument drivers that live directly in this repository (root `*.py`
files and `configs/`). It does **not** cover `RFSoC/`, which is a collection
of vendored third-party projects (QICK, a DSP-notebooks package, RFSoC-Book,
calibration notebooks) unrelated to the VISA driver layer described here.

## What this package is

A thin Python wrapper around [PyVISA](https://pyvisa.readthedocs.io/) that
gives each lab instrument (VNAs, source meters, signal generators, lock-ins,
oscilloscopes, a spectrum analyzer, a motor controller) a small Python class
with named methods/properties instead of raw SCPI strings. It is used
interactively from Jupyter notebooks / scripts to run experiments on
superconducting-circuit setups at Collège de France / FluxQuantumLab.

There is no test suite, no packaging metadata (`setup.py`/`pyproject.toml`),
and no CI. The package is imported either as `instruments.znb` (if the parent
directory is on `sys.path`) or via relative imports; see "Import
inconsistencies" below for why both styles currently coexist.

## Directory layout

```
instruments/
├── __init__.py              # empty
├── instr.py                 # base class: raw VISA plumbing, shared by nearly every driver
├── anapico.py                # AnaPico APMS signal generator
├── znb.py                    # Rohde & Schwarz ZNB vector network analyzer
├── zvk.py                    # Rohde & Schwarz ZVK vector network analyzer (older model)
├── fsva.py                   # Rohde & Schwarz FSVA spectrum analyzer
├── k2400.py                  # Keithley 2400 source meter unit (SMU)
├── k2182a.py                  # Keithley 2182A nanovoltmeter
├── k6220.py                   # Keithley 6220 current source (via a GPIB bridge, not VISA)
├── egg5210.py                 # EG&G 5210 lock-in amplifier
├── instek3032.py              # GW Instek AFG-3032 function generator
├── mcdc2805.py                 # Faulhaber MCDC 2805 motor controller
├── yoko7651.py                 # Yokogawa 7651 programmable DC source
├── yoko750.py                  # Yokogawa DL750 oscilloscope
├── configs/
│   ├── znb_config.py          # dataclasses describing ZNB sweep configurations
│   ├── anapico_config.py      # dataclasses describing AnaPico sweep/trigger configurations
│   └── yoko7651_config.py     # dataclasses describing Yoko7651 sweep configurations
└── RFSoC/                     # unrelated vendored RFSoC/QICK material (see note above)
```

## The base class: `instr.Instr`

Every driver except `k6220.py` subclasses `instr.Instr` (`instr.py`). It:

- Opens a PyVISA resource (`visa.ResourceManager(visa_library).open_resource(visa_name)`)
  and stores it as `self.visa_instr`.
- Sets a default 5 s timeout.
- Exposes thin passthroughs to the underlying `pyvisa` resource: `write()`,
  `read()`, `query()`, `query_ascii_values()`, `clear()`, `trigger()`.
- Implements the standard SCPI mandatory commands: `get_idn()` (`*IDN?`),
  `cls()` (`*CLS`), `reset()` (`*RST`).
- Implements two operation-complete synchronization helpers:
  `prepare_for_stb()`/`wait_for_stb()` (poll status byte for the OPC bit) and
  `prepare_for_srq()`/`wait_for_srq()` (GPIB service-request based, marked
  "NOT TESTED").
- Manages resource lifetime: `clean()` clears and closes the VISA session;
  `__del__()` calls `clean()` if it hasn't already run (`self._clean` flag).

Every subclass typically calls `super().__init__(visa_name, visa_library)`,
then overrides communication settings that are instrument-specific
(termination characters, baud rate for serial instruments, chunk size for
large binary transfers, timeout) and instrument-specific default state
(selecting a channel, data format, etc.).

## Driver-by-driver summary

### `anapico.py` — AnaPico APMS signal generator
- Verifies `*IDN?` starts with `"AnaPico APMS"`.
- `current_channel` property switches between the 2 available output channels
  via `:SEL`.
- Properties for `power`, `freq_mode`, `power_mode`, sweep parameters
  (`start_frequency`, `stop_frequency`, `sweep_points`, `sweep_delay`,
  `sweep_count`, `sweep_dwell_time`), trigger parameters (`trigger_source`,
  `trigger_type`, `trigger_slope`), and `init_cont`.
- `set_freq_sweep(config: AnaFreqSweepConfig)` and
  `set_ext_trig(config: AnaExtTrigInConfig)` apply a whole sweep/trigger
  configuration in one call, using dataclasses from `configs/anapico_config.py`.
- `flatness_correction_upload()` uploads a frequency/amplitude correction
  table point-by-point, waiting for `*OPC?` after each point.
- `metadata` property returns a snapshot dict of both channels' settings —
  used for saving experiment metadata alongside data.
- Uses free functions `ERR()`/`WARN()`/`INFO()` (module-level, not on the
  class) as a home-grown logging mechanism instead of raising exceptions or
  using the `logging` module.

### `znb.py` — Rohde & Schwarz ZNB vector network analyzer
The most actively developed and most complex driver (824 lines, contributed
to by at least 5 different people over the years, per the inline attribution
comments: "JLS", Leo, Lou, Alex, çağlar...).

- On init, auto-discovers the first existing channel/trace
  (`list_channels()`, `list_traces()`) and sets binary REAL,64 transfer.
- Low-level building blocks: `set_power`, `set_nb_points`, `set_average`,
  `set_if_bw`, `smoothing`, `set_freq_start_stop`/`set_freq_center_span`,
  channel/trace creation and deletion (`create_channel_and_trace`,
  `delete_trace`, etc.), and data retrieval (`get_sdata`, `get_fdata`,
  `get_trace_sdata`, `get_trace_fdata`, using `query_binary_values` for
  speed).
- `meta` / `get_meta()` / `get_state()` return/print a snapshot of the
  current sweep configuration (handles both regular and segmented sweeps).
- Segmented-sweep support: `add_segment`, `set_segment_freqs`,
  `set_segment_points`, `set_segment_bandwidth`, `clear_all_segments`.
- Trace hold (min/max hold): `hold_function` property, added most recently
  (dated 2026-09-17 in the source comments).
- High-level configuration entry points, each taking a dataclass from
  `configs/znb_config.py`: `set_lin_sweep(ZnbLinConfig)`,
  `set_cw_sweep(ZnbCWConfig)`, `set_segm_sweep(ZnbSegmConfig)`, dispatched via
  `set_sweep(config)` which does `isinstance` checks.
- High-level acquisition: `sweep()` (single sweep, blocking on `*OPC?`,
  returns `(f, z)`) and `sweeps()` (multiple sweeps in one acquisition using
  `CALC:DATA:NSWeep:FIRSt?`, returns `(f, list_of_z)`).
- A large block of properties duplicates functionality already present as
  plain methods higher up in the file (e.g. `f_center`/`f_span`/`f_start`/
  `f_stop` vs. `set_freq_center_span`/`set_freq_start_stop`; `source_freq`
  vs. nothing equivalent above; `sweep_count`/`average_count` as properties
  are new but overlap conceptually with `set_average`). This is the file's
  own comment marker: `# ---------- CODE WRITTEN BY LOU 2022/03/15`, i.e. the
  file grew by accretion rather than refactoring.
- `ext_trigger_out_interval` property is defined **twice** in the file (once
  around line 271, once again around line 588) — the second definition
  silently shadows the first at class-body execution time. See Improvements
  doc.

### `zvk.py` — Rohde & Schwarz ZVK VNA (older/simpler sibling of ZNB)
- Much simpler: no auto-discovery of channels/traces, just a fixed
  `current_channel = 1` on init and a `set_current_channel()` method for the
  4 physical channels.
- Properties for power, output, center/span/start/stop frequency (also as a
  combined `freq_center_span`/`freq_start_stop` pair), sweep duration/points/
  step, averaging, bandwidth, sweep direction, continuous/single sweep mode.
- `get_data(trace)` reads one or all named traces (`CH1DATA`..`CH4DATA`,
  `MDATA1`..`MDATA8`) via `query_binary_values`, storing results in `self.f`/
  `self.z` dicts keyed by trace name.
- No dataclass-based high-level config entry point (unlike `znb.py`) — the
  caller must set each property individually.
- The `read_termination` line is commented out with a note: "this is the
  problematic part, makes weird artifacts appear for some reason" — an
  unresolved hardware/protocol quirk.

### `fsva.py` — Rohde & Schwarz FSVA spectrum analyzer
- Small (100 lines). Properties for center/span/start/stop frequency, sweep
  time, VBW, RBW, number of points, averaging (read-only count).
- `get_trace(tracenum)` returns `(frequencies, values)` using
  `query_binary_values` for the trace data but a manually computed
  `np.linspace` for the frequency axis (`get_frequencies()`) rather than
  querying the instrument's actual X-axis data — a source of drift if
  `f_start`/`f_stop`/`nb_points` don't perfectly reproduce the instrument's
  internal grid.
- The `unit` setter has a bug: it always calls `self.query('UNIT:POW?')`
  (query, not write) regardless of the value passed, so the unit can never
  actually be changed. See Improvements doc.

### `k2400.py` — Keithley 2400 SMU
- One of the oldest, most method-heavy drivers (uses tabs for indentation,
  unlike the rest of the codebase which uses spaces).
- **Cannot currently be instantiated**: `__init__(self, visa_name)` calls
  `super(K2400, self).__init__(visa_name)`, but `instr.Instr.__init__`
  requires *both* `visa_name` and `visa_library` with no default value for
  the latter — this raises `TypeError: __init__() missing 1 required
  positional argument: 'visa_library'` on every call to `K2400(...)`. Same
  bug as `k2182a.py` below. See Improvements doc.
- Verifies IDN, tracks current/voltage limits client-side
  (`min_current`/`max_current`/etc.), source/sense mode toggles
  (`source_current`/`source_voltage`/`sense_current`/etc.), compliance
  settings, output on/off, and a buffer-based trace-data readout
  (`data_buffer_read`, `data_nb_points`).
- `set_current_smooth()` implements a client-computed linear current ramp
  using the instrument's built-in sweep feature, with a background
  "sweep-in-progress" flag (`last_sweep_finished`) that `wait_for_sweep()`
  polls — but note this state can desync if a sweep is triggered by any means
  other than `set_current_smooth()` itself.
- Several functions are explicit stubs: `read_binary()`, `bin2num()`,
  `get_range()` — `pass` with a comment, not implemented.
- `go_to_local()`/`group_execute_trigger()` are marked "NOT WORKING".

### `k2182a.py` — Keithley 2182A nanovoltmeter
- Very small driver: channel selection, measurement range, integration time
  (NPLC), analog/digital filtering, `get_voltage()` with software-averaging
  over repeated single reads.
- **Broken import**: `import instr` (absolute, no `instruments.` prefix and
  no relative `.` import) and constructor `__init__(self, visa_name)` doesn't
  accept/forward `visa_library`, unlike every sibling driver. This driver
  will fail to import as part of the `instruments` package (see Improvements
  doc — "Inconsistent imports").
- Has a stray `print('i am imported')` at module level — a leftover debug
  statement that executes every time the module is imported.

### `k6220.py` — Keithley 6220 current source
- **Does not inherit from `instr.Instr`** and does not use VISA at all. It
  wraps a `pna_instance` (apparently a legacy in-house GPIB bridge object)
  and calls `gpib_bridge_open/ask/write/read/close` on it.
- Written in **Python 2 syntax** (`print "..."` statements, not
  `print(...)`) — this file cannot be imported under Python 3 at all; it
  would raise a `SyntaxError` immediately. It appears to be dead/legacy code
  kept for reference.
- Otherwise structurally identical to `k2400.py`'s current-sweep logic
  (`set_current`, `wait_for_sweep`, etc.) — likely the ancestor that
  `k2400.py`'s sweep code was copied from.

### `egg5210.py` — EG&G 5210 lock-in amplifier
- The most defensive/robust protocol implementation in the repo: `write()`
  and `query()` are both routed through a single `communicate()` method that
  reads the GPIB status byte before and after sending a command, checking for
  "parameter error", "invalid command", and "command not complete" bits, and
  raising `RuntimeError` on failure — rather than the print-and-continue
  style used everywhere else.
- Sensitivity and time-constant ranges are stored as lists of
  `{"code":.., "sensitivity"/"timeconstant":..}` dicts (`fullscale_codes`,
  `timeconstant_codes`) rather than a formula, even though a formula
  (`rangecode_to_range()`) is defined at module level and unused — dead code
  the class could presumably use instead.
- Getters for X/Y/phase/complex output scale the raw instrument reading by
  `self.fullscale/10000`, i.e. results depend on `self.fullscale` being kept
  in sync with the instrument's actual current range; there's no query to
  cross-check before every read.
- Uses `np.float` in several places (`get_x`, `get_y`, `get_phase_degrees`,
  `get_frequency`, ...) — `numpy.float` was removed in NumPy ≥1.24, so this
  driver is broken on any reasonably modern NumPy install.
- Uses tabs for indentation, like `k2400.py`.

### `instek3032.py` — GW Instek function generator
- Small, consistent, uses Python properties throughout for every setting
  (`current_channel`, `output`, `load`, `freq`, `ampl`, `dc_offset`, `phase`,
  `unit`).
- `output` setter has a bug: `if state.lower == "on"` compares the *bound
  method* `str.lower` to the string `"on"`, which is always `False` (missing
  parentheses: should be `state.lower() == "on"`). See Improvements doc.
- `apply_waveform()` requires either none or *all three* of `freq`/`amp`/
  `offset` as kwargs — no partial application.

### `mcdc2805.py` — Faulhaber motor controller
- Serial (RS232) instrument; sets baud rate, parity, stop bits, flow control
  explicitly.
- Simple command wrappers around the manufacturer's proprietary text
  protocol (not SCPI): `velocity()`, `acceleration()`, `rotate_to()`,
  `rotate_of()`, `hardstop()`, etc., all get/set via a single positional
  `value=None` argument convention (`None` → query, else → set).
- Overrides `write()`/`query()` from the base class but the overrides do
  nothing beyond what the base class already does (the `debug` parameter is
  accepted but never used) — likely leftover from copying `anapico.py`'s
  structure.

### `yoko7651.py` — Yokogawa 7651 DC source
- Fairly elaborate: tracks voltage/current mode and range client-side,
  implements built-in ramping (`ramp_current`/`ramp_voltage`) using the
  instrument's program-memory feature, and a `write_program()` context
  manager for building multi-step programs (`begin_writing_program()` /
  `finish_writing_program()`).
- `set_source_current_sweep`/`set_source_voltage_sweep` take config
  dataclasses from `configs/yoko7651_config.py` (`YokoCurrSweepConfig`,
  `YokoVoltSweepConfig`) but only set range — they don't actually iterate
  through `config.currents`/`config.voltages`, so the "sweep" defined by
  those dataclasses is not actually executed by these methods; the caller
  must loop manually using `voltage()`/`current()`. The dataclasses' own
  `wait` field is likewise unused inside this driver.
- Free functions `output_force`, `Output`, `output_on`, `output_off` are
  defined at **module level, outside the class**, each taking `self` as
  their first argument as if they were methods — they are not attached to
  `Yoko7651` and cannot be called as `yoko.output_on()`. Dead/broken code.
- `program_run_mode()` has a typo: `self.wite("M1")` instead of `self.write("M1")`.
- Mixes tabs (existing code) — consistent with the file's Python-2-era origin
  comment header.

### `yoko750.py` — Yokogawa DL750 oscilloscope
- By far the largest file (1594 lines). Implements the full SCPI-like Yoko
  oscilloscope command set: acquisition mode/averaging, timebase, per-channel
  volt/div, trigger source/level/mode/position, binary and ASCII waveform
  transfer with adaptive timeout scaling based on record length
  (`get_binary`, `get_binary_old`, `get_binary_quick`), and IGOR Pro export
  (`save_itx`) that writes a `.itx` text file plus an embedded Igor scripting
  macro as a "footer".
- Keeps a rich nested `Trace` class (defined *inside* `__init__`, a local
  class) with per-channel metadata (gain, offset, bandwidth, probe ratio,
  etc.) — `self.traces` is a list of these.
- Contains three near-duplicate implementations of the same operation
  (`get_binary`, `get_binary_old`, `get_binary_quick`), differing mainly in
  the timeout-scaling heuristic and endianness flag — `get_binary_old` uses
  `is_big_endian=True` while `get_binary` uses `is_big_endian=False` for the
  same instrument and command, which is suspicious (unless the instrument's
  behavior genuinely changed between firmware/measurement conditions the
  comments don't explain).
- The module-level `ERR()` here takes a single positional `arg` and does
  string concatenation (`+ arg`), unlike the near-identical `ERR()` function
  redefined independently in `anapico.py`/`mcdc2805.py`, which instead take
  `*args` and use `print(*args, **kwarg)`. Three separate, slightly
  incompatible copies of the same helper exist in the codebase.

## Configuration dataclasses (`configs/`)

Three of the many drivers have grown a companion "config" module holding
`@dataclass` definitions that bundle up a full instrument configuration
(frequencies, power, averaging, sweep type, trigger settings, ...) so a whole
sweep can be set up in one call (`instrument.set_sweep(config)`) instead of
many individual property assignments:

- `configs/znb_config.py`: `ZnbLinConfig`, `ZnbCWConfig`, `ZnbSegm` +
  `ZnbSegmConfig`, `ZnbExtTrigOutConfig`.
- `configs/anapico_config.py`: `AnaFreqSweepConfig`, `AnaExtTrigInConfig`.
- `configs/yoko7651_config.py`: `YokoCurrSweepConfig`, `YokoVoltSweepConfig`.

Each dataclass validates itself in `__post_init__` (e.g. computing
`start`/`stop` from `center`/`span` or vice versa, raising `ValueError` if
required fields are missing). This is the most "modern" and consistent part
of the codebase — the other 10 drivers have no equivalent and configure
everything through individual property/method calls instead. Only 3 of 13
instruments have adopted this pattern, and even for those three, it's only
partially wired in (e.g. `Yoko7651`'s sweep configs are accepted but not
actually driven — see driver notes above).

## Cross-cutting conventions (and lack thereof)

- **Error reporting** is inconsistent across files: some raise exceptions
  (`instek3032.py`, `k2182a.py`... no, actually most `raise ValueError`
  sparingly), some `print()` an "Error: ..." message and return `None`/
  sentinel values (`k2400.py`, `znb.py`, `yoko750.py`), and three files
  (`anapico.py`, `mcdc2805.py`, `yoko750.py`) each define their *own* local
  `ERR()`/`WARN()`/`INFO()` module-level functions that are not shared
  between files (see driver notes for the format differences between them).
- **Boolean-like get/set methods** follow the `value=None` convention almost
  everywhere (`None` → query current value, `True`/`False` → set) — this is
  the most consistent pattern in the codebase and is used in `k2400.py`,
  `mcdc2805.py`, `yoko750.py`, `anapico.py`, etc. Newer code (`znb.py`,
  `instek3032.py`, `zvk.py`, `fsva.py`) instead favors Python `@property`
  get/set pairs for the same purpose — both styles coexist even inside the
  same file in some cases (`znb.py` has both `set_power()`/`get_power()`
  methods *and* newer `@property` pairs for other settings).
- **Import style** is inconsistent: most files use
  `from instruments import instr`, `yoko7651.py` uses relative
  `from . import instr`, and `k2182a.py`/`k2400.py`/`k6220.py` use bare
  `import instr` — the latter only works if the *parent* directory (not the
  repo root) is on `sys.path`, i.e. these files are not actually usable as
  `instruments.k2400` the way the rest of the package is. This suggests
  `k2400.py`/`k2182a.py` predate the package being wrapped in an
  `instruments` directory and were never fully migrated.
- **`configs/` has no `__init__.py`**, while the root package does (albeit
  empty). This works today because Python 3 supports implicit namespace
  packages, but it is inconsistent with the rest of the codebase's explicit
  style and will silently break if anyone ever adds a build step that
  assumes regular packages (e.g. some bundlers, some strict import linters).
- **Indentation**: most files use 4-space indentation, but `k2400.py`,
  `k6220.py`, and `egg5210.py` use tabs.
- **Python 2 vs. 3**: `k6220.py` is pure Python 2 (`print` statements) and
  cannot be imported under Python 3 — it appears to be unmaintained legacy
  code superseded by `k2400.py`.
- **`importlib.reload(instr)`** appears at import time in several files
  (`anapico.py`, `k2400.py`, `egg5210.py`, `mcdc2805.py`, `yoko7651.py`) —
  a leftover from interactive Jupyter development (to pick up edits to
  `instr.py` without restarting the kernel) that has no effect and no
  purpose when the package is imported normally, but runs on every import
  regardless.
- **Docstrings**: mostly absent. Where present, they cluster in the newer
  code (`znb.py`'s `sweep()`/`sweeps()`, `instek3032.py`'s properties,
  `yoko750.py`'s method docstrings) — an older/newer split rather than a
  deliberate policy.

## How a typical experiment script uses this package

```python
from instruments.znb import Znb
from instruments.configs.znb_config import ZnbLinConfig

vna = Znb("TCPIP0::192.168.1.5::inst0::INSTR")
config = ZnbLinConfig(center_frequency=6e9, span=500e6, bandwidth=1e3,
                       num_points=1001, num_averages=10, power=-30)
vna.set_sweep(config)
freqs, s_data = vna.sweep()
```

Most other drivers are used the same interactive way but without a config
object — properties and methods are called directly in sequence.
