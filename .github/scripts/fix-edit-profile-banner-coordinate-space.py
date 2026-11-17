from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
if not path.exists():
    raise SystemExit(f"Missing expected Swift source: {path}")

source = path.read_text()
start = source.find("struct EditProfileView: View {")
if start < 0:
    raise SystemExit("Could not find EditProfileView; refusing to patch the wrong view.")
end = source.find("\nstruct ", start + 1)
if end < 0:
    end = len(source)
view = source[start:end]

needle = """        }
        .background(Color(uiColor: .systemBackground))
        .navigationTitle("Edit profile")"""
replacement = """        }
        .coordinateSpace(name: "profileScroll")
        .background(Color(uiColor: .systemBackground))
        .navigationTitle("Edit profile")"""

if replacement in view:
    print("EditProfileView already defines the profileScroll coordinate space.")
    raise SystemExit(0)
if view.count(needle) != 1:
    raise SystemExit("Expected exactly one EditProfileView ScrollView modifier boundary; refusing to patch.")

source = source[:start] + view.replace(needle, replacement, 1) + source[end:]
path.write_text(source)
print("Added the profileScroll coordinate space to EditProfileView's ScrollView.")
