# Instruments: Grading, Weak/Strong Points, Improvement Strategies

## How I'm grading this

The stated goal for this codebase is: **simple, easy to read, easy to work
with, easy to extend/modify** — not a software-architecture showcase. So I'm
not grading against "should this use dependency injection" or "should there
be a plugin registry." I'm grading against:

1. **Does it work correctly** (can you instantiate every driver, does every
   documented method do what it says)?
2. **Is one file's style predictable from another's** (so reading driver #7
   doesn't require re-learning conventions from scratch)?
3. **Is there dead, broken, or duplicated code that will confuse the next
   person** who opens the file?
4. **Is it as simple as the problem allows** — no accidental complexity, but
   also no cut corners that will bite someone at 2am during a cooldown.

Given that framing, correctness bugs and consistency problems matter far more
here than "missing abstractions" — there's basically no missing abstraction
that would help; if anything, some files already have too much (three copies
of a logging helper, three copies of a binary waveform reader). Findings
below are ordered by importance within each section.

## Overall grade: workable, uneven, needs a cleanup pass

Roughly a third of the drivers (`znb.py`'s core, `instek3032.py`, `fsva.py`,
`zvk.py`, `mcdc2805.py`) are in good shape: small, single-purpose, readable
top to bottom. Another third have grown organically without cleanup
(`znb.py`'s newer property blocks, `yoko750.py`, `yoko7651.py`) — still
usable but showing their age. The rest have actual bugs that would surface
the moment someone tries to use them (`k2400.py`, `k2182a.py`, `fsva.py`'s
unit setter, `instek3032.py`'s output setter, `yoko7651.py`'s free
functions). None of this requires a rewrite — it requires an afternoon of
targeted fixes plus a short style note everyone new can read in five minutes.

---

## Weak points (ordered by importance)

### 1. Two drivers cannot be instantiated at all — `k2400.py`, `k2182a.py`
Both call `super().__init__(visa_name)` with a single argument, but
`instr.Instr.__init__(self, visa_name, visa_library)` has no default for
`visa_library`. Every call to `K2400(...)` or `K2182a(...)` raises
`TypeError` immediately. This is the single highest-priority fix: the
Keithley 2400 is a commonly used SMU, and right now the driver in this repo
is unusable without a one-line patch.
**Fix:** give `visa_library` a default of `''` in `instr.Instr.__init__`
(matches every other driver's constructor signature), or explicitly forward
`visa_library=''` from both subclasses. The former is less code and fixes
the class of bug for any future driver that forgets to pass it through.

### 2. `k6220.py` is Python 2 and cannot be imported under Python 3
`print "..."` statements are a `SyntaxError` in Python 3 — this file cannot
even be parsed, let alone imported, by any Python 3 interpreter. If it's
truly dead (superseded by `k2400.py`, which shares most of its sweep logic),
delete it. If the K6220 + GPIB-bridge hardware path is still in use, it needs
a real port, not just `print()` parenthesization — check the `except:` bare
clauses and `ask`/`ask` naming for other Python-2-isms while at it.
**Fix:** decide status with the user; either delete or port. Keeping
unparseable code in the package invites a confusing `ImportError` for anyone
who does `import instruments.k6220` or a `from instruments import *`.

### 3. Confirmed logic bugs in working (parseable) drivers
These will silently do the wrong thing rather than crash, which is worse:
- **`instek3032.py`**, `output` setter: `if state.lower == "on"` compares the
  bound method object `str.lower` to `"on"`, which is always `False` — the
  "on" branch of the string-based path never executes.
  Fix: `state.lower() == "on"`.
- **`fsva.py`**, `unit` setter: unconditionally calls
  `self.query('UNIT:POW?')` (a query!) instead of writing the new unit, so
  the instrument's power unit can never actually be changed via this driver.
  Fix: `self.write(f'UNIT:POW {unit}')`.
- **`yoko7651.py`**, `program_run_mode()`: `self.wite("M1")` — typo for
  `self.write`, raises `AttributeError` the one time this branch is hit.
- **`yoko7651.py`**, module-level `output_force`, `Output`, `output_on`,
  `output_off`: defined outside the class with `self` as first parameter, so
  they are plain module functions, not methods — `yoko.output_on()` raises
  `AttributeError: 'Yoko7651' object has no attribute 'output_on'`. Either
  these were meant to be indented into the class body, or they're leftover
  drafts. Given `Yoko7651.output(True)` already exists and does the same
  thing, simplest is to delete the four stray functions.
- **`znb.py`**, `ext_trigger_out_interval` is defined twice as a `@property`
  (once ~line 271, once ~line 588, both textually identical). The second
  definition silently wins; harmless *today* because they're identical, but
  a latent trap — if someone edits one copy during a future change, the
  other keeps the old behavior with no error or warning.
  Fix: delete one copy.
- **`egg5210.py`** uses `np.float(...)` in five places (`get_x`, `get_y`,
  `get_phase_degrees`, `get_phase_radians`, `get_frequency`,
  `get_complex`/`get_complex_`). `numpy.float` was removed in NumPy 1.24
  (Jun 2023) — this driver raises `AttributeError: module 'numpy' has no
  attribute 'float'` on any environment with a current NumPy.
  Fix: replace with the builtin `float(...)` everywhere (numpy adds nothing
  here; these are scalar conversions).
- **`anapico.py`** and **`yoko750.py`** both define an identical, broken
  `errors_get_all()`:
  ```python
  def errors_get_all(self):
      errors = [self.errors_get_last()]
      while errors[-1] != '0,"No error"':
          errors += self.errors_get_last()
          return errors
  ```
  Two independent bugs in the same 5 lines: (1) the `return` is *inside* the
  `while` body, so the loop can run at most once no matter how many errors
  are queued on the instrument — it never actually drains a multi-error
  queue; (2) `errors += self.errors_get_last()` adds a *string* to a *list*
  with `+=`, which iterates the string and appends it one character at a
  time, rather than appending the whole error string as one list element.
  Since both files copy-pasted the same code, both share the same bug —
  exactly the risk called out in §6 below about duplicated helpers.
  Fix: `errors = [self.errors_get_last()]` then
  `while errors[-1] != '0,"No error"': errors.append(self.errors_get_last())`
  (no `return` inside the loop).

### 4. Broken/inconsistent imports make several drivers unusable as part of the package
`k2182a.py` and `k2400.py` use `import instr` (bare, absolute) while
`k6220.py` doesn't import it at all (doesn't subclass `Instr`). This only
resolves if the *inner* `instruments/` directory itself is on `sys.path`
(rather than its parent) — which contradicts how the rest of the package
expects to be imported (`from instruments.znb import Znb`,
`from instruments import instr`). In other words, `k2400.py` and
`k2182a.py` are broken twice over: the bare import, and the missing
`visa_library` default (#1 above). `yoko7651.py` uses a relative import
(`from . import instr`) while everything else uses the absolute
`from instruments import instr` — inconsistent, though not currently broken.
**Fix:** standardize every driver on `from instruments import instr` (what
the majority already does), and fix the two broken ones.

### 5. `configs/` has no `__init__.py`
Every driver-config import (`from instruments.configs.znb_config import ...`)
currently works only because Python 3 supports *implicit namespace
packages*. This is inconsistent with the rest of the repo, which has an
explicit (if empty) `instruments/__init__.py`. It's not broken today, but
it's one dependency-manager quirk or packaging change away from silently
breaking, and it's needless inconsistency for a one-line fix.
**Fix:** add an empty `configs/__init__.py`, matching the root package.

### 6. Duplicated, slightly-diverging helper code across files
Three files (`anapico.py`, `mcdc2805.py`, `yoko750.py`) each define their own
module-level `ERR()`/`WARN()`/`INFO()` logging shims, with different
signatures (`*args, **kwarg` + `print(*args, **kwarg)` vs. a single `arg` +
string concatenation). None of them actually raise exceptions or integrate
with Python's `logging` module — they're a home-grown print-based severity
tag. This means: (a) behavior differs subtly between files that both call
something named `ERR()`, and (b) fixing a bug in the shared idea (e.g. making
errors actually raise) means fixing it three times.
Similarly, `yoko750.py` contains three near-identical binary-waveform
readers — `get_binary`, `get_binary_old`, `get_binary_quick` — that differ in
timeout-scaling heuristics and (suspiciously) in `is_big_endian` (`True` in
`get_binary_old`, `False` in the other two, for what the code implies is the
same instrument command). If this difference is intentional (e.g. firmware
version dependent), it needs a one-line comment saying so; if it's a
leftover from debugging, the dead variants should go.
**Fix:** consolidate `ERR`/`WARN`/`INFO` into a single tiny shared module
(e.g. a `log.py` with 3 functions, imported by the files that want them) —
this is exactly the kind of "three similar lines" duplication that's worth
collapsing since it's the *same* helper, copy-pasted, not three genuinely
different pieces of logic. For `yoko750.py`'s three binary readers, pick the
one that's actually used/working and delete the other two (or fold the
timeout heuristic into the one kept version), after confirming with the
person who added `get_binary_old`'s `is_big_endian=True` whether that was a
fix or a regression.

### 7. Stray debug/development leftovers
- `k2182a.py` has a bare `print('i am imported')` at module level — fires on
  every import, including a plain `from instruments import k2182a` done just
  to inspect the class. Delete it.
- `anapico.py`, `k2400.py`, `egg5210.py`, `mcdc2805.py`, `yoko7651.py` all
  call `importlib.reload(instr)` right after `import instr`/
  `from instruments import instr`. This is a Jupyter-notebook convenience
  (pick up live edits to `instr.py` without restarting the kernel) that has
  zero effect during normal use and costs an unnecessary re-import on every
  driver import. It's confusing to a new reader ("why would we reload a
  module we just imported?").
  **Fix:** remove `importlib.reload(instr)` from all five files; if the
  reload-on-edit workflow is genuinely valuable for interactive development,
  put a single `%load_ext autoreload` / `%autoreload 2` note in the lab's
  Jupyter setup instructions instead of baking it into shipped driver code.

### 8. Style inconsistencies that make the codebase feel like 13 different authors (because it is)
This one's inherent to a multi-decade, multi-student lab codebase, and isn't
"wrong," but it actively works against the stated goal of "easy to read
across files":
- **Indentation**: `k2400.py`, `k6220.py`, `egg5210.py` use tabs; everything
  else uses 4 spaces. Mixed tabs/spaces in the same repo is a classic source
  of `TabError` if anyone ever copy-pastes a snippet between files.
- **get/set convention**: some drivers use a single method with
  `value=None` meaning "query" (`k2400.py`, `mcdc2805.py`, `yoko750.py`,
  `anapico.py`'s older methods), others use Python `@property`
  getter/setters for the same purpose (`znb.py`'s newer code,
  `instek3032.py`, `zvk.py`, `fsva.py`). `znb.py` itself has *both* styles
  for conceptually similar settings (`set_power()`/`get_power()` as
  functions, but `source_freq` as a property) — a new contributor has no way
  to guess which style to follow when adding a new setting to `znb.py`.
- **Error signaling**: raising exceptions vs. `print()`-and-return-`None`
  vs. `print()`-and-return-a-sentinel (`RETURN_ERROR = False` /
  `RETURN_NO_ERROR = True`, defined independently at the top of `k2400.py`,
  `egg5210.py`, `yoko750.py`, `k6220.py`, each with a slightly different
  convention for what "success" returns). This means calling code can't
  write one generic "did that work?" check across drivers.
**Fix:** this is not worth a one-shot mass-reformat (high risk of breaking
things quietly, per-file, with no tests to catch it) — see the "Overall
strategy" section below for how to approach it incrementally instead of as a
single risky pass.

### 9. Under-implemented dataclass configs
`Yoko7651.set_source_current_sweep`/`set_source_voltage_sweep` accept
`YokoCurrSweepConfig`/`YokoVoltSweepConfig` (which hold a whole list of
currents/voltages, a `wait` time, and a `sweep_length`) but only apply
`config.current_range`/`config.voltage_range` — they never iterate the list
or use `wait`. This is misleading: the type signature suggests "configure and
run a full sweep," but the actual behavior is "just set a range." A caller
reading `configs/yoko7651_config.py`'s docstring would reasonably expect the
sweep to happen.
**Fix:** either finish the implementation (loop over
`config.currents`/`config.voltages`, sleeping `config.wait` between steps,
optionally yielding/returning readings), or rename the methods/dataclasses
to make clear they only *set up* one endpoint of a sweep (e.g.
`set_current_range_from_config`) so the name matches the behavior.

### 10. Docstrings and comments are sparse and unevenly distributed
Most of the SCPI command semantics — which properties are query-only, valid
ranges, units — live only in the SCPI string constants themselves or in the
author's head. This is fine for someone who already knows the instrument's
programming manual, but makes onboarding a new user of the class much slower
than it needs to be. The docstrings that do exist (`znb.py`'s `sweep()`,
`instek3032.py`'s properties, `configs/*.py`'s dataclasses) are a good
model — they explain units and expected ranges concisely, in 1-3 lines, not
essays.
**Fix:** when touching a method for another reason, add a one-line docstring
noting units and valid range if not obvious from the name — don't do a
dedicated documentation pass across all 13 files, that's low-value effort
relative to the correctness fixes above.

---

## Strong points (ordered by importance)

### 1. The `Instr` base class is exactly the right amount of abstraction
`instr.py` is 128 lines and does one job: wrap PyVISA's raw calls and the
handful of mandatory SCPI commands (`*IDN?`, `*RST`, `*CLS`, `*OPC?`) that
every instrument needs. It doesn't try to model "what is an instrument" in
some abstract sense, doesn't have a registry or factory, doesn't guess at
future instrument types. Every driver subclasses it, overrides what's
instrument-specific, and moves on. This is precisely the "simple, not
over-abstracted" target the project is aiming for, and it's the main reason
the codebase as a whole is approachable despite having 13 different authors'
fingerprints on it.

### 2. Config dataclasses (`configs/*.py`) are a good, narrowly-scoped pattern
For the three instruments that have adopted them (ZNB, AnaPico, Yoko7651),
the `@dataclass` + `__post_init__` validation pattern gives a genuinely nice
API: it validates required fields up front with a clear `ValueError`, cross
-computes derived quantities (start/stop from center/span, sweep length from
a list), and self-documents via short field-level docstrings. This is a
small amount of extra structure that pays for itself immediately — not
speculative abstraction. It's a good template if/when more drivers grow
similar "set up a whole sweep" needs; it would be a mistake to force it onto
every driver that doesn't need it (e.g. `k2182a.py` has 6 simple settings and
doesn't need a config object).

### 3. `znb.py`'s `sweep()`/`sweeps()` methods are a good example of hiding SCPI plumbing behind a clean interface
`sweep()` triggers a sweep, blocks on `*OPC?`, retrieves trace data, and
returns `(frequencies, complex_data)` as plain NumPy arrays — nothing more,
nothing less. A user of this driver never needs to know SCPI exists. This is
the right level for a physics-lab driver: complete enough to be useful
directly from a notebook cell, not so abstracted that debugging a hardware
issue means digging through several layers of indirection.

### 4. `egg5210.py`'s status-byte-based `communicate()` is a genuinely careful protocol implementation
Unlike most other drivers (which write a command and hope), `egg5210.py`
checks the GPIB status byte before sending (to make sure the instrument
isn't already mid-response), and after (to detect "parameter error",
"invalid command", or "not yet complete", raising a clear `RuntimeError` with
the offending command included). This is exactly the kind of defensive code
worth keeping *even in a "keep it simple" codebase* — it isn't over
-engineering, it's handling a real, previously-encountered hardware failure
mode (the file's commented-out earlier attempts above it suggest this was
iterated on). Any future driver for a similarly finicky GPIB instrument
should crib from this file rather than from the simpler print-and-continue
style used elsewhere.

### 5. Instrument-specific safety limits are enforced close to the hardware, not left to the caller
`k2400.py` (`min_current`/`max_current`/`min_voltage`/`max_voltage`,
compliance checks ≤210V/≤1.05A), `anapico.py` (`fmin`/`fmax` frequency range,
ALC level ≤14dBm/≥-20dBm), `yoko7651.py` (voltage/current range tables tied
to the instrument's actual hardware ranges) all validate values against the
real physical/hardware limits before sending a command. In a lab where a
wrong SCPI value can mean burning out a sample or a piece of test equipment,
this matters more than almost any other quality attribute — and it's
present and consistent across the drivers that source power/voltage/current,
which is the right place to prioritize it.

---

## Overall improvement strategy (in priority order)

1. **Fix the 2 unusable drivers first** (`k2400.py`, `k2182a.py` — the
   `visa_library` default; §1 above). This is a five-minute fix
   (`instr.py`: `visa_library=''`) that immediately un-breaks two commonly
   -needed instruments. Do this before anything else.
2. **Decide the fate of `k6220.py`** — ask the user whether the GPIB-bridge
   hardware path is still in use anywhere in the lab. If not, delete the
   file; if so, it needs a real Python 3 port, which is a separate,
   larger task.
3. **Sweep for the confirmed logic bugs in §3** (`instek3032.py`'s `.lower`,
   `fsva.py`'s `unit` setter, `yoko7651.py`'s typo and dead free functions,
   `znb.py`'s duplicate property, `egg5210.py`'s `np.float`). These are all
   independent, low-risk, one-line-to-few-line fixes — a good candidate for
   a single "bugfix sweep" PR, each with a one-line commit message
   explaining what was wrong (useful since there's no test suite to
   otherwise document "why" a line changed).
4. **Standardize imports** (§4) and **add `configs/__init__.py`** (§5) in
   the same pass as #3 above, since they touch the same files.
5. **Consolidate the duplicated `ERR`/`WARN`/`INFO` helpers** (§6) into one
   shared tiny module, and resolve the `yoko750.py` triple-implementation of
   binary trace reading (confirm which one is actually correct first, since
   this touches active data-acquisition code — don't delete without
   verifying against real hardware, per the "measure twice" caution that
   applies to any change without a test suite backing it).
6. **Remove the debug/dev leftovers** (§7 — `importlib.reload`, the stray
   `print`) — trivial, no risk, do it opportunistically whenever a file is
   next touched rather than as its own pass.
7. **Don't attempt a wholesale style unification** (§8) in one shot. With no
   test suite and hardware in the loop, a giant mechanical reformat PR is
   exactly the kind of change that's hard to verify and easy to regret. The
   better path: write a short `CONTRIBUTING`-style note (half a page) stating
   the *preferred* conventions for *new* code (spaces not tabs; `@property`
   get/set over `value=None` methods; raise exceptions rather than
   print-and-sentinel for new drivers) — and let old files converge
   naturally as they're touched for other reasons. Given the explicit design
   goal of staying simple, a heavyweight linting/formatting pipeline would be
   overkill for a 13-file lab-driver package; a one-page convention note
   read once by each contributor is proportionate.
8. **Only after the above**, consider whether `Yoko7651`'s sweep config
   methods (§9) should be completed or renamed — this is a feature-
   completeness gap, not a bug, so it's lowest priority unless someone is
   actively relying on the sweep actually looping.

## What I'd explicitly avoid doing

- **Don't introduce a shared "Instrument registry" or plugin-discovery
  mechanism.** With 13 drivers, each imported explicitly by name in every
  script (`from instruments.znb import Znb`), there is no discovery problem
  to solve. This would add a layer of indirection with no benefit given how
  the package is actually used in notebooks.
- **Don't add a generic settings/config layer that all drivers must
  implement.** The `configs/` dataclass pattern is good for instruments with
  many interdependent settings (VNAs, signal generators). For simple
  6-setting instruments (`k2182a.py`), individual property calls are
  already the simplest possible interface — forcing a config dataclass onto
  every driver "for consistency" would add busywork, not clarity.
- **Don't add a test suite that mocks the VISA layer for its own sake.**
  Since almost every method here is "format a SCPI string and send it," a
  mocked-VISA unit test mostly re-asserts the string literal already visible
  in the method body — low value, real maintenance cost. If tests are added,
  the highest-value target is the *config dataclasses* (`configs/*.py`),
  since their `__post_init__` validation/derivation logic is genuine,
  hardware-independent logic that's easy to get subtly wrong (e.g.
  center/span vs. start/stop math) and easy to test without any hardware.

---

## Style guide for new instruments, properties, and methods

This is deliberately short — the goal is a page a contributor reads once, not
a linter config. It codifies the conventions the *best* existing files
already follow (mainly `znb.py`'s core, `instek3032.py`, `zvk.py`,
`fsva.py`), so following it should feel like imitating the parts of the
codebase that already read well, not learning something new. See
`instruments_refactor.md` for where existing files currently diverge from
it.

### File structure
- One instrument per file; filename is the lowercase model name
  (`znb.py`, `k2400.py`) — already universal, keep it.
- Import order: standard library, then third-party (`numpy`, `pyvisa`), then
  `from instruments import instr` and, if needed,
  `from instruments.configs.<name>_config import ...`. Never a bare
  `import instr` and never a relative `from . import instr` — both should
  resolve to the same absolute form so every driver is importable the same
  way from anywhere in the package.
- No `importlib.reload(...)` in shipped code — it belongs in a notebook's own
  interactive setup, not in the driver module.
- The class name is CapWords matching the instrument (`Znb`, `K2400`,
  `AnaPico`) and subclasses `instr.Instr`.

### Constructor
- Signature is always `def __init__(self, visa_name, visa_library=''):` —
  `visa_library` must have the `''` default, matching `instr.Instr` itself
  (see Refactor doc for the two files that skip this and are currently
  broken because of it).
- First line: `super().__init__(visa_name, visa_library)`.
- Then communication settings grouped together (termination characters, baud
  rate for serial instruments, `chunk_size`, `timeout`).
- Then an `*IDN?` sanity check where practical, reporting both the expected
  and actual prefixes on mismatch.
- Then instrument-specific default state (selecting a default channel,
  measurement, or data format).
- No `print()` debug leftovers (e.g. `print('i am imported')`) and no dead
  commented-out code blocks — delete rather than comment out; git history is
  the place for "what it used to be."

### Properties vs. methods
- Use a `@property` get/set pair for any single scalar setting that maps
  directly to one SCPI query/write pair (power, frequency, bandwidth,
  channel, ...). This is more discoverable (tab-completion, `help()`,
  type hints on the setter) than a function, and is already the direction
  `znb.py`'s newer code, `instek3032.py`, `zvk.py`, and `fsva.py` take.
- Reserve plain methods for verbs — things that *do* something rather than
  hold a value: `sweep()`, `trigger()`, `reset()`, `output_on()` — or for
  settings that inherently take more than one value at once
  (`set_freq_start_stop(fstart, fstop)`).
- Do not use the `value=None` "`None` means query, anything else means set"
  convention in new code. It hides the getter/setter split from tooling and
  from a reader skimming the class body. (`k2400.py`, `yoko750.py`,
  `mcdc2805.py`, and `anapico.py`'s older methods use it; don't add more of
  it, and prefer `@property` when next touching those methods for another
  reason.)
- Never mix both styles for the *same kind* of setting within one file —
  pick one path per file and follow it end to end.

### Error handling
- Raise a builtin exception — `ValueError` for a bad argument, `RuntimeError`
  for a confirmed instrument-reported failure — instead of `print()`-and-
  return-`None`/sentinel. A raised exception can't be silently ignored the
  way a printed line can, and it lets calling code use a normal
  `try`/`except` instead of remembering each driver's private sentinel
  convention.
- Don't invent a new per-file `RETURN_ERROR`/`RETURN_NO_ERROR` pair or a new
  per-file `ERR()`/`WARN()`/`INFO()` logging shim (`anapico.py`,
  `mcdc2805.py`, and `yoko750.py` each already have their own, subtly
  different, copy — see Refactor doc). If a shared error/log helper is
  genuinely useful, it belongs in one place (e.g. `instr.py`) and gets
  imported, not redefined.

### Docstrings
- Give every property/method that isn't obvious from its name a 1-3 line
  docstring: what it does, its unit, and its valid range if the instrument
  enforces one. `configs/*.py` and `instek3032.py` are the models to copy —
  short and concrete, not essays.
- Add a short module-level comment/docstring at the top of the file: what
  instrument this is, what it's for, and a minimal usage snippet (open →
  configure → acquire). The existing author/date header comment
  (`# Author: ..., # 20xx-xx, Collège de France`) is worth keeping *in
  addition to*, not instead of, this.
- A docstring must be a real docstring (the first statement inside the
  `def`, or immediately following the property's `def`) — not a stray
  triple-quoted string left dangling in the class body after the function it
  was meant to document (see `znb.py`'s `hold_function` in the Refactor doc
  for a concrete example of this going wrong).

### Config dataclasses
- Add a `configs/<name>_config.py` once an instrument has roughly 5+
  interdependent settings that are normally configured together for one
  "mode" (a sweep, a specific measurement setup) — the pattern already used
  well for ZNB, AnaPico, and Yoko7651.
- Don't add one for an instrument with a handful of independent settings
  (e.g. `k2182a.py`) — that's abstraction with no payoff.
- Every field a config dataclass declares must be consumed by its
  corresponding `set_*(config)` driver method. An unused field is worse than
  no field: it documents a promise ("this instrument supports a power
  sweep") that the driver silently doesn't keep. (See Refactor doc — this is
  currently true of `powers`/`power_sweep_length` in all three existing
  config files.)

### Formatting
- 4-space indentation, never tabs.
- `snake_case` for methods/properties/variables, `CapWords` for classes —
  already the majority convention; the few tab-indented, non-conforming
  files should converge opportunistically (see Refactor doc — not worth a
  dedicated mass-reformat).
- Prefer f-strings for new SCPI command formatting
  (`f"SOURce{self.current_channel}:POWer {power}"`) over `.format()` — a
  minor readability nit, not worth back-porting on its own.

### Safety limits
- Any property/method that maps to a physical output (power, voltage,
  current, frequency, velocity, ...) must validate the requested value
  against the instrument's real hardware limits *before* writing, raising
  `ValueError` on an out-of-range request rather than sending it to the
  instrument and hoping it errors safely on its own. `k2400.py`'s
  compliance/range checks and `anapico.py`'s frequency/ALC-level checks are
  the model to follow (see Strong Points #5 above).

---

## Properties and methods missing from existing instruments (feature gaps)

Ordered with the three instruments the user relies on most — ZNB, Yoko7651,
AnaPico — first, since gaps there matter more than gaps in rarely-touched
drivers.

### ZNB (`znb.py`)
- **No first-class "repeat a sweep N times, keep every sweep in the
  instrument's memory, then fetch all of them in one transfer" operation.**
  `sweeps()` gets close but conflates hardware averaging count with the
  stored-sweep count, leaves a debug `print()` in, has no docstring, and
  isn't reachable from a config the way `sweep()`/`set_sweep()` are. This is
  the concrete feature requested — see `instruments_refactor.md` for a
  redesign proposal.
- No `is_averaging` accessor distinct from the numeric `averaging` count
  (which represents "off" as `1` — a magic number every caller has to know
  rather than checking a boolean).
- No power-sweep support in the driver even though `ZnbLinConfig` and
  `ZnbCWConfig` both declare `powers`/`power_sweep_length` fields for it —
  the feature is declared but not implemented (systemic; see AnaPico below
  and the Refactor doc).
- `screenshot()` is marked "DOESNT WORK" in its own comment — either fix or
  remove; a method that's known-broken and still present invites someone to
  spend an afternoon debugging their own script before discovering the
  driver itself never worked.
- No calibration-state accessor (`is_calibrated` / correction on/off) even
  though `set_electrical_delay()` implies correction-aware use — worth
  adding if calibration is relied on for real measurements, so a script can
  assert the VNA is calibrated before taking data.

### Yoko7651 (`yoko7651.py`)
- **`set_source_current_sweep`/`set_source_voltage_sweep` don't sweep** —
  the single most important gap for this driver given its name and its
  dedicated config dataclasses (see Improvements §9, and the Refactor doc
  for the concrete fix).
- `voltage`/`current` are `value=None`-convention methods, not `@property`
  pairs — inconsistent with the style guide above and with newer drivers.
- No non-blocking ramp-status accessor: `ramp_current`/`ramp_voltage` accept
  `blocking=False`, implying async use, but the only way to poll completion
  is the undocumented, bitmask-based `program_running()`. A documented
  `is_ramping` property would make the async path actually usable without
  reading the Yokogawa manual's status-byte table first.
- No convenience for the common "ramp to zero, then turn output off" shutdown
  sequence — every script currently hand-rolls this.

### AnaPico (`anapico.py`)
- **`set_freq_sweep()` never consumes `config.powers`/
  `config.power_sweep_length`** — same declared-but-unimplemented power-sweep
  gap as ZNB. Since the exact same two field names appear, unused, in three
  separate config files (`ZnbLinConfig`, `ZnbCWConfig`,
  `AnaFreqSweepConfig`), this is worth fixing (or deliberately removing) once
  for all three rather than three separate times.
- `errors_get_all()` is broken (see Weak Points §3) and has no working
  replacement — there's currently no reliable way to drain and inspect the
  full instrument error queue from this driver.
- No `is_sweeping`/`sweep_done` boolean — only `sweep_progress` (a
  percentage), which is more than a caller needs for a simple "has it
  finished" check before proceeding.
