from pathlib import Path

path = Path("ios/Carbyne/Sources/ContentView.swift")
source = path.read_text()
start = source.index("struct PublicChannelScreen: View {")
end = source.index("\nstruct ChannelDirectorySheet: View {", start)
screen = source[start:end]
needle = """            .background(Color.clear)

            Button { dismiss() } label: {"""
replacement = """            .background(Color.clear)
            .ignoresSafeArea(.container, edges: .top)

            Button { dismiss() } label: {"""
if needle not in screen:
    raise SystemExit("PublicChannelScreen ScrollView anchor not found; refusing to patch the wrong view.")
if ".ignoresSafeArea(.container, edges: .top)" not in screen:
    screen = screen.replace(needle, replacement, 1)
    source = source[:start] + screen + source[end:]
    path.write_text(source)
print("Public profile ScrollView now extends behind the top status-bar safe area.")
