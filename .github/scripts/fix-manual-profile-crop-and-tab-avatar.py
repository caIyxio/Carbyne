from pathlib import Path

account_path = Path("ios/Carbyne/Sources/AccountSheets.swift")
tab_path = Path("ios/Carbyne/Sources/CarbyneNativeTabController.swift")

account = account_path.read_text()
start = account.find("    private func renderCrop() throws -> UIImage {")
end = account.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate the current profile crop renderer; refusing unsafe edit.")

replacement = r'''    private func renderCrop() throws -> UIImage {
        let normalized = image.carbyneUpright()
        guard let source = normalized.cgImage,
              normalized.size.width > 0,
              normalized.size.height > 0 else {
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

        // Match the preview's aspect-fill scale and its exact drag/zoom transform.
        let previewScale = max(viewport.width / normalized.size.width,
                               viewport.height / normalized.size.height) * zoom
        let visibleWidth = viewport.width / previewScale
        let visibleHeight = viewport.height / previewScale
        let sourceRectInPoints = CGRect(
            x: (normalized.size.width - visibleWidth) / 2 - offset.width / previewScale,
            y: (normalized.size.height - visibleHeight) / 2 - offset.height / previewScale,
            width: visibleWidth,
            height: visibleHeight
        )

        let pixelsPerPointX = CGFloat(source.width) / normalized.size.width
        let pixelsPerPointY = CGFloat(source.height) / normalized.size.height
        var pixelRect = CGRect(
            x: sourceRectInPoints.minX * pixelsPerPointX,
            y: sourceRectInPoints.minY * pixelsPerPointY,
            width: sourceRectInPoints.width * pixelsPerPointX,
            height: sourceRectInPoints.height * pixelsPerPointY
        ).integral
        pixelRect = pixelRect.intersection(CGRect(x: 0, y: 0, width: source.width, height: source.height))
        guard !pixelRect.isNull, pixelRect.width >= 1, pixelRect.height >= 1,
              let croppedCG = source.cropping(to: pixelRect) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "Could not create the selected crop. Please adjust the image and try again."])
        }

        let target = kind == .avatar
            ? CGSize(width: 1080, height: 1080)
            : CGSize(width: 1500, height: 500)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: target, format: format)
        let croppedImage = UIImage(cgImage: croppedCG, scale: 1, orientation: .up)
        let result = renderer.image { context in
            UIColor.white.setFill()
            context.fill(CGRect(origin: .zero, size: target))
            context.cgContext.interpolationQuality = .high
            croppedImage.draw(in: CGRect(origin: .zero, size: target))
        }
        guard let output = result.cgImage, output.width > 0, output.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return result
    }'''
account = account[:start] + replacement + account[end:]
account_path.write_text(account)

tab = tab_path.read_text()
old_size = "let size = CGSize(width: 28, height: 28)"
if old_size not in tab:
    raise SystemExit("Could not locate the tab avatar size; refusing unsafe edit.")
tab = tab.replace(old_size, "let size = CGSize(width: 34, height: 34)", 1)
tab_path.write_text(tab)
print("Replaced crop export with source-pixel cropping that mirrors preview zoom/drag, and increased the Profile tab avatar to 34pt.")
