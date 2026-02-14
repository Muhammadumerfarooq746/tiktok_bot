# Run uiautomator2 on Your Android Phone (No PC Needed)

Use **Termux** so everything runs on the phone: Python 3.12, ADB, and uiautomator2. The phone controls itself over **Wireless debugging** (localhost).

---

## 1. Install Termux

- **Recommended:** Install from [F-Droid](https://f-droid.org/en/packages/com.termux/) (better package support).
- Or install **Termux** from the Google Play Store.

---

## 2. In Termux: Install Python 3.12 and ADB

Open Termux and run:

```bash
pkg update
pkg upgrade -y
pkg install python android-tools -y
```

Check versions:

```bash
python --version   # should be 3.12.x
adb version
```

---

## 3. Install system packages (avoids building lxml in pip)

**Do this before `pip install`.** It installs a pre-built **lxml** so pip won’t try to compile it (which often fails on Termux):

```bash
pkg install python-lxml -y
```

Optional (for image support and building other packages if needed):

```bash
pkg install libjpeg-turbo libpng libtiff freetype libxml2 libxslt clang make net-tools -y
```

Then upgrade pip (recommended):

```bash
pip install --upgrade pip
```

---

## 4. Install uiautomator2 and weditor (Python)

In Termux:

```bash
pip install uiautomator2
```

Or, if you copied this project onto the phone:

```bash
pip install -r requirements.txt
```

---

## 5. Enable Wireless Debugging on Your Phone

1. Open **Settings → About phone** and tap **Build number** 7 times to enable Developer options.
2. Go to **Settings → Developer options**.
3. Turn on **Wireless debugging**.
4. Tap **Wireless debugging** and note:
   - **Pairing port** (e.g. `37123`) and **pairing code**, or
   - **Connection port** (e.g. `5555`) after pairing.

On **Android 11+** you must **pair** once, then **connect**:

- Tap **Pair device with pairing code**.
- Note the **IP:pair_port** (e.g. `127.0.0.1:37123`) and the **6-digit code**.

---

## 6. In Termux: Connect ADB to This Phone (localhost)

**One-time pairing (Android 11+):**

```bash
adb pair 127.0.0.1:PAIR_PORT
# Enter the 6-digit code when asked.
# Example: adb pair 127.0.0.1:37123
```

**Connect:**

```bash
adb connect 127.0.0.1:CONNECT_PORT
# Example: adb connect 127.0.0.1:5555
```

Check:

```bash
adb devices
# You should see 127.0.0.1:5555 device
```

---

## 7. Install uiautomator2 Agent on the Phone (one time)

In Termux:

```bash
python -m uiautomator2 init
```

This installs the automation helper app on the same device. If you have multiple devices, use:

```bash
python -m uiautomator2 init --serial 127.0.0.1:5555
```

---

## 8. Run Your Scripts

In your Python script, connect to the local device:

```python
import uiautomator2 as u2

# Use the same port you used in adb connect
d = u2.connect("127.0.0.1:5555")

# Example: open app, tap, etc.
d.app_start("com.zhiliaoapp.musically")  # TikTok
# d(text="Like").click()
```

Run from Termux:

```bash
python /path/to/your_script.py
```

---

## Quick Reference

| Step              | Command / Action                          |
|-------------------|-------------------------------------------|
| Update Termux     | `pkg update && pkg upgrade -y`            |
| Install stack     | `pkg install python android-tools -y`      |
| Avoid lxml build  | `pkg install python-lxml -y`              |
| Install u2        | `pip install -r requirements.txt`         |
| Pair (once)       | `adb pair 127.0.0.1:PAIR_PORT`            |
| Connect           | `adb connect 127.0.0.1:CONNECT_PORT`      |
| Init agent        | `python -m uiautomator2 init`             |
| Check device      | `adb devices`                             |

---

## Troubleshooting

- **“Failed building wheel for lxml”**  
  Install the pre-built package first: `pkg install python-lxml -y`, then run `pip install -r requirements.txt` again.

- **“device offline”**  
  Restart Wireless debugging or run `adb kill-server` then `adb connect 127.0.0.1:PORT` again.

- **“no devices”**  
  Confirm Wireless debugging is on and you’ve run `adb pair` (if needed) and `adb connect 127.0.0.1:PORT`.

- **Port changes**  
  Wireless debugging can change the port after reboot. Check **Developer options → Wireless debugging** and run `adb connect 127.0.0.1:NEW_PORT` again.

- **Termux packages not found**  
  Prefer installing Termux from F-Droid and run `pkg update` again.
