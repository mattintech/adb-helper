---
name: Bug report
about: Create a report to help us improve
title: '[BUG] '
labels: bug
assignees: ''

---

**IMPORTANT: This bug report MUST include both Host OS and Android OS version information or it will be closed immediately.**

## Bug Description
A clear and concise description of what the bug is.

## System Information (REQUIRED)
**Host Operating System:**
- [ ] macOS (version: ______)
- [ ] Linux (distribution and version: ______)
- [ ] Windows (version: ______)
- [ ] WSL (Windows version: ______, WSL version: ______)

**Android Device Information:**
- Device Model: 
- Android Version: 
- Connection Type: [ ] USB [ ] Wireless

**ADB Helper Version:**
```
# Run: adbh --version
# Paste output here
```

**Python Version:**
```
# Run: python --version
# Paste output here
```

## To Reproduce
Steps to reproduce the behavior:
1. Run command '...'
2. Select option '...'
3. See error

## Expected Behavior
A clear and concise description of what you expected to happen.

## Actual Behavior
What actually happened, including any error messages.

## Error Output
```
# Paste any error messages or stack traces here
```

## Screenshots
If applicable, add screenshots to help explain your problem.

## Additional Context
Add any other context about the problem here.

## Attempted Solutions
- [ ] I have checked that ADB is properly installed (`adbh check`)
- [ ] I have verified the device is connected (`adbh devices`)
- [ ] I have tried reconnecting the device
- [ ] I have checked the [Discussions](https://github.com/mattintech/adbhelper/discussions) for similar issues

---
**Note: Bug reports missing OS version information will be closed without investigation.**