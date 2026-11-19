from pathlib import Path
import re

root = Path("ios/Carbyne/Sources")
sheets_path = root / "AccountSheets.swift"
content_path = root / "ContentView.swift"

sheets = sheets_path.read_text()
start = sheets.index("struct SettingsPrivacyView: View {")
end = sheets.index("\n\nstruct CarbyneAboutView: View {", start)

replacement = r'''struct SettingsPrivacyView: View {
    var body: some View {
        List {
            Section("Messages") {
                NavigationLink {
                    DirectMessagesSettingsView()
                } label: {
                    Label {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("Direct Messages")
                            Text("Read receipts and message preferences")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    } icon: {
                        Image(systemName: "bubble.left.and.bubble.right")
                    }
                }
            }
            Section("About") {
                NavigationLink { CarbyneAboutView() } label: {
                    Label {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("About Carbyne")
                            Text("Version, build, serial number and update notes")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    } icon: {
                        Image(systemName: "info.circle")
                    }
                }
            }
            Section("Security") {
                NavigationLink {
                    SecuritySettingsView()
                } label: {
                    Label {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("Two-factor authentication")
                            Text("Add an extra layer of account protection")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    } icon: {
                        Image(systemName: "lock.shield")
                    }
                }
            }
            Section("Account") {
                NavigationLink {
                    AccountSwitcherView()
                } label: {
                    Label {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("Account switching")
                            Text("Manage accounts signed in on this device")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    } icon: {
                        Image(systemName: "person.2")
                    }
                }
            }
        }
        .scrollContentBackground(.hidden)
        .background(CarbynePalette.background.ignoresSafeArea())
        .navigationTitle("Settings & Privacy")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct DirectMessagesSettingsView: View {
    @AppStorage("carbyne.readReceiptsEnabled") private var readReceiptsEnabled = true

    var body: some View {
        List {
            Section("Read receipts") {
                Toggle("Read Receipts", isOn: $readReceiptsEnabled)
                Text(readReceiptsEnabled
                     ? "People can see when you’ve read their messages."
                     : "Read receipts are off. People won’t see when you’ve read their messages.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .scrollContentBackground(.hidden)
        .background(CarbynePalette.background.ignoresSafeArea())
        .navigationTitle("Direct Messages")
        .navigationBarTitleDisplayMode(.inline)
    }
}'''
sheets = sheets[:start] + replacement + sheets[end:]
sheets_path.write_text(sheets)

# Reusable image-backed wordmark for every visible app header.
wordmark = r'''struct CarbyneWordmark: View {
    @Environment(\.colorScheme) private var colorScheme
    var height: CGFloat = 34

    var body: some View {
        Image("CarbyneWordmark")
            .resizable()
            .scaledToFit()
            .frame(height: height)
            .colorMultiply(colorScheme == .dark ? Color.white : Color.black)
            .accessibilityLabel("Carbyne")
    }
}

'''
content = content_path.read_text()
if "struct CarbyneWordmark: View" not in content:
    marker = "struct ContentView: View {"
    if marker not in content:
        raise SystemExit("ContentView declaration not found; refusing to insert the wordmark view.")
    content = content.replace(marker, wordmark + marker, 1)
content_path.write_text(content)

# Replace visible text wordmarks (including the Home and iPad headers), leaving
# About/version labels and other non-logo references untouched.
replacements = 0
for path in root.rglob("*.swift"):
    source = path.read_text()
    updated, count = re.subn(
        r'Text\("Carbyne"\)(?:\s*\n\s*\.(?:font|tracking)\([^\n]*\))*',
        'CarbyneWordmark(height: 34)',
        source
    )
    if count:
        path.write_text(updated)
        replacements += count

if replacements == 0:
    raise SystemExit("No visible Carbyne text wordmarks found; refusing to report a branding change.")

print(f"Installed image-backed wordmark component; replaced {replacements} visible text wordmark(s).")
print("Direct Messages is now a Settings list row with its own detail page.")
