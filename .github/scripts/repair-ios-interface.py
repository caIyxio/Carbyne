from pathlib import Path
import re

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
s = content_path.read_text()

start = s.index("struct ContentView: View {")
end = s.index("struct UploadScreen: View {", start)
replacement = r'''struct ContentView: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\.horizontalSizeClass) private var sizeClass
    @State private var selectedTab: CarbyneTab = .home
    @State private var showDirectory = false
    @State private var showAuth = false
    @State private var showProfileEditor = false
    @State private var showSecurity = false
    @State private var showAlert = false

    private var isPad: Bool { sizeClass == .regular }

    var body: some View {
        Group {
            if isPad {
                VStack(spacing: 0) {
                    iPadNavigation
                    selectedScreen
                }
            } else {
                TabView(selection: $selectedTab) {
                    HomeScreen(showDirectory: $showDirectory, selectChannel: openChannel)
                        .tabItem { Label("Home", systemImage: "house.fill") }
                        .tag(CarbyneTab.home)

                    ContentUnavailableView("Moments", systemImage: "circle.fill",
                        description: Text("Moments will appear here."))
                        .tabItem { Label("Moments", systemImage: "circle.fill") }
                        .tag(CarbyneTab.moments)

                    UploadScreen(openAuth: { showAuth = true })
                        .tabItem { Label("Upload", systemImage: "triangle.fill") }
                        .tag(CarbyneTab.upload)

                    MessagesScreen(openAuth: { showAuth = true })
                        .tabItem { Label("Chat", systemImage: "gearshape.fill") }
                        .tag(CarbyneTab.messages)

                    ChannelScreen(openAuth: { showAuth = true },
                                  openEditor: { showProfileEditor = true },
                                  openSecurity: { showSecurity = true })
                        .tabItem {
                            AvatarView(url: store.publicImageURL(path: store.profile?.avatarPath), size: 25)
                            Text("Profile")
                        }
                        .tag(CarbyneTab.channel)
                }
                .modifier(NativeLiquidGlassTabBar())
            }
        }
        .background(Color(uiColor: .systemBackground).ignoresSafeArea())
        .sheet(isPresented: $showAuth) { AuthenticationSheet() }
        .sheet(isPresented: $showProfileEditor) { ProfileEditorSheet() }
        .sheet(isPresented: $showSecurity) { MFASettingsSheet() }
        .sheet(isPresented: $showDirectory) { ChannelDirectorySheet(selectChannel: openChannel) }
        .onChange(of: store.errorMessage) { _, value in showAlert = value != nil }
        .alert("Carbyne", isPresented: $showAlert) {
            Button("OK") { store.errorMessage = nil }
        } message: {
            Text(store.errorMessage ?? "Something went wrong.")
        }
    }

    @ViewBuilder
    private var selectedScreen: some View {
        switch selectedTab {
        case .home: HomeScreen(showDirectory: $showDirectory, selectChannel: openChannel)
        case .moments:
            ContentUnavailableView("Moments", systemImage: "circle.fill",
                                   description: Text("Moments will appear here."))
        case .upload: UploadScreen(openAuth: { showAuth = true })
        case .messages: MessagesScreen(openAuth: { showAuth = true })
        case .channel:
            ChannelScreen(openAuth: { showAuth = true },
                          openEditor: { showProfileEditor = true },
                          openSecurity: { showSecurity = true })
        }
    }

    private var iPadNavigation: some View {
        HStack(spacing: 20) {
            Text("Carbyne")
                .font(.system(size: 29, weight: .semibold, design: .rounded))
                .tracking(-1.1)
            Spacer(minLength: 16)
            HStack(spacing: 4) {
                iPadTab("Home", .home, icon: "house.fill")
                iPadTab("Moments", .moments, icon: "circle.fill")
                iPadTab("Upload", .upload, icon: "triangle.fill")
                iPadTab("Chat", .messages, icon: "gearshape.fill")
                Button {
                    openOwnProfile()
                } label: {
                    AvatarView(url: store.publicImageURL(path: store.profile?.avatarPath), size: 29)
                        .padding(.horizontal, 10).padding(.vertical, 7)
                        .background(selectedTab == .channel ? Color.primary.opacity(0.08) : .clear, in: Capsule())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Profile")
            }
            .padding(5)
            .background(.ultraThinMaterial, in: Capsule())
            .overlay(Capsule().strokeBorder(Color.primary.opacity(0.08)))
            Button { showDirectory = true } label: {
                Image(systemName: "magnifyingglass").font(.system(size: 19))
                    .frame(width: 42, height: 42)
                    .background(.thinMaterial, in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Search")
        }
        .padding(.horizontal, 32)
        .padding(.vertical, 12)
    }

    private func iPadTab(_ title: String, _ tab: CarbyneTab, icon: String) -> some View {
        Button {
            selectedTab = tab
            if tab == .home { Task { await store.loadChannels() } }
        } label: {
            Label(title, systemImage: icon)
                .font(.system(size: 13, weight: selectedTab == tab ? .semibold : .regular))
                .foregroundStyle(selectedTab == tab ? Color.accentColor : Color.primary)
                .padding(.horizontal, 11).padding(.vertical, 9)
                .background(selectedTab == tab ? Color.primary.opacity(0.08) : .clear, in: Capsule())
        }
        .buttonStyle(.plain)
    }

    private func openOwnProfile() {
        guard store.session != nil else { showAuth = true; return }
        Task {
            await store.showOwnChannel()
            selectedTab = .channel
        }
    }

    private func openChannel(_ profile: CarbyneProfile) {
        Task {
            await store.viewChannel(profile)
            selectedTab = .channel
        }
    }
}

private struct NativeLiquidGlassTabBar: ViewModifier {
    func body(content: Content) -> some View {
        if #available(iOS 26.0, *) {
            content.tabBarMinimizeBehavior(.never)
        } else {
            content
        }
    }
}

struct HomeScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\.horizontalSizeClass) private var sizeClass
    @Binding var showDirectory: Bool
    let selectChannel: (CarbyneProfile) -> Void
    private var isPad: Bool { sizeClass == .regular }
    private let cards = [
        ("I asked 7 AIs to remake Mario Kart and…", "2M Views", "Habib"),
        ("BIG ROBLOX NEWS!!", "8M Views", "KreekCraft")
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                HStack {
                    Text("Carbyne")
                        .font(.system(size: isPad ? 36 : 34, weight: .semibold, design: .rounded))
                        .tracking(-1.3)
                    Spacer()
                    Button { showDirectory = true } label: {
                        Image(systemName: "magnifyingglass")
                            .font(.system(size: 19, weight: .medium))
                            .frame(width: 46, height: 46)
                            .background(.thinMaterial, in: Circle())
                            .overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Search")
                }

                LazyVGrid(columns: isPad
                    ? [GridItem(.flexible()), GridItem(.flexible())]
                    : [GridItem(.flexible())], spacing: 28) {
                    ForEach(cards, id: \.0) { card in
                        VStack(alignment: .leading, spacing: 9) {
                            RoundedRectangle(cornerRadius: 24)
                                .fill(Color(uiColor: .systemGray5))
                                .aspectRatio(16/9, contentMode: .fit)
                            HStack(spacing: 12) {
                                Circle().fill(Color(uiColor: .systemGray4))
                                    .frame(width: isPad ? 38 : 58, height: isPad ? 38 : 58)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(card.0).font(.system(size: isPad ? 14 : 17, weight: .semibold)).lineLimit(1)
                                    Text(card.1).foregroundStyle(.secondary)
                                    Text(card.2).foregroundStyle(.tertiary)
                                }
                                .font(.system(size: isPad ? 12 : 14))
                                Spacer(minLength: 0)
                            }
                        }
                    }
                }

                if !store.channels.isEmpty {
                    Text("Channels").font(.system(size: 21, weight: .semibold))
                    ForEach(store.channels) { channel in
                        Button { selectChannel(channel) } label: {
                            ChannelRow(profile: channel, imageURL: store.publicImageURL(path: channel.avatarPath))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .padding(.horizontal, isPad ? 34 : 20)
            .padding(.top, 12)
            .padding(.bottom, 30)
            .frame(maxWidth: 1200)
            .frame(maxWidth: .infinity)
        }
        .task { await store.loadChannels() }
        .refreshable { await store.loadChannels() }
    }
}

struct MessagesScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void

    var body: some View {
        NavigationStack {
            ContentUnavailableView {
                Label("Chat is coming soon", systemImage: "bubble.left.and.bubble.right")
            } description: {
                Text(store.session == nil
                     ? "Sign in to your Carbyne account. Messaging will appear here when the chat service is connected."
                     : "Your Carbyne account is connected. Messaging is not yet available in the current backend.")
            } actions: {
                if store.session == nil {
                    Button("Log in", action: openAuth).buttonStyle(.borderedProminent)
                }
            }
            .navigationTitle("Chat")
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

'''
s = s[:start] + replacement + s[end:]

