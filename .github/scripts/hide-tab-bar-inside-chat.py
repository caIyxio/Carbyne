from pathlib import Path

sources = Path('ios/Carbyne/Sources')
content_path = sources / 'ContentView.swift'
content = content_path.read_text()

def once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        raise SystemExit(f'{label}: expected one match, got {n}')
    return text.replace(old, new, 1)

content = once(content,
'''    @State private var navigationPath: [CarbyneNavigationRoute] = []
    @State private var showDevelopmentNotice = false
''',
'''    @State private var navigationPath: [CarbyneNavigationRoute] = []
    @State private var isChatThreadOpen = false
    @State private var showDevelopmentNotice = false
''', 'Add chat visibility state')
content = once(content,
'''                    navigationPath: $navigationPath,
                    showAuth: { showAuth = true },
''',
'''                    navigationPath: $navigationPath,
                    isChatThreadOpen: $isChatThreadOpen,
                    showAuth: { showAuth = true },
''', 'Pass chat visibility into UIKit tab controller')
content = once(content,
'''        case .messages:
            MessagesScreen(openAuth: { showAuth = true })
''',
'''        case .messages:
            MessagesScreen(openAuth: { showAuth = true },
                           setTabBarHidden: { isChatThreadOpen = $0 })
''', 'Wire iPad message screen visibility')
content = once(content,
'''struct MessagesScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void
    @State private var showNewMessage = false
''',
'''struct MessagesScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void
    var setTabBarHidden: (Bool) -> Void = { _ in }
    @State private var showNewMessage = false
''', 'Add tab bar visibility callback to messages screen')
content = once(content,
'''                        NavigationLink {
                            ChatThreadScreen(profile: conversation.profile)
''',
'''                        NavigationLink {
                            ChatThreadScreen(profile: conversation.profile,
                                             onTabBarVisibilityChange: setTabBarHidden)
''', 'Connect conversation navigation to tab bar visibility')
content = once(content,
'''struct ChatThreadScreen: View {
    @Environment(\\.dismiss) private var dismiss
    @EnvironmentObject private var store: CarbyneStore
    let profile: CarbyneProfile
''',
'''struct ChatThreadScreen: View {
    @Environment(\\.dismiss) private var dismiss
    @EnvironmentObject private var store: CarbyneStore
    let profile: CarbyneProfile
    var onTabBarVisibilityChange: (Bool) -> Void = { _ in }
''', 'Add chat thread visibility callback')
content = once(content,
'''        .onChange(of: selectedPhoto) { _, item in
''',
'''        .onAppear { onTabBarVisibilityChange(true) }
        .onChange(of: selectedPhoto) { _, item in
''', 'Hide tab bar when a chat thread appears')
content = once(content,
'''        .onDisappear {
            if store.activeChatProfile?.id == profile.id { store.activeChatProfile = nil }
        }
''',
'''        .onDisappear {
            onTabBarVisibilityChange(false)
            if store.activeChatProfile?.id == profile.id { store.activeChatProfile = nil }
        }
''', 'Restore tab bar when leaving a chat thread')
content_path.write_text(content)

controller_path = sources / 'CarbyneNativeTabController.swift'
controller = controller_path.read_text()
controller = once(controller,
'''    @Binding var navigationPath: [CarbyneNavigationRoute]
    let showAuth: () -> Void
''',
'''    @Binding var navigationPath: [CarbyneNavigationRoute]
    @Binding var isChatThreadOpen: Bool
    let showAuth: () -> Void
''', 'Add chat visibility binding to native tab controller')
controller = once(controller,
'''        controller.tabBar.isTranslucent = true

        let children = makeHostingControllers()
''',
'''        controller.tabBar.isTranslucent = true
        controller.tabBar.isHidden = isChatThreadOpen

        let children = makeHostingControllers()
''', 'Set initial native tab bar visibility')
controller = once(controller,
'''        context.coordinator.selection = $selection

        let roots = makeRootViews()
''',
'''        context.coordinator.selection = $selection
        if controller.tabBar.isHidden != isChatThreadOpen {
            controller.tabBar.isHidden = isChatThreadOpen
        }

        let roots = makeRootViews()
''', 'Update native tab bar visibility as chat opens and closes')
controller = once(controller,
'''                MessagesScreen(openAuth: showAuth)
                    .ignoresSafeArea(.container, edges: .all)
''',
'''                MessagesScreen(openAuth: showAuth,
                               setTabBarHidden: { isChatThreadOpen = $0 })
                    .ignoresSafeArea(.container, edges: .all)
''', 'Wire iPhone messages screen to native tab bar')
controller_path.write_text(controller)
print('Chat threads now hide the native bottom tab bar and restore it when leaving the thread.')
