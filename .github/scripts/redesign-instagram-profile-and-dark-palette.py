from pathlib import Path

p = Path("ios/Carbyne/Sources/ContentView.swift")
s = p.read_text()

palette = r'''
enum CarbynePalette {
    static let background = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark
            ? UIColor(red: 0.047, green: 0.055, blue: 0.063, alpha: 1)
            : .systemBackground
    })
    static let surface = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark
            ? UIColor(red: 0.145, green: 0.165, blue: 0.184, alpha: 1)
            : .secondarySystemBackground
    })
    static let divider = Color(uiColor: UIColor { traits in
        traits.userInterfaceStyle == .dark
            ? UIColor(red: 0.18, green: 0.20, blue: 0.22, alpha: 1)
            : .separator
    })
}

'''
if "enum CarbynePalette {" not in s:
    marker = "struct ContentView: View {"
    if marker not in s: raise SystemExit("ContentView declaration missing")
    s = s.replace(marker, palette + marker, 1)

# Use Instagram-like charcoal surfaces throughout the app while preserving
# the user's iOS-selected appearance (no preferredColorScheme override).
s = s.replace("Color(uiColor: .systemBackground)", "CarbynePalette.background")
s = s.replace("Color(uiColor: .secondarySystemBackground)", "CarbynePalette.surface")
s = s.replace("Color(uiColor: .separator)", "CarbynePalette.divider")
s = s.replace("Circle().fill(Color(uiColor: .systemGray5))", "Circle().fill(CarbynePalette.surface)")

# Avatar images must be laid out at their exact square size before clipping.
avatar_start = s.index("struct AvatarView: View {")
avatar_end = s.index("\n}", avatar_start) + 2
avatar = r'''struct AvatarView: View {
    let url: URL?
    let size: CGFloat

    var body: some View {
        ZStack {
            Circle().fill(CarbynePalette.surface)
            CarbyneCachedImage(url: url, isAvatar: true)
                .frame(width: size, height: size)
                .clipped()
                .clipShape(Circle())
            if url == nil {
                Image(systemName: "person.fill")
                    .font(.system(size: size * 0.42))
                    .foregroundStyle(.secondary)
            }
        }
        .frame(width: size, height: size)
        .clipShape(Circle())
        .contentShape(Circle())
        .accessibilityHidden(true)
    }
}'''
s = s[:avatar_start] + avatar + s[avatar_end:]

# Own profile: Instagram-style identity row and compact account actions.
start = s.index("struct ChannelScreen: View {")
end = s.index("\nstruct PublicChannelScreen: View {", start)
own = r'''struct ChannelScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void
    let openEditor: () -> Void
    let openSecurity: () -> Void
    let openAccounts: () -> Void
    @State private var selectedSection = "Posts"
    @State private var showSettings = false
    @State private var showEditProfile = false

    private var profile: CarbyneProfile? { store.profile }

    var body: some View {
        NavigationStack {
            Group {
                if let profile, store.session != nil {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 0) {
                            ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))
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
                            HStack(spacing: 12) {
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

                            HStack(alignment: .center, spacing: 18) {
                                AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)
                                    .overlay(Circle().stroke(CarbynePalette.background, lineWidth: 3))
                                    .padding(.leading, 2)
                                    .padding(.top, -26)
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                        .font(.system(size: 17, weight: .semibold))
                                        .lineLimit(2)
                                    HStack(spacing: 0) {
                                        profileMetric("0", label: "posts")
                                        Spacer(minLength: 8)
                                        profileMetric("\(store.subscriberCount)", label: "subscribers")
                                    }
                                }
                                Spacer(minLength: 0)
                            }
                            .padding(.horizontal, 16)
                            .padding(.top, 18)

                            if let bio = profile.bio, !bio.isEmpty {
                                Text(bio)
                                    .font(.system(size: 14))
                                    .padding(.horizontal, 16)
                                    .padding(.top, 12)
                            }

                            HStack(spacing: 8) {
                                Button { showEditProfile = true } label: {
                                    Text("Edit profile")
                                        .font(.system(size: 14, weight: .semibold))
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 36)
                                        .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 9))
                                }
                                Button(action: openAccounts) {
                                    Text("Share profile")
                                        .font(.system(size: 14, weight: .semibold))
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 36)
                                        .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 9))
                                }
                            }
                            .buttonStyle(.plain)
                            .padding(.horizontal, 16)
                            .padding(.top, 16)
                            .padding(.bottom, 16)

                            profileSectionTabs(selection: $selectedSection)

                            Group {
                                switch selectedSection {
                                case "Posts":
                                    ContentUnavailableView("No posts yet", systemImage: "square.grid.3x3",
                                        description: Text("Your posts will appear here."))
                                case "About":
                                    VStack(alignment: .leading, spacing: 8) {
                                        Text(profile.title).font(.system(size: 15, weight: .semibold))
                                        Text("@\(profile.username ?? "unknown")").foregroundStyle(.secondary)
                                        if let bio = profile.bio, !bio.isEmpty { Text(bio) }
                                        else { Text("No bio yet.").foregroundStyle(.secondary) }
                                    }
                                    .font(.system(size: 14))
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(16)
                                default:
                                    Text("Your Carbyne profile")
                                        .font(.system(size: 14))
                                        .foregroundStyle(.secondary)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .padding(16)
                                }
                            }
                            .frame(minHeight: 180, alignment: .topLeading)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .background(CarbynePalette.background)
                } else {
                    ContentUnavailableView("Your Profile", systemImage: "person.crop.circle",
                        description: Text("Sign in to view and edit your profile."))
                    Button("Log in", action: openAuth).buttonStyle(.borderedProminent)
                }
            }
            .navigationDestination(isPresented: $showSettings) { SettingsPrivacyView() }
            .navigationDestination(isPresented: $showEditProfile) { EditProfileView() }
            .toolbar(.hidden, for: .navigationBar)
        }
    }

    private func profileMetric(_ value: String, label: String) -> some View {
        VStack(spacing: 2) {
            Text(value).font(.system(size: 17, weight: .semibold))
            Text(label).font(.system(size: 12)).foregroundStyle(.secondary)
        }
        .frame(minWidth: 58)
    }
}

private func profileSectionTabs(selection: Binding<String>) -> some View {
    HStack(spacing: 0) {
        ForEach(["Posts", "Home", "About"], id: \.self) { item in
            Button { selection.wrappedValue = item } label: {
                VStack(spacing: 10) {
                    Image(systemName: item == "Posts" ? "square.grid.3x3" : (item == "Home" ? "house" : "person.crop.square"))
                        .font(.system(size: 19, weight: selection.wrappedValue == item ? .semibold : .regular))
                        .foregroundStyle(selection.wrappedValue == item ? .primary : .secondary)
                        .frame(maxWidth: .infinity)
                    Rectangle()
                        .fill(selection.wrappedValue == item ? Color.primary : Color.clear)
                        .frame(height: 2)
                }
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
        }
    }
    .overlay(alignment: .bottom) {
        CarbynePalette.divider.frame(height: 0.5)
    }
}
'''
s = s[:start] + own + s[end:]

