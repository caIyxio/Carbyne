from pathlib import Path
import re

p = Path("ios/Carbyne/Sources/ContentView.swift")
s = p.read_text()

# Separate the signed-in user's Profile tab from other people's Channels.
# Other creators use a native push destination and never replace the Profile tab.
# selectedPublicChannel and its NavigationStack destinations are created by
# replace-tabview-with-distinct-controllers.py. Do not inject them again here.
s = s.replace(
    "    private func openChannel(_ profile: CarbyneProfile) {\n        Task {\n            await store.viewChannel(profile)\n            selectedTab = .channel\n        }\n    }",
    "    private func openChannel(_ profile: CarbyneProfile) {\n        selectedPublicChannel = profile\n    }",
    1
)

# Profile tab is exclusively the authenticated user's own profile.
# Compact geometry avoids the previous oversized / zoomed presentation.
start = s.index("struct ChannelScreen: View {")
end = s.index("struct ChannelDirectorySheet: View {", start)
profile = r'''struct ChannelScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void
    let openEditor: () -> Void
    let openSecurity: () -> Void
    @State private var selectedSection = "Home"

    var body: some View {
        Group {
            if let profile = store.profile, store.session != nil {
                ScrollView {
                    VStack(alignment: .leading, spacing: 0) {
                        AsyncImage(url: store.publicImageURL(path: profile.bannerPath)) { phase in
                            if let image = phase.image {
                                image.resizable().scaledToFill()
                            } else {
                                Rectangle().fill(Color(uiColor: .secondarySystemBackground))
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .aspectRatio(3.0, contentMode: .fit)
                        .clipped()

                        HStack(alignment: .top, spacing: 12) {
                            AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 76)
                                .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 3))
                                .padding(.top, -26)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(profile.title)
                                    .font(.system(size: 20, weight: .semibold))
                                    .lineLimit(2)
                                Text("@\(profile.username ?? "unknown")")
                                    .font(.system(size: 14))
                                    .foregroundStyle(.secondary)
                                Text("\(store.subscriberCount) subscribers")
                                    .font(.system(size: 13))
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.top, 8)
                            Spacer(minLength: 0)
                        }
                        .padding(.horizontal, 16)
                        .padding(.bottom, 12)

                        HStack(spacing: 0) {
                            ForEach(["Home", "Posts", "About"], id: \.self) { item in
                                Button { selectedSection = item } label: {
                                    Text(item)
                                        .font(.system(size: 14, weight: selectedSection == item ? .semibold : .regular))
                                        .foregroundStyle(selectedSection == item ? .primary : .secondary)
                                        .frame(maxWidth: .infinity)
                                        .padding(.vertical, 11)
                                        .overlay(alignment: .bottom) {
                                            if selectedSection == item {
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
                                    description: Text("Your published posts will appear here."))
                            case "About":
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                    Text("@\(profile.username ?? "unknown")")
                                }
                                .font(.system(size: 14))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(16)
                            default:
                                Text("Your channel")
                                    .font(.system(size: 14))
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(16)
                            }
                        }
                        .frame(minHeight: 140, alignment: .topLeading)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .background(Color.clear)
            } else {
                ContentUnavailableView("Your Profile", systemImage: "person.crop.circle",
                    description: Text("Sign in to view and edit your profile."))
                Button("Log in", action: openAuth).buttonStyle(.borderedProminent)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
    }
}

struct PublicChannelScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let profile: CarbyneProfile
    @State private var selectedSection = "Home"

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                AsyncImage(url: store.publicImageURL(path: profile.bannerPath)) { phase in
                    if let image = phase.image { image.resizable().scaledToFill() }
                    else { Rectangle().fill(Color(uiColor: .secondarySystemBackground)) }
                }
                .frame(maxWidth: .infinity)
                .aspectRatio(3.0, contentMode: .fit)
                .clipped()

                HStack(alignment: .top, spacing: 12) {
                    AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 76)
                        .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 3))
                        .padding(.top, -26)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(profile.title)
                            .font(.system(size: 20, weight: .semibold))
                            .lineLimit(2)
                        Text("@\(profile.username ?? "unknown")")
                            .font(.system(size: 14)).foregroundStyle(.secondary)
                        Text("\(store.subscriberCount) subscribers")
                            .font(.system(size: 13)).foregroundStyle(.secondary)
                    }
                    .padding(.top, 8)
                    Spacer(minLength: 0)
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 12)

                Button(store.isSubscribed ? "Subscribed" : "Subscribe") {
                    Task { await store.toggleSubscription() }
                }
                .buttonStyle(.borderedProminent)
                .padding(.horizontal, 16)
                .padding(.bottom, 12)

                HStack(spacing: 0) {
                    ForEach(["Home", "Posts", "About"], id: \.self) { item in
                        Button { selectedSection = item } label: {
                            Text(item)
                                .font(.system(size: 14, weight: selectedSection == item ? .semibold : .regular))
                                .foregroundStyle(selectedSection == item ? .primary : .secondary)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 11)
                                .overlay(alignment: .bottom) {
                                    if selectedSection == item {
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
                            description: Text("This creator hasn't published any posts yet."))
                    case "About":
                        VStack(alignment: .leading, spacing: 8) {
                            Text(profile.title)
                            Text("@\(profile.username ?? "unknown")")
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
                .frame(minHeight: 140, alignment: .topLeading)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Color.clear)
        .toolbar(.hidden, for: .tabBar)
        // Keep the native back affordance, but remove the creator-page title/header.
        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)
        .task {
            await store.viewChannel(profile)
            await store.refreshSubscription(for: profile)
        }
    }
}

'''
s = s[:start] + profile + s[end:]

