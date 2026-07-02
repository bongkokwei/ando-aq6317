# ando-aq6317

Python driver for the **ANDO AQ6317 / AQ6317B** optical spectrum analyzer, built on [PyVISA](https://pyvisa.readthedocs.io/).

## Install

```bash
pip install -r requirements.txt
```

You also need a VISA backend: either [NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html), or the pure-Python `pyvisa-py` backend (already listed in `requirements.txt`, including its `psutil` and `hislip-discovery` extras so TCPIP resource discovery can scan all network interfaces without warnings) for GPIB-USB/USB-TMC/serial access.

## Connecting

```python
from ando_aq6317 import AQ6317

# discover connected VISA resources
print(AQ6317.list_resources())

osa = AQ6317("GPIB0::1::INSTR")   # GPIB address set on the instrument's front panel
print(osa.identify())
osa.close()

# or, as a context manager:
with AQ6317("GPIB0::1::INSTR") as osa:
    ...
```

## Basic usage

```python
osa.set_center_wavelength(1550.0)   # nm
osa.set_span(50.0)                  # nm
osa.set_resolution(0.5)             # nm
osa.set_sensitivity("high1")        # hold | auto | high1 | high2 | high3

trace = osa.sweep_and_fetch()       # triggers a single sweep, waits, returns a TraceData
print(trace.wavelength_nm, trace.level, trace.level_unit)
```

`TraceData` is a small dataclass with `wavelength_nm`, `level`, `level_unit`, and `trace` (`"A"`, `"B"`, or `"C"`).

## Plotting

```python
osa.plot_trace()                              # sweep isn't triggered; fetches current trace and plots it
osa.plot_trace(data=trace, save_path="out.png", show=False)

# continuously re-sweep and update a live plot until the window is closed
osa.live_plot(interval=1.0)
```

See `examples/basic_scan.py` and `examples/live_plot.py` for runnable scripts.

## Command set note

The AQ6317 family speaks a short ASCII mnemonic command set (`CTRWL`, `SPAN`, `SGL`, `WDATA`/`LDATA`, ...) rather than full SCPI — the same set exposed by later Yokogawa OSAs in their "AQ6317-compatible" mode. Every command and its syntax in this driver is cross-checked against Table 2-14, "AQ6317-compatible Commands," in the Yokogawa AQ6319 Program/Remote Function Manual (AS-62642-02Y), plus a working GPIB session log for this instrument family. Note that legacy AQ6317 commands take their parameter directly appended with no separator (e.g. `CTRWL1550.00`), unlike the `<mnemonic> <value>` form used by SCPI.

## API overview

- Sweep control: `single_sweep`, `repeat_sweep`, `stop_sweep`, `is_sweeping`, `wait_for_sweep`
- Trace selection: `get_active_trace`, `set_active_trace`
- Parameters: `{get,set}_center_wavelength`, `{get,set}_span`, `{get,set}_start_wavelength`, `{get,set}_stop_wavelength`, `{get,set}_resolution`, `{get,set}_reference_level`, `{get,set}_sample_points`, `{get,set}_sensitivity`
- Data: `get_wavelength_data`, `get_level_data`, `get_level_unit`, `get_trace`, `sweep_and_fetch`
- Plotting: `plot_trace`, `live_plot`
- Low level: `write`, `query`, `query_float`, `query_int`, `identify`
