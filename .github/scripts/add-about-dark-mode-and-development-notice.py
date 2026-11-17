from pathlib import Path
import os
import datetime
import re

root = Path("ios/Carbyne/Sources")

# Appearance follows iOS system settings. Never force a scheme in the app.
app = root / "CarbyneApp.swift"
text = app.read_text()
text = text.replace('    @AppStorage("carbyne.darkMode") private var darkMode = false\n', '')
text = text.replace('                    .preferredColorScheme(.light)\n', '')
text = text.replace('                    .preferredColorScheme(darkMode ? .dark : .light)\n', '')
app.write_text(text)

# Settings includes About, with no in-app appearance toggle.
p = root / "AccountSheets.swift"
text = p.read_text()
text = text.replace(
    'struct SettingsPrivacyView: View {\n    var body: some View {\n        List {\n',
    '''struct SettingsPrivacyView: View {
    var body: some View {
        List {
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
'''
)
text = text.replace('    @AppStorage("carbyne.darkMode") private var darkMode = false\n', '')
text = text.replace('            Section("Appearance") {\n                Toggle(isOn: $darkMode) {\n                    Label("Dark mode", systemImage: "moon.fill")\n                }\n            }\n', '')
text = text.replace('?? "202611170158000001"', '?? "202611170160000001"')
text = text.replace('?? "158"', '?? "160"')
text = text.replace('Label("Dark mode and appearance settings", systemImage: "moon.fill")',
                    'Label("Automatic appearance based on iOS settings", systemImage: "circle.lefthalf.filled")')
if "struct CarbyneAboutView:" not in text:
    text += r"""

struct CarbyneAboutView: View {
    private var info: [String: Any] { Bundle.main.infoDictionary ?? [:] }
    private var version: String { info["CFBundleShortVersionString"] as? String ?? "26.0.1" }
    private var build: String { info["CFBundleVersion"] as? String ?? "161" }
    private var serial: String { info["CarbyneBuildSerial"] as? String ?? "202611170161000001" }

    var body: some View {
        List {
            Section("Version") {
                LabeledContent("Carbyne", value: version)
                LabeledContent("Build", value: build)
                LabeledContent("Serial number") {
                    Text(serial).font(.system(.footnote, design: .monospaced)).textSelection(.enabled)
                }
            }
            Section("What's new") {
                Label("Automatic appearance based on iOS settings", systemImage: "circle.lefthalf.filled")
                Label("About page with build details", systemImage: "info.circle")
                Label("Updated navigation icons and Spotlights naming", systemImage: "rectangle.stack.play")
                Label("Private development notice and testing restrictions", systemImage: "hammer.fill")
                Label("Improved speech-recognition fallback", systemImage: "waveform")
            }
            Section("Development build") {
                Text("This is a private development version of Carbyne. Features may be incomplete or change without notice.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("About Carbyne")
        .navigationBarTitleDisplayMode(.inline)
    }
}
"""
p.write_text(text)

