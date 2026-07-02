"""
Unit tests for the FR36 style-span testability layer (TASK-013).

``render_lines()`` returns a :class:`RenderedFrame`: the printable ANSI lines
(behaving as the ``list[str]`` every caller expects) plus a parallel ``.spans``
structure — one list of ``(start_col, end_col, style)`` tuples per line, in the
line's ANSI-stripped display columns. Tests assert bold / dim / reverse-video
styling by column without parsing raw escape codes, and the zero-width escapes
never affect display-width calculations.
"""

from mapping_resolution_tui.events import KeyEvent
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import (
    RenderedFrame,
    _extract_style_spans,
    render_lines,
    strip_ansi,
)
from tests.fixtures.storyboard import make_config, make_mappings


_BOLD, _DIM, _REV, _RESET = "\x1b[1m", "\x1b[2m", "\x1b[7m", "\x1b[0m"


# ── _extract_style_spans ──────────────────────────────────────────────────────


def test_no_styles_yields_no_spans():
    assert _extract_style_spans("plain text") == []


def test_bold_span_uses_stripped_display_columns():
    line = f"ab{_BOLD}cd{_RESET}ef"  # bold covers the two chars at columns 2..4
    assert _extract_style_spans(line) == [(2, 4, "bold")]


def test_dim_span_is_reported():
    line = f"{_DIM}hi{_RESET} there"
    assert _extract_style_spans(line) == [(0, 2, "dim")]


def test_reverse_span_is_reported():
    line = f"x{_REV}y{_RESET}z"
    assert _extract_style_spans(line) == [(1, 2, "reverse")]


def test_combined_reverse_and_bold_yield_two_spans_on_the_same_cell():
    # The confirmation active choice is reverse-video AND bold on one cell.
    line = f"[{_REV}{_BOLD}N{_RESET}]"
    assert _extract_style_spans(line) == [(1, 2, "bold"), (1, 2, "reverse")]


def test_unterminated_style_runs_to_end_of_line():
    assert _extract_style_spans(f"ab{_BOLD}cd") == [(2, 4, "bold")]


def test_escape_sequences_do_not_count_toward_columns():
    # The style span coordinates ignore the width of the escape sequences: the
    # 'v' sits at display column 1 regardless of the SGR bytes preceding it.
    line = f"a{_BOLD}{_REV}v{_RESET}"
    spans = _extract_style_spans(line)
    assert all(end <= len(strip_ansi(line)) for _s, end, _ in spans)
    assert (1, 2, "bold") in spans and (1, 2, "reverse") in spans


# ── RenderedFrame contract ────────────────────────────────────────────────────


def _browsing_frame():
    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    return render_lines(state)


def test_render_lines_returns_a_rendered_frame():
    frame = _browsing_frame()
    assert isinstance(frame, RenderedFrame)
    assert isinstance(frame, list)


def test_rendered_frame_equals_a_plain_list_of_its_lines():
    frame = _browsing_frame()
    assert frame == list(frame)  # equality ignores the extra .spans attribute


def test_spans_are_parallel_to_lines_and_within_display_width():
    frame = _browsing_frame()
    assert len(frame.spans) == len(frame)
    for line, spans in zip(frame, frame.spans):
        width = len(strip_ansi(line))
        for start, end, style in spans:
            assert 0 <= start < end <= width
            assert style in {"bold", "dim", "reverse"}


def test_confirmation_active_choice_has_reverse_and_bold_spans():
    # ctrl+c from BROWSING opens the exit confirmation with the N active; the
    # prompt line carries reverse+bold spans on the active choice cell.
    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    frame = render_lines(reduce(state, KeyEvent.QUIT))
    prompt_spans = frame.spans[1]
    reverse = [s for s in prompt_spans if s[2] == "reverse"]
    bold = [s for s in prompt_spans if s[2] == "bold"]
    assert len(reverse) == 1 and len(bold) == 1
    # Both cover the same single cell (the reverse-video, bold "N").
    (r_start, r_end, _), (b_start, b_end, _) = reverse[0], bold[0]
    assert (r_start, r_end) == (b_start, b_end)
    assert strip_ansi(frame[1])[r_start:r_end] == "N"


def test_accepted_terminal_frame_carries_empty_spans():
    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    state = reduce(state, KeyEvent.TAB)
    state = reduce(state, KeyEvent.SELECTION_DOWN)
    state = reduce(state, KeyEvent.ENTER)
    for char in "ATT":
        state = reduce(state, char)
    state = reduce(state, KeyEvent.ENTER)
    state = reduce(state, "y")
    state = reduce(state, KeyEvent.ENTER)
    frame = render_lines(state)
    assert frame == ["11 commodities created.", "❯"]
    assert frame.spans == [[], []]