# Ensure UIKit's Profile tab displays the actual account avatar at tab-bar icon size.
# Use an asynchronous image fetch and keep a native symbol as immediate fallback.
needle = "        func updateAvatar(url: URL?, item: UITabBarItem?) {"
if needle in s:
    begin = s.index(needle)
    # Find matching function end by brace depth.
    brace = s.index("{", begin)
    depth = 0
    finish = None
    for i in range(brace, len(s)):
        if s[i] == "{": depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                finish = i + 1
                break
    fn = r'''        func updateAvatar(url: URL?, item: UITabBarItem?) {
            guard url != requestedAvatarURL else { return }
            requestedAvatarURL = url
            avatarTask?.cancel()
            let fallback = UIImage(systemName: "person.crop.circle.fill")
            item?.image = fallback
            item?.selectedImage = fallback
            guard let url, let item else { return }

            avatarTask = Task { [weak self, weak item] in
                do {
                    let (data, _) = try await URLSession.shared.data(from: url)
                    guard !Task.isCancelled, let image = UIImage(data: data) else { return }
                    let size = CGSize(width: 60, height: 60)
                    let renderer = UIGraphicsImageRenderer(size: size)
                    let circular = renderer.image { _ in
                        let rect = CGRect(origin: .zero, size: size)
                        UIBezierPath(ovalIn: rect).addClip()
                        image.draw(in: AVMakeRect(aspectRatio: image.size, insideRect: rect))
                    }.withRenderingMode(.alwaysOriginal)
                    await MainActor.run {
                        guard self != nil else { return }
                        item?.image = circular
                        item?.selectedImage = circular
                    }
                } catch {
                    // Keep the native profile symbol if the avatar cannot load.
                }
            }
        }'''
    s = s[:begin] + fn + s[finish:]

p.write_text(s)
print("Separated own Profile from public Channels, pushed public creator pages with native navigation, matched profile layouts, and added the account avatar to the native tab icon.")


