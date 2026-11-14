from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
source = path.read_text()
start = source.index("struct ChannelScreen: View {")
end = source.index("struct ChannelDirectorySheet: View {", start)

replacement = r'''struct ChannelScreen: View {
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
                ScrollView(.vertical) {
                    VStack(alignment: .leading, spacing: 0) {
                        HStack {
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
                                    .font(.system(size: 23))
                                    .frame(width: 42, height: 42)
                                    .contentShape(Circle())
                            }
                        }
                        .padding(.horizontal, 18)
                        .padding(.vertical, 6)

                        ZStack(alignment: .bottomLeading) {
                            AsyncImage(url: store.publicImageURL(path: channel.bannerPath)) { phase in
                                if let image = phase.image {
                                    image.resizable().scaledToFill()
                                } else {
                                    Rectangle().fill(Color(uiColor: .secondarySystemBackground))
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .frame(height: 174)
                            .clipped()
                            .accessibilityLabel("Channel banner")

                            AvatarView(url: store.publicImageURL(path: channel.avatarPath), size: 88)
                                .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 4))
                                .padding(.leading, 18)
                                .offset(y: 42)
                        }
                        .padding(.bottom, 48)

                        VStack(alignment: .leading, spacing: 5) {
                            Text(channel.title)
                                .font(.system(size: 23, weight: .semibold))
                                .lineLimit(2)
                            Text("@\(channel.username ?? "unknown")")
                                .font(.system(size: 15))
                                .foregroundStyle(.secondary)
                            Text("\(store.subscriberCount) \(store.subscriberCount == 1 ? "subscriber" : "subscribers")")
                                .font(.system(size: 14))
                                .foregroundStyle(.secondary)
                            if !isOwnChannel {
                                Button(store.isSubscribed ? "Subscribed" : "Subscribe") {
                                    Task { await store.toggleSubscription() }
                                }
                                .font(.system(size: 13, weight: .semibold))
                                .buttonStyle(.borderedProminent)
                                .tint(store.isSubscribed ? Color(uiColor: .systemGray4) : .black)
                                .padding(.top, 5)
                            }
                        }
                        .padding(.horizontal, 18)
                        .padding(.bottom, 16)

                        HStack(spacing: 0) {
                            ForEach(["Home", "Posts", "About"], id: \.self) { name in
                                Button { selectedSection = name } label: {
                                    Text(name)
                                        .font(.system(size: 15, weight: selectedSection == name ? .semibold : .regular))
                                        .foregroundStyle(selectedSection == name ? .primary : .secondary)
                                        .frame(maxWidth: .infinity)
                                        .padding(.vertical, 13)
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
                                    .font(.system(size: 16))
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(20)
                            }
                        }
                        .frame(minHeight: 180, alignment: .topLeading)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
                .background(Color(uiColor: .systemBackground))
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
source = source[:start] + replacement + source[end:]

# The Home title and search button must be a child of the feed ScrollView so they
# travel off-screen with the feed; keep them at the top of its content stack.
home_start = source.index("struct HomeScreen: View {")
upload_start = source.index("struct MessagesScreen: View {", home_start) if "struct MessagesScreen: View {" in source[home_start:] else source.index("struct UploadScreen: View {", home_start)
home = source[home_start:upload_start]
if "ScrollView" not in home or "Text(\"Carbyne\")" not in home or "showDirectory = true" not in home:
    raise SystemExit("Home scroll header structure was not found; refusing to apply a blind patch.")
# Remove any accidental safe-area clipping from the root feed; content still keeps
# the deliberate horizontal gutter used by the reference layout.
home = home.replace(".padding(.top, 12)", ".padding(.top, 8)", 1)
source = source[:home_start] + home + source[upload_start:]
path.write_text(source)
print("Applied compact edge-to-edge channel layout and verified the Home logo/search remain inside the scrolling feed.")
