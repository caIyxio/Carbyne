from pathlib import Path

# Fix crop rendering: calculate the destination rectangle directly in output pixels
# and draw UIImage in UIKit's renderer coordinate space (no manual CGContext scaling).
account_path = Path("ios/Carbyne/Sources/AccountSheets.swift")
account = account_path.read_text()
start = account.find("    private func renderCrop() throws -> UIImage {")
end = account.find("\n}\n\nextension UIImage", start)
if start < 0 or end < 0:
    raise SystemExit("Could not locate crop renderer; refusing unsafe edit.")
replacement = r'''    private func renderCrop() throws -> UIImage {
        let upright = image.carbyneUpright()
        guard upright.size.width > 0, upright.size.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected photo could not be decoded."])
        }

        let viewport = cropAreaSize == .zero
            ? CGSize(width: 320, height: 320 / aspect)
            : cropAreaSize
        guard viewport.width > 0, viewport.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The crop area is not ready yet. Please try again."])
        }

        // Match the SwiftUI preview's aspect-fill, zoom, and drag transform.
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
        let sx = target.width / viewport.width
        let sy = target.height / viewport.height
        let outputRect = CGRect(x: previewRect.minX * sx,
                                y: previewRect.minY * sy,
                                width: previewRect.width * sx,
                                height: previewRect.height * sy)

        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: target, format: format)
        let result = renderer.image { rendererContext in
            UIColor.black.setFill()
            rendererContext.fill(CGRect(origin: .zero, size: target))
            rendererContext.cgContext.saveGState()
            rendererContext.cgContext.clip(to: CGRect(origin: .zero, size: target))
            upright.draw(in: outputRect)
            rendererContext.cgContext.restoreGState()
        }

        guard let cgImage = result.cgImage,
              cgImage.width == Int(target.width),
              cgImage.height == Int(target.height) else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The edited image could not be exported. Please try again."])
        }
        return result
    }'''
account = account[:start] + replacement + account[end:]
account_path.write_text(account)

# Make the status-bar foreground follow the actual pixels behind the top safe area.
app_path = Path("ios/Carbyne/Sources/CarbyneApp.swift")
app = app_path.read_text()
app = app.replace("let controller = UIHostingController(rootView: content)",
                  "let controller = CarbyneAdaptiveStatusHostingController(rootView: content)", 1)
if "final class CarbyneAdaptiveStatusHostingController" not in app:
    app += r'''

/// Samples the rendered content underneath the status bar and chooses a contrasting
/// status-bar foreground. This works with image banners as well as solid backgrounds.
final class CarbyneAdaptiveStatusHostingController<Content: View>: UIHostingController<Content> {
    private var currentStyle: UIStatusBarStyle = .darkContent

    override var preferredStatusBarStyle: UIStatusBarStyle { currentStyle }

    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        refreshStatusBarStyle()
    }

    override func viewDidLayoutSubviews() {
        super.viewDidLayoutSubviews()
        refreshStatusBarStyle()
    }

    private func refreshStatusBarStyle() {
        let bounds = view.bounds
        let width = Int(bounds.width.rounded(.up))
        let height = max(1, Int(max(view.safeAreaInsets.top, 24).rounded(.up)))
        guard width > 0, bounds.height >= CGFloat(height),
              let context = CGContext(data: nil,
                                      width: width,
                                      height: height,
                                      bitsPerComponent: 8,
                                      bytesPerRow: width * 4,
                                      space: CGColorSpaceCreateDeviceRGB(),
                                      bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { return }

        // Render only the top strip; the context clips the rest of the view.
        context.translateBy(x: 0, y: CGFloat(height) - bounds.height)
        view.layer.render(in: context)

        guard let data = context.data else { return }
        let pixels = data.bindMemory(to: UInt8.self, capacity: width * height * 4)
        var totalLuminance: CGFloat = 0
        var samples = 0
        let strideX = max(1, width / 48)
        let strideY = max(1, height / 8)
        for y in Swift.stride(from: 0, to: height, by: strideY) {
            for x in Swift.stride(from: 0, to: width, by: strideX) {
                let index = (y * width + x) * 4
                let red = CGFloat(pixels[index]) / 255
                let green = CGFloat(pixels[index + 1]) / 255
                let blue = CGFloat(pixels[index + 2]) / 255
                totalLuminance += 0.2126 * red + 0.7152 * green + 0.0722 * blue
                samples += 1
            }
        }
        guard samples > 0 else { return }
        let average = totalLuminance / CGFloat(samples)
        let nextStyle: UIStatusBarStyle = average < 0.48 ? .lightContent : .darkContent
        guard nextStyle != currentStyle else { return }
        currentStyle = nextStyle
        setNeedsStatusBarAppearanceUpdate()
    }
}
'''
app_path.write_text(app)
print("Updated crop export and added adaptive status-bar contrast sampling.")