# Public profiles share the same Instagram-like header and provide subscribe/message actions.
start = s.index("struct PublicChannelScreen: View {")
end = s.index("\nstruct ChannelDirectorySheet: View {", start)
public = r'''struct PublicChannelScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\.dismiss) private var dismiss
    let profile: CarbyneProfile
    @State private var selectedSection = "Posts"
    @State private var showMessages = false

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 12) {
                Button { dismiss() } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 20, weight: .semibold))
                        .frame(width: 36, height: 40)
                }
                Text(profile.username ?? profile.title)
                    .font(.system(size: 20, weight: .bold))
                    .lineLimit(1)
                Spacer()
                Image(systemName: "ellipsis")
                    .font(.system(size: 20, weight: .semibold))
                    .frame(width: 36, height: 40)
            }
            .padding(.horizontal, 12)
            .padding(.top, 4)

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    ProfileBannerView(url: store.publicImageURL(path: profile.bannerPath))
                    HStack(alignment: .center, spacing: 18) {
                        AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)
                            .overlay(Circle().stroke(CarbynePalette.background, lineWidth: 3))
                            .padding(.leading, 2)
                            .padding(.top, -26)
                        VStack(alignment: .leading, spacing: 8) {
                            Text(profile.title)
                                .font(.system(size: 17, weight: .semibold))
                                .lineLimit(2)
                            HStack(spacing: 0) {
                                VStack(spacing: 2) {
                                    Text("0").font(.system(size: 17, weight: .semibold))
                                    Text("posts").font(.system(size: 12)).foregroundStyle(.secondary)
                                }
                                Spacer(minLength: 8)
                                VStack(spacing: 2) {
                                    Text("\(store.subscriberCount)").font(.system(size: 17, weight: .semibold))
                                    Text("subscribers").font(.system(size: 12)).foregroundStyle(.secondary)
                                }
                            }
                        }
                        Spacer(minLength: 0)
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 18)

                    if let bio = profile.bio, !bio.isEmpty {
                        Text(bio)
                            .font(.system(size: 14))
                            .padding(.horizontal, 16)
                            .padding(.top, 12)
                    }

                    HStack(spacing: 8) {
                        Button {
                            Task { await store.toggleSubscription() }
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: store.isSubscribed ? "checkmark" : "plus")
                                Text(store.isSubscribed ? "Subscribed" : "Subscribe")
                            }
                            .font(.system(size: 14, weight: .semibold))
                            .frame(maxWidth: .infinity)
                            .frame(height: 36)
                            .foregroundStyle(.white)
                            .background(Color.accentColor, in: RoundedRectangle(cornerRadius: 9))
                        }
                        Button { showMessages = true } label: {
                            Text("Message")
                                .font(.system(size: 14, weight: .semibold))
                                .frame(maxWidth: .infinity)
                                .frame(height: 36)
                                .background(CarbynePalette.surface, in: RoundedRectangle(cornerRadius: 9))
                        }
                    }
                    .buttonStyle(.plain)
                    .padding(.horizontal, 16)
                    .padding(.top, 16)
                    .padding(.bottom, 16)

                    profileSectionTabs(selection: $selectedSection)

                    Group {
                        switch selectedSection {
                        case "Posts":
                            ContentUnavailableView("No posts yet", systemImage: "square.grid.3x3",
                                description: Text("This creator hasn't published any posts yet."))
                        case "About":
                            VStack(alignment: .leading, spacing: 8) {
                                Text(profile.title).font(.system(size: 15, weight: .semibold))
                                Text("@\(profile.username ?? "unknown")").foregroundStyle(.secondary)
                                if let bio = profile.bio, !bio.isEmpty { Text(bio) }
                            }
                            .font(.system(size: 14))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(16)
                        default:
                            Text("Channel")
                                .font(.system(size: 14))
                                .foregroundStyle(.secondary)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(16)
                        }
                    }
                    .frame(minHeight: 180, alignment: .topLeading)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(CarbynePalette.background)
        }
        .background(CarbynePalette.background.ignoresSafeArea())
        .toolbar(.hidden, for: .tabBar)
        .toolbar(.hidden, for: .navigationBar)
        .sheet(isPresented: $showMessages) {
            NavigationStack { ChatThreadScreen(profile: profile) }
        }
        .task {
            await store.viewChannel(profile)
            await store.refreshSubscription(for: profile)
        }
    }
}
'''
s = s[:start] + public + s[end:]

