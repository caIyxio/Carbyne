from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
store_path = Path("ios/Carbyne/Sources/CarbyneStore.swift")

content = content_path.read_text()
store = store_path.read_text()

if "@Environment(\\.colorScheme) private var colorScheme" not in content:
    anchor = "struct HomeScreen: View {\n    @EnvironmentObject private var store: CarbyneStore\n    @Environment(\\.horizontalSizeClass) private var sizeClass\n"
    if anchor not in content:
        raise SystemExit("HomeScreen environment declaration not found.")
    content = content.replace(
        anchor,
        anchor + "    @Environment(\\.colorScheme) private var colorScheme\n",
        1
    )

old_header = '''        .safeAreaInset(edge: .top, spacing: 0) {
            HStack {
                CarbyneWordmark(height: 34)
                Spacer()
                Button { openSearch() } label: {
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
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Search")
            }
            .padding(.horizontal, isPad ? 34 : 20)
            .padding(.vertical, 7)
            .background(.ultraThinMaterial)
        }'''

new_header = '''        .safeAreaInset(edge: .top, spacing: 0) {
            ZStack(alignment: .top) {
                LinearGradient(
                    stops: [
                        .init(color: colorScheme == .dark ? .black : .white, location: 0.0),
                        .init(color: colorScheme == .dark ? .black.opacity(0.78) : .white.opacity(0.78), location: 0.34),
                        .init(color: colorScheme == .dark ? .black.opacity(0.34) : .white.opacity(0.34), location: 0.72),
                        .init(color: colorScheme == .dark ? .black.opacity(0.0) : .white.opacity(0.0), location: 1.0)
                    ],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .frame(height: 184)
                .frame(maxWidth: .infinity)
                .ignoresSafeArea(edges: .top)
                .allowsHitTesting(false)

                HStack {
                    Button {
                        Task {
                            await store.loadChannels(force: true)
                            if let ownProfile = store.profile {
                                await store.refreshSubscription(for: ownProfile)
                            }
                        }
                    } label: {
                        CarbyneWordmark(height: 34)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Refresh Home")

                    Spacer()
                    Button { openSearch() } label: {
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
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Search")
                }
                .padding(.horizontal, isPad ? 34 : 20)
                .padding(.vertical, 7)
            }
            .frame(height: 56, alignment: .top)
        }'''

if old_header not in content:
    raise SystemExit("Expected original Home header block was not found.")
content = content.replace(old_header, new_header, 1)
content = content.replace(".background(CarbynePalette.background.ignoresSafeArea())\n        .safeAreaInset(edge: .top, spacing: 0) {", ".background(CarbynePalette.background)\n        .safeAreaInset(edge: .top, spacing: 0) {", 1)

old_method = '''    func loadChannels() async {
        guard let userID = session?.user.id else { return }
        if loadedChannelsForUserID == userID { return }'''
new_method = '''    func loadChannels(force: Bool = false) async {
        guard let userID = session?.user.id else { return }
        if loadedChannelsForUserID == userID && !force { return }'''
if old_method not in store:
    raise SystemExit("Expected loadChannels method was not found.")
store = store.replace(old_method, new_method, 1)

content_path.write_text(content)
store_path.write_text(store)
print("Applied adaptive light/dark Home gradient, tappable wordmark refresh, and forced channel reload.")
