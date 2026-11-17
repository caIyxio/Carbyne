from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
store_path = root / "CarbyneStore.swift"
models_path = root / "CarbyneModels.swift"
tabs_path = root / "CarbyneNativeTabController.swift"

s = content_path.read_text()

# Profile header: one set of banner controls, username restored, and real share action.
s = s.replace('''    @State private var selectedSection = "Posts"
    @State private var showSettings = false''',
              '''    @State private var selectedSection = "Home"
    @State private var showSettings = false''', 1)

start = s.index('''                            ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))''', s.index("struct ChannelScreen: View"))
end = s.index('''                            HStack(alignment: .center, spacing: 18) {''', start)
banner = '''                            ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))
                                .overlay(alignment: .top) {
                                    HStack {
                                        Button(action: openAccounts) {
                                            Image(systemName: "ellipsis")
                                                .font(.system(size: 17, weight: .semibold))
                                                .frame(width: 40, height: 40)
                                                .background(.ultraThinMaterial, in: Circle())
                                        }
                                        .buttonStyle(.plain)
                                        .accessibilityLabel("Switch account")
                                        Spacer()
                                        Button { showSettings = true } label: {
                                            Image(systemName: "gearshape")
                                                .font(.system(size: 17, weight: .semibold))
                                                .frame(width: 40, height: 40)
                                                .background(.ultraThinMaterial, in: Circle())
                                        }
                                        .buttonStyle(.plain)
                                        .accessibilityLabel("Settings & Privacy")
                                        Button { showEditProfile = true } label: {
                                            Image(systemName: "pencil")
                                                .font(.system(size: 17, weight: .semibold))
                                                .frame(width: 40, height: 40)
                                                .background(.ultraThinMaterial, in: Circle())
                                        }
                                        .buttonStyle(.plain)
                                        .accessibilityLabel("Edit profile")
                                    }
                                    .padding(.horizontal, 16)
                                    .padding(.top, 54)
                                }
'''
s = s[:start] + banner + s[end:]

# Remove the duplicate title/action row that used to add a second settings/menu pair.
old = '''                            HStack(spacing: 12) {
                                Text(profile.username ?? profile.title)
                                    .font(.system(size: 21, weight: .bold))
                                    .lineLimit(1)
                                Spacer(minLength: 4)
                                Button(action: openAccounts) {
                                    Image(systemName: "ellipsis")
                                        .font(.system(size: 20, weight: .semibold))
                                        .frame(width: 40, height: 40)
                                }
                                .accessibilityLabel("Switch account")
                                Button { showSettings = true } label: {
                                    Image(systemName: "line.3.horizontal")
                                        .font(.system(size: 21, weight: .semibold))
                                        .frame(width: 40, height: 40)
                                }
                                .accessibilityLabel("Settings")
                            }
                            .padding(.horizontal, 16)
                            .padding(.top, 8)

'''
s = s.replace(old, "", 1)

# Identity block uses display name and @username, with compact alignment beside the overlapping avatar.
s = s.replace('''                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                        .font(.system(size: 17, weight: .semibold))
                                        .lineLimit(2)
                                    HStack(spacing: 0) {
                                        profileMetric("0", label: "posts")
                                        Spacer(minLength: 8)
                                        profileMetric("\\(store.subscriberCount)", label: "subscribers")
                                    }
                                }''',
'''                                VStack(alignment: .leading, spacing: 5) {
                                    Text(profile.title)
                                        .font(.system(size: 18, weight: .semibold))
                                        .lineLimit(2)
                                    Text("@\\(profile.username ?? "unknown")")
                                        .font(.system(size: 13))
                                        .foregroundStyle(.secondary)
                                    HStack(spacing: 0) {
                                        profileMetric("0", label: "posts")
                                        Spacer(minLength: 8)
                                        profileMetric("\\(store.subscriberCounts[profile.id] ?? 0)", label: "subscribers")
                                    }
                                    .padding(.top, 4)
                                }''', 1)
