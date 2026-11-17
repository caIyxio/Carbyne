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
                                    .padding(.leading, 2)
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
                    HStack(alignment: .center, spacing: 18) {
                        AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 88)
                            .padding(.leading, 2)
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
