from pathlib import Path
import re

p = Path("ios/Carbyne/Sources/ContentView.swift")
s = p.read_text()

# Separate the signed-in user's Profile tab from other people's Channels.
# Other creators use a native push destination and never replace the Profile tab.
s = s.replace(
    "    @State private var showAlert = false\n",
    "    @State private var showAlert = false\n    @State private var selectedPublicChannel: CarbyneProfile?\n",
    1
)
s = s.replace(
    "        .sheet(isPresented: $showDirectory) { ChannelDirectorySheet(selectChannel: openChannel) }\n",
    "        .sheet(isPresented: $showDirectory) { ChannelDirectorySheet(selectChannel: openChannel) }\n        .navigationDestination(item: $selectedPublicChannel) { profile in PublicChannelScreen(profile: profile) }\n",
    1
)
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
                // Let the profile content draw beneath both system bars.
                // A clear hosting surface prevents UIKit's safe-area fill from
                // painting opaque strips above the status bar and below the tab bar.
                .background(Color.clear)
                .ignoresSafeArea()
            } else {
                ContentUnavailableView("Your Profile", systemImage: "person.crop.circle",
                    description: Text("Sign in to view and edit your profile."))
                Button("Log in", action: openAuth).buttonStyle(.borderedProminent)
            }
        }
        .toolbar(.hidden, for: .navigationBar)
    }
}

private struct PublicChannelScreen: View {
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
        .background(Color.clear.ignoresSafeArea())
        .ignoresSafeArea(.container, edges: [.top, .bottom])
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
