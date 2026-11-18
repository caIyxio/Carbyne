from pathlib import Path

path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
source = path.read_text()

line_initial = "        controller.tabBar.isHidden = isChatThreadOpen\n"
insert_initial = line_initial + "        controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0\n"
if "controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0" not in source:
    if source.count(line_initial) == 0:
        candidates = [line for line in source.splitlines(keepends=True) if ".tabBar.isHidden = isChatThreadOpen" in line]
        if not candidates:
            raise SystemExit("No tab bar visibility assignment found in native tab controller")
        line_initial = candidates[0]
        indent = line_initial[:len(line_initial) - len(line_initial.lstrip())]
        insert_initial = line_initial + indent + "controller.additionalSafeAreaInsets.bottom = isChatThreadOpen ? -controller.tabBar.bounds.height : 0\n"
    source = source.replace(line_initial, insert_initial, 1)

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
