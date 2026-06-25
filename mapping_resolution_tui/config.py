"""
Configuration module: application-wide input constants.

These are session-independent constants for the event loop, distinct from the
caller-supplied :class:`mapping_resolution_tui.state.AppConfig` that carries the
per-dataset labels, prompts, and target policy.
"""

# Control character emitted by ctrl+c. It is the configured key that exits the
# blocking event loop cleanly (the header affordance reads "ctrl+c cancel").
QUIT_KEY = "\x03"
