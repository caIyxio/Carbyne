from pathlib import Path
import datetime
import os
import plistlib
import sys

if len(sys.argv) != 2:
    raise SystemExit("Usage: stamp-built-app-metadata.py /path/to/Carbyne.app")

app = Path(sys.argv[1])
plist_path = app / "Info.plist"
if not plist_path.is_file():
    raise SystemExit(f"App Info.plist not found: {plist_path}")

version = Path("ios/Carbyne/VERSION").read_text().strip()
build = os.environ.get("GITHUB_RUN_NUMBER", "")
if not build.isdigit():
    raise SystemExit(f"Invalid GitHub build number: {build!r}")

date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
serial = f"{date}{int(build):04d}000001"

with plist_path.open("rb") as stream:
    info = plistlib.load(stream)

info["CFBundleShortVersionString"] = version
info["CFBundleVersion"] = build
info["CarbyneBuildSerial"] = serial
info["UIUserInterfaceStyle"] = "Automatic"

plist_path.write_bytes(plistlib.dumps(info, fmt=plistlib.FMT_BINARY, sort_keys=False))
print(f"Stamped app metadata: version={version}, build={build}, serial={serial}, appearance=Automatic")
