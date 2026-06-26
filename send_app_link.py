"""
Run: python send_app_link.py
Prints WhatsApp-ready messages with install instructions for RSOs.
"""
DASHBOARD_URL = "https://tanishq-mn-dashboard.streamlit.app"

ANDROID_INSTALL_MSG = f"""
💎 *Tanishq MN Dashboard — Install on Your Phone*

1. Open this link in Chrome: {DASHBOARD_URL}
2. Tap the ⋮ menu (top right)
3. Tap *"Add to Home Screen"* or *"Install app"*
4. Name: Tanishq MN → Tap Add
5. 💎 Done! Tap the icon on your home screen to open your dashboard

Your login: Pick your name from dropdown, password: rso2026
"""

IOS_INSTALL_MSG = f"""
💎 *Tanishq MN Dashboard — Install on iPhone*

1. Open this link in Safari: {DASHBOARD_URL}
2. Tap the Share button (box with arrow, bottom of screen)
3. Scroll down → tap *"Add to Home Screen"*
4. Name: Tanishq MN → Tap Add
5. 💎 Done! Tap the diamond icon on your home screen

Your login: Pick your name from dropdown, password: rso2026
"""

print("ANDROID MESSAGE:")
print(ANDROID_INSTALL_MSG)
print("\niOS MESSAGE:")
print(IOS_INSTALL_MSG)
