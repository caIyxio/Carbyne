from pathlib import Path

source = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")
if not source.is_file():
    raise SystemExit(f"Swift tab controller not found: {source}")

text = source.read_text()

old_symbols = """    private static let symbols = [
        "house.fill",
        "movieclapper.fill",
        "plus.square.fill",
        "bubble.left.and.bubble.right.fill",
        "person.crop.circle"
    ]"""

new_symbols = """    // SF Symbols resolve against the symbol library provided by the running OS.
    // Use outline/filled pairs for the four action tabs. The fifth tab remains
    // the account-avatar slot and is replaced with the user's live profile image.
    private static let unselectedSymbols = [
        "house",
        "movieclapper",
        "plus.app",
        "bubble.left.and.bubble.right",
        "person.crop.circle"
    ]
    private static let selectedSymbols = [
        "house.fill",
        "movieclapper.fill",
        "plus.app.fill",
        "bubble.left.and.bubble.right.fill",
        "person.crop.circle.fill"
    ]"""

if old_symbols not in text:
    raise SystemExit("Expected original five-tab symbol array was not found; refusing to guess.")

text = text.replace(old_symbols, new_symbols, 1)

old_images = """                image: UIImage(systemName: Self.symbols[index]),
                selectedImage: UIImage(systemName: Self.symbols[index])"""
new_images = """                image: UIImage(systemName: Self.unselectedSymbols[index]),
                selectedImage: UIImage(systemName: Self.selectedSymbols[index])"""

if old_images not in text:
    raise SystemExit("Expected tab bar image initializer was not found; refusing to guess.")

text = text.replace(old_images, new_images, 1)

if text.count("Self.unselectedSymbols[index]") != 1 or text.count("Self.selectedSymbols[index]") != 1:
    raise SystemExit("Tab icon update validation failed.")
if '"person.crop.circle"' not in text or '"person.crop.circle.fill"' not in text:
    raise SystemExit("The avatar fallback symbol must remain intact.")

source.write_text(text)
print("Updated four action tabs to SF Symbols outline/filled pairs; profile avatar slot preserved.")
