from pathlib import Path
import re

root = Path("ios/Carbyne/Sources")
account_path = root / "AccountSheets.swift"
content_path = root / "ContentView.swift"
store_path = root / "CarbyneStore.swift"

account = account_path.read_text()
account = account.replace(
    """                        let cropped = renderCrop()
                        await store.uploadProfileImage(cropped, kind: kind)
                        isSaving = false
                        if store.errorMessage == nil { dismiss() }""",
    """                        do {
                            let cropped = try renderCrop()
                            await store.uploadProfileImage(cropped, kind: kind)
                            if store.errorMessage == nil { dismiss() }
                        } catch {
                            store.errorMessage = error.localizedDescription
                        }
                        isSaving = false"""
)
crop = r'''    private func renderCrop() throws -> UIImage {
        let normalized = image.carbyneUpright()
        guard normalized.cgImage != nil, normalized.size.width > 0, normalized.size.height > 0 else {
            throw NSError(domain: "CarbyneImage", code: 422,
                          userInfo: [NSLocalizedDescriptionKey: "The selected photo could not be decoded. Please choose another image."])
        }
        let target = kind == .avatar ? CGSize(width: 1080, height: 1080) : CGSize(width: 1500, height: 500)
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: target, format: format)
        let viewport = cropAreaSize == .zero ? CGSize(width: 320, height: 320 / aspect) : cropAreaSize
        let outputScale = target.width / viewport.width
        let baseScale = max(viewport.width / normalized.size.width, viewport.height / normalized.size.height)
        let drawWidth = normalized.size.width * baseScale * zoom
        let drawHeight = normalized.size.height * baseScale * zoom
        let rect = CGRect(
            x: ((viewport.width - drawWidth) / 2 + offset.width) * outputScale,
            y: ((viewport.height - drawHeight) / 2 + offset.height) * outputScale,
            width: drawWidth * outputScale,
            height: drawHeight * outputScale
        )
        return renderer.image { context in
            UIColor.white.setFill()
            context.fill(CGRect(origin: .zero, size: target))
            context.cgContext.interpolationQuality = .high
            normalized.draw(in: rect)
        }
    }
}

extension UIImage {
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
start = account.find("    private func renderCrop() -> UIImage {")
end = account.find("\n}\n\nstruct ProfileEditorSheet", start)
if start < 0 or end < 0:
    raise SystemExit("Profile crop renderer location changed; refusing unsafe edit.")
account = account[:start] + crop + account[end+2:]
account_path.write_text(account)

content = content_path.read_text()
if "import ImageIO" not in content:
    content = content.replace("import PhotosUI\n", "import PhotosUI\nimport ImageIO\n", 1)
content = content.replace("cropImage = image", "cropImage = image.carbyneUpright()")

pipeline = r'''
@MainActor
final class CarbyneRemoteImageCache {
    static let shared = CarbyneRemoteImageCache()
    private let memory = NSCache<NSString, UIImage>()
    private var pending: [String: Task<UIImage?, Never>] = [:]

    private func diskURL(for key: String) -> URL? {
        guard let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first else { return nil }
        let directory = base.appendingPathComponent("CarbyneRemoteImages", isDirectory: true)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let name = Data(key.utf8).base64EncodedString()
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "=", with: "")
        return directory.appendingPathComponent(name + ".img")
    }

    func image(for url: URL?) async -> UIImage? {
        guard let url else { return nil }
        let key = url.absoluteString
        if let cached = memory.object(forKey: key as NSString) { return cached }
        if let file = diskURL(for: key), let cached = UIImage(contentsOfFile: file.path) {
            memory.setObject(cached, forKey: key as NSString)
            return cached
        }
        if let task = pending[key] { return await task.value }
        let task = Task.detached(priority: .utility) { () -> UIImage? in
            guard let (data, response) = try? await URLSession.shared.data(from: url),
                  (response as? HTTPURLResponse).map({ (200..<300).contains($0.statusCode) }) ?? true,
                  let source = CGImageSourceCreateWithData(data as CFData, nil) else { return nil }
            let options: [CFString: Any] = [
                kCGImageSourceCreateThumbnailFromImageAlways: true,
                kCGImageSourceCreateThumbnailWithTransform: true,
                kCGImageSourceThumbnailMaxPixelSize: 1400
            ]
            guard let cg = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else { return nil }
            return UIImage(cgImage: cg, scale: 1, orientation: .up)
        }
        pending[key] = task
        let loaded = await task.value
        pending[key] = nil
        if let loaded {
            memory.setObject(loaded, forKey: key as NSString)
            if let file = diskURL(for: key), let data = loaded.jpegData(compressionQuality: 0.88) {
                try? data.write(to: file, options: .atomic)
            }
        }
        return loaded
    }
}

