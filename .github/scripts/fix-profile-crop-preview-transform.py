from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()

# Normalize once and use the same upright dimensions for both preview and export.
source = source.replace(
    "    private var aspect: CGFloat { kind == .avatar ? 1 : 3 }",
    "    private var aspect: CGFloat { kind == .avatar ? 1 : 3 }\n    private var previewImage: UIImage { image.carbyneUpright() }",
    1
)
source = source.replace(
    "let baseScale = max(geometry.size.width / image.size.width, geometry.size.height / image.size.height)",
    "let baseScale = max(geometry.size.width / previewImage.size.width, geometry.size.height / previewImage.size.height)",
    1
)
source = source.replace(
    "Image(uiImage: image)\n                            .resizable()\n                            .frame(width: image.size.width * baseScale * zoom,\n                                   height: image.size.height * baseScale * zoom)",
    "Image(uiImage: previewImage)\n                            .resizable()\n                            .frame(width: previewImage.size.width * baseScale * zoom,\n                                   height: previewImage.size.height * baseScale * zoom)",
    1
)
source = source.replace(
    "let drawWidth = image.size.width * baseScale * zoom\n                                let drawHeight = image.size.height * baseScale * zoom",
    "let drawWidth = previewImage.size.width * baseScale * zoom\n                                let drawHeight = previewImage.size.height * baseScale * zoom",
    1
)

start = source.find("    private func renderCrop() throws -> UIImage {")
end = source.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate renderCrop; refusing unsafe edit.")
crop = source[start:end]
crop = crop.replace("image.size.width", "upright.size.width")
crop = crop.replace("image.size.height", "upright.size.height")
source = source[:start] + crop + source[end:]

# Ensure the preview and exporter actually reference the same normalized image.
required = [
    "private var previewImage: UIImage { image.carbyneUpright() }",
    "Image(uiImage: previewImage)",
    "let normalizedSize = upright.size"
]
if not all(token in source for token in required):
    raise SystemExit("Crop preview/export alignment verification failed.")
path.write_text(source)
print("Aligned crop preview and export to the same upright UIImage dimensions.")
