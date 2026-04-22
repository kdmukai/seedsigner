"""
Adapter layer that bridges LVGL C module screens into SeedSigner's
View/Screen architecture.

LVGL screens render through SeedSigner's existing ST7789 SPI driver via a
flush callback. Input is handled natively by the LVGL extension (gpiochip
ioctl GPIO reads). The Renderer.lock is held for the entire lifetime of an
LVGL screen to prevent PIL-based screens from writing concurrently.

Screensaver: by default all LVGL screens activate the screensaver after
the configured timeout. Screens that should not trigger the screensaver
(e.g. camera scanning) pass allow_screensaver=False.
"""
from __future__ import annotations

import array
import logging

from seedsigner.gui.screens import RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON

logger = logging.getLogger(__name__)

# Lazy import; set by ensure_lvgl_runtime().
_lv = None

# Global screensaver timeout; set once during init from Controller setting.
_screensaver_timeout_ms = 0


def ensure_lvgl_runtime():
    """Import and initialize the LVGL runtime (idempotent)."""
    global _lv, _screensaver_timeout_ms
    if _lv is not None:
        return
    import seedsigner_lvgl as lv
    lv.lvgl_init(hor_res=240, ver_res=240)
    lv.native_input_init()
    _lv = lv

    from seedsigner.controller import Controller
    _screensaver_timeout_ms = Controller.get_instance().screensaver_activation_ms

    logger.info("LVGL runtime initialized (screensaver timeout=%dms)",
                _screensaver_timeout_ms)


def _make_flush_callback(display_driver):
    """Return a flush callback that writes LVGL RGB565 pixels through an
    existing SeedSigner display driver instance."""
    def _flush(x1, y1, x2, y2, buf):
        # LVGL outputs little-endian RGB565; ST7789 expects big-endian.
        arr = array.array("H", buf)
        arr.byteswap()
        display_driver.blit_rgb565(x1, y1, x2, y2, arr.tobytes())
    return _flush


def _translate_event(event):
    """Map an LVGL result event tuple to a SeedSigner return code.

    LVGL events:
        ("button_selected", index, label)
        ("topnav_back", -1, "topnav_back")
        ("topnav_power", -1, "topnav_power")

    SeedSigner return codes:
        int index (0, 1, 2, ...) for button selection
        RET_CODE__BACK_BUTTON (1000) for back
        RET_CODE__POWER_BUTTON (1001) for power
    """
    kind, index, _label = event
    if kind == "topnav_back":
        return RET_CODE__BACK_BUTTON
    if kind == "topnav_power":
        return RET_CODE__POWER_BUTTON
    return index


def run_lvgl_screen(renderer, screen_fn, *args, allow_screensaver=True, **kwargs):
    """Run an LVGL screen function while holding the renderer lock.

    Args:
        renderer: The SeedSigner Renderer singleton.
        screen_fn: An LVGL screen function (e.g. _lv.main_menu_screen).
        allow_screensaver: If True (default), activate the screensaver after
            the global timeout. Set False for screens that should stay active
            indefinitely (e.g. camera scanning).
        *args, **kwargs: Passed through to screen_fn.

    Returns:
        A SeedSigner-compatible return code (int or RET_CODE constant).
    """
    ensure_lvgl_runtime()
    timeout_ms = _screensaver_timeout_ms if allow_screensaver else 0

    try:
        while True:
            with renderer.lock:
                _lv.set_flush_mode("python")
                _lv.set_flush_callback(_make_flush_callback(renderer.disp))
                _lv.clear_result_queue()
                if timeout_ms > 0:
                    screen_fn(*args, wait_timeout_ms=timeout_ms, **kwargs)
                else:
                    screen_fn(*args, **kwargs)

            event = _lv.poll_for_result()
            if event is not None:
                # Reset the PIL-side input timer so returning to a PIL screen
                # doesn't immediately trigger the screensaver.
                from seedsigner.hardware.buttons import HardwareButtons
                HardwareButtons.get_instance().update_last_input_time()
                return _translate_event(event)

            # No result means timeout — launch screensaver and loop back.
            # The screensaver's LVGL screen will be cleaned up by
            # load_screen_and_cleanup_previous() when screen_fn recreates.
            if timeout_ms > 0:
                lvgl_screensaver_screen(renderer, _restore_pil=False)
                # Debounce: wait for the wakeup press to be released so it
                # doesn't register as input on the re-entered screen.
                import time
                time.sleep(0.25)
                continue

            return None
    finally:
        _lv.set_flush_callback(None)


def lvgl_main_menu_screen(renderer):
    """Run the LVGL main menu screen.

    Returns:
        Button index (0-3) or RET_CODE__POWER_BUTTON.
    """
    return run_lvgl_screen(renderer, _lv.main_menu_screen)


def lvgl_screensaver_screen(renderer, _restore_pil=True):
    """Run the LVGL screensaver (bouncing logo). Blocks until any input.

    When _restore_pil is True (default, PIL context), save and restore
    the PIL canvas to repaint the display after the screensaver exits.
    When False (LVGL context), skip the restore since the LVGL screen
    will repaint itself."""
    if _restore_pil:
        last_screen = renderer.canvas.copy()
    try:
        run_lvgl_screen(renderer, _lv.screensaver_screen, allow_screensaver=False)
    finally:
        if _restore_pil:
            with renderer.lock:
                renderer.show_image(last_screen)
