from pathlib import Path

path = Path("ios/Carbyne/Sources/AccountSheets.swift")
source = path.read_text()
start = source.find("    private func renderCrop() throws -> UIImage {")
end = source.find("\n    }\n}", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate crop renderer; refusing unsafe edit.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        // Work in decoded source pixels from end to end. This avoids both
        // SwiftUI snapshot rendering and UIKit's second image-drawing pass.
        let upright = previewImage
        guard let sourceCG = upright.cgImage,
              upright.size.width > 0, upright.size.height > 0 else {
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

        let baseScale = max(viewport.width / upright.size.width,
                            viewport.height / upright.size.height)
        let displayedWidth = upright.size.width * baseScale * zoom
        let displayedHeight = upright.size.height * baseScale * zoom
        let maxX = max((displayedWidth - viewport.width) / 2, 0)
        let maxY = max((displayedHeight - viewport.height) / 2, 0)
        let dragX = min(max(offset.width, -maxX), maxX)
        let dragY = min(max(offset.height, -maxY), maxY)

        let sourceOriginX = ((displayedWidth - viewport.width) / 2 - dragX) / (baseScale * zoom)
        let sourceOriginY = ((displayedHeight - viewport.height) / 2 - dragY) / (baseScale * zoom)
        let pixelsPerPointX = CGFloat(sourceCG.width) / upright.size.width
        let pixelsPerPointY = CGFloat(sourceCG.height) / upright.size.height

        let rawX = sourceOriginX * pixelsPerPointX
        let rawY = sourceOriginY * pixelsPerPointY
        let rawWidth = (viewport.width / (baseScale * zoom)) * pixelsPerPointX
        let rawHeight = (viewport.height / (baseScale * zoom)) * pixelsPerPointY
        let left = max(0, min(rawX, CGFloat(sourceCG.width) - 1))
        let top = max(0, min(rawY, CGFloat(sourceCG.height) - 1))
        let width = min(rawWidth, CGFloat(sourceCG.width) - left)
        let height = min(rawHeight, CGFloat(sourceCG.height) - top)
        guard width >= 1, height >= 1 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected crop is outside the image. Please reposition it and try again."])
        }

        // CIImage coordinates have a bottom-left origin; convert the preview's
        // top-left source rectangle before cropping.
        let ciRect = CGRect(x: left,
                            y: CGFloat(sourceCG.height) - top - height,
                            width: width,
                            height: height)
        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let cropped = CIImage(cgImage: sourceCG).cropped(to: ciRect)
        let originNormalized = cropped.transformed(
            by: CGAffineTransform(translationX: -ciRect.minX, y: -ciRect.minY)
        )
        let scaled = originNormalized.transformed(
            by: CGAffineTransform(scaleX: target.width / width,
                                  y: target.height / height)
        )
        let outputRect = CGRect(origin: .zero, size: target)
        guard let outputCG = CIContext(options: nil).createCGImage(scaled, from: outputRect),
              outputCG.width == Int(target.width),
              outputCG.height == Int(target.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return UIImage(cgImage: outputCG, scale: 1, orientation: .up)
    }'''
source = source[:start] + replacement + source[end + 6:]

# The crop output already has the exact upload dimensions. Encode its CGImage
# directly rather than redrawing it through another renderer.
store_path = Path("ios/Carbyne/Sources/CarbyneStore.swift")
store = store_path.read_text()
needle = '''        let image = source.normalizedOrientation()
        guard image.size.width > 0, image.size.height > 0 else { throw NSError(domain: "Carbyne", code: 422, userInfo: [NSLocalizedDescriptionKey: "The selected image is invalid."]) }
        let format = UIGraphicsImageRendererFormat()'''
replacement_store = '''        let image = source.normalizedOrientation()
        guard image.size.width > 0, image.size.height > 0 else { throw NSError(domain: "Carbyne", code: 422, userInfo: [NSLocalizedDescriptionKey: "The selected image is invalid."]) }
        if let cgImage = image.cgImage,
           cgImage.width == Int(targetSize.width),
           cgImage.height == Int(targetSize.height) {
            let upright = UIImage(cgImage: cgImage, scale: 1, orientation: .up)
            for quality in [0.90, 0.84, 0.78, 0.72, 0.66, 0.60] {
                if let data = upright.jpegData(compressionQuality: quality),
                   data.count <= 5 * 1024 * 1024 {
                    return data
                }
            }
            throw NSError(domain: "Carbyne", code: 413, userInfo: [NSLocalizedDescriptionKey: "This image exceeds the 5 MB upload limit."])
        }
        let format = UIGraphicsImageRendererFormat()'''
if needle not in store:
    raise SystemExit("Could not locate JPEG encoder; refusing unsafe edit.")
store = store.replace(needle, replacement_store, 1)

path.write_text(source)
store_path.write_text(store)
print("Replaced crop export with direct CI pixel cropping and bypassed the redundant UIKit redraw during JPEG encoding.")