# Compact private development notice, shown once per build serial.
p = root / "ContentView.swift"
text = p.read_text()
text = text.replace(
    '    @State private var navigationPath: [CarbyneNavigationRoute] = []\n',
    '''    @State private var navigationPath: [CarbyneNavigationRoute] = []
    @State private var showDevelopmentNotice = false
    @AppStorage("carbyne.devNoticeSeenSerial") private var seenDevelopmentSerial = ""
    private var developmentSerial: String {
        Bundle.main.object(forInfoDictionaryKey: "CarbyneBuildSerial") as? String ?? "202611170160000001"
    }
'''
)
text = text.replace('    @AppStorage("carbyne.darkMode") private var darkMode = false\n', '')
text = text.replace('                    darkMode: darkMode,\n', '')
text = text.replace(
    '        .sheet(isPresented: $showAccounts) { AccountSwitcherSheet() }\n',
    '''        .sheet(isPresented: $showAccounts) { AccountSwitcherSheet() }
        .onAppear {
            if seenDevelopmentSerial != developmentSerial {
                showDevelopmentNotice = true
            }
        }
        .alert("You’re in a development version of Carbyne", isPresented: $showDevelopmentNotice) {
            Button("I Understand") { seenDevelopmentSerial = developmentSerial }
        } message: {
            Text("""
            PRIVATE TEST BUILD

            1. Do not distribute or share this build.
            2. Do not publish screenshots, recordings, or unreleased feature information.
            3. Do not use Carbyne commercially.
            4. Do not rely on it for important data or permanent storage.
            5. Do not reverse-engineer, modify, or redistribute the app.
            6. Only authorized testers may access it.

            NEW: Automatic iOS appearance, About/version details, refreshed navigation, Spotlights naming, and an improved speech-recognition fallback.

            Version 26.0.1  •  Serial \(developmentSerial)
            """)
        }
'''
)
text = text.replace(
    'iPadTab("Moments", .moments, icon: "play.rectangle.fill")',
    'iPadTab("Spotlights", .moments, icon: "play.rectangle.fill")'
)
text = text.replace(
    'iPadTab("Chat", .messages, icon: "paperplane.fill")',
    'iPadTab("Chat", .messages, icon: "bubble.left.and.bubble.right.fill")'
)
text = text.replace(
    'ContentUnavailableView("Moments", systemImage: "play.rectangle",\n                description: Text("Moments will appear here."))',
    'ContentUnavailableView("Spotlights", systemImage: "play.rectangle",\n                description: Text("Spotlights will appear here."))'
)
p.write_text(text)

# Native UIKit controller inherits the iOS appearance. Preserve Profile avatar/icon.
p = root / "CarbyneNativeTabController.swift"
text = p.read_text()
text = text.replace('    let darkMode: Bool\n', '')
text = text.replace('        controller.overrideUserInterfaceStyle = darkMode ? .dark : .light\n', '')
text = text.replace(
    'private static let titles = ["Home", "Moments", "Upload", "Chat", "Profile"]',
    'private static let titles = ["Home", "Spotlights", "Upload", "Chat", "Profile"]'
)
text = text.replace(
    '        "house",\n        "play.rectangle",\n        "plus.circle.fill",\n        "paperplane.fill",\n',
    '        "house.fill",\n        "play.rectangle.fill",\n        "plus.square.fill",\n        "bubble.left.and.bubble.right.fill",\n'
)
text = text.replace(
    'ContentUnavailableView("Moments", systemImage: "play.rectangle",\n                    description: Text("Moments will appear here."))',
    'ContentUnavailableView("Spotlights", systemImage: "play.rectangle",\n                    description: Text("Spotlights will appear here."))'
)
p.write_text(text)

# Dynamic appearance plus numeric build serial embedded in the app.
project = Path("ios/Carbyne/project.yml")
text = project.read_text().replace(
    "INFOPLIST_KEY_UIUserInterfaceStyle: Light",
    "INFOPLIST_KEY_UIUserInterfaceStyle: Automatic"
)
build = os.environ.get("GITHUB_RUN_NUMBER", "160")
date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
serial = f"{date}{int(build):04d}000001"
if "INFOPLIST_KEY_CarbyneBuildSerial:" in text:
    text = re.sub(
        r"(?m)^(\s*)INFOPLIST_KEY_CarbyneBuildSerial:.*$",
        rf'\g<1>INFOPLIST_KEY_CarbyneBuildSerial: "{serial}"',
        text
    )
else:
    text = text.replace(
        "    INFOPLIST_KEY_UIUserInterfaceStyle: Automatic\n",
        f'    INFOPLIST_KEY_UIUserInterfaceStyle: Automatic\n    INFOPLIST_KEY_CarbyneBuildSerial: "{serial}"\n'
    )
project.write_text(text)
Path("ios/Carbyne/VERSION").write_text("26.0.1\n")
print(f"Applied iOS-controlled appearance, About page, private development notice and navigation updates. Serial: {serial}")
