# Instruments: Refactor Plan

This document assumes the style guide in
[`instruments_improvements.md`](instruments_improvements.md#style-guide-for-new-instruments-properties-and-methods)
as the target, and lists (1) where today's code diverges from it, (2) other
refactor steps worth doing beyond pure style, and (3) documentation gaps —
all ordered by importance. **ZNB, Yoko7651, and AnaPico are treated as the
priority instruments throughout**, since they're the ones actually in daily
use; gaps in the other 10 drivers are listed but pushed to the bottom.

---

## Part 1 — Divergence from the style guide, by rule

For each rule, the priority instruments are called out first; other files
are listed after for completeness but are lower priority to fix.

### Constructor signature (`visa_library=''` default)
- **Priority instruments:** ZNB, Yoko7651, AnaPico all already comply — no
  action needed here for the top 3.
- **Others:** `k2400.py` and `k2182a.py` omit the default entirely, and as a
  result cannot be instantiated (see Improvements doc §1) — this is a
  correctness bug, not just a style gap, and should be fixed regardless of
  priority ordering (it's a 5-minute fix in `instr.py`, see Part 2 below).

### Imports
- **Priority instruments:** ZNB and AnaPico use
  `from instruments import instr` (compliant). **Yoko7651 uses a relative
  `from . import instr`** — the one place a priority instrument diverges
  from the style guide. Low risk, easy fix, but not urgent since it works
  today.
- **Others:** `k2400.py`/`k2182a.py` use bare `import instr` (broken outside
  a nonstandard `sys.path` setup); `k6220.py` doesn't apply (not a VISA
  driver, and not valid Python 3 to begin with).

### Property vs. `value=None`-method convention
- **ZNB**: inconsistent *within the same file* — `set_power()`/
  `get_power()` are old-style methods while `source_freq`, `sweep_count`,
  `average_count` are properties added later. Since ZNB is the most
  actively-developed driver, this is the highest-value single file to
  reconcile: pick properties (matching the newer additions and the style
  guide) and fold the older `set_X`/`get_X` method pairs into properties as
  they're next touched. Do **not** do this as one giant mechanical pass —
  `znb.py` is 824 lines and used for real acquisitions; convert setting by
  setting, verifying against real hardware each time.
- **Yoko7651**: `voltage`/`current` are still `value=None`-style methods.
  Given how central these two are to how the instrument is actually used
  (every script calls one or the other repeatedly), converting them to
  `@property` pairs would be the single most visible ZNB/Yoko-adjacent style
  fix a user would notice day to day. Worth doing deliberately (its own
  small commit, tested against hardware) rather than folding into a larger
  change.
- **AnaPico**: already mostly property-based; a few sweep-control methods
  (`freq()`, `alc_level()`, `attenuator()`, `att_hold()`, `modulation()`,
  `output()`) still use the `value=None` convention. Lower priority than
  ZNB/Yoko7651's gaps since these are set-once-per-experiment settings, not
  per-point hot paths.
- **Others:** `k2400.py`, `mcdc2805.py`, `yoko750.py` are consistently
  `value=None`-style throughout each file (internally consistent, just not
  matching the style guide) — lowest priority, convert opportunistically.

### Error handling (exceptions vs. print-and-sentinel)
- **ZNB**: mixed — some methods `raise ValueError` (`sweep_type` setter,
  `average_count` setter), most others `print("ERROR: ...")` and return
  `None`/`-1`/silently do nothing (`set_data_format`, `get_nb_points`,
  `set_if_bw`, `create_channel_and_trace`, ...). Recommend: any *new* ZNB
  method raises; existing `print`-based methods converge opportunistically,
  starting with the ones most likely to fail silently in ways that waste
  beamtime — `create_channel_and_trace`'s multiple `print`-and-`return None`
  branches are the best first candidate, since a script that doesn't check
  the return value will silently continue with no channel configured.
- **Yoko7651**: uses `print("ERROR: ...")` + `return RETURN_ERROR` (a
  module-level `False`) throughout. Given how safety-critical this
  instrument's output is (it sources current/voltage into a real sample),
  converting `range_current`/`range_voltage`/`voltage`/`current`'s error
  paths to raise `ValueError` is worth prioritizing over cosmetic changes
  elsewhere — a silently-ignored `print("ERROR: ...")` before a
  `set_current()` call is exactly the kind of thing that could mean a script
  proceeds to source current in the wrong range unattended.
- **AnaPico**: uses module-level `ERR()`/`WARN()`/`INFO()` print shims
  throughout instead of exceptions — see Part 2's helper-consolidation item.
- **Others:** `k2400.py`, `yoko750.py`, `k6220.py`, `egg5210.py` each have
  their own `RETURN_ERROR`/`RETURN_NO_ERROR` convention; lowest priority.

### Docstrings
- **ZNB**: only `sweep()`/`sweeps()` have real docstrings; the rest of the
  824-line file has none. Given this is the most complex and most-used
  driver, it's the highest-value docstring target in the whole codebase —
  see Part 3 below for specifics.
- **Yoko7651**: docstrings exist for the newer additions (`interval()`,
  `sweep_duration()`, `write_program()`) but not for the core `voltage()`/
  `current()`/`range_current()`/`range_voltage()` — the methods used in
  nearly every script. See Part 3.
- **AnaPico**: docstrings exist for the OPC/reset SCPI-mandatory commands
  but not for the sweep/trigger properties actually used to configure an
  experiment. See Part 3.
- **Others:** sparse to absent across the board; lowest priority per
  Improvements doc §10.

### Config dataclasses — unused fields
This affects all three priority instruments identically and is worth fixing
once, consistently, rather than three separate times:
- `ZnbLinConfig` and `ZnbCWConfig` (`configs/znb_config.py`) both declare
  `powers: np.ndarray[np.float64]` and `power_sweep_length: int`, computed in
  `__post_init__`, but neither `Znb.set_lin_sweep()` nor
  `Znb.set_cw_sweep()` reference `config.powers` at all.
- `AnaFreqSweepConfig` (`configs/anapico_config.py`) declares the same two
  fields with the same `__post_init__` logic, and `AnaPico.set_freq_sweep()`
  likewise never reads `config.powers`.
- **Fix, once, applied consistently to all three:** either (a) implement the
  power sweep in each driver's `set_*` method (iterate `config.powers`,
  presumably one sweep/acquisition per power, similar to how `sweeps()`
  already loops over stored VNA sweeps), or (b) if power sweeps aren't
  actually needed right now, delete the `powers`/`power_sweep_length` fields
  and their `_validate_power_sweep()` methods from all three config files.
  Leaving them in place, unused, is the worst of the three options — see
  style guide rationale in Improvements doc.