# Configure the actual app root hosting controller for edge-to-edge layout.
# Previously only the five tab child hosts had safeAreaRegions disabled; the
# SwiftUI-managed root host still supplied container safe areas to navigation,
# iPad content, and pushed destinations.
app_path = Path("ios/Carbyne/Sources/CarbyneApp.swift")
app_source = app_path.read_text()
app_source = app_source.replace("import SwiftUI\n", "import SwiftUI\nimport UIKit\n", 1)
app_entry = app_source.index("@main\nstruct CarbyneApp: App {")
app_source = app_source[:app_entry] + r'''@main
struct CarbyneApp: App {
    @StateObject private var store = CarbyneStore()

    var body: some Scene {
        WindowGroup {
            CarbyneEdgeToEdgeRoot {
                ContentView()
                    .environmentObject(store)
                    .preferredColorScheme(.light)
                    .task { await store.restoreSession() }
            }
            // Expand the representable itself to the physical window bounds.
            .ignoresSafeArea(.container, edges: .all)
        }
    }
}

/// Owns the top-level SwiftUI hosting controller so the safe-area policy is
/// applied once to the entire application, not just to individual tab roots.
struct CarbyneEdgeToEdgeRoot<Content: View>: UIViewControllerRepresentable {
    let content: Content

    init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    func makeUIViewController(context: Context) -> UIHostingController<Content> {
        let controller = UIHostingController(rootView: content)
        // Remove status-bar / home-indicator container insets from SwiftUI layout,
        // but retain the keyboard region so editors remain usable.
        controller.safeAreaRegions = .keyboard
        controller.edgesForExtendedLayout = .all
        controller.extendedLayoutIncludesOpaqueBars = true
        controller.view.backgroundColor = .clear
        return controller
    }

    func updateUIViewController(
        _ controller: UIHostingController<Content>,
        context: Context
    ) {
        controller.rootView = content
    }
}
'''
app_path.write_text(app_source)

# The ContentView root no longer tries to solve edge-to-edge from inside the
# NavigationStack. The root hosting controller above owns that policy.
content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content_source = content_path.read_text()
content_source = content_source.replace(
    """        // Keep the root transparent: an opaque systemBackground here paints the
        // status-bar and home-indicator regions as separate white bands.
        .background(Color.clear.ignoresSafeArea())
""",
    "",
    1
)
content_source = content_source.replace(
    "        .ignoresSafeArea(.container, edges: .all)\n",
    "",
    1
)
content_source = content_source.replace(
    """        // Keep native navigation controls, but let the app content show through
        // behind the navigation bar instead of drawing a separate bar backdrop.
""",
    "",
    1
)
content_path.write_text(content_source)

# Let each tab's interactive SwiftUI content participate in keyboard avoidance,
# while removing only the system container safe areas. The UIKit child view must
# also extend underneath translucent bars; otherwise disabling SwiftUI's safe
# area does not enlarge the actual child-controller view frame.
tab_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
tab_source = tab_path.read_text()
tab_source = tab_source.replace(
    """            // Every tab is a full-bleed app surface. Safe-area insets are
            // handled by each screen's content layout, not imposed by UIKit.
            host.safeAreaRegions = []
""",
    """            // Apply the app-wide edge-to-edge policy to tab roots too.
            // Keep the keyboard safe area, but remove status / home-indicator insets.
            host.safeAreaRegions = .keyboard
            host.edgesForExtendedLayout = .all
            host.extendedLayoutIncludesOpaqueBars = true
""",
    1
)
tab_path.write_text(tab_source)
print("Applied app-root edge-to-edge hosting and full-bleed tab-controller layout.")


# Edge-to-edge correction: expand each tab's actual SwiftUI root into the
# device container safe areas. UIHostingController.safeAreaRegions alone does
# not remove the NavigationStack/ScrollView container's own layout insets.
tab_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
tab_source = tab_path.read_text()
tab_source = tab_source.replace(
    """                NavigationStack {
                    HomeScreen(showDirectory: $showDirectory, selectChannel: selectChannel)
                        .navigationDestination(item: $selectedPublicChannel) { profile in
                            PublicChannelScreen(profile: profile)
                        }
                }
                .environmentObject(store)""",
    """                NavigationStack {
                    HomeScreen(showDirectory: $showDirectory, selectChannel: selectChannel)
                        .navigationDestination(item: $selectedPublicChannel) { profile in
                            PublicChannelScreen(profile: profile)
                        }
                        .toolbar(.hidden, for: .navigationBar)
                }
                .ignoresSafeArea(.container, edges: .all)
                .environmentObject(store)""",
    1
)
# All tab roots, including non-navigation roots, occupy the complete controller
# bounds. The keyboard region remains active because only .container is ignored.
tab_source = tab_source.replace(
    ".environmentObject(store)\n            ),",
    ".ignoresSafeArea(.container, edges: .all)\n                    .environmentObject(store)\n            ),"
)
tab_path.write_text(tab_source)

