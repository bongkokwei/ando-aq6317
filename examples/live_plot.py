"""Continuously sweep the AQ6317 and update a live plot of the trace."""

from ando_aq6317 import AQ6317

RESOURCE = "GPIB1::1::INSTR"  # update to match your instrument's GPIB address

with AQ6317(RESOURCE) as osa:
    osa.live_plot(interval=1.0)