### Formatting (tabs, `.format()` vs f-strings)
- **None of the three priority instruments use tabs** — ZNB, Yoko7651, and
  AnaPico are all space-indented already, so this rule requires no action
  for the priority set.
- `znb.py` mixes `.format()` (older methods) and f-strings (newer methods) —
  purely cosmetic, not worth a dedicated pass; let it converge as methods are
  touched for other reasons.
- **Others:** `k2400.py`, `k6220.py`, `egg5210.py` use tabs — lowest
  priority, see Improvements doc §8.

### Safety limits
- **ZNB**: N/A in the same sense as source instruments — a VNA's power
  setting has a `set_power()` but no client-side range check before writing
  it (relies entirely on the instrument rejecting an out-of-range value).
  Given ZNB power can matter for sample protection in the same way a source
  meter's compliance does, adding a `min_power`/`max_power` check (mirroring
  `k2400.py`'s pattern) is a reasonable low-risk addition — low urgency only
  because the instrument itself already enforces its own limits and rejects
  bad values.
- **Yoko7651**: already has good range-table-based validation
  (`range_current`/`range_voltage`) — compliant, no action needed.
- **AnaPico**: already has `fmin`/`fmax` and ALC-level checks — compliant.

---

## Part 2 — Other refactor steps (beyond style), ordered by importance

### 1. ZNB: redesign "repeat-sweep-and-fetch-all-data" into a clean, documented feature
This is the concrete feature requested: measure the same sweep configuration
N times, let the instrument hold all N results in memory, then pull all N
sets of S-parameter data back in a single transfer (much faster than N
separate `sweep()` round-trips, since each round-trip pays the VISA/SCPI
latency cost independently).

