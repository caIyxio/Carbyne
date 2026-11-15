from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
store_path = root / "CarbyneStore.swift"
sheets_path = root / "AccountSheets.swift"
tabs_path = root / "CarbyneNativeTabController.swift"
content = content_path.read_text()
store = store_path.read_text()
sheets = sheets_path.read_text()
tabs = tabs_path.read_text()

def replace_once(source, old, new, label):
    if old not in source:
        if new in source:
            return source
        raise SystemExit(f"Could not find {label}; refusing to patch the wrong source.")
    return source.replace(old, new, 1)

# Stretch the banner image itself during top-edge overscroll.
if "struct ProfileBannerView: View {" not in content:
    component = """struct ProfileBannerView: View {
    let url: URL?

    var body: some View {
        GeometryReader { geometry in
            let pullDistance = max(geometry.frame(in: .named("profileScroll")).minY, 0)
            AsyncImage(url: url) { phase in
                if let image = phase.image {
                    image.resizable().scaledToFill()
                } else {
                    Rectangle().fill(Color(uiColor: .secondarySystemBackground))
                }
            }
            .frame(width: geometry.size.width,
                   height: geometry.size.width / 3 + pullDistance)
            .clipped()
            .offset(y: -pullDistance)
        }
        .aspectRatio(3.0, contentMode: .fit)
    }
}

"""
    content = replace_once(content, "struct ContentView: View {", component + "struct ContentView: View {", "ContentView declaration")

own_banner = """                        AsyncImage(url: store.publicImageURL(path: profile.bannerPath)) { phase in
                            if let image = phase.image {
                                image.resizable().scaledToFill()
                            } else {
                                Rectangle().fill(Color(uiColor: .secondarySystemBackground))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .aspectRatio(3.0, contentMode: .fit)
                        .clipped()
"""
content = replace_once(content, own_banner,
    """                        ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))
""", "own profile banner")

public_banner = """                    AsyncImage(url: store.publicImageURL(path: profile.bannerPath)) { phase in
                        if let image = phase.image { image.resizable().scaledToFill() }
                        else { Rectangle().fill(Color(uiColor: .secondarySystemBackground)) }
                    }
                    .frame(maxWidth: .infinity)
                    .aspectRatio(3.0, contentMode: .fit)
                    .clipped()
"""
content = replace_once(content, public_banner,
    """                    ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))
""", "public profile banner")

start = content.index("struct ChannelScreen: View {")
end = content.index("\nstruct PublicChannelScreen: View {", start)
own = content[start:end]
own = replace_once(own, """                .background(Color.clear)
            } else {""",
    """                .background(Color.clear)
                .coordinateSpace(name: "profileScroll")
            } else {""", "own profile scroll coordinate space")
content = content[:start] + own + content[end:]

start = content.index("struct PublicChannelScreen: View {")
end = content.index("\nstruct ChannelDirectorySheet: View {", start)
public = content[start:end]
public = replace_once(public, """            .background(Color.clear)
            .ignoresSafeArea(.container, edges: .top)""",
    """            .background(Color.clear)
            .coordinateSpace(name: "profileScroll")
            .ignoresSafeArea(.container, edges: .top)""", "public profile scroll coordinate space")
content = content[:start] + public + content[end:]

# Put account management on the own-profile identity row.
content = replace_once(content,
    """    @State private var showSecurity = false
    @State private var showAlert = false""",
    """    @State private var showSecurity = false
    @State private var showAccounts = false
    @State private var showAlert = false""", "account sheet state")
content = replace_once(content,
    """                    showSecurity: { showSecurity = true },
                    selectChannel: openChannel""",
    """                    showSecurity: { showSecurity = true },
                    showAccounts: { showAccounts = true },
                    selectChannel: openChannel""", "native tab account callback")
content = replace_once(content,
    """        .sheet(isPresented: $showSecurity) { MFASettingsSheet() }
        .onChange(of: store.errorMessage)""",
    """        .sheet(isPresented: $showSecurity) { MFASettingsSheet() }
        .sheet(isPresented: $showAccounts) { AccountSwitcherSheet() }
        .onChange(of: store.errorMessage)""", "account switcher sheet presentation")
