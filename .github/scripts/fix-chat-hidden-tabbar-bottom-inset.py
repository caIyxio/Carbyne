from pathlib import Path

path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
source = path.read_text()

needle = "controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0"
lines = source.splitlines()
out = []
patched = 0
for line in lines:
    out.append(line)
    if ".tabBar.isHidden = isChatThreadOpen" in line:
        indent = line[:len(line) - len(line.lstrip())]
        out.append(indent + needle)
        patched += 1

if patched == 0:
    raise SystemExit("No chat tab-bar visibility assignment found")
source = "\n".join(out) + "\n"
source = source.replace(needle + "\n" + needle, needle)
path.write_text(source)
print(f"Adjusted bottom safe area alongside {patched} chat tab-bar visibility assignment(s).")
