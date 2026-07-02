"""PyVISA driver for the ANDO AQ6317 / AQ6317B optical spectrum analyzer.

Communicates over GPIB (or any other PyVISA-supported interface the
instrument is configured for) using the analyzer's native ASCII command
set (the same set used in "AQ6317-compatible" mode on later Yokogawa OSAs).
Commands here are cross-checked against Table 2-14 ("AQ6317-compatible
Commands") of the Yokogawa AQ6319 Program/Remote Function Manual
(AS-62642-02Y) and a working GPIB session log for this instrument family.
Legacy AQ6317 commands take their parameter directly appended with no
separator (e.g. ``CTRWL1550.00``), unlike SCPI's `<mnemonic> <value>` form.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pyvisa


@dataclass
class TraceData:
    """A single OSA trace: wavelength (nm) vs. level."""

    wavelength_nm: np.ndarray
    level: np.ndarray
    level_unit: str = "dBm"
    trace: str = "A"

    def __len__(self) -> int:
        return len(self.wavelength_nm)


class AQ6317:
    """PyVISA wrapper around an ANDO AQ6317 / AQ6317B optical spectrum analyzer."""

    TRACES = ("A", "B", "C")

    SENSITIVITY_MODES = {
        "hold": "SNHD",   # normal range, hold
        "auto": "SNAT",   # normal range, auto
        "mid": "SMID",
        "high1": "SHI1",
        "high2": "SHI2",
        "high3": "SHI3",
    }
    _SENSITIVITY_CODES = {1: "high1", 2: "high2", 3: "high3", 4: "hold", 5: "auto"}

    def __init__(
        self,
        resource_name: str,
        resource_manager: Optional[pyvisa.ResourceManager] = None,
        timeout: float = 5000,
        open_timeout: float = 5000,
        read_termination: Optional[str] = "\r\n",
        write_termination: Optional[str] = "\r\n",
    ):
        self.resource_name = resource_name
        self._rm = resource_manager or pyvisa.ResourceManager()
        self.inst = self._rm.open_resource(
            resource_name, timeout=timeout, open_timeout=open_timeout
        )
        if read_termination is not None:
            self.inst.read_termination = read_termination
        if write_termination is not None:
            self.inst.write_termination = write_termination

    def __repr__(self) -> str:
        return f"AQ6317({self.resource_name!r})"

    def __enter__(self) -> "AQ6317":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def close(self) -> None:
        self.inst.close()

    @staticmethod
    def list_resources(resource_manager: Optional[pyvisa.ResourceManager] = None) -> Tuple[str, ...]:
        """Convenience helper to discover connected VISA resources."""
        rm = resource_manager or pyvisa.ResourceManager()
        return rm.list_resources()

    # -- low level -----------------------------------------------------------
    def write(self, command: str) -> None:
        self.inst.write(command)

    def query(self, command: str) -> str:
        return self.inst.query(command).strip()

    def query_float(self, command: str) -> float:
        return float(self.query(command))

    def query_int(self, command: str) -> int:
        return int(float(self.query(command)))

    def identify(self) -> str:
        try:
            return self.query("*IDN?")
        except pyvisa.errors.VisaIOError:
            # some AQ6317 firmware in legacy-compatible mode does not implement *IDN?
            return self.query("ID?")

    # -- sweep control ---------------------------------------------------------
    def single_sweep(self, wait: bool = True, poll_interval: float = 0.2, timeout: float = 1200.0) -> None:
        self.write("SGL")
        if wait:
            self.wait_for_sweep(poll_interval=poll_interval, timeout=timeout)

    def repeat_sweep(self) -> None:
        self.write("RPT")

    def stop_sweep(self) -> None:
        self.write("STP")

    def is_sweeping(self) -> bool:
        return self.query_int("SWEEP?") > 0

    def wait_for_sweep(self, poll_interval: float = 0.2, timeout: float = 1200.0) -> None:
        """Poll SWEEP? until the sweep in progress finishes.

        High-sensitivity modes (e.g. HIGH3) can take on the order of
        10-20 minutes per sweep, hence the generous default timeout.
        """
        start = time.monotonic()
        while self.is_sweeping():
            if time.monotonic() - start > timeout:
                raise TimeoutError("Timed out waiting for the OSA sweep to complete.")
            time.sleep(poll_interval)

    # -- active trace ------------------------------------------------------------
    def get_active_trace(self) -> str:
        return self.TRACES[self.query_int("ACTV?")]

    def set_active_trace(self, trace: str) -> None:
        trace = trace.upper()
        if trace not in self.TRACES:
            raise ValueError(f"trace must be one of {self.TRACES}")
        self.write(f"ACTV{trace}")

    # -- measurement parameters --------------------------------------------------
    def set_center_wavelength(self, nm: float) -> None:
        self.write(f"CTRWL{nm:.2f}")

    def get_center_wavelength(self) -> float:
        return self.query_float("CTRWL?")

    def set_span(self, nm: float) -> None:
        self.write(f"SPAN{nm:.1f}")

    def get_span(self) -> float:
        return self.query_float("SPAN?")

    def set_start_wavelength(self, nm: float) -> None:
        self.write(f"STAWL{nm:.2f}")

    def get_start_wavelength(self) -> float:
        return self.query_float("STAWL?")

    def set_stop_wavelength(self, nm: float) -> None:
        self.write(f"STPWL{nm:.2f}")

    def get_stop_wavelength(self) -> float:
        return self.query_float("STPWL?")

    def set_resolution(self, nm: float) -> None:
        self.write(f"RESLN{nm:.2f}")

    def get_resolution(self) -> float:
        return self.query_float("RESLN?")

    def set_reference_level(self, level: float) -> None:
        self.write(f"REFL{level:.1f}")

    def get_reference_level(self) -> float:
        return self.query_float("REFL?")

    def set_sample_points(self, n: int) -> None:
        self.write(f"SEGP{int(n)}")

    def get_sample_points(self) -> int:
        return self.query_int("SEGP?")

    def set_sensitivity(self, mode: str) -> None:
        mode = mode.lower()
        if mode not in self.SENSITIVITY_MODES:
            raise ValueError(f"mode must be one of {sorted(self.SENSITIVITY_MODES)}")
        self.write(self.SENSITIVITY_MODES[mode])

    def get_sensitivity(self) -> str:
        code = self.query_int("SENS?")
        return self._SENSITIVITY_CODES.get(code, f"unknown({code})")

    # -- trace data ----------------------------------------------------------------
    @staticmethod
    def _parse_trace(raw: str) -> np.ndarray:
        values = raw.strip().split(",")
        return np.array([float(v) for v in values[1:]])  # values[0] is the point count

    def get_wavelength_data(self, trace: Optional[str] = None) -> np.ndarray:
        trace = (trace or self.get_active_trace()).upper()
        return self._parse_trace(self.query(f"WDAT{trace}"))

    def get_level_data(self, trace: Optional[str] = None) -> np.ndarray:
        trace = (trace or self.get_active_trace()).upper()
        return self._parse_trace(self.query(f"LDAT{trace}"))

    def get_level_unit(self) -> str:
        log_scale = bool(self.query_int("LSCL?"))
        density = bool(self.query_int("LSUNT?"))
        unit = "dBm" if log_scale else "W"
        return unit + "/nm" if density else unit

    def get_trace(self, trace: Optional[str] = None) -> TraceData:
        trace = (trace or self.get_active_trace()).upper()
        return TraceData(
            wavelength_nm=self.get_wavelength_data(trace),
            level=self.get_level_data(trace),
            level_unit=self.get_level_unit(),
            trace=trace,
        )

    def sweep_and_fetch(self, trace: Optional[str] = None, **sweep_kwargs) -> TraceData:
        """Trigger a single sweep, block until it completes, and return the trace."""
        self.single_sweep(wait=True, **sweep_kwargs)
        return self.get_trace(trace)

    # -- plotting --------------------------------------------------------------------
    def plot_trace(
        self,
        trace: Optional[str] = None,
        data: Optional[TraceData] = None,
        ax=None,
        title: Optional[str] = None,
        save_path: Optional[str] = None,
        show: bool = True,
        **plot_kwargs,
    ):
        """Fetch (or reuse) a trace and plot level vs. wavelength."""
        import matplotlib.pyplot as plt

        if data is None:
            data = self.get_trace(trace)

        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 5))
        else:
            fig = ax.figure

        ax.plot(data.wavelength_nm, data.level, **plot_kwargs)
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel(f"Level ({data.level_unit})")
        ax.set_title(title or f"AQ6317 - Trace {data.trace}")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150)
        if show:
            plt.show()
        return fig, ax

    def wait_for_sweep_complete(self, poll_interval: float = 0.1, timeout: float = 1200.0) -> None:
        """Wait for any in-progress sweep to finish (SWEEP? transitions to 0).

        In repeat mode the instrument may still be mid-sweep when this is
        called, so we first wait for sweeping to begin (in case we catch a
        brief gap between sweeps) and then wait for it to end.
        """
        start = time.monotonic()
        # If not yet sweeping, wait up to 2 s for the next sweep to start
        # before falling through to the completion wait below.
        deadline = min(start + 2.0, start + timeout)
        while not self.is_sweeping():
            if time.monotonic() > deadline:
                break
            time.sleep(poll_interval)
        # Now wait for the sweep to finish
        while self.is_sweeping():
            if time.monotonic() - start > timeout:
                raise TimeoutError("Timed out waiting for the OSA sweep to complete.")
            time.sleep(poll_interval)

    def live_plot(
        self,
        trace: Optional[str] = None,
        interval: float = 1.0,
        n_frames: Optional[int] = None,
    ):
        """Use the instrument's repeat-sweep mode to drive a live plot.

        Sends ``RPT`` once to start continuous sweeping, then after each
        sweep completes reads the trace and updates the plot.  Sends
        ``STP`` when the window is closed or *n_frames* is reached.
        """
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        (line,) = ax.plot([], [])
        ax.set_xlabel("Wavelength (nm)")
        ax.set_ylabel("Level")
        ax.set_title("AQ6317 - live trace")
        ax.grid(True, alpha=0.3)
        plt.ion()
        fig.show()

        self.repeat_sweep()
        frame = 0
        try:
            while plt.fignum_exists(fig.number) and (n_frames is None or frame < n_frames):
                self.wait_for_sweep_complete()
                data = self.get_trace(trace)

                line.set_data(data.wavelength_nm, data.level)
                ax.relim()
                ax.autoscale_view()
                ax.set_ylabel(f"Level ({data.level_unit})")
                fig.canvas.draw_idle()
                fig.canvas.flush_events()

                frame += 1
                if interval > 0:
                    plt.pause(interval)
        finally:
            self.stop_sweep()
            plt.ioff()

        return fig, ax