p.write_text(s)
print("Applied Instagram-inspired charcoal palette, profile headers/actions, and exact-size avatar clipping.")


# Correct the profile composition: keep Carbyne's banner, let the avatar
# overlap its lower edge, and retain exactly one settings control.
banner_header = '''                            HStack(spacing: 12) {
                                Text(profile.username ?? profile.title)'''
if banner_header in s:
    a = s.index(banner_header)
    b = s.index('                            HStack(alignment: .center, spacing: 18) {', a)
    s = s[:a] + s[b:]

s = s.replace('''                                    .padding(.top, -26)
                                VStack(alignment: .leading, spacing: 8) {''',
              '''                                    .padding(.top, -48)
                                VStack(alignment: .leading, spacing: 8) {''')
s = s.replace('''                            .padding(.top, 18)

                            if let bio = profile.bio''',
              '''                            .padding(.top, 0)

                            if let bio = profile.bio''')

# Public profile: overlap the avatar substantially instead of leaving it below
# the banner; preserve the back/navigation row and existing banner.
s = s.replace('''                            .padding(.top, -26)
                        VStack(alignment: .leading, spacing: 8) {''',
              '''                            .padding(.top, -48)
                        VStack(alignment: .leading, spacing: 8) {''')
s = s.replace('''                    .padding(.top, 18)

                    if let bio = profile.bio''',
              '''                    .padding(.top, 0)

                    if let bio = profile.bio''')

# Apply the dynamic charcoal palette to app roots, not just profile surfaces.
# The palette remains UIColor-trait driven, so iOS appearance is still automatic.
s = s.replace('''        Group {
            if isPad {''',
              '''        Group {
            if isPad {''', 1)
s = s.replace('''        .sheet(isPresented: $showAuth) { AuthenticationSheet() }''',
              '''        .background(CarbynePalette.background.ignoresSafeArea())
        .sheet(isPresented: $showAuth) { AuthenticationSheet() }''', 1)
s = s.replace('''        .task { await store.loadChannels() }
        .refreshable { await store.loadChannels() }
        .safeAreaInset(edge: .top, spacing: 0) {''',
              '''        .task { await store.loadChannels() }
        .refreshable { await store.loadChannels() }
        .background(CarbynePalette.background.ignoresSafeArea())
        .safeAreaInset(edge: .top, spacing: 0) {''', 1)
s = s.replace('''        .listStyle(.plain)
        .searchable(text: $query, prompt: "Search channels")''',
              '''        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(CarbynePalette.background.ignoresSafeArea())
        .searchable(text: $query, prompt: "Search channels")''', 1)
s = s.replace('''        Color.clear
            .ignoresSafeArea()''',
              '''        CarbynePalette.background
            .ignoresSafeArea()''', 1)

