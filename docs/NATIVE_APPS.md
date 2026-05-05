# Native App Plan

CircuitSage now has three client surfaces:

1. Web Studio for session management and reports.
2. macOS Desktop Companion for always-on screen watching.
3. iOS Bench Companion for camera-based lab evidence.

## macOS Desktop Companion

Location: `apps/desktop`

Tech: Electron.

Why: It gives fast access to macOS screen/window capture and can later request Accessibility permission for click/type actions. A pure browser cannot reliably control native apps.

Current capabilities:

- floating always-on-top companion window,
- background tray/menu-bar app that hides instead of quitting,
- global ask shortcut: `CommandOrControl+Shift+Space`,
- list macOS screens/windows,
- select the current frontmost LTspice/MATLAB/Tinkercad/browser window when Accessibility permission is available,
- poll selected window thumbnails while watch mode is enabled,
- follow the active macOS app/window while watch mode is enabled,
- optional auto-insight loop that sends the current frame to the local backend about every 25 seconds,
- glowing visual state while watching/listening,
- typed prompt and Web Speech voice prompt where Electron exposes speech recognition,
- send the current screen image to `/api/companion/analyze`,
- open Screen Recording and Accessibility settings,
- guarded AppleScript helpers for click/type automation.

Next production steps:

- notarized macOS build,
- explicit permission onboarding,
- coordinate calibration for safe click actions,
- action confirmation UI before every OS action,
- native speech-to-text fallback if Web Speech is unavailable,
- active-window screenshot through lower-level macOS APIs if Electron thumbnails are not enough,
- signed auto-update channel.

## iOS Bench Companion

Location: `apps/ios`

Tech: Expo React Native.

Current capabilities:

- camera capture,
- photo-library attachment,
- backend URL configuration,
- optional session id attachment,
- save snapshot to session,
- render Gemma/fallback analysis.

Next production steps:

- QR pairing from Studio to auto-fill backend URL and session id,
- offline queue when lab Wi-Fi drops,
- voice note capture,
- App Store/TestFlight build with EAS,
- Cactus/LiteRT on-device model route if time allows.