# Rebuild the channel screen to match the supplied channel screenshot.
start = s.index("struct ChannelScreen: View {")
end = s.index("struct ChannelDirectorySheet: View {", start)
channel = r'''struct ChannelScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void
    let openEditor: () -> Void
    let openSecurity: () -> Void
    @State private var selectedSection = "Home"
    @State private var showMenu = false

    private var channel: CarbyneProfile? { store.viewedProfile ?? store.profile }
    private var isOwnChannel: Bool { channel?.id == store.session?.user.id }

    var body: some View {
        Group {
            if let channel {
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        HStack {
                            Spacer()
                            Text(isOwnChannel ? "Your Channel" : channel.title)
                                .font(.system(size: 17, weight: .semibold))
                            Spacer()
                            Menu {
                                if isOwnChannel {
                                    Button("Edit profile", systemImage: "pencil", action: openEditor)
                                    Button("Security / 2FA", systemImage: "lock.shield", action: openSecurity)
                                }
                                Button("Switch account", systemImage: "person.2") { showMenu = true }
                                if store.session != nil {
                                    Button("Sign out", systemImage: "rectangle.portrait.and.arrow.right", role: .destructive) {
                                        Task { await store.signOut() }
                                    }
                                }
                            } label: {
                                Image(systemName: "ellipsis.circle")
                                    .font(.system(size: 25))
                                    .frame(width: 44, height: 44)
                                    .contentShape(Circle())
                            }
                        }
                        .padding(.horizontal, 18)
                        .padding(.vertical, 8)

                        AsyncImage(url: store.publicImageURL(path: channel.bannerPath)) { phase in
                            if let image = phase.image { image.resizable().scaledToFill() }
                            else { Rectangle().fill(Color(uiColor: .secondarySystemBackground)) }
                        }
                        .frame(maxWidth: .infinity)
                        .frame(height: 266)
                        .clipped()

                        HStack(alignment: .center, spacing: 18) {
                            AvatarView(url: store.publicImageURL(path: channel.avatarPath), size: 145)
                            VStack(alignment: .leading, spacing: 6) {
                                Text(channel.title)
                                    .font(.system(size: 27, weight: .semibold))
                                Text("@\(channel.username ?? "unknown")")
                                    .font(.system(size: 18))
                                    .foregroundStyle(.secondary)
                                Text("\(store.subscriberCount) \(store.subscriberCount == 1 ? "subscriber" : "subscribers")")
                                    .font(.system(size: 16))
                                    .foregroundStyle(.secondary)
                                if !isOwnChannel {
                                    Button(store.isSubscribed ? "Subscribed" : "Subscribe") {
                                        Task { await store.toggleSubscription() }
                                    }
                                    .font(.system(size: 13, weight: .semibold))
                                    .buttonStyle(.borderedProminent)
                                    .tint(store.isSubscribed ? Color(uiColor: .systemGray4) : .black)
                                }
                            }
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 18)
                        .padding(.top, 28)
                        .padding(.bottom, 14)

                        HStack(spacing: 0) {
                            ForEach(["Home", "Posts", "About"], id: \.self) { name in
                                Button { selectedSection = name } label: {
                                    Text(name)
                                        .font(.system(size: 17, weight: selectedSection == name ? .semibold : .regular))
                                        .foregroundStyle(selectedSection == name ? .primary : .secondary)
                                        .frame(maxWidth: .infinity)
                                        .padding(.vertical, 14)
                                        .overlay(alignment: .bottom) {
                                            if selectedSection == name {
                                                Rectangle().fill(Color.primary).frame(height: 2)
                                            }
                                        }
                                }
                                .buttonStyle(.plain)
                            }
                        }
                        .overlay(alignment: .bottom) {
                            Rectangle().fill(Color(uiColor: .separator)).frame(height: 0.5)
                        }

                        Group {
                            switch selectedSection {
                            case "Posts":
                                ContentUnavailableView("No posts yet", systemImage: "play.rectangle",
                                    description: Text("This channel has no published posts in Carbyne yet."))
                            case "About":
                                VStack(alignment: .leading, spacing: 10) {
                                    Text("Name: \(channel.title)")
                                    Text("Username: @\(channel.username ?? "unknown")")
                                }
                                .font(.system(size: 14))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(20)
                            default:
                                Text("Welcome to \(channel.title)’s channel.")
                                    .font(.system(size: 17))
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(20)
                            }
                        }
                        .frame(minHeight: 180, alignment: .topLeading)
                    }
                }
                .ignoresSafeArea(edges: .horizontal)
            } else {
                ContentUnavailableView("Your channel", systemImage: "person.crop.square",
                    description: Text("Sign in to view your channel or browse channels from Home."))
                Button("Log in", action: openAuth).buttonStyle(.borderedProminent)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .task(id: channel?.id) {
            if let channel { await store.refreshSubscription(for: channel) }
        }
        .sheet(isPresented: $showMenu) { AccountSwitcherSheet() }
    }
}

'''
s = s[:start] + channel + s[end:]
content_path.write_text(s)