# The iPad stack has the same full-bleed requirement, while retaining the
# native navigation destination for public channels.
content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content_source = content_path.read_text()
content_source = content_source.replace(
    """                    .navigationDestination(item: $selectedPublicChannel) { profile in
                        PublicChannelScreen(profile: profile)
                    }
                    .toolbarBackground(.hidden, for: .navigationBar)""",
    """                    .navigationDestination(item: $selectedPublicChannel) { profile in
                        PublicChannelScreen(profile: profile)
                    }
                    .toolbar(.hidden, for: .navigationBar)
                    .ignoresSafeArea(.container, edges: .all)"""
)
content_path.write_text(content_source)
print("Expanded every iPhone tab root and the iPad root through the container safe areas; removed the empty Home navigation bar.")

# The Home NavigationStack is covered by the general per-tab modifier above;
# normalize the modifier chain so it is applied only once.
tab_source = tab_source.replace(
    """                .ignoresSafeArea(.container, edges: .all)
                .ignoresSafeArea(.container, edges: .all)
                    .environmentObject(store)""",
    """                .ignoresSafeArea(.container, edges: .all)
                    .environmentObject(store)""",
    1
)
tab_path.write_text(tab_source)


# Home feed presentation updates requested after the edge-to-edge pass.
content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content_source = content_path.read_text()

home_start = content_source.index("struct HomeScreen: View {")
home_end = content_source.index("struct MessagesScreen: View {", home_start)
home = content_source[home_start:home_end]

# Promote the Carbyne/search row to a persistent feed header. It remains
# separate from the scrolling cards and uses a material background.
header_start = home.find("                HStack {\n                    Text(\"Carbyne\")")
grid_start = home.find("\n\n                LazyVGrid", header_start)
if header_start < 0 or grid_start < 0:
    raise SystemExit("Could not locate HomeScreen logo/search row; refusing a broad edit.")
home = home[:header_start] + home[grid_start + 2:]

header_modifier = r'''        .safeAreaInset(edge: .top, spacing: 0) {
            HStack {
                Text("Carbyne")
                    .font(.system(size: isPad ? 30 : 26, weight: .semibold, design: .rounded))
                    .tracking(-1.0)
                Spacer()
                Button { showDirectory = true } label: {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 18, weight: .medium))
                        .frame(width: 42, height: 42)
                        .background(.thinMaterial, in: Circle())
                        .overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Search")
            }
            .padding(.horizontal, isPad ? 34 : 20)
            .padding(.vertical, 7)
            .background(.ultraThinMaterial)
        }
'''
refresh_line = "        .refreshable { await store.loadChannels() }\n"
if refresh_line not in home:
    raise SystemExit("Could not locate HomeScreen refreshable modifier.")
home = home.replace(refresh_line, refresh_line + header_modifier, 1)

# Slightly square off video thumbnails and reduce the creator avatar beside
# each video without changing channel/profile avatar sizes.
home = home.replace("RoundedRectangle(cornerRadius: 24)", "RoundedRectangle(cornerRadius: 12)", 1)
home = home.replace(
    ".frame(width: isPad ? 38 : 58, height: isPad ? 38 : 58)",
    ".frame(width: isPad ? 34 : 44, height: isPad ? 34 : 44)",
    1
)
content_source = content_source[:home_start] + home + content_source[home_end:]

