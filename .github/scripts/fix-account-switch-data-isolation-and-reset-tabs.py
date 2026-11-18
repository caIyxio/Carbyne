from pathlib import Path

root = Path("ios/Carbyne/Sources")
store_path = root / "CarbyneStore.swift"
sheets_path = root / "AccountSheets.swift"
content_path = root / "ContentView.swift"

store = store_path.read_text()
sheets = sheets_path.read_text()
content = content_path.read_text()

def replace_once(source, old, new, label):
    if new in source:
        return source
    if old not in source:
        raise SystemExit(f"PATCH ANCHOR NOT FOUND: {label}")
    return source.replace(old, new, 1)

store = replace_once(
    store,
    """    @Published private(set) var accountProfiles: [String: CarbyneProfile] = [:]
    @Published private(set) var conversations:""",
    """    @Published private(set) var accountProfiles: [String: CarbyneProfile] = [:]
    @Published private(set) var isLoadingAccountProfiles = false
    @Published private(set) var conversations:""",
    "account list loading state"
)

start = store.index("    func refreshAccountProfiles() async {")
end = store.index("\n    private func inspectMFA()", start)
store = store[:start] + """    func refreshAccountProfiles() async {
        guard !isLoadingAccountProfiles else { return }
        isLoadingAccountProfiles = true
        defer { isLoadingAccountProfiles = false }

        var refreshed: [String: CarbyneProfile] = [:]
        for email in accounts {
            do {
                let accountClient = client(for: email)
                let accountSession = try await accountClient.auth.session
                let loaded: CarbyneProfile? = try await accountClient.from("profiles")
                    .select()
                    .eq("id", value: accountSession.user.id.uuidString)
                    .maybeSingle()
                    .execute().value
                if let loaded { refreshed[email] = loaded }
            } catch {
                // Keep unavailable accounts out of the profile cache. The saved
                // account itself remains listed so its owner can sign in again.
            }
        }
        accountProfiles = refreshed
    }

    func switchAccount(to email: String) async {
        let normalizedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard normalizedEmail != session?.user.email?.lowercased() else { return }

        isLoading = true
        isSwitchingAccount = true
        errorMessage = nil
        statusMessage = nil
        var completed = false
        defer {
            isLoading = false
            isSwitchingAccount = false
            if completed {
                UINotificationFeedbackGenerator().notificationOccurred(.success)
            }
        }

        do {
            // Validate the saved session and fetch its profile before replacing
            // any currently visible account data.
            let nextClient = client(for: normalizedEmail)
            let restored = try await nextClient.auth.session
            let nextProfile: CarbyneProfile? = try await nextClient.from("profiles")
                .select()
                .eq("id", value: restored.user.id.uuidString)
                .maybeSingle()
                .execute().value

            await stopMessagesRealtime()
            conversations = []
            messages = []
            activeChatProfile = nil
            channels = []
            viewedProfile = nil
            subscriberCount = 0
            subscriberCounts = [:]
            likeCounts = [:]
            isSubscribed = false
            knownLatestMessageIDs.removeAll()
            conversationSnapshotUserID = nil
            hasInitialConversationSnapshot = false
            loadedChannelsForUserID = nil
            pendingFactorID = nil
            pendingChallengeID = nil

            supabase = nextClient
            session = restored
            profile = nextProfile
            viewedProfile = nextProfile
            rememberAccount(normalizedEmail)

            try await inspectMFA()
            if requiresMFA {
                try await beginLoginMFAChallenge()
            } else {
                await loadChannels()
                await loadConversations()
                completed = true
            }
        } catch {
            errorMessage = "This account could not be loaded. Sign in again if its saved session has expired. \(error.localizedDescription)"
        }
    }
""" + store[end:]

sheets = replace_once(
    sheets,
    """        List {
            if store.accounts.isEmpty {""",
    """        List {
            if store.isLoadingAccountProfiles {
                HStack(spacing: 12) {
                    ProgressView()
                    Text("Loading your accounts…")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 24)
            } else if store.accounts.isEmpty {""",
    "real account loading screen"
)
sheets = replace_once(
    sheets,
    """            Section("Accounts") {
                ForEach(store.accounts, id: \\.self) { email in""",
    """            if !store.isLoadingAccountProfiles {
            Section("Accounts") {
                ForEach(store.accounts, id: \\.self) { email in""",
    "hide stale account rows while loading"
)
sheets = replace_once(
    sheets,
    """            Section {
                Button {
                    showAddAccount = true""",
    """            Section {
                Button {
                    showAddAccount = true""",
    "add account section anchor"
)
# Close the conditional after the accounts section, before the add-account section.
sheets = replace_once(
    sheets,
    """            }
            Section {
                Button {
                    showAddAccount = true""",
    """            }
            }
            Section {
                Button {
                    showAddAccount = true""",
    "close account list loading conditional"
)

content = replace_once(
    content,
    """                CarbyneNativeTabController(
                    store: store,""",
    """                CarbyneNativeTabController(
                    store: store,""",
    "native tabs identity"
)
# Attach identity to the UIKit representable so all five hosting roots are recreated on account change.
content = replace_once(
    content,
    """                    selectChannel: openChannel
                )
            }
        }""",
    """                    selectChannel: openChannel
                )
                .id(store.session?.user.id)
            }
        }""",
    "recreate all tab roots for the new account"
)
content = replace_once(
    content,
    """        .onChange(of: store.errorMessage) { _, value in showAlert = value != nil }""",
    """        .onChange(of: store.session?.user.id) { _, _ in
            selectedTab = .home
            isChatThreadOpen = false
            navigationPath.removeAll()
            showProfileEditor = false
            showSecurity = false
            showAccounts = false
        }
        .onChange(of: store.errorMessage) { _, value in showAlert = value != nil }""",
    "reset selected tab and navigation on account change"
)

store_path.write_text(store)
sheets_path.write_text(sheets)
content_path.write_text(content)
print("Account switch now loads real profile data, clears account-scoped state, and recreates every tab root.")