struct CarbyneCachedImage: View {
    let url: URL?
    let isAvatar: Bool
    @State private var image: UIImage?

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image).resizable().scaledToFill()
            } else if isAvatar {
                Circle().fill(Color(uiColor: .systemGray5))
            } else {
                Rectangle().fill(Color(uiColor: .secondarySystemBackground))
            }
        }
        .task(id: url?.absoluteString) {
            image = await CarbyneRemoteImageCache.shared.image(for: url)
        }
    }
}

'''
if "final class CarbyneRemoteImageCache" not in content:
    content = content.replace("struct ProfileBannerView: View {", pipeline + "struct ProfileBannerView: View {", 1)
content = re.sub(
    r'''            AsyncImage\(url: url\) \{ phase in
                if let image = phase.image \{
                    image.resizable\(\).scaledToFill\(\)
                \} else \{
                    Rectangle\(\).fill\(Color\(uiColor: \.secondarySystemBackground\)\)
                \}
            \}''',
    "            CarbyneCachedImage(url: url, isAvatar: false)",
    content, count=1
)
content = re.sub(
    r'''        AsyncImage\(url: url\) \{ phase in
            if let image = phase.image \{ image.resizable\(\).scaledToFill\(\) \}
            else \{ Circle\(\).fill\(Color\(\.systemGray5\)\).overlay\(Image\(systemName: "person.fill"\).font\(\.system\(size: size \* 0.42\)\).foregroundStyle\(\.secondary\)\) \}
        \}''',
    '''        CarbyneCachedImage(url: url, isAvatar: true)
            .overlay {
                if url == nil {
                    Image(systemName: "person.fill")
                        .font(.system(size: size * 0.42))
                        .foregroundStyle(.secondary)
                }
            }''',
    content, count=1
)
if "AsyncImage(url: url)" in content:
    raise SystemExit("An uncached avatar/banner AsyncImage remains; refusing to continue.")
content_path.write_text(content)

store = store_path.read_text()
store = store.replace(
    "    private var hasInitialConversationSnapshot = false\n    private var supabase: SupabaseClient",
    "    private var hasInitialConversationSnapshot = false\n    private var loadedChannelsForUserID: UUID?\n    private var supabase: SupabaseClient"
)
store = store.replace(
    """        do {
            channels = try await supabase.from("profiles")
                .select()
                .order("display_name", ascending: true)
                .limit(100)
                .execute().value
        } catch { errorMessage = error.localizedDescription }
    }""",
    """        guard let userID = session?.user.id else { return }
        if loadedChannelsForUserID == userID { return }
        do {
            let loaded: [CarbyneProfile] = try await supabase.from("profiles")
                .select()
                .order("display_name", ascending: true)
                .limit(100)
                .execute().value
            channels = loaded
            loadedChannelsForUserID = userID
        } catch { errorMessage = error.localizedDescription }
    }""",
    1
)
old_conversations = """            var loaded: [CarbyneConversation] = []
            for (peerID, lastMessage) in latestByPeer {
                let peer: CarbyneProfile? = try await supabase.from("profiles")
                    .select()
                    .eq("id", value: peerID.uuidString)
                    .maybeSingle()
                    .execute().value
                if let peer { loaded.append(CarbyneConversation(profile: peer, lastMessage: lastMessage)) }
            }
            let sorted = loaded.sorted { $0.lastMessage.createdAt > $1.lastMessage.createdAt }"""
new_conversations = """            let peerIDs = Array(latestByPeer.keys)
            let peerProfiles: [CarbyneProfile]
            if peerIDs.isEmpty {
                peerProfiles = []
            } else {
                peerProfiles = try await supabase.from("profiles")
                    .select()
                    .in("id", values: peerIDs.map { $0.uuidString })
                    .execute().value
            }
            let profilesByID = Dictionary(uniqueKeysWithValues: peerProfiles.map { ($0.id, $0) })
            let loaded = latestByPeer.compactMap { peerID, lastMessage in
                profilesByID[peerID].map { CarbyneConversation(profile: $0, lastMessage: lastMessage) }
            }
            let sorted = loaded.sorted { $0.lastMessage.createdAt > $1.lastMessage.createdAt }"""
if old_conversations not in store:
    raise SystemExit("Sequential conversation profile lookups not found.")
store = store.replace(old_conversations, new_conversations, 1)
old_messages = """            let outgoing: [CarbyneMessage] = try await supabase.from("messages")
                .select()
                .eq("sender_id", value: userID.uuidString)
                .eq("recipient_id", value: peer.id.uuidString)
                .order("created_at", ascending: true)
                .limit(200)
                .execute().value
            let incoming: [CarbyneMessage] = try await supabase.from("messages")
                .select()
                .eq("sender_id", value: peer.id.uuidString)
                .eq("recipient_id", value: userID.uuidString)
                .order("created_at", ascending: true)
                .limit(200)
                .execute().value
            messages = (outgoing + incoming).sorted { $0.createdAt < $1.createdAt }"""
new_messages = """            let loaded: [CarbyneMessage] = try await supabase.from("messages")
                .select()
                .or("and(sender_id.eq.\\(userID.uuidString),recipient_id.eq.\\(peer.id.uuidString)),and(sender_id.eq.\\(peer.id.uuidString),recipient_id.eq.\\(userID.uuidString))")
                .order("created_at", ascending: true)
                .limit(400)
                .execute().value
            messages = loaded.sorted { $0.createdAt < $1.createdAt }"""
if old_messages not in store:
    raise SystemExit("Two-request message history block not found.")
store = store.replace(old_messages, new_messages, 1)
store = store.replace(
    """        profile = loaded
        if let email = session?.user.email?.lowercased(), let loaded {""",
    """        profile = loaded
        if let loaded {
            channels = channels.map { $0.id == loaded.id ? loaded : $0 }
            if viewedProfile?.id == loaded.id { viewedProfile = loaded }
        }
        if let email = session?.user.email?.lowercased(), let loaded {""",
    1
)
store = store.replace(
    """            session = nil
            profile = nil
            requiresMFA = false""",
    """            session = nil
            profile = nil
            channels = []
            loadedChannelsForUserID = nil
            requiresMFA = false""",
    1
)
store = store.replace(
    """            session = restored
            profile = nextProfile
            rememberAccount(email)""",
    """            session = restored
            profile = nextProfile
            channels = []
            loadedChannelsForUserID = nil
            rememberAccount(email)""",
    1
)
store = store.replace(
    """        let renderer = UIGraphicsImageRenderer(size: targetSize, format: UIGraphicsImageRendererFormat.default())
        for quality in [0.90, 0.84, 0.78, 0.72, 0.66, 0.60] {
            let data = renderer.jpegData(withCompressionQuality: quality) { context in
                UIColor(white: 0.22, alpha: 1).setFill()
                context.fill(CGRect(origin: .zero, size: targetSize))""",
    """        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        format.opaque = true
        let renderer = UIGraphicsImageRenderer(size: targetSize, format: format)
        for quality in [0.90, 0.84, 0.78, 0.72, 0.66, 0.60] {
            let data = renderer.jpegData(withCompressionQuality: quality) { context in
                UIColor.white.setFill()
                context.fill(CGRect(origin: .zero, size: targetSize))
                context.cgContext.interpolationQuality = .high"""
)
store_path.write_text(store)
print("Fixed profile image crop/export; added persistent downsampled image caching; reduced repeated channel, conversation, and message requests.")