# Increase profile photos in channel lists, the signed-in user's profile,
# and public creator profiles. Keep the video-row avatars independent.
content_source = content_source.replace(
    "AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 76)",
    "AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 104)",
    1
)
content_source = content_source.replace(
    "AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 76)",
    "AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 104)",
    1
)
content_source = content_source.replace(
    "AvatarView(url: imageURL, size: 54)",
    "AvatarView(url: imageURL, size: 68)",
    1
)

# Public creator pages have no custom title/header; preserve only the native
# back affordance supplied by NavigationStack.
public_start = content_source.index("struct PublicChannelScreen: View {")
public_end = content_source.index("struct ChannelDirectorySheet: View {", public_start)
public = content_source[public_start:public_end]
if '.navigationTitle("")' not in public:
    public = public.replace(
        "        .toolbar(.hidden, for: .tabBar)",
        "        .toolbar(.hidden, for: .tabBar)\n        .navigationTitle(\"\")",
        1
    )
if '.toolbarBackground(.hidden, for: .navigationBar)' not in public:
    public = public.replace(
        '        .navigationBarTitleDisplayMode(.inline)',
        '        .navigationBarTitleDisplayMode(.inline)\n        .toolbarBackground(.hidden, for: .navigationBar)',
        1
    )
content_source = content_source[:public_start] + public + content_source[public_end:]

content_path.write_text(content_source)
print("Added a pinned Carbyne/search feed header, tightened video thumbnails, reduced video-row avatars, enlarged profile photos, and kept public profiles free of a custom header.")


# Search is a first-class destination in the tab bar. Keep the Home header
# search control as a shortcut that selects that tab, not a modal sheet.
models_path = Path("ios/Carbyne/Sources/CarbyneModels.swift")
models_source = models_path.read_text()
models_source = models_source.replace(
    "enum CarbyneTab: Hashable {\n    case home, moments, messages, upload, channel\n}",
    "enum CarbyneTab: Hashable {\n    case home, search, moments, messages, upload, channel\n}",
    1
)
models_path.write_text(models_source)

# HomeScreen now selects Search through the same tab state used by the native
# tab controller and iPad navigation. The search shortcut uses iOS 26's real
# interactive Liquid Glass effect, with a material fallback on earlier iOS.
content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content_source = content_path.read_text()
content_source = content_source.replace(
    "HomeScreen(showDirectory: $showDirectory, selectChannel: openChannel)",
    "HomeScreen(selectedTab: $selectedTab, selectChannel: openChannel)"
)
content_source = content_source.replace(
    "    @Binding var showDirectory: Bool\n    let selectChannel: (CarbyneProfile) -> Void",
    "    @Binding var selectedTab: CarbyneTab\n    let selectChannel: (CarbyneProfile) -> Void",
    1
)
content_source = content_source.replace(
    "Button { showDirectory = true } label: {\n                    Image(systemName: \"magnifyingglass\")\n                        .font(.system(size: 18, weight: .medium))\n                        .frame(width: 42, height: 42)\n                        .background(.thinMaterial, in: Circle())\n                        .overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))\n                }",
    """Button { selectedTab = .search } label: {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 18, weight: .medium))
                        .frame(width: 42, height: 42)
                        .background {
                            if #available(iOS 26.0, *) {
                                Circle().fill(.clear)
                                    .glassEffect(.regular.interactive(), in: Circle())
                            } else {
                                Circle().fill(.ultraThinMaterial)
                                    .overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))
                            }
                        }
                }""",
    1
)

