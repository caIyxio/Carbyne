from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
source = content_path.read_text()

start = source.index("struct ContentView: View {")
end = source.index("struct HomeScreen: View {", start)

content_view = r'''struct ContentView: View {
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
                CarbyneNativeTabController(
                    store: store,
                    selection: $selectedTab,
                    showDirectory: $showDirectory,
                    showAuth: { showAuth = true },
                    showProfileEditor: { showProfileEditor = true },
                    showSecurity: { showSecurity = true },
                    selectChannel: openChannel
                )
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
        case .home:
            HomeScreen(showDirectory: $showDirectory, selectChannel: openChannel)
        case .moments:
            ContentUnavailableView("Moments", systemImage: "play.rectangle",
                description: Text("Moments will appear here."))
        case .upload:
            UploadScreen(openAuth: { showAuth = true })
        case .messages:
            MessagesScreen(openAuth: { showAuth = true })
        case .channel:
            ChannelScreen(openAuth: { showAuth = true },
                          openEditor: { showProfileEditor = true },
                          openSecurity: { showSecurity = true })
        }
    }

    private var iPadNavigation: some View {
        HStack(spacing: 5) {
            Spacer(minLength: 0)
            iPadTab("Home", .home, icon: "house.fill")
            iPadTab("Moments", .moments, icon: "play.rectangle.fill")
            iPadTab("Upload", .upload, icon: "plus.square.fill")
            iPadTab("Chat", .messages, icon: "bubble.left.and.bubble.right.fill")
            Button {
                openOwnProfile()
            } label: {
                AvatarView(url: store.publicImageURL(path: store.profile?.avatarPath), size: 20)
                    .padding(.horizontal, 6).padding(.vertical, 5)
                    .background(selectedTab == .channel ? Color.primary.opacity(0.08) : .clear, in: Capsule())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Profile")
            Spacer(minLength: 0)
            Button { showDirectory = true } label: {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 19, weight: .medium))
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Search")
        }
        .padding(6)
        .background {
            if #available(iOS 26.0, *) {
                Capsule().fill(.clear).glassEffect(.regular.interactive(), in: Capsule())
            } else {
                Capsule().fill(.ultraThinMaterial)
                    .overlay(Capsule().strokeBorder(Color.primary.opacity(0.08)))
            }
        }
        .padding(.horizontal, 26)
        .padding(.top, 10)
        .padding(.bottom, 8)
    }

    private func iPadTab(_ title: String, _ tab: CarbyneTab, icon: String) -> some View {
        Button {
            selectedTab = tab
            if tab == .home { Task { await store.loadChannels() } }
        } label: {
            Label(title, systemImage: icon)
                .font(.system(size: 13, weight: selectedTab == tab ? .semibold : .regular))
                .foregroundStyle(selectedTab == tab ? Color.accentColor : Color.primary)
                .padding(.horizontal, 12).padding(.vertical, 10)
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

'''
source = source[:start] + content_view + source[end:]
content_path.write_text(source)

