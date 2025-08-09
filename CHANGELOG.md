# Changelog - PySerial GUI Project

All notable changes to this project will be documented in this file.

## [3.1.0] - 2025-08-09 - Enhanced Packet Preview with Color-Coded Formatting

### 🎨 UI/UX Improvements
- **Color-Coded Packet Preview**: Added syntax highlighting to the Packet Preview & Inspection section in Host (Master) tab
  - Hex bytes displayed in blue bold (#0066CC) for better visibility
  - Field labels in gray (#666666) for clear distinction
  - Field values in green bold (#009900) for emphasis
  - Function codes in purple bold (#9900CC) for easy identification
  - Address fields in orange bold (#FF6600) for quick reference
  - Error messages in red bold (#CC0000) for immediate attention
  - Separators in light gray (#999999) for visual organization
- **Dynamic Preview Updates**: Real-time color-coded updates as parameters change
- **Improved Error Handling**: Preview shows informative messages instead of error dialogs
  - Count mismatch warnings for Write Multiple operations
  - "Waiting for valid input..." status when packet can't be built
  - Non-intrusive error display during live editing

### 🔧 Technical Improvements
- **Text Widget Tag Configuration**: Added comprehensive color tags for both preview_text and parsed_text widgets
- **Smart Error Suppression**: Added show_errors parameter to build_packet() method to prevent dialog spam during preview updates
- **Event-Driven Updates**: Added trace handlers for all input fields to trigger immediate preview updates
- **Grid Layout Fix**: Resolved widget visibility issues by switching from pack to grid-based show/hide logic

### 🐛 Bug Fixes
- **Fixed Error Dialog Spam**: Prevented error dialogs from appearing during live preview updates
- **Fixed Widget Layout Issues**: Resolved "can't pack inside" errors when switching operation types
- **Fixed Count Mismatch Handling**: Gracefully handles count/value mismatches in Write Multiple operations

## [3.0.0] - 2025-08-09 - Major UI Reorganization & Space Optimization

### 🎨 Major UI/UX Improvements
- **Tab-Specific Controls**: Moved all global UI elements (checkboxes, command bar, quick commands, status bar) into their respective tabs for better space utilization
- **Enhanced Device Tab**: 
  - Added packet counters to panel headers (Incoming Requests: X packets, Outgoing Responses: Y packets)
  - Integrated auto-scroll toggles for each communication panel
  - Added search functionality with real-time highlighting
  - Reorganized Error Simulation into 3-column layout to fit all 5 options (No Error, Invalid Function, Invalid Address, Invalid Value, Internal Error)
  - Enhanced Register Map with search, tooltips, and "Set Multiple" functionality
  - Improved entry field width from 18 to 50 characters for comma-separated values
- **Improved Host Tab**:
  - Expanded Packet Preview & Inspection height (Raw: 2→6 lines, Parsed: 2→8 lines) to match Communication Log
  - Enhanced parameter field labeling with better alignment
  - Increased "Values (comma-separated)" field width from 25→30 label width and 40→50 entry width

### 🔧 Layout Optimizations
- **Self-Contained Tabs**: Each tab now contains all its relevant controls, eliminating floating elements in the main window
- **Space Efficiency**: Reduced text display heights from 20 to 15 lines to accommodate integrated command bars
- **Fixed Overlapping Issues**: Resolved status bar and quick commands overlapping by proper grid row assignments
- **Better Visual Hierarchy**: Improved panel organization with consistent padding and alignment

### 🐛 Bug Fixes
- **IndentationError**: Fixed incorrect indentation in Device Tab error simulation code at line 829
- **Label Truncation**: Fixed "Size" label being truncated to "Siz" by switching to grid layout with proper column configuration
- **Error Simulation Clipping**: Resolved option clipping by reorganizing from single column to 3-column layout
- **Command Section Disappearing**: Fixed overlapping row assignments in grid layout
- **UI Element Positioning**: Moved command bar, quick commands, and status bar from root layout into appropriate tabs

### 🔧 Technical Improvements
- **Grid Layout Standardization**: Consistent use of grid layout for better alignment and spacing
- **Entry Field Widths**: Optimized entry field sizes for better usability
- **Panel Header Updates**: Dynamic counters that update in real-time
- **Search Functionality**: Real-time search with case-insensitive matching and highlighting

## [2.1.1] - 2025-08-08 - Device Tab Font Size Enhancement

### 🎨 UI Improvements
- **Increased Font Size**: Communication logs in Device tab now use 14pt font (up from 11pt)
  - Incoming Requests text box: 14pt Courier font for better readability
  - Outgoing Responses text box: 14pt Courier font for better readability
  - Header tags increased to 15pt bold for proper visual hierarchy
- **Better Visibility**: Larger text makes it easier to read protocol messages and debug communication

## [2.1.0] - 2025-08-08 - Serial Reception Reliability Update

### 🐛 Critical Bug Fixes
- **Fixed serial data reception issues**: Eliminated race conditions causing data loss
- **Improved packet reliability**: No longer requires sending data multiple times
- **Enhanced buffer management**: Consistent 4KB buffer for stable performance

### ⚡ Performance Improvements
- **Faster response times**: Reduced read thread delay from 10ms to 5ms
- **Better GUI responsiveness**: Reduced GUI update interval from 50ms to 25ms  
- **Optimized polling**: Tab processing intervals reduced from 10ms to 5ms
- **Continuous polling strategy**: Always-on data reading prevents timing-based packet loss

### 🔧 Technical Changes
- **Serial Reading Strategy**: 
  - **Before**: `if self.serial_port.in_waiting > 0: data = self.serial_port.read(self.serial_port.in_waiting)`
  - **After**: `data = self.serial_port.read(4096)` with continuous polling
- **Thread Synchronization**: Better coordination between read thread and UI updates
- **Buffer Management**: Fixed 4KB buffer size for consistent performance

### 📚 Documentation Updates
- Updated README.md with new performance specifications
- Enhanced dev_note.md with detailed technical analysis of the fixes
- Added troubleshooting section for data reception issues

## [2.0.0] - 2025-08-07 - Device Tab Layout Optimization

### 🎨 Major UI/UX Improvements
- **Device Tab Redesign**: Complete layout restructuring for optimal space utilization
- **Compact Control Panels**: Reorganized Device Configuration, Error Simulation, and Statistics
- **Expanded Communication Logs**: Moved to prominent top row with larger display areas
- **Horizontal Layout**: All control sections aligned for better visual organization
- **Register Map Enhancement**: Full-width display for better data visibility

### 🔧 Layout Optimizations
- **Device Configuration**: Combined address/size into single row, reduced spinbox widths
- **Communication Logs**: Increased width from 30 to 45 characters, added expand capability
- **Statistics Display**: Standardized label widths with fixed alignment
- **Button Organization**: Optimized placement and sizing for better workflow

## [1.5.0] - 2025-08-06 - UI/UX Enhancements

### 🎨 Interface Improvements
- **Window Size**: Increased from 800x600 to 1400x900 for better visibility
- **Font Size**: Upgraded from 9-12pt to 14pt for improved readability
- **Layout Optimization**: Single-line radio button layout for register operations
- **Minimum Size**: Added constraint (1200x800) to maintain usability

### 🔌 Port Detection
- **Virtual TTY Support**: Added detection for socat-created virtual ports
- **Cross-platform**: Enhanced port discovery for macOS, Windows, and Linux
- **Testing Support**: Improved development workflow with virtual port integration

## [1.0.0] - 2025-08-05 - Protocol Implementation

### 🚀 Major Features Added
- **Host (Master) Mode**: Send register read/write commands with timeout handling
- **Device (Slave) Mode**: Simulate device with configurable register map
- **Custom Protocol**: Fletcher-16 checksum verification for data integrity
- **Error Simulation**: Configurable error injection for robust testing
- **Broadcast Support**: Device address 0 for broadcast messaging

### 🔧 Protocol Specifications
- **Packet Structure**: `[Start Flag|Device Addr|Message ID|Length|Data|Checksum]`
- **Function Codes**: Read/Write Single/Multiple (0x01-0x04) with responses (0x41-0x44)
- **Error Handling**: Comprehensive error codes (0x81-0x84) with descriptive messages
- **Register Operations**: Support for 16-bit registers with address range validation

### 🧪 Testing Infrastructure
- **Protocol Tests**: Comprehensive test suite in `test_protocol.py`
- **Port Detection Tests**: Validation of serial port discovery
- **Virtual Port Scripts**: Automated setup for development testing

## [0.5.0] - 2025-08-04 - Basic Serial GUI

### 🎯 Initial Implementation
- **Cross-platform Support**: Windows, macOS, and Linux compatibility
- **Non-blocking I/O**: Threading-based serial communication
- **Real-time Display**: Auto-scrolling data view with timestamp logging
- **Data Views**: Both ASCII and hexadecimal display modes
- **Command Features**: History navigation, quick macros, configurable line endings

### ⚙️ Core Features
- **Serial Configuration**: Configurable baud rate, data bits, parity, stop bits
- **Data Logging**: CSV file export with timestamps
- **Command History**: Up/Down arrow navigation through sent commands
- **Quick Macros**: Predefined command buttons (Reset, Status, Help, Version)
- **Port Management**: Auto-detection and refresh capabilities

### 🏗️ Architecture
- **Threading Model**: Main GUI thread + dedicated serial read thread
- **Queue-based Communication**: Thread-safe data passing via `queue.Queue`
- **Event-driven UI**: Proper Tkinter event handling with periodic updates
- **Modular Design**: Clean separation of GUI, serial I/O, and protocol layers

---

## Version Numbering

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality in backwards-compatible manner  
- **PATCH**: Backwards-compatible bug fixes

## Development Timeline

- **Total Development Time**: ~16.5 hours
- **Lines of Code**: ~2,000+ (Python)
- **Test Coverage**: Protocol implementation, port detection, packet validation
- **Documentation**: Comprehensive README, development notes, and inline comments