content = replace_once(content,
    """                          openSecurity: { showSecurity = true })""",
    """                          openSecurity: { showSecurity = true },
                          openAccounts: { showAccounts = true })""", "iPad ChannelScreen account callback")
content = replace_once(content,
    """    let openSecurity: () -> Void
    @State private var selectedSection = "Home" """.rstrip(),
    """    let openSecurity: () -> Void
    let openAccounts: () -> Void
    @State private var selectedSection = "Home" """.rstrip(), "ChannelScreen account callback property")
content = replace_once(content,
    """                            .padding(.top, 8)
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 16)
                        .padding(.bottom, 12)

                        HStack(spacing: 0) {""",
    """                            .padding(.top, 8)
                            Spacer(minLength: 0)
                            Button(action: openAccounts) {
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
                            .accessibilityLabel("Switch account")
                        }
                        .padding(.horizontal, 16)
                        .padding(.bottom, 12)

                        HStack(spacing: 0) {""", "own profile account switcher button")
content_path.write_text(content)

# Keep account identity data private to the device and render profile details, not emails.
store = replace_once(store,
    """    @Published private(set) var accounts: [String] = []
    @Published private(set) var subscriberCount = 0""",
    """    @Published private(set) var accounts: [String] = []
    @Published private(set) var accountProfiles: [String: CarbyneProfile] = [:]
    @Published private(set) var subscriberCount = 0""", "account profile cache")
if "func refreshAccountProfiles() async {" not in store:
    store = replace_once(store,
        """    func switchAccount(to email: String) async {
        isLoading = true""",
        """    func refreshAccountProfiles() async {
        for email in accounts {
            do {
                let accountClient = client(for: email)
                let accountSession = try await accountClient.auth.session
                let loaded: CarbyneProfile? = try await accountClient.from("profiles")
                    .select()
                    .eq("id", value: accountSession.user.id.uuidString)
                    .maybeSingle()
                    .execute().value
                if let loaded {
                    accountProfiles[email] = loaded
                } else {
                    accountProfiles.removeValue(forKey: email)
                }
            } catch {
                accountProfiles.removeValue(forKey: email)
            }
        }
    }

    func switchAccount(to email: String) async {
        isLoading = true""", "account profile refresh method")
store = replace_once(store,
    """        profile = loaded
    }

    func saveProfile""",
    """        profile = loaded
        if let email = session?.user.email?.lowercased(), let loaded {
            accountProfiles[email] = loaded
        }
    }

    func saveProfile""", "active account profile cache update")
store_path.write_text(store)

# Restore the switcher with avatar/name/username rows and an Add an account flow.
start = sheets.index("struct AccountSwitcherSheet: View {")
end = sheets.index("\nstruct MFASettingsSheet: View {", start)
new_sheet = """struct AccountSwitcherSheet: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\\.dismiss) private var dismiss
    @State private var code = ""
    @State private var showAddAccount = false

    var body: some View {
        NavigationStack {
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
                    Text("Each account keeps its own secure Supabase session on this device.")
                        .font(.caption).foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Switch account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        }
        .task { await store.refreshAccountProfiles() }
        .onChange(of: store.accounts) { _, _ in Task { await store.refreshAccountProfiles() } }
        .sheet(isPresented: $showAddAccount) { AuthenticationSheet() }
        .presentationDetents([.medium, .large])
    }
}
"""
sheets = sheets[:start] + new_sheet + sheets[end:]
sheets_path.write_text(sheets)

tabs = replace_once(tabs,
    """    let showSecurity: () -> Void
    let selectChannel: (CarbyneProfile) -> Void""",
    """    let showSecurity: () -> Void
    let showAccounts: () -> Void
    let selectChannel: (CarbyneProfile) -> Void""", "native tab account callback property")
tabs = replace_once(tabs,
    """                              openSecurity: showSecurity)
                    .environmentObject(store)""",
    """                              openSecurity: showSecurity,
                              openAccounts: showAccounts)
                    .environmentObject(store)""", "native tab ChannelScreen account callback")
tabs_path.write_text(tabs)

print("Added stretchy profile banners and restored profile-based account switching with Add an account.")
