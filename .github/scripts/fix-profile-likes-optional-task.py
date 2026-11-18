from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
source = path.read_text()

broken = """            .task(id: profile.id) {
                await store.refreshProfileLikes(for: profile)
            }"""
fixed = """            .task {
                if let profile {
                    await store.refreshProfileLikes(for: profile)
                }
            }"""

if broken not in source:
    if fixed in source:
        print("Profile-likes task already uses safe optional unwrapping.")
    else:
        raise SystemExit("Could not locate the failing optional-profile task.")
else:
    source = source.replace(broken, fixed, 1)
    path.write_text(source)
    print("Fixed the optional profile task that prevented Swift compilation.")
