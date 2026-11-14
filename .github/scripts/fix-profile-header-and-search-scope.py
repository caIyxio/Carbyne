from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
source = path.read_text()

# The previous navigation rewrite accidentally left the HomeScreen shortcut
# referring to ContentView's private path. HomeScreen must invoke its action.
home_start = source.index("struct HomeScreen: View {")
home_end = source.index("\nstruct MessagesScreen: View {", home_start)
home = source[home_start:home_end]
bad = "Button { navigationPath.append(.search) } label: {"
if bad not in home:
    raise SystemExit("Expected misplaced Search path reference was not found in HomeScreen.")
home = home.replace(bad, "Button { openSearch() } label: {", 1)
source = source[:home_start] + home + source[home_end:]

# Place Subscribe at the trailing edge of the creator identity row, using the
# free space beside the name/handle instead of a separate full-width row.
public_start = source.index("struct PublicChannelScreen: View {")
public_end = source.index("\nstruct ChannelDirectorySheet: View {", public_start)
public = source[public_start:public_end]

button_start = public.index("                    Button {\n                        Task { await store.toggleSubscription() }")
button_end_marker = "                    .padding(.bottom, 12)\n"
button_end = public.index(button_end_marker, button_start) + len(button_end_marker)
button = public[button_start:button_end]
public = public[:button_start] + public[button_end:]
button = button.replace("                    .padding(.horizontal, 16)\n", "")
button = button.replace("                    .padding(.bottom, 12)\n", "")
button = button.replace(".font(.system(size: 14, weight: .semibold))", ".font(.system(size: 12, weight: .semibold))")
button = button.replace(".padding(.horizontal, 18)", ".padding(.horizontal, 10)")
button = button.replace(".padding(.vertical, 10)", ".padding(.vertical, 7)")
button = button.replace("                    .buttonStyle(.plain)", "                    .buttonStyle(.plain)\n                    .fixedSize(horizontal: true, vertical: false)")
header_anchor = "                        Spacer(minLength: 0)\n                    }"
if header_anchor not in public:
    raise SystemExit("Could not find the public-profile identity row trailing spacer.")
public = public.replace(
    header_anchor,
    "                        Spacer(minLength: 8)\n" + button + "                    }",
    1,
)
public = public.replace("HStack(alignment: .top, spacing: 12)", "HStack(alignment: .center, spacing: 12)", 1)
source = source[:public_start] + public + source[public_end:]

if "navigationPath.append(.search)" in home:
    raise SystemExit("HomeScreen still references ContentView navigation state.")
if "Task { await store.toggleSubscription() }" not in public:
    raise SystemExit("Subscribe action was lost while moving the button.")
path.write_text(source)
print("Fixed the Home Search action scope and moved Subscribe beside the public creator identity.")
