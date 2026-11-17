from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content = content_path.read_text()

old_speech = """            if recognizer.supportsOnDeviceRecognition {
                request.requiresOnDeviceRecognition = true
            }"""
new_speech = """            # Keep the request eligible for Apple's speech service instead of
            # forcing the device-local acoustic model. Some iOS asset builds expose
            # an incompatible H16 VAD bundle and fail before transcription starts.
            request.requiresOnDeviceRecognition = false"""
if new_speech not in content:
    if old_speech not in content:
        raise SystemExit("Could not find the exact on-device recognition block; refusing to patch.")
    content = content.replace(old_speech, new_speech, 1)

old_send = 'Image(systemName: "arrow.up.circle.fill")'
new_send = 'Image(systemName: "paperplane.fill")'
if new_send not in content:
    if old_send not in content:
        raise SystemExit("Could not find the message send icon; refusing to patch.")
    content = content.replace(old_send, new_send, 1)

content_path.write_text(content)
print("Disabled forced on-device speech model loading and changed the message send icon to a paper airplane.")
