from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
sheets_path = root / "AccountSheets.swift"
tabs_path = root / "CarbyneNativeTabController.swift"

def replace_once(source, old, new, label):
    if old not in source:
        if new in source:
            return source
        raise SystemExit(f"Could not find {label}; refusing to patch the wrong source.")
    return source.replace(old, new, 1)

# The account-isolation patch can reintroduce this optional-profile compile error,
# so this final source patch deliberately runs after every other UI/store patch.
content = content_path.read_text()
content = replace_once(
    content,
    """            .task(id: profile.id) {
                await store.refreshProfileLikes(for: profile)
            }""",
    """            .task {
                if let profile {
                    await store.refreshProfileLikes(for: profile)
                }
            }""",
    "optional profile likes task"
)
content_path.write_text(content)

# Spotlights uses Apple's native clapperboard symbol.
tabs = tabs_path.read_text()
tabs = replace_once(tabs, '"play.rectangle.fill",', '"movieclapper.fill",', "Spotlights tab symbol")
tabs = replace_once(tabs, 'ContentUnavailableView("Spotlights", systemImage: "play.rectangle",',
                    'ContentUnavailableView("Spotlights", systemImage: "movieclapper",',
                    "Spotlights empty-state symbol")
tabs_path.write_text(tabs)

content = content.replace('iPadTab("Spotlights", .moments, icon: "play.rectangle.fill")',
                          'iPadTab("Spotlights", .moments, icon: "movieclapper.fill")')
content_path.write_text(content)

# Settings uses actual top-level tabs, not a Direct Messages section heading.
sheets = sheets_path.read_text()
start = sheets.index("struct SettingsPrivacyView: View {")
end = sheets.index("\n\nstruct CarbyneAboutView: View {", start)
replacement = """struct SettingsPrivacyView: View {
    @AppStorage("carbyne.readReceiptsEnabled") private var readReceiptsEnabled = true
    @State private var selectedSettingsTab = "General"

    var body: some View {
        VStack(spacing: 0) {
            Picker("Settings", selection: $selectedSettingsTab) {
                Text("General").tag("General")
                Text("Direct Messages").tag("Direct Messages")
            }
            .pickerStyle(.segmented)
            .padding(.horizontal, 16)
            .padding(.top, 12)
            .padding(.bottom, 8)

            List {
                if selectedSettingsTab == "Direct Messages" {
                    Section {
                        Toggle("Read Receipts", isOn: $readReceiptsEnabled)
                        Text(readReceiptsEnabled
                             ? "People can see when you’ve read their messages."
                             : "Read receipts are off. People won’t see when you’ve read their messages.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                } else {
                    Section("About") {
                        NavigationLink { CarbyneAboutView() } label: {
                            Label {
                                VStack(alignment: .leading, spacing: 3) {
                                    Text("About Carbyne")
                                    Text("Version, build, serial number and update notes")
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            } icon: { Image(systemName: "info.circle") }
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
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            } icon: { Image(systemName: "lock.shield") }
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
                                        .font(.caption).foregroundStyle(.secondary)
                                }
                            } icon: { Image(systemName: "person.2") }
                        }
                    }
                }
            }
            .scrollContentBackground(.hidden)
            .background(CarbynePalette.background.ignoresSafeArea())
        }
        .background(CarbynePalette.background.ignoresSafeArea())
        .navigationTitle("Settings & Privacy")
        .navigationBarTitleDisplayMode(.inline)
    }
}"""
sheets = sheets[:start] + replacement + sheets[end:]
sheets_path.write_text(sheets)

print("Fixed the optional-profile compile error, applied the native clapperboard icon, and moved Direct Messages into its own Settings tab.")
