import threading
import time
import types

from serial_gui import SerialGUI


class DummyWidget:
    def config(self, **kwargs):
        pass


def create_dummy_gui():
    gui = types.SimpleNamespace()
    gui.running = True
    gui.serial_port = types.SimpleNamespace(is_open=True, close=lambda: None)
    gui.is_connected = True
    gui.COLORS = SerialGUI.COLORS
    # Widgets required by disconnect_serial
    gui.connect_btn = DummyWidget()
    gui.send_btn = DummyWidget()
    gui.port_combo = DummyWidget()
    gui.baud_combo = DummyWidget()
    gui.databits_combo = DummyWidget()
    gui.parity_combo = DummyWidget()
    gui.stopbits_combo = DummyWidget()
    gui.refresh_btn = DummyWidget()
    gui.status_indicator = DummyWidget()
    gui.status_bar = DummyWidget()
    gui.port_info_label = DummyWidget()
    gui.add_system_message = lambda msg: None
    return gui


def test_disconnect_joins_read_thread():
    gui = create_dummy_gui()

    def target():
        while gui.running:
            time.sleep(0.01)

    thread = threading.Thread(target=target)
    gui.read_thread = thread
    thread.start()

    SerialGUI.disconnect_serial(gui)

    assert not thread.is_alive()
    assert gui.read_thread is None
