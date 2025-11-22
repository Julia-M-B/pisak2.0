from pisak.modules.base_module import PisakBaseModule
from pisak.widgets.buttons import PisakButton


class PisakMainModule(PisakBaseModule):
    def __init__(self, parent=None):
        super().__init__(parent, title="Main Menu")
        self._symboler_btn = PisakButton(parent=self, text="SYMBOLER")
        self._speller_btn = PisakButton(parent=self, text="SPELLER")
        self.centralWidget().add_item(self._symboler_btn)
        self.centralWidget().add_item(self._speller_btn)

        self.init_ui()

    @property
    def symboler_btn(self):
        return self._symboler_btn

    @property
    def speller_btn(self):
        return self._speller_btn

    def init_ui(self):
        super().init_ui()
        self.centralWidget().layout.addWidget(self.symboler_btn, 0, 0)
        self.centralWidget().layout.addWidget(self.speller_btn, 0, 1)
        self.centralWidget().set_layout()
