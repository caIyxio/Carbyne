from pathlib import Path

roots = Path("ios/Carbyne").rglob("*.swift")
needle = "additionalSafeAreaInsets.bottom = isChatThreadOpen ? -tabBar.bounds.height : 0"
patched = 0

for path in roots:
    source = path.read_text()
    if needle in source:
        continue
    lines = source.splitlines()
    out = []
    for line in lines:
        out.append(line)
        if "isChatThreadOpen" in line and "isHidden" in line and "tabBar" in line:
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + "controller." + needle)
            patched += 1
    if patched:
        path.write_text("\n".join(out) + "\n")

if patched == 0:
    print("No direct tab-bar visibility assignment found; preserving source and continuing build.")
else:
    print(f"Adjusted hidden-tab-bar bottom safe area at {patched} visibility update(s).")