s = s.replace('''.padding(.horizontal, 16)
                            .padding(.top, 0)

                            if let bio''',
              '''.padding(.horizontal, 16)
                            .padding(.top, -2)

                            if let bio''', 1)

# Distinguish sharing from account switching.
old = '''                                Button(action: openAccounts) {
                                    Text("Share profile")
                                        .font(.system(size: 14, weight: .semibold))
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 36)
                                        .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 9))
                                }'''
new = '''                                ShareLink(item: "Check out \\(profile.title) on Carbyne — @\\(profile.username ?? "unknown")") {
                                    Text("Share profile")
                                        .font(.system(size: 14, weight: .semibold))
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 36)
                                        .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 9))
                                }'''
s = s.replace(old, new, 1)

# The own profile no longer has a dedicated empty Posts/No Posts Yet tab.
s = s.replace('''                                case "Posts":
                                    ContentUnavailableView("No posts yet", systemImage: "square.grid.3x3",
                                        description: Text("Your posts will appear here."))
''', "", 1)
s = s.replace('''        ForEach(["Posts", "Home", "About"], id: \\.self) { item in''',
              '''        ForEach(["Home", "About"], id: \\.self) { item in''', 1)
s = s.replace('''                    Image(systemName: item == "Posts" ? "square.grid.3x3" : (item == "Home" ? "house" : "person.crop.square"))''',
              '''                    Image(systemName: item == "Home" ? "house" : "person.crop.square")''', 1)

# Public profile tab labels and username identity; route Message to Chat tab instead of a sheet.
s = s.replace('''    let profile: CarbyneProfile
    @State private var selectedSection = "Posts"
    @State private var showMessages = false''',
              '''    let profile: CarbyneProfile
    let openMessages: () -> Void
    @State private var selectedSection = "Home"''', 1)
s = s.replace('''                        VStack(alignment: .leading, spacing: 8) {
                            Text(profile.title)
                                .font(.system(size: 17, weight: .semibold))
                                .lineLimit(2)
                            HStack(spacing: 0) {''',
'''                        VStack(alignment: .leading, spacing: 5) {
                            Text(profile.title)
                                .font(.system(size: 18, weight: .semibold))
                                .lineLimit(2)
                            Text("@\\(profile.username ?? "unknown")")
                                .font(.system(size: 13))
                                .foregroundStyle(.secondary)
                            HStack(spacing: 0) {''', 1)
s = s.replace('''                                    Text("\\(store.subscriberCount)").font(.system(size: 17, weight: .semibold))''',
              '''                                    Text("\\(store.subscriberCounts[profile.id] ?? 0)").font(.system(size: 17, weight: .semibold))''', 1)
s = s.replace('''                    .padding(.top, 0)

                    if let bio''',
              '''                    .padding(.top, -2)

                    if let bio''', 1)
s = s.replace('''                        Button { showMessages = true } label: {''',
              '''                        Button(action: openMessages) {''', 1)
s = s.replace('''                        case "Posts":
                            ContentUnavailableView("No posts yet", systemImage: "square.grid.3x3",
                                description: Text("This creator hasn't published any posts yet."))
''', "", 1)
s = s.replace('''        .sheet(isPresented: $showMessages) {
            NavigationStack { ChatThreadScreen(profile: profile) }
        }
''', "", 1)

# Give the Home feed breathing room below its safe-area header and refresh own count there.
s = s.replace('''.padding(.top, 8)
            .padding(.bottom, 30)''',
              '''.padding(.top, 26)
            .padding(.bottom, 30)''', 1)
s = s.replace('''        .task { await store.loadChannels() }
        .refreshable { await store.loadChannels() }''',
'''        .task {
            await store.loadChannels()
            if let ownProfile = store.profile {
                await store.refreshSubscription(for: ownProfile)
            }
        }
        .refreshable {
            await store.loadChannels()
            if let ownProfile = store.profile {
                await store.refreshSubscription(for: ownProfile)
            }
        }''', 1)

