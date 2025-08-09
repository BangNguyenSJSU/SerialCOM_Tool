# Copilot Instructions for SerialCOM_Tool

## Project Overview
- **Purpose:** Cross-platform GUI tool for serial communication and register-based protocol testing, built with Python and Tkinter.
- **Key Files:**
  - `serial_gui.py`: Main GUI, serial port management, threading, and event loop.
  - `protocol.py`: Protocol logic (packet encoding/decoding, Fletcher-16 checksum, register map).
  - `host_tab.py`: Host (master) mode logic, request/response, timeout handling.
  - `device_tab.py`: Device (slave) mode logic, register simulation, error simulation.
  - `test_protocol.py`: Protocol test suite (checksum, packet, register map, error handling).
  - `test_port_detection.py`: Serial port detection test.
  - `requirements.txt`: Python dependencies (mainly `pyserial`).
  - `dev_note.md`: Implementation notes, architecture, and design decisions.

## Architecture & Data Flow
- **Threading:**
  - Main thread: Tkinter GUI and event handling.
  - Read thread: Non-blocking serial data reading (5ms polling, 4KB buffer).
  - Thread-safe queue (`queue.Queue`) for data transfer between threads.
  - GUI updates every 25ms via `root.after()`.
- **Protocol:**
  - Custom frame: `[0x7E][Addr][MsgID][Len][Data][Checksum]` (Fletcher-16, big-endian).
  - Host/Device tabs use `PacketBuilder`/`PacketParser` for protocol logic.
  - Register map simulation in device mode.
- **Testing:**
  - Run `python test_protocol.py` for protocol validation.
  - Use virtual ports for integration testing (see README for platform-specific setup).

## Developer Workflows
- **Run app:** `python serial_gui.py`
- **Install deps:** `pip install -r requirements.txt`
- **Test protocol:** `python test_protocol.py`
- **Test port detection:** `python test_port_detection.py`
- **Debugging:** Enable logging in `serial_gui.py`:
  ```python
  import logging
  logging.basicConfig(level=logging.DEBUG)
  ```
- **Virtual ports:** Use `socat` (macOS/Linux) or `com0com` (Windows) for virtual serial pairs.

## Project Conventions & Patterns
- **PEP 8** and type hints throughout.
- **Docstrings** for all public methods.
- **Error handling:** Specific exception types, user-friendly messages.
- **Modular design:** Separate files for GUI, protocol, host/device logic.
- **Extending protocol:**
  - Add new function codes in `protocol.py` (update enums, builders, parsers, tests).
  - Update host/device tabs and add test cases as needed.
- **UI/UX:**
  - Font sizes and layouts optimized for readability (see `device_tab.py` for log font changes).
  - Device tab: compact controls, expanded logs, register map spans full width.

## Integration Points
- **External:**
  - `pyserial` for serial comms.
  - `tkinter` for GUI.
  - `socat`/`com0com` for virtual ports (testing only).
- **Cross-component:**
  - `serial_gui.py` imports and coordinates `host_tab.py`, `device_tab.py`, and `protocol.py`.
  - Protocol logic is reused in both host and device modes.

## Tips for AI Agents
- Reference `dev_note.md` for rationale behind architectural and UI decisions.
- When adding protocol features, update both protocol logic and UI/test code.
- Use the threading/queue pattern for any new background tasks.
- Follow the modular structure: keep protocol, GUI, and business logic separate.
- For platform-specific code (e.g., port detection), check for OS and use conditional logic as in `serial_gui.py`.

---
For more details, see `README.md` and `dev_note.md`.
