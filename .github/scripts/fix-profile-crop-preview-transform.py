from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()

# Normalize the source once; the exact same UIImage is used by preview and export.
if "import SwiftUI" not in source:
    raise SystemExit("SwiftUI import not found.")
if "private var previewImage: UIImage { image.carbyneUpright() }" not in source:
    source = source.replace(
        "    private var aspect: CGFloat { kind == .avatar ? 1 : 3 }",
        "    private var aspect: CGFloat { kind == .avatar ? 1 : 3 }\n"
        "    private var previewImage: UIImage { image.carbyneUpright() }",
        1
    )

# Extract the exact visual layer into one reusable SwiftUI view.
body_start = source.find("struct ProfileImageCropSheet: View {")
body_end = source.find("\nstruct ProfileEditorSheet", body_start)
if body_start < 0 or body_end < 0:
    raise SystemExit("Could not locate ProfileImageCropSheet.")
sheet = source[body_start:body_end]

old_image = """                        Image(uiImage: image)
                            .resizable()
                            .frame(width: image.size.width * baseScale * zoom,
                                   height: image.size.height * baseScale * zoom)
                            .offset(offset)"""
new_image = """                        Image(uiImage: previewImage)
                            .resizable()
                            .frame(width: previewImage.size.width * baseScale * zoom,
                                   height: previewImage.size.height * baseScale * zoom)
                            .offset(offset)"""
if old_image in sheet:
    sheet = sheet.replace(old_image, new_image, 1)
elif "Image(uiImage: previewImage)" not in sheet:
    raise SystemExit("Could not locate preview image layer.")

sheet = sheet.replace(
    "let baseScale = max(geometry.size.width / image.size.width, geometry.size.height / image.size.height)",
    "let baseScale = max(geometry.size.width / previewImage.size.width, geometry.size.height / previewImage.size.height)",
    1
)
sheet = sheet.replace(
    "let drawWidth = image.size.width * baseScale * zoom\n"
    "                                let drawHeight = image.size.height * baseScale * zoom",
    "let drawWidth = previewImage.size.width * baseScale * zoom\n"
    "                                let drawHeight = previewImage.size.height * baseScale * zoom",
    1
)

start = sheet.find("    private func renderCrop() throws -> UIImage {")
end = sheet.find("\n    }", start)
# Find the matching function close by brace counting, not a fragile substring.
if start < 0:
    raise SystemExit("Could not locate renderCrop.")
brace = sheet.find("{", start)
depth = 0
finish = None
for i in range(brace, len(sheet)):
    if sheet[i] == "{":
        depth += 1
    elif sheet[i] == "}":
        depth -= 1
        if depth == 0:
            finish = i + 1
            break
if finish is None:
    raise SystemExit("Could not parse renderCrop function.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        let viewport = cropAreaSize == .zero
            ? CGSize(width: 320, height: 320 / aspect)
            : cropAreaSize
        guard viewport.width > 0, viewport.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The crop area is not ready yet. Please try again."])
        }

        // Render the very same SwiftUI image layer used in the live preview.
        // This avoids maintaining a second, subtly different UIKit/CoreGraphics
        // coordinate transform for zoom, drag, orientation, and point/pixel scale.
        let baseScale = max(viewport.width / previewImage.size.width,
                            viewport.height / previewImage.size.height)
        let previewLayer = ZStack {
            Color.black
            Image(uiImage: previewImage)
                .resizable()
                .frame(width: previewImage.size.width * baseScale * zoom,
                       height: previewImage.size.height * baseScale * zoom)
                .offset(offset)
        }
        .frame(width: viewport.width, height: viewport.height)
        .clipped()

        let snapshot = ImageRenderer(content: previewLayer)
        snapshot.proposedSize = ProposedViewSize(width: viewport.width, height: viewport.height)
        snapshot.scale = 1
        guard let previewImageOutput = snapshot.uiImage else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The crop preview could not be rendered. Please try again."])
        }

        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let result = UIGraphicsImageRenderer(size: target, format: format).image { _ in
            previewImageOutput.draw(in: CGRect(origin: .zero, size: target))
        }
        guard let cg = result.cgImage,
              cg.width == Int(target.width),
              cg.height == Int(target.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return result
    }'''
sheet = sheet[:start] + replacement + sheet[finish:]
source = source[:body_start] + sheet + source[body_end:]

if "ImageRenderer(content: previewLayer)" not in source:
    raise SystemExit("ImageRenderer snapshot was not installed.")
path.write_text(source)
print("Export now snapshots the exact SwiftUI preview image layer, then scales that snapshot to the upload dimensions.")
