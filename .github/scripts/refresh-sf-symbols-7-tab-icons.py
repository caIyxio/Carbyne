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

new_symbols = """    // Match the reference navigation glyphs, not merely filled variants
    // of the previous symbols. The fifth tab is still the live account avatar.
    private static let symbols = [
        "house.fill",
        "play.rectangle",
        "paperplane",
        "magnifyingglass",
        "person.crop.circle"
    ]"""

if old_symbols in text:
    text = text.replace(old_symbols, new_symbols, 1)
else:
    old_pair = """    // SF Symbols resolve against the symbol library provided by the running OS.
    // Use outline/filled pairs for the four action tabs. The fifth tab remains
    // the account-avatar slot and is replaced with the user's live profile image.
    private static let unselectedSymbols = [
        "house",
        "movieclapper",
        "plus.app",
        "paperplane",
        "person.crop.circle"
    ]
    private static let selectedSymbols = [
        "house.fill",
        "movieclapper.fill",
        "plus.app.fill",
        "paperplane.fill",
        "person.crop.circle.fill"
    ]"""
    new_pair = """    // Match the reference navigation glyphs, not merely filled variants
    // of the previous symbols. The fifth tab is still the live account avatar.
    private static let symbols = [
        "house.fill",
        "play.rectangle",
        "paperplane",
        "magnifyingglass",
        "person.crop.circle"
    ]"""
    if old_pair not in text:
        raise SystemExit("Expected prior tab symbol definitions were not found; refusing to guess.")
    text = text.replace(old_pair, new_pair, 1)

old_images_pair = """                image: UIImage(systemName: Self.unselectedSymbols[index]),
                selectedImage: UIImage(systemName: Self.selectedSymbols[index])"""
new_images_pair = """                image: UIImage(systemName: Self.symbols[index]),
                selectedImage: UIImage(systemName: Self.symbols[index])"""
if old_images_pair in text:
    text = text.replace(old_images_pair, new_images_pair, 1)

if "Self.symbols[index]" not in text:
    old_images = """                image: UIImage(systemName: Self.symbols[index]),
                selectedImage: UIImage(systemName: Self.symbols[index])"""
    if old_images not in text:
        raise SystemExit("Expected tab bar image initializer was not found; refusing to guess.")

for symbol in ('"house.fill"', '"play.rectangle"', '"paperplane"', '"magnifyingglass"'):
    if symbol not in text:
        raise SystemExit(f"Missing expected reference symbol: {symbol}")
if '"person.crop.circle"' not in text:
    raise SystemExit("The profile avatar fallback must remain intact.")

source.write_text(text)
print("Applied reference glyphs: filled home, play-in-rectangle Spotlights, paper-plane DMs, magnifying-glass Search; preserved live avatar.")
