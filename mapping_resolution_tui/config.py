"""
Configuration module.
"""

# Semantic key token that terminates the event loop. ctrl+c is the interim quit
# key until the exit-confirmation flow (a later epic) owns the cancellation
# contract. Expressed as a normalised TUI token so the loop can compare it
# directly against the input layer's output.
QUIT_KEY = "ctrl+c"