**Current state.** `sweeps()` (znb.py) already implements roughly this, via
the R&S ZNB's native "multiple sweep" memory feature:
```python
def sweeps(self):
    self.sweep_hold()
    self.sweep_single()                 # INITiate:IMMediate — runs `sweep_count` sweeps, held afterward
    while not self.query('*OPC?'):
        pass
    acquired_sweeps = int(self.query('CALC:DATA:NSW:COUN?'))
    print(acquired_sweeps)              # debug leftover
    ...
    values_interlaced = np.array(self.visa_instr.query_binary_values(
        f":CALC{self.current_channel}:DATA:NSWeep:FIRSt? SDAT,1,{acquired_sweeps}", datatype='d'))
    z = values_interlaced[0::2] + 1j*values_interlaced[1::2]
    S = np.array_split(z, acquired_sweeps)
    return f, S
```
This is the right underlying SCPI mechanism (`SENSe:SWEep:COUNt` +
`INITiate:IMMediate` in hold mode + `CALC:DATA:NSWeep:FIRSt?`), but it has
several problems that make it unfit to build on directly:

1. **Averaging count and stored-sweep count are conflated through write
   order, not through design.** `set_average(nb_averages, mode)` writes
   `SENSe:AVERage:COUNt` **and** `SENSe:SWEep:COUNt` to the *same* value
   (`nb_averages`). `set_lin_sweep()` then calls `set_average(config.num_averages, ...)`
   followed by `self.sweep_count = config.num_sweeps`, so the final
   `SWEep:COUNt` ends up correct (`num_sweeps` wins because it's written
   last) — but only by accident of ordering. Anyone who reorders these two
   lines, or calls `set_average()` again after configuring `sweep_count`
   directly, silently breaks the multi-sweep-count. `set_average()` should
   only ever touch `AVERage:COUNt`; `SWEep:COUNt` should be owned
   exclusively by the `sweep_count` property.
2. **No relationship between averaging state and the "store raw sweeps"
   use case is documented or enforced.** If hardware averaging
   (`AVERage:STATe ON`) is left on while collecting `num_sweeps` repeats for
   later Python-side analysis, it's unclear (and untested in this codebase)
   whether `CALC:DATA:NSWeep:FIRSt?` returns the *raw* per-sweep trace or an
   *already-averaged* trace — these are different things and the caller
   needs to know which they're getting. This needs to be verified once
   against real hardware and then written down as a one-line rule (e.g.
   "turn `averaging` off before calling `repeated_sweep()` if you want
   independent raw sweeps; leave it on if you want the instrument's own
   moving average per stored point").
3. **No validation that the requested count was actually acquired.**
   `acquired_sweeps` is read back from the instrument and used as-is; if a
   sweep was interrupted (aborted, error, timeout) the caller silently gets
   fewer sweeps than they asked for, with no warning.
4. **Leftover debug `print(acquired_sweeps)`**, no docstring, and the
   method isn't reachable from `set_sweep(config)`/the config-driven flow
   that `sweep()` is — a caller has to know to call the differently-named
   `sweeps()` (plural) instead of `sweep()` and know it behaves differently
   under the hood.
5. **Return shape is a list of 1-D arrays (`np.array_split`)**, whereas most
   other array-returning methods in this codebase return a single ndarray —
   inconsistent, and `np.array_split` will silently produce unequal splits
   if `len(z)` isn't evenly divisible by `acquired_sweeps` (shouldn't happen
   in practice, but there's no assertion guarding it).

**Proposed redesign:**
```python
def set_average(self, nb_averages, mode='MOVing'):
    """Set the hardware (moving/reducing) average count. Does not affect
    how many sweeps are stored for repeated_sweep()."""
    if nb_averages >= 1:
        self.set_average_mode(mode)
        self.write(f"SENSe{self.current_channel}:AVERage:COUNt {nb_averages}")
        self.write(f"SENSe{self.current_channel}:AVERage:STATe ON")
    elif nb_averages == 1:
        self.average_off()
    else:
        raise ValueError("nb_averages must be >=1 (1 turns averaging off).")
    # NOTE: no longer touches SWEep:COUNt -- that's owned by `sweep_count`.

def repeated_sweep(self, num_sweeps: int = None) -> Tuple[np.ndarray, np.ndarray]:
    """
    Trigger `num_sweeps` sweeps (defaults to the currently configured
    `sweep_count`), holding all of them in the VNA's sweep-history memory,
    then fetch all of them in a single binary transfer.

    Returns:
        frequencies: 1-D array, shared by every sweep.
        data: 2-D complex array of shape (num_sweeps, num_points) -- one
        row per sweep, in acquisition order.

    Note: whether each row is a raw sweep or an instrument-averaged sweep
    depends on `averaging` state -- turn averaging off first if you want
    independent raw repeats.
    """
    if num_sweeps is not None:
        self.sweep_count = num_sweeps
    requested = self.sweep_count

    self.sweep_hold()
    self.sweep_single()
    while not self.query('*OPC?'):
        sleep(0.01)          # avoid hammering the VISA bus, see Part 2 #4 below

    acquired = int(self.query('CALC:DATA:NSW:COUN?'))
    if acquired != requested:
        raise RuntimeError(
            f"Requested {requested} sweeps but only {acquired} were acquired "
            "(sweep may have been interrupted).")

    self.write("FORMAT REAL,64")
    self.write(f"CALC{self.current_channel}:PAR:SEL '{self.current_measurement_name}'")
    f = np.array(self.visa_instr.query_binary_values(
        f":CALC{self.current_channel}:DATA:STIM?", datatype='d'))
    raw = np.array(self.visa_instr.query_binary_values(
        f":CALC{self.current_channel}:DATA:NSWeep:FIRSt? SDAT,1,{acquired}", datatype='d'))
    z = raw[0::2] + 1j * raw[1::2]
    data = z.reshape(acquired, -1)   # one row per sweep; raises if not evenly divisible

    return f, data
```
Key changes from today's `sweeps()`: `set_average()` no longer touches
`SWEep:COUNt` (removes the write-order footgun); the acquired count is
validated against the request; the busy-wait sleeps; the debug print is
gone; the docstring states the averaging-vs-raw caveat explicitly instead of
leaving it to be discovered by trial and error; and the return shape is one
2-D ndarray instead of a list of 1-D arrays, matching the rest of the
codebase's array conventions. Renaming `sweeps()` → `repeated_sweep()` (or
similar) also makes it discoverable as "the multi-sweep version of
`sweep()`" rather than a same-word plural that's easy to typo past.