tab_controller = r'''import SwiftUI
import UIKit

/// Hosts five independent SwiftUI roots inside UIKit's native tab controller.
///
/// Each tab receives a newly-created UIHostingController. Never reuse one hosting
/// controller for more than one tab: UIKit rejects a controller attached to multiple
/// UITab instances ("UIViewController cannot be shared between multiple UITab").
struct CarbyneNativeTabController: UIViewControllerRepresentable {
    let store: CarbyneStore
    @Binding var selection: CarbyneTab
    @Binding var showDirectory: Bool
    let showAuth: () -> Void
    let showProfileEditor: () -> Void
    let showSecurity: () -> Void
    let selectChannel: (CarbyneProfile) -> Void

    private static let tabs: [CarbyneTab] = [
        .home, .moments, .upload, .messages, .channel
    ]
    private static let titles = ["Home", "Moments", "Upload", "Chat", "Profile"]
    private static let symbols = [
        "house.fill",
        "play.rectangle.fill",
        "plus.square.fill",
        "bubble.left.and.bubble.right.fill",
        "person.crop.circle.fill"
    ]

    func makeCoordinator() -> Coordinator {
        Coordinator(selection: $selection)
    }

    func makeUIViewController(context: Context) -> UITabBarController {
        let controller = UITabBarController()
        controller.delegate = context.coordinator
        controller.view.backgroundColor = .clear

        let children = makeHostingControllers()
        let uniqueControllerCount = Set(children.map { ObjectIdentifier($0) }).count
        precondition(uniqueControllerCount == Self.tabs.count,
                     "Carbyne requires one unique hosting controller per tab.")

        controller.setViewControllers(children, animated: false)
        controller.selectedIndex = selectedIndex

        // Do not set standardAppearance or scrollEdgeAppearance here. UIKit owns
        // the native tab bar appearance, including Liquid Glass on iOS 26+.
        return controller
    }

    func updateUIViewController(_ controller: UITabBarController, context: Context) {
        context.coordinator.selection = $selection

        let roots = makeRootViews()
        let hosts = controller.viewControllers?.compactMap {
            $0 as? UIHostingController<AnyView>
        } ?? []

        if hosts.count != Self.tabs.count {
            let freshHosts = makeHostingControllers()
            precondition(Set(freshHosts.map { ObjectIdentifier($0) }).count == Self.tabs.count)
            controller.setViewControllers(freshHosts, animated: false)
        } else {
            // Update each existing host in place; the controller identities remain
            // distinct and stable for the lifetime of the tab bar controller.
            for index in Self.tabs.indices {
                hosts[index].rootView = roots[index]
            }
        }

        if controller.selectedIndex != selectedIndex {
            controller.selectedIndex = selectedIndex
        }

        context.coordinator.updateAvatar(
            url: store.publicImageURL(path: store.profile?.avatarPath),
            item: controller.tabBar.items?.last
        )
    }

    private var selectedIndex: Int {
        Self.tabs.firstIndex(of: selection) ?? 0
    }

    private func makeHostingControllers() -> [UIHostingController<AnyView>] {
        let roots = makeRootViews()
        return roots.enumerated().map { index, root in
            let host = UIHostingController(rootView: root)
            host.view.backgroundColor = .clear
            host.view.restorationIdentifier = "Carbyne.Tab.\(Self.titles[index])"
            host.tabBarItem = UITabBarItem(
                title: Self.titles[index],
                image: UIImage(systemName: Self.symbols[index]),
                selectedImage: UIImage(systemName: Self.symbols[index])
            )
            return host
        }
    }

    private func makeRootViews() -> [AnyView] {
        [
            AnyView(
                HomeScreen(showDirectory: $showDirectory, selectChannel: selectChannel)
                    .environmentObject(store)
            ),
            AnyView(
                ContentUnavailableView("Moments", systemImage: "play.rectangle",
                    description: Text("Moments will appear here."))
                    .environmentObject(store)
            ),
            AnyView(
                UploadScreen(openAuth: showAuth)
                    .environmentObject(store)
            ),
            AnyView(
                MessagesScreen(openAuth: showAuth)
                    .environmentObject(store)
            ),
            AnyView(
                ChannelScreen(openAuth: showAuth,
                              openEditor: showProfileEditor,
                              openSecurity: showSecurity)
                    .environmentObject(store)
            )
        ]
    }

    @MainActor
    final class Coordinator: NSObject, UITabBarControllerDelegate {
        var selection: Binding<CarbyneTab>
        private var requestedAvatarURL: URL?
        private var avatarTask: Task<Void, Never>?

        init(selection: Binding<CarbyneTab>) {
            self.selection = selection
        }

        func tabBarController(_ tabBarController: UITabBarController,
                              didSelect viewController: UIViewController) {
            guard let index = tabBarController.viewControllers?.firstIndex(of: viewController),
                  CarbyneNativeTabController.tabs.indices.contains(index) else { return }
            selection.wrappedValue = CarbyneNativeTabController.tabs[index]
        }

        func updateAvatar(url: URL?, item: UITabBarItem?) {
            guard url != requestedAvatarURL else { return }
            requestedAvatarURL = url
            avatarTask?.cancel()
            item?.image = UIImage(systemName: "person.crop.circle.fill")
            item?.selectedImage = UIImage(systemName: "person.crop.circle.fill")

            guard let url, let item else { return }
            avatarTask = Task { [weak self, weak item] in
                do {
                    let (data, _) = try await URLSession.shared.data(from: url)
                    guard !Task.isCancelled, let image = UIImage(data: data) else { return }
                    let icon = Self.circularAvatar(image)
                    guard !Task.isCancelled, self?.requestedAvatarURL == url else { return }
                    item?.image = icon
                    item?.selectedImage = icon
                } catch {
                    // Keep the system profile glyph if the avatar is unavailable.
                }
            }
        }

        private static func circularAvatar(_ image: UIImage) -> UIImage {
            let size = CGSize(width: 24, height: 24)
            let renderer = UIGraphicsImageRenderer(size: size)
            return renderer.image { context in
                let rect = CGRect(origin: .zero, size: size)
                UIBezierPath(ovalIn: rect.insetBy(dx: 1, dy: 1)).addClip()
                image.draw(in: rect)
                context.cgContext.setStrokeColor(UIColor.white.withAlphaComponent(0.9).cgColor)
                context.cgContext.setLineWidth(2)
                context.cgContext.strokeEllipse(in: rect.insetBy(dx: 1, dy: 1))
            }.withRenderingMode(.alwaysOriginal)
        }

        deinit {
            avatarTask?.cancel()
        }
    }
}

'''
(root / "CarbyneNativeTabController.swift").write_text(tab_controller)
print("Installed distinct UIKit-hosted tabs and native system tab bar.")
