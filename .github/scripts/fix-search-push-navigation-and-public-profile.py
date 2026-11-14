from pathlib import Path

root = Path("ios/Carbyne/Sources")
cp, tp, mp = root / "ContentView.swift", root / "CarbyneNativeTabController.swift", root / "CarbyneModels.swift"
c, t, m = cp.read_text(), tp.read_text(), mp.read_text()

# Search is a pushed destination in the existing navigation stack, never a tab.
c = c.replace(
    """                    .navigationDestination(item: $selectedPublicChannel) { profile in
                        PublicChannelScreen(profile: profile)
                    }""",
    """                    .navigationDestination(isPresented: $showDirectory) {
                        SearchScreen(selectChannel: openChannel)
                    }
                    .navigationDestination(item: $selectedPublicChannel) { profile in
                        PublicChannelScreen(profile: profile)
                    }""",
    1,
)
c = c.replace('        .sheet(isPresented: $showDirectory) { ChannelDirectorySheet(selectChannel: openChannel) }\n', "")
c = c.replace("HomeScreen(selectedTab: $selectedTab, selectChannel: openChannel)", "HomeScreen(showDirectory: $showDirectory, selectChannel: openChannel)")
c = c.replace(
    '            iPadTab("Search", .search, icon: "magnifyingglass")',
    """            Button { showDirectory = true } label: {
                Label("Search", systemImage: "magnifyingglass")
                    .font(.system(size: 13))
                    .padding(.horizontal, 12).padding(.vertical, 10)
            }
            .buttonStyle(.plain)""",
)
c = c.replace("    @Binding var selectedTab: CarbyneTab\n    let selectChannel:", "    @Binding var showDirectory: Bool\n    let selectChannel:")
c = c.replace("Button { selectedTab = .search } label: {", "Button { showDirectory = true } label: {")
c = c.replace("""        case .search:
            SearchScreen(selectChannel: openChannel)
""", "")

# Repair the malformed public-profile view with balanced SwiftUI structure.
start = c.index("struct PublicChannelScreen: View {")
end = c.index("\nstruct ChannelDirectorySheet: View {", start)
c = c[:start] + r'''struct PublicChannelScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\.dismiss) private var dismiss
    let profile: CarbyneProfile
    @State private var selectedSection = "Home"

    var body: some View {
        ZStack(alignment: .topLeading) {
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
                        AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 104)
                            .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 3))
                            .padding(.top, -26)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(profile.title)
                                .font(.system(size: 24, weight: .semibold))
                                .lineLimit(2)
                            Text("@\(profile.username ?? "unknown")")
                                .font(.system(size: 16)).foregroundStyle(.secondary)
                            Text("\(store.subscriberCount) subscribers")
                                .font(.system(size: 16, weight: .medium)).foregroundStyle(.secondary)
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
        .toolbar(.hidden, for: .navigationBar)
        .task {
            await store.viewChannel(profile)
            await store.refreshSubscription(for: profile)
        }
    }
}
''' + c[end:]
cp.write_text(c)

# Remove Search from the enum: only five real tabs remain.
m = m.replace("case home, search, moments, messages, upload, channel", "case home, moments, messages, upload, channel")
mp.write_text(m)

# Keep exactly five UIKit tab roots. Search is pushed from the Home tab.
t = t.replace(
    """private static let tabs: [CarbyneTab] = [
        .home, .search, .moments, .upload, .messages, .channel
    ]""",
    """private static let tabs: [CarbyneTab] = [
        .home, .moments, .upload, .messages, .channel
    ]""",
)
t = t.replace(
    'private static let titles = ["Home", "Search", "Moments", "Upload", "Chat", "Profile"]',
    'private static let titles = ["Home", "Moments", "Upload", "Chat", "Profile"]',
)
t = t.replace(
    """    private static let symbols = [
        "house.fill",
        "magnifyingglass",
        "play.rectangle.fill",
        "plus.square.fill",
        "bubble.left.and.bubble.right.fill",
        "person.crop.circle.fill"
    ]""",
    """    private static let symbols = [
        "house.fill",
        "play.rectangle.fill",
        "plus.square.fill",
        "bubble.left.and.bubble.right.fill",
        "person.crop.circle.fill"
    ]""",
)
t = t.replace(
    """                    HomeScreen(selectedTab: $selection, selectChannel: selectChannel)
                        .navigationDestination(item: $selectedPublicChannel) { profile in""",
    """                    HomeScreen(showDirectory: $showDirectory, selectChannel: selectChannel)
                        .navigationDestination(isPresented: $showDirectory) {
                            SearchScreen(selectChannel: { profile in selectedPublicChannel = profile })
                        }
                        .navigationDestination(item: $selectedPublicChannel) { profile in""",
)
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
if search_root not in t:
    raise SystemExit("Expected standalone Search tab root was not found; refusing to guess.")
t = t.replace(search_root, "")
tp.write_text(t)

for label, source in [("ContentView", c), ("tab controller", t), ("models", m)]:
    if "CarbyneTab.search" in source or "selectedTab = .search" in source or "case .search:" in source:
        raise SystemExit(f"Stale Search-tab reference remains in {label}.")
print("Search is a pushed destination; public profile syntax repaired; five tabs retained.")