This should be implemented as its own small PR, tested against the real ZNB
before merging (per the "measure twice" caution — there's no test suite to
catch a subtly wrong SCPI sequence), and the averaging-vs-raw behavior
should be confirmed against actual hardware output, not assumed from the
manual.

### 2. Yoko7651: make the sweep config dataclasses actually sweep
`set_source_current_sweep(config: YokoCurrSweepConfig)` and
`set_source_voltage_sweep(config: YokoVoltSweepConfig)` currently only call
`source_current()`/`range_current(config.current_range)` (or the voltage
equivalents) — they never iterate `config.currents`/`config.voltages`, and
never use `config.wait`. Given this is one of the three priority
instruments and its own config dataclass's docstring explicitly says
"A list of currents ... to be sourced," this mismatch between documented and
actual behavior is a trap for the next person who reads the dataclass and
trusts its docstring. Two options, in order of preference:
1. **Implement the sweep**: have the `set_*_sweep` methods (or a new
   `run_current_sweep(config)`/`run_voltage_sweep(config)` pair, if "set"
   should stay reserved for configuration-only) loop over
   `config.currents`/`config.voltages`, call `current(v)`/`voltage(v)` for
   each, `sleep(config.wait)` between steps, and optionally collect/return
   any readings taken during the sweep (or accept a callback for what to do
   at each step, if the use case is "set current, then trigger a
   measurement on another instrument").
2. **Rename to match current behavior**: if range-setup-only is genuinely
   all that's needed today, rename to `configure_current_range(config)` and
   strip `currents`/`wait` out of the dataclass (or leave them for a future
   sweep implementation but note in the docstring that they're not yet
   consumed).
Given the dataclass is actively described as a "sweep config," (1) is
probably what was originally intended and simply never finished — worth
checking with whoever added it before picking between the two options.

### 3. AnaPico / ZNB: resolve the power-sweep fields once, for all three configs
As covered in Part 1, `ZnbLinConfig`, `ZnbCWConfig`, and `AnaFreqSweepConfig`
all declare unused `powers`/`power_sweep_length` fields. Since it's the same
gap in three places, fix it in one pass: decide whether power sweeps are a
real near-term need, and either implement the loop in all three `set_*`
methods (most naturally as "for each power in config.powers: set power,
[re-run averaging / sweep], collect data" — likely wanting to reuse the
`repeated_sweep()` design from item #1 above for ZNB specifically) or remove
the fields from all three dataclasses simultaneously so the documented
capability matches the real one everywhere at once.

### 4. ZNB: fix the busy-wait polling loops
`sweep()` and `sweeps()` both do:
```python
while not self.query('*OPC?'):
    pass
```
with no `sleep()` — every other polling loop in the codebase
(`instr.wait_for_stb()`, `k2400.wait_for_sweep()`, `Yoko7651.write_program`
usage patterns) includes a small `sleep()` between polls. A tight loop with
no sleep sends `*OPC?` as fast as the VISA transport allows, which is
unnecessary load on the GPIB/LAN link and the instrument's command parser
for no benefit (a sweep takes at minimum tens of milliseconds; polling every
microsecond buys nothing). Add `sleep(0.01)` (matching `instr.py`'s existing
`wait_for_stb()` interval) to both loops.

### 5. ZNB: fix the misplaced `hold_function` "docstring"
```python
@hold_function.setter
def hold_function(self, hold_state):
    ...
    self.write(f"CALC:PHOL OFF; PHOL {hold_state}")
"""
CALCulate<Chn>:PHOLd <HoldFunc>
...
"""
```
The triple-quoted block documenting `CALCulate:PHOLd` sits *after* the
setter's `def` block ends, at class-body indentation — it's a dangling
string statement, not attached to any function, so it never shows up via
`help(Znb.hold_function)` or an IDE tooltip. Move its content into an actual
docstring on the `hold_function` property getter (or the setter), trimmed to
the 1-3 line convention from the style guide rather than the full manual
excerpt.

### 6. Consolidate the duplicated `ERR`/`WARN`/`INFO` helpers (affects AnaPico directly)
`anapico.py` (a priority instrument), `mcdc2805.py`, and `yoko750.py` each
define their own slightly different copy. Since AnaPico is a priority
instrument, this is worth doing sooner rather than later — every `ERR()`
call in `anapico.py` is a `print()`, not an exception, which contradicts the
style guide's "raise, don't print" rule; consolidating to a single shared
helper is also the natural moment to convert `ERR()` calls into actual
raised exceptions for the highest-traffic driver rather than doing it file
by file later. See Improvements doc §6 for the cross-file duplication
detail.

### 7. Everything else in Improvements doc's "Overall improvement strategy"
The remaining refactor items (`k2400.py`/`k2182a.py` constructor fix,
`k6220.py`'s fate, the confirmed one-line bugs in `instek3032.py`/
`fsva.py`/`egg5210.py`, `configs/__init__.py`, import standardization) are
already covered there in priority order and apply equally regardless of
this document's ZNB/Yoko7651/AnaPico focus — they're not repeated here to
avoid the two documents drifting out of sync. Do the `instr.py`
`visa_library=''` fix (Improvements §1) first regardless of anything in this
document, since it's the highest-severity item in the whole codebase and
touches the base class every driver depends on.

---

## Part 3 — Documentation review: ZNB, Yoko7651, AnaPico

### ZNB (`znb.py`)
- **No module-level usage example.** A new user has to read 824 lines (or
  this repo's `instruments_overview.md`) to learn the basic flow: open
  connection → `set_sweep(config)` → `sweep()`. A 4-line example at the top
  of the file (matching the "Constructor" style-guide item) would save that
  read every time.
- **Almost no per-method docstrings.** Only `sweep()`/`sweeps()` have them.
  High-value targets to add first (most-used, least self-explanatory):
  `set_sweep()` (needs to explain it dispatches on config type),
  `create_channel_and_trace()` (needs to explain its side effects — it also
  sets power to -60 dBm and turns power off as a safety default, which
  isn't obvious from the name), `get_trace_sdata()`/`get_trace_fdata()`
  (still marked "BETA"/"temporary fix" in comments — either confirm they're
  solid and remove the hedge, or document the known limitation explicitly
  so a user knows to double check results).
- **The `hold_function` docstring is present but structurally broken** —
  see Part 2 item #5. Fix the structure, then trim the content to match the
  style guide's length convention.
- **No documentation of the averaging/sweep-count interaction** described in
  Part 2 item #1 — this is the single most important documentation gap
  relative to the feature being requested, since getting this wrong silently
  changes what data `repeated_sweep()`/`sweeps()` returns.
- **No documentation of preconditions.** Many methods
  (`set_current_channel_and_trace`, `sweep()`, `get_trace_sdata()`) implicitly
  require a channel and trace to already exist, created via
  `create_channel_and_trace()` — this dependency is discoverable by reading
  the code but not stated anywhere.

### Yoko7651 (`yoko7651.py`)
- **No module-level usage example** — same gap as ZNB.
- **Core methods lack docstrings**: `voltage()`, `current()`,
  `range_current()`, `range_voltage()` — used in essentially every script
  that touches this instrument — have no docstring at all, only inline
  `print("ERROR: ...")` messages that only appear at the *wrong* call. A
  docstring stating "query with no argument; set with a float within the
  current range; raises/prints if sourcing mode doesn't match" would save
  a lot of trial-and-error for a new user.
- **The sweep config dataclasses' docstrings currently promise behavior the
  driver doesn't deliver** (see Part 2 item #2) — this is a documentation
  *correctness* problem, not just a gap: `YokoCurrSweepConfig`'s docstring
  says "A list of currents ... to be sourced by the Yoko," which is false as
  currently wired. Fix the implementation or fix the docstring — don't leave
  them contradicting each other.
- **`program_running()` has no docstring** despite decoding an
  undocumented-in-code status bitmask (`int(status[5:]) & 0b00000010`) — a
  one-line comment on what bit 1 of the `OC` response means (and a citation
  to the manual page, matching this file's existing citation style in other
  methods) would make the async-ramp path usable without cross-referencing
  the Yokogawa manual from scratch.
- **`self.ranges` table** (the `F1R2`/`F5R4`-style codes) has no comment
  explaining the code scheme beyond the file header's manual-edition
  citation — a one-line note ("F<function><range> per manual p.X") next to
  the table itself, not just in the header, would help since that's where a
  reader's eye actually lands when trying to add a new range.

### AnaPico (`anapico.py`)
- **No module-level usage example**, and specifically no example showing
  `set_freq_sweep()` + `set_ext_trig()` used together, even though that's
  the normal way this instrument is configured for an experiment (frequency
  sweep driven by an external trigger from the rest of the setup).
- **The `dummy`/`dummy_frequency` mechanism is documented in the wrong
  place.** `AnaFreqSweepConfig` (in `configs/anapico_config.py`) has a
  trailing comment explaining it's "extra start frequency that will get
  skipped due to double triggering at beginning, to actually start at start
  frequency" — but the *driver* method that actually consumes it
  (`AnaPico.set_freq_sweep()`) has no comment at all referencing this
  workaround. A reader of `anapico.py` alone (the more likely entry point
  when debugging a sweep that starts one point off) has no way to discover
  why `config.dummy` branches the way it does without also finding and
  reading the config file's dataclass comment. Move (or duplicate, briefly)
  the explanation into `set_freq_sweep()` itself.
- **Sweep/trigger properties have type hints but no docstrings** — e.g.
  `freq_mode`, `power_mode`, `trigger_source`, `trigger_type`,
  `trigger_slope` all validate against an explicit list of legal SCPI values
  in the setter body, but that list isn't visible via `help()` or a
  docstring — only by reading the setter's source. A one-line docstring
  quoting the legal values (`"""FIX(ed), CW, SWEep, LIST, CHIRp"""`-style)
  would surface this without needing to open the file.
- **`metadata` property is a good, well-scoped piece of self-documenting
  code** (it already has a docstring) but doesn't mention that it
  temporarily switches `current_channel` back and forth to read both
  channels' state, which briefly changes the instrument's selected channel
  as a side effect — worth a one-line note for anyone calling `metadata`
  mid-experiment while relying on the previously-selected channel remaining
  selected elsewhere in a script.
