from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content = content_path.read_text()

old_speech = "        let useOnDeviceFirst = recognizer.supportsOnDeviceRecognition"
new_speech = """        // Do not force the device-local acoustic model. Some iOS speech asset
        // builds expose an incompatible H16 VAD bundle and fail before recognition.
        let useOnDeviceFirst = false"""
if new_speech not in content:
    if old_speech not in content:
        raise SystemExit("Could not find the on-device recognition selection; refusing to patch.")
    content = content.replace(old_speech, new_speech, 1)

old_send = 'Image(systemName: "arrow.up.circle.fill")'
new_send = 'Image(systemName: "paperplane.fill")'
if new_send not in content:
    if old_send not in content:
        raise SystemExit("Could not find the message send icon; refusing to patch.")
    content = content.replace(old_send, new_send, 1)

content_path.write_text(content)
print("Avoided the incompatible local speech asset path and changed the message send icon to a paper airplane.")