# Make profile writes explicit, keyed by auth user ID, and refresh all local copies.
models_path = root / "CarbyneModels.swift"
models = models_path.read_text()
models = re.sub(
    r"struct ProfileUpdate: Encodable \{.*?^\}",
    '''struct ProfileUpdate: Encodable {
    let id: UUID
    let displayName: String
    let username: String
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id, username
        case displayName = "display_name"
        case updatedAt = "updated_at"
    }
}''',
    models, count=1, flags=re.S | re.M
)
models = models.replace("case home, messages, upload, channel", "case home, moments, messages, upload, channel")
models_path.write_text(models)

store_path = root / "CarbyneStore.swift"
store = store_path.read_text()
old = '''        try await supabase.from("profiles").update(ProfileUpdate(
            displayName: cleanName, username: cleanUsername, updatedAt: ISO8601DateFormatter().string(from: Date())
        )).eq("id", value: userID.uuidString).execute()
        try await refreshProfile()'''
new = '''        let update = ProfileUpdate(
            id: userID,
            displayName: cleanName,
            username: cleanUsername,
            updatedAt: ISO8601DateFormatter().string(from: Date())
        )
        try await supabase.from("profiles")
            .upsert(update, onConflict: "id")
            .execute()
        try await refreshProfile()
        if let refreshed = profile {
            viewedProfile = refreshed
            channels = channels.map { $0.id == refreshed.id ? refreshed : $0 }
            statusMessage = "Profile updated."
        } else {
            throw NSError(domain: "Carbyne", code: 404,
                          userInfo: [NSLocalizedDescriptionKey: "The profile save completed, but the updated profile could not be read back. Check the profiles table permissions and row-level security policies."])
        }'''
