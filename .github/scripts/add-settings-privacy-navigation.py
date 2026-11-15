from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
sheets_path = root / "AccountSheets.swift"
content = content_path.read_text()
sheets = sheets_path.read_text()

def replace_once(source, old, new, label):
    if old not in source:
        if new in source:
            return source
        raise SystemExit(f"Could not find {label}; refusing to patch the wrong source.")
    return source.replace(old, new, 1)

# Keep implementation details out of the customer-facing copy.
sheets = replace_once(
    sheets,
    "Use your existing Carbyne account. Your website and iOS sessions share the same Supabase authentication.",
    "Use your Carbyne account to sign in and keep your profile in sync across devices.",
    "sign-in description"
)
sheets = replace_once(
    sheets,
    "Each account keeps its own secure Supabase session on this device.",
    "Each account stays signed in on this device.",
    "account switcher description"
)

# Turn the website's working Settings routes into native navigation destinations.
start = sheets.index("struct AccountSwitcherSheet: View {")
end = sheets.index("\nstruct MFASettingsSheet: View {", start)
account_view = """struct AccountSwitcherView: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\\.dismiss) private var dismiss
    @State private var code = ""
    @State private var showAddAccount = false

    var body: some View {
        List {
            if store.accounts.isEmpty {
                ContentUnavailableView("No saved accounts", systemImage: "person.2", description: Text("Accounts you've signed into on this device will appear here."))
            }
            Section("Accounts") {
                ForEach(store.accounts, id: \\.self) { email in
                    let profile = store.accountProfiles[email]
                    Button {
                        Task {
                            await store.switchAccount(to: email)
                            if store.session != nil && !store.requiresMFA { dismiss() }
                        }
                    } label: {
                        HStack(spacing: 12) {
                            AvatarView(url: store.publicImageURL(path: profile?.avatarPath), size: 44)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(profile?.title ?? "Carbyne account")
                                    .font(.system(size: 15, weight: .semibold))
                                    .foregroundStyle(.primary)
                                Text(profile?.username.map { "@\\($0)" } ?? "Profile details unavailable")
                                    .font(.system(size: 12))
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if email == store.session?.user.email?.lowercased() {
                                Label("Current", systemImage: "checkmark.circle.fill")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .disabled(store.isLoading || email == store.session?.user.email?.lowercased())
                }
            }
            Section {
                Button {
                    showAddAccount = true
                } label: {
                    Label("Add an account", systemImage: "plus.circle")
                }
                .disabled(store.isLoading)
            }
            if store.requiresMFA {
                Section("Authenticator verification") {
                    TextField("Six-digit code", text: $code).keyboardType(.numberPad).textContentType(.oneTimeCode)
                    Button("Verify") { Task { await store.verifyLoginMFA(code: code); if !store.requiresMFA { dismiss() } } }
                        .disabled(code.count < 6 || store.isLoading)
                }
            }
            Section {
                Text("Each account stays signed in on this device.")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Account switching")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        .task { await store.refreshAccountProfiles() }
        .onChange(of: store.accounts) { _, _ in Task { await store.refreshAccountProfiles() } }
        .sheet(isPresented: $showAddAccount) { AuthenticationSheet() }
    }
}

struct AccountSwitcherSheet: View {
    var body: some View {
        NavigationStack {
            AccountSwitcherView()
        }
        .presentationDetents([.medium, .large])
    }
}

"""
sheets = sheets[:start] + account_view + sheets[end:]

start = sheets.index("struct MFASettingsSheet: View {")
new_security = """struct SecuritySettingsView: View {
    @EnvironmentObject private var store: CarbyneStore
    @State private var code = ""
    @State private var isSettingUp = false

    var body: some View {
        Form {
            Section("Authenticator app") {
                if store.mfaIsEnabled && !isSettingUp {
                    Label("Two-factor authentication is enabled", systemImage: "checkmark.shield.fill")
                        .foregroundStyle(.green)
                    SecureField("Current six-digit code", text: $code)
                        .keyboardType(.numberPad)
                        .textContentType(.oneTimeCode)
                    Button("Disable authenticator", role: .destructive) {
                        Task { await store.disableMFA(code: code); code = "" }
                    }
                    .disabled(code.count < 6 || store.isLoading)
                } else if let secret = store.pendingMFASecret {
                    Text("Add this account to an authenticator app, then enter the current six-digit code.")
                        .font(.footnote).foregroundStyle(.secondary)
                    Text("Setup key").font(.caption).foregroundStyle(.secondary)
                    Text(secret).font(.system(.body, design: .monospaced)).textSelection(.enabled)
                    if let uri = store.pendingMFAURI, let url = URL(string: uri) {
                        ShareLink(item: url) { Label("Share setup URI", systemImage: "square.and.arrow.up") }
                    }
                    TextField("Six-digit code", text: $code)
                        .keyboardType(.numberPad)
                        .textContentType(.oneTimeCode)
                    Button("Enable two-factor authentication") {
                        Task { await store.completeMFAEnrollment(code: code); code = ""; isSettingUp = false }
                    }
                    .disabled(code.count < 6 || store.isLoading)
                } else {
                    Text("Add an extra layer of protection to your Carbyne account with an authenticator app.")
                        .font(.footnote).foregroundStyle(.secondary)
                    Button("Set up authenticator") {
                        Task { await store.beginMFAEnrollment(); isSettingUp = true }
                    }
                    .disabled(store.isLoading)
                }
            }
            if store.isLoading { ProgressView() }
            if let error = store.errorMessage { Text(error).font(.footnote).foregroundStyle(.red) }
            if let status = store.statusMessage { Text(status).font(.footnote).foregroundStyle(.secondary) }
        }
        .navigationTitle("Security")
        .navigationBarTitleDisplayMode(.inline)
        .task { if !store.mfaIsEnabled { isSettingUp = false } }
    }
}

struct MFASettingsSheet: View {
    var body: some View {
        NavigationStack {
            SecuritySettingsView()
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Done") { }
                    }
                }
        }
        .presentationDetents([.medium, .large])
    }
}

struct SettingsPrivacyView: View {
    var body: some View {
        List {
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
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    } icon: {
                        Image(systemName: "person.2")
                    }
                }
            }
        }
        .navigationTitle("Settings & Privacy")
        .navigationBarTitleDisplayMode(.inline)
    }
}
"""
sheets = sheets[:start] + new_security
sheets_path.write_text(sheets)

