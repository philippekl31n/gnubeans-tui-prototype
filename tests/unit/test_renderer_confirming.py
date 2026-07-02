"""
TASK-009 — unit tests for the CONFIRMING render case (spec §6.4–6.6, §8.4).

render_lines() must overlay the confirmation prompt below the full table at the
current scroll offset, style the confirmation header, render the active y/n
choice reverse-video and bold, and suppress the row cursor and any dim rows.
"""
from dataclasses import replace

from tests.fixtures.storyboard import make_config, make_mappings
from mapping_resolution_tui.reducer import make_initial_state, reduce
from mapping_resolution_tui.renderer import render_lines, strip_ansi
from mapping_resolution_tui.state import (
    ConfirmationChoice,
    ConfirmationKind,
    ConfirmationState,
    Mode,
)

_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_REV = "\x1b[7m"
_RESET = "\x1b[0m"


def _confirming(state, kind, choice):
    return replace(
        state,
        mode=Mode.CONFIRMING,
        confirmation=ConfirmationState(
            kind=kind,
            choice=choice,
            second_ctrl_c_armed=kind is ConfirmationKind.EXIT,
        ),
    )


def _resolved_state():
    """Storyboard state with the AT-T collision resolved (ordinal 3 -> 'ATT')."""
    state = make_initial_state(make_config(), make_mappings(), frame_height=15)
    mappings = [
        replace(m, target_value="ATT") if m.ordinal == 3 else m
        for m in state.mappings
    ]
    return replace(state, mappings=mappings)


def _accept_no_lines():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    return render_lines(state)


# ── header (spec §6.4) ────────────────────────────────────────────────────────

def test_confirming_header_text_and_styling():
    header = _accept_no_lines()[0]
    assert strip_ansi(header) == "❯ Reviewing 11 commodity mappings. ctrl+c cancel"
    assert header.startswith(f"{_BOLD}❯{_RESET}")
    assert header.endswith(f"{_DIM}ctrl+c cancel{_RESET}")


def test_exit_confirming_header_keeps_count_and_dim_exit_shortcut():
    state = _confirming(
        make_initial_state(make_config(), make_mappings(), frame_height=15),
        ConfirmationKind.EXIT,
        ConfirmationChoice.NO,
    )
    header = render_lines(state)[0]
    assert strip_ansi(header) == (
        "❯ Reviewing 11 commodity mappings. 1 unresolved collision. ctrl+c exit"
    )
    assert header.endswith(f"{_DIM}ctrl+c exit{_RESET}")


# ── prompt (spec §6.5) ────────────────────────────────────────────────────────

def test_accept_prompt_no_active_reverses_the_n():
    prompt = _accept_no_lines()[1]
    assert strip_ansi(prompt) == "  Accept all? [y/N]"
    assert f"[y/{_REV}{_BOLD}N{_RESET}]" in prompt


def test_accept_prompt_yes_active_reverses_the_y():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.YES)
    prompt = render_lines(state)[1]
    assert strip_ansi(prompt) == "  Accept all? [Y/n]"
    assert f"[{_REV}{_BOLD}Y{_RESET}/n]" in prompt


def test_exit_prompt_uses_exit_text():
    state = _confirming(
        make_initial_state(make_config(), make_mappings(), frame_height=15),
        ConfirmationKind.EXIT,
        ConfirmationChoice.NO,
    )
    assert strip_ansi(render_lines(state)[1]) == "  Skip adding commodities? [y/N]"


# ── table body (spec §8.2, §8.4) ──────────────────────────────────────────────

def test_confirming_body_renders_no_row_cursor():
    lines = _accept_no_lines()
    body = [strip_ansi(line) for line in lines[4:-2]]
    assert body  # table body present
    assert all("▸" not in row for row in body)


def test_confirming_body_renders_no_dim_rows():
    lines = _accept_no_lines()
    assert all(_DIM not in line for line in lines[4:-2])


def test_confirming_renders_full_table_despite_active_filter():
    state = _resolved_state()
    state = reduce(state, "1")
    state = reduce(state, "2")  # filter "12" matches no rows (frame 13)
    state = _confirming(state, ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    lines = render_lines(state)
    body = [strip_ansi(line) for line in lines[4:-2]]
    assert len(body) == 9  # capacity at frame_height 15
    assert body[0].lstrip().startswith("1 ")


def test_confirming_body_scrolls_with_scroll_offset():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    state = replace(state, selection=replace(state.selection, scroll_offset=1))
    first_row = strip_ansi(render_lines(state)[4])
    assert first_row.lstrip().startswith("2 ")


# ── footer and redraw stability (spec §4.1 / §10.2) ───────────────────────────

def test_confirming_footer_follows_the_kind_and_choice():
    # The ENTER hint is keyed on (kind, choice), never the entry path (spec
    # §6.6 / §10.2): choice=NO reads "edit mappings" for both kinds, accept+YES
    # reads "submit mappings", exit+YES reads "skip". No "confirm" verb exists.
    no_footer = strip_ansi(_accept_no_lines()[-1])
    assert no_footer == "  ↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ edit mappings"

    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.YES)
    yes_footer = strip_ansi(render_lines(state)[-1])
    assert yes_footer == "  ↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ submit mappings"

    state = _confirming(make_initial_state(make_config(), make_mappings(), frame_height=15), ConfirmationKind.EXIT, ConfirmationChoice.YES)
    skip_footer = strip_ansi(render_lines(state)[-1])
    assert skip_footer == "  ↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ skip"

    state = _confirming(make_initial_state(make_config(), make_mappings(), frame_height=15), ConfirmationKind.EXIT, ConfirmationChoice.NO)
    exit_no_footer = strip_ansi(render_lines(state)[-1])
    assert exit_no_footer == "  ↑↓ scroll  ·  shift+↑↓ pageup/dn  ·  ↵ edit mappings"


def test_render_is_idempotent_and_preserves_the_choice():
    state = _confirming(_resolved_state(), ConfirmationKind.ACCEPT, ConfirmationChoice.NO)
    assert render_lines(state) == render_lines(state)
    assert state.confirmation.choice is ConfirmationChoice.NO
