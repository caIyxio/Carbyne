from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
content = content_path.read_text()

# Restore the in-conversation send control; the requested paper airplane belongs
# to the Chat destination in the five-item navigation bar.
content = content.replace(
    'Image(systemName: "paperplane.fill")',
    'Image(systemName: "arrow.up.circle.fill")'
)
content = content.replace(
    'iPadTab("Chat", .messages, icon: "bubble.left.and.bubble.right.fill")',
    'iPadTab("Chat", .messages, icon: "paperplane.fill")'
)
content_path.write_text(content)

tab_path = root / "CarbyneNativeTabController.swift"
if not tab_path.exists():
    raise SystemExit("Native tab controller source was not found.")
tabs = tab_path.read_text()
old = '"bubble.left.and.bubble.right",'
new = '"paperplane.fill",'
if new not in tabs:
    if old not in tabs:
        raise SystemExit("Could not find the Chat tab symbol; refusing to patch.")
    tabs = tabs.replace(old, new, 1)
tab_path.write_text(tabs)

print("Restored the in-chat send arrow and changed the iPhone/iPad Chat navigation icon to a paper airplane.")