# Remove infrastructure status from normal app screens.
content = replace_once(
    content,
    """                Text(store.session == nil
                     ? "Sign in to your Carbyne account. Messaging will appear here when the chat service is connected."
                     : "Your Carbyne account is connected. Messaging is not yet available in the current backend.")""",
    """                Text(store.session == nil
                     ? "Sign in to get started."
                     : "Messaging is coming soon.")""",
    "chat empty-state copy"
)
content = replace_once(
    content,
    "The connected Supabase project has one image-only avatars bucket (5 MB per file). The existing website uses it for profile pictures and channel banners. Video upload is not configured on this backend.",
    "Choose a new profile picture or channel banner. Video uploads aren't available yet.",
    "upload description"
)

# Put account switching and Settings & Privacy controls directly on the banner.
start = content.index("struct ChannelScreen: View {")
end = content.index("\nstruct PublicChannelScreen: View {", start)
channel = content[start:end]
channel = replace_once(
    channel,
    """    @State private var selectedSection = "Home"

    var body: some View {
        Group {""",
    """    @State private var selectedSection = "Home"
    @State private var showSettings = false

    var body: some View {
        NavigationStack {
            Group {""",
    "profile navigation stack"
)
channel = replace_once(
    channel,
    """                        ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))

                        HStack(alignment: .top, spacing: 12) {""",
    """                        ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))
                            .overlay(alignment: .top) {
                                HStack {
                                    Button(action: openAccounts) {
                                        Image(systemName: "ellipsis")
                                            .font(.system(size: 17, weight: .semibold))
                                            .frame(width: 40, height: 40)
                                            .background {
                                                if #available(iOS 26.0, *) {
                                                    Circle().fill(.clear).glassEffect(.regular.interactive(), in: Circle())
                                                } else {
                                                    Circle().fill(.ultraThinMaterial)
                                                        .overlay(Circle().strokeBorder(Color.primary.opacity(0.12)))
                                                }
                                            }
                                    }
                                    .buttonStyle(.plain)
                                    .accessibilityLabel("Switch account")

                                    Spacer()

                                    Button { showSettings = true } label: {
                                        Image(systemName: "gearshape")
                                            .font(.system(size: 17, weight: .semibold))
                                            .frame(width: 40, height: 40)
                                            .background {
                                                if #available(iOS 26.0, *) {
                                                    Circle().fill(.clear).glassEffect(.regular.interactive(), in: Circle())
                                                } else {
                                                    Circle().fill(.ultraThinMaterial)
                                                        .overlay(Circle().strokeBorder(Color.primary.opacity(0.12)))
                                                }
                                            }
                                    }
                                    .buttonStyle(.plain)
                                    .accessibilityLabel("Settings & Privacy")
                                }
                                .padding(.horizontal, 16)
                                .padding(.top, 54)
                            }

                        HStack(alignment: .top, spacing: 12) {""",
    "profile banner action buttons"
)
old_button = """                            Button(action: openAccounts) {
                                Image(systemName: "ellipsis")
                                    .font(.system(size: 17, weight: .semibold))
                                    .frame(width: 40, height: 40)
                                    .contentShape(Circle())
                                    .background {
                                        if #available(iOS 26.0, *) {
                                            Circle().fill(.clear).glassEffect(.regular.interactive(), in: Circle())
                                        } else {
                                            Circle().fill(.ultraThinMaterial)
                                        }
                                    }
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("Switch account")"""
channel = replace_once(channel, old_button, "", "remove old account button position")
channel = replace_once(
    channel,
    """        }
        .toolbar(.hidden, for: .navigationBar)
    }
}""",
    """            }
            .navigationDestination(isPresented: $showSettings) {
                SettingsPrivacyView()
            }
            .toolbar(.hidden, for: .navigationBar)
        }
    }
}""",
    "profile settings navigation destination"
)
content = content[:start] + channel + content[end:]
content_path.write_text(content)

print("Replaced infrastructure copy, moved account switching onto the banner, and added native Settings & Privacy navigation.")