if old not in store:
    raise SystemExit("Could not find the existing saveProfile update block.")
store = store.replace(old, new, 1)
store_path.write_text(store)

# Load current profile before presenting the editor; report errors inline and keep the sheet open on failure.
sheet_path = root / "AccountSheets.swift"
sheets = sheet_path.read_text()
sheets = sheets.replace('''                    TextField("Display name", text: $displayName)
                        .textContentType(.name)
                        .onAppear { displayName = store.profile?.displayName ?? "" }
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .onAppear { username = store.profile?.username ?? "" }''','''                    TextField("Display name", text: $displayName)
                        .textContentType(.name)
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()''')
sheets = sheets.replace('''                if let message { Text(message).font(.footnote).foregroundStyle(.secondary) }''','''                if let message { Text(message).font(.footnote).foregroundStyle(.red) }''',1)
sheets = sheets.replace('''        }
    }
}

struct AccountSwitcherSheet: View {''','''        }
        .task {
            do {
                try await store.refreshProfile()
                displayName = store.profile?.displayName ?? ""
                username = store.profile?.username ?? ""
            } catch {
                message = error.localizedDescription
            }
        }
    }
}

struct AccountSwitcherSheet: View {''',1)
sheet_path.write_text(sheets)

print("Rebuilt native tab navigation, scrolling Home header, screenshot-matched channel layout, and profile persistence.")
