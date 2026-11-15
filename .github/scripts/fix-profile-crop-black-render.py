from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()
start = source.find("    private func renderCrop() throws -> UIImage {")
end = source.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate crop renderer; refusing unsafe edit.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        // Materialize a real CGImage first. Photos and edited images can be CIImage-backed,
        // and UIImage.draw(in:) on that backing was producing black exports on this path.
        let upright = image.carbyneUpright()
        let sourceCG: CGImage
        if let cg = upright.cgImage {
            sourceCG = cg
        } else if let ci = upright.ciImage,
                  let cg = CIContext(options: nil).createCGImage(ci, from: ci.extent) {
            sourceCG = cg
        } else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected photo could not be decoded. Please choose another image."])
        }

        let viewport = cropAreaSize == .zero
            ? CGSize(width: 320, height: 320 / aspect)
            : cropAreaSize
        guard viewport.width > 0, viewport.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The crop area is not ready yet. Please try again."])
        }

        // Reproduce the exact aspect-fill + zoom + drag transform used by the preview.
        let baseScale = max(viewport.width / image.size.width,
                            viewport.height / image.size.height)
        let drawSize = CGSize(width: image.size.width * baseScale * zoom,
                              height: image.size.height * baseScale * zoom)
        let previewRect = CGRect(
            x: (viewport.width - drawSize.width) / 2 + offset.width,
            y: (viewport.height - drawSize.height) / 2 + offset.height,
            width: drawSize.width,
            height: drawSize.height
        )
        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let outputRect = CGRect(
            x: previewRect.minX * target.width / viewport.width,
            y: previewRect.minY * target.height / viewport.height,
            width: previewRect.width * target.width / viewport.width,
            height: previewRect.height * target.height / viewport.height
        )

        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = false
        let renderer = UIGraphicsImageRenderer(size: target, format: format)
        let result = renderer.image { rendererContext in
            let cg = rendererContext.cgContext
            cg.saveGState()
            // Core Graphics uses a bottom-left origin; the crop math is top-left.
            cg.translateBy(x: 0, y: target.height)
            cg.scaleBy(x: 1, y: -1)
            cg.interpolationQuality = .high
            cg.draw(sourceCG, in: outputRect)
            cg.restoreGState()
        }

        guard let output = result.cgImage,
              output.width == Int(target.width),
              output.height == Int(target.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        // Reject a blank export instead of silently uploading it.
        let data = output.dataProvider?.data as Data?
        if let data, data.count >= 4 {
            let bytes = [UInt8](data.prefix(4))
            if bytes.allSatisfy({ $0 == 0 }) {
                throw NSError(domain: "CarbyneImage", code: 422,
                              userInfo: [NSLocalizedDescriptionKey: "The crop rendered blank. Please reposition the image and try again."])
            }
        }
        return result
    }'''
source = source[:start] + replacement + source[end:]
# Ensure Core Image is available for CIImage-backed picker images.
if "import CoreImage" not in source:
    source = source.replace("import SwiftUI", "import SwiftUI\nimport CoreImage", 1)

# Make orientation normalization materialize CIImage-backed images before drawing.
old = '''extension UIImage {
    func carbyneUpright() -> UIImage {
        guard imageOrientation != .up else { return self }
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = false
        return UIGraphicsImageRenderer(size: size, format: format).image { _ in
            draw(in: CGRect(origin: .zero, size: size))
        }
    }
}'''
new = '''extension UIImage {
    func carbyneUpright() -> UIImage {
        let materialized: UIImage
        if cgImage != nil {
            materialized = self
        } else if let ciImage,
                  let cg = CIContext(options: nil).createCGImage(ciImage, from: ciImage.extent) {
            materialized = UIImage(cgImage: cg, scale: scale, orientation: imageOrientation)
        } else {
            return self
        }
        guard materialized.imageOrientation != .up else { return materialized }
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = false
        return UIGraphicsImageRenderer(size: materialized.size, format: format).image { _ in
            materialized.draw(in: CGRect(origin: .zero, size: materialized.size))
        }
    }
}'''
if old not in source:
    raise SystemExit("Could not locate UIImage orientation helper; refusing unsafe edit.")
source = source.replace(old, new, 1)
path.write_text(source)
print("Replaced profile crop export with explicit CGImage materialization and Core Graphics drawing.")