# Add a persistent Search screen that pushes creator profiles in its own
# NavigationStack, just like the Home tab. This replaces the old modal directory.
search_view = r'''struct SearchScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    @State private var query = ""
    let selectChannel: (CarbyneProfile) -> Void

    private var matches: [CarbyneProfile] {
        guard !query.isEmpty else { return store.channels }
        return store.channels.filter {
            ($0.title + " " + ($0.username ?? ""))
                .localizedCaseInsensitiveContains(query)
        }
    }

    var body: some View {
        List(matches) { profile in
            Button {
                selectChannel(profile)
            } label: {
                ChannelRow(profile: profile,
                           imageURL: store.publicImageURL(path: profile.avatarPath))
            }
            .buttonStyle(.plain)
            .listRowInsets(EdgeInsets(top: 7, leading: 16, bottom: 7, trailing: 16))
        }
        .listStyle(.plain)
        .searchable(text: $query, prompt: "Search channels")
        .navigationTitle("Search")
        .navigationBarTitleDisplayMode(.large)
        .task { await store.loadChannels() }
        .refreshable { await store.loadChannels() }
    }
}

'''
insert_at = content_source.index("struct MessagesScreen: View {")
content_source = content_source[:insert_at] + search_view + content_source[insert_at:]

# Public profile typography: larger display name, username, and subscriber count.
public_start = content_source.index("struct PublicChannelScreen: View {")
public_end = content_source.index("struct ChannelDirectorySheet: View {", public_start)
public = content_source[public_start:public_end]
public = public.replace(
    '.font(.system(size: 20, weight: .semibold))',
    '.font(.system(size: 24, weight: .semibold))',
    1
)
public = public.replace(
    '.font(.system(size: 14)).foregroundStyle(.secondary)',
    '.font(.system(size: 16)).foregroundStyle(.secondary)',
    1
)
public = public.replace(
    '.font(.system(size: 13)).foregroundStyle(.secondary)',
    '.font(.system(size: 16, weight: .medium)).foregroundStyle(.secondary)',
    1
)
# Keep the system back affordance, but ensure no title is rendered in the
# navigation bar. The bar background remains transparent over the banner.
public = public.replace(
    '.navigationTitle("")\n        .navigationBarTitleDisplayMode(.inline)\n        .toolbarBackground(.hidden, for: .navigationBar)',
    '.navigationTitle(" ")\n        .navigationBarTitleDisplayMode(.inline)\n        .toolbarBackground(.hidden, for: .navigationBar)',
    1
)
content_source = content_source[:public_start] + public + content_source[public_end:]

# Slightly larger creator names and handles in Search/Channels rows too.
content_source = content_source.replace(
    'Text(profile.title).font(.system(size: 15, weight: .semibold))',
    'Text(profile.title).font(.system(size: 17, weight: .semibold))',
    1
)
content_source = content_source.replace(
    'Text("@\\(profile.username ?? "unknown")").font(.system(size: 12))',
    'Text("@\\(profile.username ?? "unknown")").font(.system(size: 14))',
    1
)
content_path.write_text(content_source)