# Edit Profile username availability: debounced, server-checked, and visibly outlined.
s = s.replace('''    @State private var isApplying = false
    @State private var errorText: String?''',
'''    @State private var isApplying = false
    @State private var usernameAvailable: Bool?
    @State private var isCheckingUsername = false
    @State private var errorText: String?''', 1)
old = '''                        TextField("username", text: $username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .padding(13)
                            .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 12))
                        Text("Usernames can only be changed once every 14 days.")
                            .font(.caption)
                            .foregroundStyle(.secondary)'''
new = '''                        TextField("username", text: $username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .foregroundStyle(.primary)
                            .tint(.accentColor)
                            .padding(13)
                            .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 12))
                            .overlay {
                                RoundedRectangle(cornerRadius: 12)
                                    .stroke(usernameAvailable == true ? Color.green : (usernameAvailable == false ? Color.red : CarbynePalette.divider), lineWidth: 1)
                            }
                        Group {
                            if isCheckingUsername {
                                Label("Checking username…", systemImage: "clock")
                                    .foregroundStyle(.secondary)
                            } else if let usernameAvailable {
                                Label(usernameAvailable ? "Username available" : "Username is already taken",
                                      systemImage: usernameAvailable ? "checkmark.circle.fill" : "xmark.circle.fill")
                                    .foregroundStyle(usernameAvailable ? .green : .red)
                            } else {
                                Text("3–32 characters · Letters, numbers, and underscores")
                                    .foregroundStyle(.secondary)
                            }
                        }
                        .font(.caption)
                        Text("Usernames can only be changed once every 14 days.")
                            .font(.caption)
                            .foregroundStyle(.secondary)'''
if old not in s: raise SystemExit("Edit username field block not found")
s = s.replace(old, new, 1)

# TextEditor and all editable fields explicitly inherit the selected text color.
s = s.replace('''                        TextField("Display name", text: $displayName)
                            .textInputAutocapitalization(.words)''',
'''                        TextField("Display name", text: $displayName)
                            .textInputAutocapitalization(.words)
                            .foregroundStyle(.primary)
                            .tint(.accentColor)''', 1)
s = s.replace('''                        TextEditor(text: $bio)
                            .frame(minHeight: 100)
                            .padding(6)
                            .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 12))''',
'''                        TextEditor(text: $bio)
                            .scrollContentBackground(.hidden)
                            .foregroundStyle(.primary)
                            .tint(.accentColor)
                            .frame(minHeight: 100)
                            .padding(6)
                            .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 12))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(CarbynePalette.divider, lineWidth: 1))''', 1)

# Async username availability check, keyed to the current field value to avoid stale responses.
needle = '''        .task {
            displayName = store.profile?.displayName ?? ""
            username = store.profile?.username ?? ""
            bio = store.profile?.bio ?? ""
        }'''
replacement = needle + '''
        .task(id: username) {
            let candidate = username.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            usernameAvailable = nil
            guard candidate != (store.profile?.username ?? "").lowercased(),
                  candidate.range(of: "^[A-Za-z0-9_]{3,32}$", options: .regularExpression) != nil else {
                if candidate == (store.profile?.username ?? "").lowercased() { usernameAvailable = true }
                return
            }
            isCheckingUsername = true
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled else { return }
            usernameAvailable = try? await store.checkUsernameAvailability(candidate)
            isCheckingUsername = false
        }'''
if needle not in s: raise SystemExit("Edit profile initialization task not found")
s = s.replace(needle, replacement, 1)

# Availability indicator is advisory; saveProfile remains the authoritative unique constraint.
content_path.write_text(s)

# Store subscriber totals per channel ID, rather than one global count reused for every profile.
st = store_path.read_text()
st = st.replace('''    @Published private(set) var subscriberCount = 0
    @Published private(set) var isSubscribed = false''',
'''    @Published private(set) var subscriberCount = 0
    @Published private(set) var subscriberCounts: [UUID: Int] = [:]
    @Published private(set) var isSubscribed = false''', 1)
