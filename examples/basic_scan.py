"""Connect to an AQ6317, trigger a single sweep, and plot the resulting trace."""

from ando_aq6317 import AQ6317

RESOURCE = "GPIB0::1::INSTR"  # update to match your instrument's GPIB address

with AQ6317(RESOURCE) as osa:
    print(osa.identify())

    osa.set_center_wavelength(1550.0)
    osa.set_span(50.0)
    osa.set_resolution(0.5)
    osa.set_sensitivity("high1")

    trace = osa.sweep_and_fetch()
    print(f"Captured {len(trace)} points on trace {trace.trace}")

    osa.plot_trace(data=trace, save_path="trace.png")