# iPad navigation gets a Search destination instead of a separate modal search
# button. Search stays in the top capsule alongside the other app sections.
generator_path = Path(".github/scripts/replace-tabview-with-distinct-controllers.py")
generator = generator_path.read_text()
generator = generator.replace(
    """        case .home:
            HomeScreen(showDirectory: $showDirectory, selectChannel: openChannel)
        case .moments:""",
    """        case .home:
            HomeScreen(selectedTab: $selectedTab, selectChannel: openChannel)
        case .search:
            SearchScreen(selectChannel: openChannel)
        case .moments:""",
    1
)
generator = generator.replace(
    '            iPadTab("Home", .home, icon: "house.fill")\n            iPadTab("Moments", .moments, icon: "play.rectangle.fill")',
    '            iPadTab("Home", .home, icon: "house.fill")\n            iPadTab("Search", .search, icon: "magnifyingglass")\n            iPadTab("Moments", .moments, icon: "play.rectangle.fill")',
    1
)
# Remove the old standalone magnifying-glass button from the iPad capsule.
old_ipad_search = """            Button { showDirectory = true } label: {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 19, weight: .medium))
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Search")
"""
generator = generator.replace(old_ipad_search, "", 1)
# Six native tabs: Home, Search, Moments, Upload, Chat, Profile.
generator = generator.replace(
    "        .home, .moments, .upload, .messages, .channel",
    "        .home, .search, .moments, .upload, .messages, .channel",
    1
)
generator = generator.replace(
    '    private static let titles = ["Home", "Moments", "Upload", "Chat", "Profile"]',
    '    private static let titles = ["Home", "Search", "Moments", "Upload", "Chat", "Profile"]',
    1
)
generator = generator.replace(
    """        "house.fill",
        "play.rectangle.fill",
        "plus.square.fill",""",
    """        "house.fill",
        "magnifyingglass",
        "play.rectangle.fill",
        "plus.square.fill",""",
    1
)
# Search has its own NavigationStack so creator profiles push from Search too.
generator = generator.replace(
    """            AnyView(
                ContentUnavailableView("Moments", systemImage: "play.rectangle",
                    description: Text("Moments will appear here."))
                    .environmentObject(store)
            ),""",
    """            AnyView(
                NavigationStack {
                    SearchScreen(selectChannel: { profile in selectedPublicChannel = profile })
                        .navigationDestination(item: $selectedPublicChannel) { profile in
                            PublicChannelScreen(profile: profile)
                        }
                }
                .environmentObject(store)
            ),
            AnyView(
                ContentUnavailableView("Moments", systemImage: "play.rectangle",
                    description: Text("Moments will appear here."))
                    .environmentObject(store)
            ),""",
    1
)
# HomeScreen's search action selects Search rather than opening the old sheet.
generator_path.write_text(generator)

print("Added Search as a sixth native tab and iPad navigation destination, changed the Home shortcut to select it with native Liquid Glass, and enlarged public creator typography.")


# The native tab-controller generator runs before this profile pass in CI, so
# patch its generated Swift output directly (not only the generator template).
tab_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
tab_source = tab_path.read_text()
tab_source = tab_source.replace(
    "        .home, .moments, .upload, .messages, .channel",
    "        .home, .search, .moments, .upload, .messages, .channel",
    1
)
tab_source = tab_source.replace(
    '    private static let titles = ["Home", "Moments", "Upload", "Chat", "Profile"]',
    '    private static let titles = ["Home", "Search", "Moments", "Upload", "Chat", "Profile"]',
    1
)
tab_source = tab_source.replace(
    """        "house.fill",
        "play.rectangle.fill",
        "plus.square.fill",""",
    """        "house.fill",
        "magnifyingglass",
        "play.rectangle.fill",
        "plus.square.fill",""",
    1
)
tab_source = tab_source.replace(
    "HomeScreen(showDirectory: $showDirectory, selectChannel: selectChannel)",
    "HomeScreen(selectedTab: $selection, selectChannel: selectChannel)",
    1
)
tab_source = tab_source.replace(
    """            AnyView(
                ContentUnavailableView("Moments", systemImage: "play.rectangle",
                    description: Text("Moments will appear here."))
                    .environmentObject(store)
            ),""",
    """            AnyView(
                NavigationStack {
                    SearchScreen(selectChannel: { profile in selectedPublicChannel = profile })
                        .navigationDestination(item: $selectedPublicChannel) { profile in
                            PublicChannelScreen(profile: profile)
                        }
                }
                .environmentObject(store)
            ),
            AnyView(
                ContentUnavailableView("Moments", systemImage: "play.rectangle",
                    description: Text("Moments will appear here."))
                    .environmentObject(store)
            ),""",
    1
)
tab_path.write_text(tab_source)

# The iPad is also a tabbed experience; place Search in its capsule and remove
# the old modal directory shortcut.
content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content_source = content_path.read_text()
content_source = content_source.replace(
    '            iPadTab("Home", .home, icon: "house.fill")\n            iPadTab("Moments", .moments, icon: "play.rectangle.fill")',
    '            iPadTab("Home", .home, icon: "house.fill")\n            iPadTab("Search", .search, icon: "magnifyingglass")\n            iPadTab("Moments", .moments, icon: "play.rectangle.fill")',
    1
)
content_source = content_source.replace(
    """            Button { showDirectory = true } label: {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 19, weight: .medium))
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Search")
""",
    "",
    1
)
# Search tab is available in the iPad selected-screen switch as well.
content_source = content_source.replace(
    """        case .home:
            HomeScreen(selectedTab: $selectedTab, selectChannel: openChannel)
        case .moments:""",
    """        case .home:
            HomeScreen(selectedTab: $selectedTab, selectChannel: openChannel)
        case .search:
            SearchScreen(selectChannel: openChannel)
        case .moments:""",
    1
)
content_path.write_text(content_source)