# Messages screen is a NavigationStack containing Lists; hide their default
# platform background so the same app-wide palette shows through.
s = s.replace('''        NavigationStack {
            Group {
                if store.session == nil {''',
              '''        NavigationStack {
            Group {
                if store.session == nil {''', 1)
s = s.replace('''            }
        }
    }
}

struct ChatThreadScreen''',
              '''            }
        }
        .background(CarbynePalette.background.ignoresSafeArea())
    }
}

struct ChatThreadScreen''', 1)

# All native tab roots receive the app palette beneath their content.
s = s.replace('''                        .ignoresSafeArea(.container, edges: .all)
                    .environmentObject(store)''',
              '''                        .ignoresSafeArea(.container, edges: .all)
                    .background(CarbynePalette.background.ignoresSafeArea())
                    .environmentObject(store)''')
s = s.replace('''                    .ignoresSafeArea(.container, edges: .all)
                    .environmentObject(store)''',
              '''                    .ignoresSafeArea(.container, edges: .all)
                    .background(CarbynePalette.background.ignoresSafeArea())
                    .environmentObject(store)''')

p.write_text(s)
print("Corrected avatar/banner overlap, removed duplicate profile controls, and extended charcoal palette app-wide.")



# Ensure the avatar actually straddles the banner edge by roughly half its size.
s = s.replace('''                                    .padding(.leading, 2)
                                    .padding(.top, -26)''',
              '''                                    .padding(.leading, 2)
                                    .padding(.top, -52)''')
s = s.replace('''                            .padding(.top, 18)

                            if let bio = profile.bio''',
              '''                            .padding(.top, 0)

                            if let bio = profile.bio''')
s = s.replace('''                    .padding(.top, 18)

                    if let bio = profile.bio''',
              '''                    .padding(.top, 0)

                    if let bio = profile.bio''')
p.write_text(s)

# Extend the same dynamic palette to settings/about lists.
settings_path = Path("ios/Carbyne/Sources/AccountSheets.swift")
a = settings_path.read_text()
a = a.replace('''        .navigationTitle("Settings & Privacy")''',
              '''        .scrollContentBackground(.hidden)
        .background(CarbynePalette.background.ignoresSafeArea())
        .navigationTitle("Settings & Privacy")''')
a = a.replace('''        .navigationTitle("About Carbyne")''',
              '''        .scrollContentBackground(.hidden)
        .background(CarbynePalette.background.ignoresSafeArea())
        .navigationTitle("About Carbyne")''')
settings_path.write_text(a)

# Native tab roots are full-screen surfaces too; prevent a system-default
# background from peeking through between each hosted screen and the tab bar.
tabs_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
t = tabs_path.read_text()
t = t.replace('''            host.view.backgroundColor = .clear''',
              '''            host.view.backgroundColor = UIColor { traits in
                traits.userInterfaceStyle == .dark
                    ? UIColor(red: 0.047, green: 0.055, blue: 0.063, alpha: 1)
                    : .systemBackground
            }''')
t = t.replace('''            controller.view.backgroundColor = .clear''',
              '''            controller.view.backgroundColor = UIColor { traits in
                traits.userInterfaceStyle == .dark
                    ? UIColor(red: 0.047, green: 0.055, blue: 0.063, alpha: 1)
                    : .systemBackground
            }''')
tabs_path.write_text(t)
print("Applied corrected banner overlap and app-wide palette to profile, tabs, settings, and About.")


# Make every conversation surface use the same charcoal background as Home/Profile.
s = s.replace('''                    .listStyle(.plain)
                }
            }
            .navigationTitle("Chat")''',
              '''                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                    .background(CarbynePalette.background)
                }
            }
            .navigationTitle("Chat")''')
s = s.replace('''            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if store.session != nil {''',
              '''            .navigationBarTitleDisplayMode(.inline)
            .background(CarbynePalette.background.ignoresSafeArea())
            .toolbar {
                if store.session != nil {''', 1)
s = s.replace('''            List(store.channels.filter { $0.id != store.session?.user.id }) { profile in''',
              '''            List(store.channels.filter { $0.id != store.session?.user.id }) { profile in''')
s = s.replace('''            }
            .navigationTitle("New message")''',
              '''            }
            .scrollContentBackground(.hidden)
            .background(CarbynePalette.background.ignoresSafeArea())
            .navigationTitle("New message")''', 1)
# The thread message scroll view and composer should sit on the app-wide surface.
s = s.replace('''            HStack(spacing: 10) {
                PhotosPicker(selection: $selectedPhoto''',
              '''            HStack(spacing: 10) {
                PhotosPicker(selection: $selectedPhoto''', 1)
s = s.replace('''        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)''',
              '''        .background(CarbynePalette.background.ignoresSafeArea())
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)''', 1)
p.write_text(s)
print("Extended the charcoal theme across conversations and messaging screens.")