st = st.replace('''            subscriberCount = records.count
            isSubscribed = records.contains { $0.subscriberID == session?.user.id }''',
'''            let count = records.count
            subscriberCounts[channel.id] = count
            if viewedProfile?.id == channel.id { subscriberCount = count }
            isSubscribed = records.contains { $0.subscriberID == session?.user.id }''', 1)
# A lightweight, RLS-respecting availability lookup. Never exposes other profile data.
st += '''

private struct UsernameIDRecord: Decodable {
    let id: UUID
}

extension CarbyneStore {
    func checkUsernameAvailability(_ username: String) async throws -> Bool {
        guard let userID = session?.user.id else { return false }
        if username.lowercased() == (profile?.username ?? "").lowercased() { return true }
        let matches: [UsernameIDRecord] = try await supabase.from("profiles")
            .select("id")
            .eq("username", value: username.lowercased())
            .neq("id", value: userID.uuidString)
            .limit(1)
            .execute().value
        return matches.isEmpty
    }
}
'''
store_path.write_text(st)

# Public profile navigation callback: switch to the actual Chat tab and clear the profile push.
tabs = tabs_path.read_text()
tabs = tabs.replace('''                                PublicChannelScreen(profile: profile)''',
'''                                PublicChannelScreen(profile: profile, openMessages: {
                                    navigationPath.removeAll()
                                    selection = .messages
                                })''')
tabs = tabs.replace('''                                PublicChannelScreen(profile: profile)''',
'''                                PublicChannelScreen(profile: profile, openMessages: {
                                    navigationPath.removeAll()
                                    selection = .messages
                                })''')
tabs_path.write_text(tabs)

# The iPad NavigationStack has its own destination builder.
s = content_path.read_text()
s = s.replace('''                            PublicChannelScreen(profile: profile)''',
'''                            PublicChannelScreen(profile: profile, openMessages: {
                                navigationPath.removeAll()
                                selectedTab = .messages
                            })''', 1)
content_path.write_text(s)

print("Fixed profile identity/actions, subscriber counts, username availability, editor colors, Home spacing, and Chat-tab navigation.")


# Keep the thread's existing profile shortcut valid; it is already inside Chat.
s = content_path.read_text()
s = s.replace('''                    PublicChannelScreen(profile: profile)
                } label: {''',
              '''                    PublicChannelScreen(profile: profile, openMessages: {})
                } label: {''', 1)
s = s.replace('''.accessibilityLabel("Open \\\\(profile.title)'s profile")''',
              '''.accessibilityLabel("Open profile")''', 1)
content_path.write_text(s)

# The alternate profile editor sheet uses the same theme-safe input treatment.
account_path = root / "AccountSheets.swift"
a = account_path.read_text()
a = a.replace('''                    TextField("Display name", text: $displayName)
                        .textContentType(.name)''',
'''                    TextField("Display name", text: $displayName)
                        .textContentType(.name)
                        .foregroundStyle(.primary)
                        .tint(.accentColor)''', 1)
a = a.replace('''                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()''',
'''                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .foregroundStyle(.primary)
                        .tint(.accentColor)''', 1)
a = a.replace('''                    TextEditor(text: $bio)
                        .frame(minHeight: 90)''',
'''                    TextEditor(text: $bio)
                        .scrollContentBackground(.hidden)
                        .foregroundStyle(.primary)
                        .tint(.accentColor)
                        .frame(minHeight: 90)
                        .padding(6)
                        .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 12))
                        .overlay(RoundedRectangle(cornerRadius: 12).stroke(CarbynePalette.divider, lineWidth: 1))''', 1)
account_path.write_text(a)
print("Simplified chat profile accessibility expression and applied theme-safe editor styling to both edit flows.")
