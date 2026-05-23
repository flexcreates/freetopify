# Android Build Doc (Caveman)

## Big Goal
Android app talk same server API. Play music. Work LAN + Tailscale + BT PAN.

## Must Have
- Flutter `>=3.10`
- Dart
- Android SDK (min 26)
- Device/emulator

## Android Folder Tree (Need)
```txt
android/
├── pubspec.yaml
├── lib/
│   ├── main.dart
│   ├── config/
│   │   └── app_config.dart
│   ├── models/
│   │   ├── track.dart
│   │   └── folder.dart
│   ├── services/
│   │   ├── api_service.dart
│   │   ├── auth_service.dart
│   │   ├── player_service.dart
│   │   └── ws_service.dart
│   ├── screens/
│   │   ├── login_screen.dart
│   │   ├── library_screen.dart
│   │   ├── player_screen.dart
│   │   └── settings_screen.dart
│   ├── widgets/
│   │   ├── folder_tile.dart
│   │   ├── track_tile.dart
│   │   └── mini_player.dart
│   └── providers/
│       ├── player_provider.dart
│       └── library_provider.dart
└── android/app/src/main/AndroidManifest.xml
```

## pubspec deps (Need)
- `dio`
- `just_audio`
- `provider`
- `shared_preferences`
- `connectivity_plus`
- `flutter_background_service`
- `flutter_secure_storage`

## Build Order
1. `pubspec.yaml`
2. models
3. services
4. providers
5. screens
6. widgets
7. manifest permissions

## Rules
- First launch ask server URL + login
- Discover button via mDNS query `_freetopify._tcp.local.`
- Save token secure storage
- WebSocket live update
- Auto reconnect with backoff
- Offline show last folder cache
- Connection dot: green/yellow/red

## Connectivity Modes
- WiFi: use normal URL
- Tailscale: use stored Tailscale IP
- Bluetooth PAN: user sets BT network IP

## AndroidManifest perms
- `INTERNET`
- `FOREGROUND_SERVICE`
- Bluetooth permissions needed for target SDK

## Verify
```bash
flutter pub get
flutter analyze
flutter build apk --release
```

## Git Flow
- `android: scaffold models and services`
- `android: add library and player screens`
- `android: add connectivity and ws updates`
