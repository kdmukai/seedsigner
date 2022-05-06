from gettext import gettext as _

from seedsigner.gui.components import FontAwesomeIconConstants
from seedsigner.gui.screens import main_menu_screens
from seedsigner.gui.screens.screen import RET_CODE__BACK_BUTTON, RET_CODE__POWER_BUTTON, LargeButtonScreen
from seedsigner.models.threads import BaseThread
from seedsigner.views.view import BackStackView, Destination, View


class MainMenuView(View):
    def run(self):
        from .seed_views import SeedsMenuView
        from .settings_views import SettingsMenuView
        from .scan_views import ScanView
        from .tools_views import ToolsMenuView
        from seedsigner.gui.screens.main_menu_screens import MainMenuScreen
        menu_items = [
            ((_("Scan"), FontAwesomeIconConstants.QRCODE), ScanView),
            ((_("Seeds"), FontAwesomeIconConstants.KEY), SeedsMenuView),
            ((_("Tools"), FontAwesomeIconConstants.SCREWDRIVER_WRENCH), ToolsMenuView),
            ((_("Settings"), FontAwesomeIconConstants.GEAR), SettingsMenuView),
        ]

        screen = MainMenuScreen(
            button_data=[entry[0] for entry in menu_items],
        )
        selected_menu_num = screen.display()

        if selected_menu_num == RET_CODE__POWER_BUTTON:
            return Destination(PowerOptionsView)

        return Destination(menu_items[selected_menu_num][1])



class PowerOptionsView(View):
    def run(self):
        RESET = (_("Restart"), FontAwesomeIconConstants.ROTATE_RIGHT)
        POWER_OFF = (_("Power Off"), FontAwesomeIconConstants.POWER_OFF)
        button_data = [RESET, POWER_OFF]
        selected_menu_num = LargeButtonScreen(
            title=_("Reset / Power"),
            show_back_button=True,
            button_data=button_data
        ).display()

        if selected_menu_num == RET_CODE__BACK_BUTTON:
            return Destination(BackStackView)
        
        elif button_data[selected_menu_num] == RESET:
            return Destination(RestartView)
        
        elif button_data[selected_menu_num] == POWER_OFF:
            return Destination(PowerOffView)



class RestartView(View):
    def run(self):
        thread = RestartView.DoResetThread()
        thread.start()
        main_menu_screens.ResetScreen().display()


    class DoResetThread(BaseThread):
        def run(self):
            import time
            from subprocess import call

            # Give the screen just enough time to display the reset message before
            # exiting.
            time.sleep(0.25)

            # Kill the SeedSigner process; systemd will automatically restart it.
            # `.*` is a wildcard to detect either `python`` or `python3` and with or
            # without the `-u` flag.
            call("kill $(ps aux | grep '[p]ython.*main.py' | awk '{print $2}')", shell=True)



class PowerOffView(View):
    def run(self):
        thread = PowerOffView.PowerOffThread()
        thread.start()
        main_menu_screens.PowerOffScreen().display()


    class PowerOffThread(BaseThread):
        def run(self):
            import time
            from subprocess import call
            while self.keep_running:
                time.sleep(5)
                call("sudo shutdown --poweroff now", shell=True)
