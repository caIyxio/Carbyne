from pathlib import Path

path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
source = path.read_text()

old_initial = """        controller.tabBar.isTranslucent = true
        controller.tabBar.isHidden = isChatThreadOpen

        let children = makeHostingControllers()
"""
new_initial = """        controller.tabBar.isTranslucent = true
        controller.tabBar.isHidden = isChatThreadOpen
        controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0

        let children = makeHostingControllers()
"""
if old_initial in source:
    source = source.replace(old_initial, new_initial, 1)
elif new_initial not in source:
    raise SystemExit("Initial tab bar visibility block not found")

old_update = """        if controller.tabBar.isHidden != isChatThreadOpen {
            controller.tabBar.isHidden = isChatThreadOpen
        }

        let roots = makeRootViews()
"""
new_update = """        if controller.tabBar.isHidden != isChatThreadOpen {
            controller.tabBar.isHidden = isChatThreadOpen
            controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0
            controller.view.setNeedsLayout()
            controller.view.layoutIfNeeded()
        }

        let roots = makeRootViews()
"""
if old_update in source:
    source = source.replace(old_update, new_update, 1)
elif new_update not in source:
    raise SystemExit("Tab bar update block not found")

path.write_text(source)
print("Removed the hidden tab bar's reserved bottom safe-area height while a chat is open.")
