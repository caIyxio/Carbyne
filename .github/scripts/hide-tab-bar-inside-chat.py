from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
content = content_path.read_text()

def replace_once(source, old, new, label):
    if new in source:
        return source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return source.replace(old, new, 1)

content = replace_once(content,
    "    @State private var selectedTab: CarbyneTab = .home\n",
    "    @State private var selectedTab: CarbyneTab = .home\n    @State private var isChatThreadOpen = false\n",
    "Add chat visibility state")
content = replace_once(content,
    "                    selection: $selectedTab,\n",
    "                    selection: $selectedTab,\n                    isChatThreadOpen: $isChatThreadOpen,\n",
    "Pass chat visibility to native tab controller")
content = replace_once(content,
    "            MessagesScreen(openAuth: { showAuth = true })\n",
    "            MessagesScreen(openAuth: { showAuth = true }, setTabBarHidden: { isChatThreadOpen = $0 })\n",
    "Wire iPad messages screen")
content = replace_once(content,
    "struct MessagesScreen: View {\n    @EnvironmentObject private var store: CarbyneStore\n    let openAuth: () -> Void\n",
    "struct MessagesScreen: View {\n    @EnvironmentObject private var store: CarbyneStore\n    let openAuth: () -> Void\n    var setTabBarHidden: (Bool) -> Void = { _ in }\n",
    "Add MessagesScreen callback")
content = replace_once(content,
    "ChatThreadScreen(profile: conversation.profile)",
    "ChatThreadScreen(profile: conversation.profile, onTabBarVisibilityChange: setTabBarHidden)",
    "Connect chat thread visibility")

start = content.index("struct ChatThreadScreen: View {")
end = content.find("\nstruct ", start + 10)
if end < 0: end = len(content)
chat = content[start:end]
chat = replace_once(chat,
    "    let profile: CarbyneProfile\n",
    "    let profile: CarbyneProfile\n    var onTabBarVisibilityChange: (Bool) -> Void = { _ in }\n",
    "Add ChatThreadScreen callback")
if ".onAppear { onTabBarVisibilityChange(true) }" not in chat:
    if "        .task {\n" not in chat:
        raise SystemExit("ChatThreadScreen task modifier not found")
    chat = chat.replace("        .task {\n", "        .onAppear { onTabBarVisibilityChange(true) }\n        .task {\n", 1)
if "onTabBarVisibilityChange(false)" not in chat:
    old = "        .onDisappear {\n            if store.activeChatProfile?.id == profile.id { store.activeChatProfile = nil }\n        }"
    if old not in chat: raise SystemExit("ChatThreadScreen onDisappear block not found")
    chat = chat.replace(old, "        .onDisappear {\n            onTabBarVisibilityChange(false)\n            if store.activeChatProfile?.id == profile.id { store.activeChatProfile = nil }\n        }", 1)
content = content[:start] + chat + content[end:]
content_path.write_text(content)

controller_path = root / "CarbyneNativeTabController.swift"
controller = controller_path.read_text()
controller = replace_once(controller,
    "    @Binding var selection: CarbyneTab\n",
    "    @Binding var selection: CarbyneTab\n    @Binding var isChatThreadOpen: Bool\n",
    "Add chat visibility binding")
controller = replace_once(controller,
    "        controller.tabBar.isTranslucent = true\n",
    "        controller.tabBar.isTranslucent = true\n        controller.tabBar.isHidden = isChatThreadOpen\n        controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0\n",
    "Set initial tab bar visibility")
controller = replace_once(controller,
    "        context.coordinator.selection = $selection\n",
    "        context.coordinator.selection = $selection\n        if controller.tabBar.isHidden != isChatThreadOpen {\n            controller.tabBar.isHidden = isChatThreadOpen\n            controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0\n            controller.view.setNeedsLayout()\n            controller.view.layoutIfNeeded()\n        }\n",
    "Update tab bar visibility")
controller = replace_once(controller,
    "                MessagesScreen(openAuth: showAuth)\n",
    "                MessagesScreen(openAuth: showAuth, setTabBarHidden: { isChatThreadOpen = $0 })\n",
    "Wire native messages screen")
controller_path.write_text(controller)
print("Chat threads now hide the native tab bar and restore it when leaving the thread.")