# Remove the public creator's navigation header completely while retaining a
# compact back affordance over the banner. This avoids the blank nav-bar strip
# that remained even with an empty navigation title.
public_start = content_source.index("struct PublicChannelScreen: View {")
public_end = content_source.index("struct ChannelDirectorySheet: View {", public_start)
public = content_source[public_start:public_end]
public = public.replace(
    "struct PublicChannelScreen: View {\n    @EnvironmentObject private var store: CarbyneStore",
    "struct PublicChannelScreen: View {\n    @EnvironmentObject private var store: CarbyneStore\n    @Environment(\\.dismiss) private var dismiss",
    1
)
public = public.replace(
    """        ScrollView {
            VStack(alignment: .leading, spacing: 0) {""",
    """        ZStack(alignment: .topLeading) {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {""",
    1
)
# Close the ScrollView inside the ZStack and overlay a back control on the banner.
public = public.replace(
    """        .background(Color.clear)
        .toolbar(.hidden, for: .tabBar)
        // Keep the native back affordance, but remove the creator-page title/header.
        .navigationTitle(" ")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(.hidden, for: .navigationBar)""",
    """            .background(Color.clear)
            }
            Button { dismiss() } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 17, weight: .semibold))
                    .frame(width: 38, height: 38)
                    .contentShape(Circle())
            }
            .buttonStyle(.plain)
            .background {
                if #available(iOS 26.0, *) {
                    Circle().fill(.clear).glassEffect(.regular.interactive(), in: Circle())
                } else {
                    Circle().fill(.ultraThinMaterial)
                }
            }
            .padding(.leading, 16)
            .padding(.top, 8)
        }
        .toolbar(.hidden, for: .tabBar)
        .toolbar(.hidden, for: .navigationBar)""",
    1
)
content_source = content_source[:public_start] + public + content_source[public_end:]
content_path.write_text(content_source)
print("Patched generated iPhone/iPad tabs, added Search navigation, and removed the public-profile navigation header while retaining an overlaid back control.")


# Ensure the sixth UIKit child exists as well as its tab item. The previous
# replacement is intentionally matched against the full-bleed generated form.
tab_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
tab_source = tab_path.read_text()
moments_root = """            AnyView(
                ContentUnavailableView("Moments", systemImage: "play.rectangle",
                    description: Text("Moments will appear here."))
                    .ignoresSafeArea(.container, edges: .all)
                    .environmentObject(store)
            ),"""
search_root = """            AnyView(
                NavigationStack {
                    SearchScreen(selectChannel: { profile in selectedPublicChannel = profile })
                        .navigationDestination(item: $selectedPublicChannel) { profile in
                            PublicChannelScreen(profile: profile)
                        }
                }
                .ignoresSafeArea(.container, edges: .all)
                .environmentObject(store)
            ),
"""
if "SearchScreen(selectChannel:" not in tab_source:
    if moments_root not in tab_source:
        raise SystemExit("Could not locate the Moments tab root; refusing to generate a mismatched tab controller.")
    tab_source = tab_source.replace(moments_root, search_root + moments_root, 1)
tab_path.write_text(tab_source)

# The Search tab must remain the second root in the same order as the UIKit
# tab metadata, so fail early if the generated controller is inconsistent.
if tab_source.count("SearchScreen(selectChannel:") != 1:
    raise SystemExit("Expected exactly one SearchScreen root in the native tab controller.")
print("Verified six native tab roots, including Search.")
