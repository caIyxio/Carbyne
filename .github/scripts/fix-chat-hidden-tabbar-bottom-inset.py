from pathlib import Path

for path in Path("ios/Carbyne").rglob("*.swift"):
    source = path.read_text()
    bad = "controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -tabBar.bounds.height : 0"
    good = "controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0"
    if bad in source:
        source = source.replace(bad, good)
        path.write_text(source)
        print(f"Corrected tab-bar safe-area reference in {path}")
