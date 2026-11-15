from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()

# Use the exact same orientation-normalized UIImage and dimensions in the preview
# and the source-pixel exporter. UIImage.size can otherwise disagree with cgImage
# dimensions for EXIF-rotated photos.
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
source = source.replace("Image(uiImage: image)\n                            .resizable()\n                            .frame(width: image.size.width * baseScale * zoom,\n                                   height: image.size.height * baseScale * zoom)",
                        "Image(uiImage: previewImage)\n                            .resizable()\n                            .frame(width: previewImage.size.width * baseScale * zoom,\n                                   height: previewImage.size.height * baseScale * zoom)", 1)
source = source.replace("let drawWidth = image.size.width * baseScale * zoom\n                                let drawHeight = image.size.height * baseScale * zoom",
                        "let drawWidth = previewImage.size.width * baseScale * zoom\n                                let drawHeight = previewImage.size.height * baseScale * zoom", 1)

# The zoom slider can change the valid drag range. Clamp the shared preview/export
# offset immediately so the preview never shows a position the exporter later alters.
needle = """                .padding(20)
            }
            .navigationTitle("Adjust image")"""
replacement = """                .padding(20)
            }
            .onChange(of: zoom) { _, _ in
                let viewport = cropAreaSize
                guard viewport.width > 0, viewport.height > 0 else { return }
                let baseScale = max(viewport.width / previewImage.size.width,
                                    viewport.height / previewImage.size.height)
                let drawWidth = previewImage.size.width * baseScale * zoom
                let drawHeight = previewImage.size.height * baseScale * zoom
                let maxX = max((drawWidth - viewport.width) / 2, 0)
                let maxY = max((drawHeight - viewport.height) / 2, 0)
                offset.width = min(max(offset.width, -maxX), maxX)
                offset.height = min(max(offset.height, -maxY), maxY)
                dragOrigin = offset
            }
            .navigationTitle("Adjust image")"""
if needle not in source:
    raise SystemExit("Could not locate crop sheet modifier insertion point.")
source = source.replace(needle, replacement, 1)

# Keep the export's aspect-fill transform in the same normalized point space
# as the actual preview image.
start = source.find("    private func renderCrop() throws -> UIImage {")
end = source.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate renderCrop; refusing unsafe edit.")
crop = source[start:end]
crop = crop.replace("image.size.width", "upright.size.width")
crop = crop.replace("image.size.height", "upright.size.height")
source = source[:start] + crop + source[end:]

path.write_text(source)
print("Aligned crop preview and export to the same upright UIImage dimensions; zoom changes now clamp the shared offset.")
