from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
content = content_path.read_text()

def replace_once(source, old, new, label):
    if new in source:
        return source
    if old not in source:
        raise SystemExit(f"Could not find expected source for {label}; refusing to make a partial patch.")
    return source.replace(old, new, 1)

# Slightly reduce the in-chat avatar without shrinking the actual chat header.
content = replace_once(
    content,
    "AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 68)",
    "AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 60)",
    "chat header avatar size"
)

# A path-keyed image cache prevents signed-URL changes and LazyVStack row recreation
# from repeatedly downloading the same immutable attachment.
cache_and_image_view = r"""
@MainActor
final class ChatAttachmentImageCache {
    static let shared = ChatAttachmentImageCache()
    private let images = NSCache<NSString, UIImage>()

    private func diskURL(for path: String) -> URL? {
        guard let base = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first else {
            return nil
        }
        let directory = base.appendingPathComponent("ChatAttachmentImages", isDirectory: true)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let key = Data(path.utf8).base64EncodedString()
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "=", with: "")
        return directory.appendingPathComponent(key + ".img")
    }

    func image(for path: String) -> UIImage? {
        if let image = images.object(forKey: path as NSString) { return image }
        guard let fileURL = diskURL(for: path),
              let data = try? Data(contentsOf: fileURL),
              let image = UIImage(data: data) else { return nil }
        images.setObject(image, forKey: path as NSString)
        return image
    }

    func store(_ image: UIImage, data: Data, for path: String) {
        images.setObject(image, forKey: path as NSString)
        if let fileURL = diskURL(for: path) {
            try? data.write(to: fileURL, options: .atomic)
        }
    }
}

struct CachedChatAttachmentImage: View {
    let path: String
    let url: URL?
    let maxWidth: CGFloat?
    let maxHeight: CGFloat?
    @State private var image: UIImage?

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFit()
            } else {
                ProgressView()
                    .frame(maxWidth: .infinity, minHeight: 90)
            }
        }
        .frame(maxWidth: maxWidth, maxHeight: maxHeight)
        .task(id: url?.absoluteString ?? path) {
            if let cached = ChatAttachmentImageCache.shared.image(for: path) {
                image = cached
                return
            }
            guard let url else { return }
            do {
                let (data, response) = try await URLSession.shared.data(from: url)
                if let response = response as? HTTPURLResponse,
                   !(200..<300).contains(response.statusCode) {
                    return
                }
                guard let decoded = UIImage(data: data) else { return }
                ChatAttachmentImageCache.shared.store(decoded, data: data, for: path)
                image = decoded
            } catch {
                // Keep the lightweight placeholder; a later appearance can retry.
            }
        }
    }
}

"""
if "final class ChatAttachmentImageCache" not in content:
    marker = "struct AttachmentThumbnail: View {"
    if marker not in content:
        raise SystemExit("Could not find AttachmentThumbnail insertion point.")
    content = content.replace(marker, cache_and_image_view + marker, 1)

# Replace the fixed 170pt crop with an aspect-fit image capped in both dimensions.
start = content.index("struct AttachmentThumbnail: View {")
end = content.index("struct FullscreenChatMediaView: View {", start)
new_thumbnail = r"""struct AttachmentThumbnail: View {
    let path: String
    let url: URL?
    let name: String?
    let mimeType: String?

    var body: some View {
        Group {
            if mimeType?.hasPrefix("image/") == true {
                CachedChatAttachmentImage(path: path, url: url, maxWidth: 230, maxHeight: 280)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
            } else if mimeType?.hasPrefix("video/") == true {
                ZStack {
                    RoundedRectangle(cornerRadius: 12).fill(Color.black.opacity(0.12))
                    Image(systemName: "play.circle.fill")
                        .font(.system(size: 48))
                        .symbolRenderingMode(.hierarchical)
                }
                .frame(width: 220, height: 140)
                .overlay(alignment: .bottomLeading) {
                    Text(name ?? "Video").font(.caption.weight(.medium))
                        .padding(8).foregroundStyle(.primary)
                }
            } else {
                Label(name ?? "Attachment", systemImage: "doc")
                    .font(.system(size: 13, weight: .medium))
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.primary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
            }
        }
        .frame(maxWidth: 230, maxHeight: 280)
        .accessibilityLabel(mimeType?.hasPrefix("video/") == true ? "Video attachment preview" : "Photo attachment preview")
    }
}

"""
content = content[:start] + new_thumbnail + content[end:]

# Full-screen photos reuse the same cached UIImage instead of starting a second download.
content = content.replace(
    """struct FullscreenChatMediaView: View {
    @Environment(\.dismiss) private var dismiss
    let url: URL
    let isVideo: Bool""",
    """struct FullscreenChatMediaView: View {
    @Environment(\.dismiss) private var dismiss
    let path: String
    let url: URL?
    let isVideo: Bool"""
)
content = content.replace(
    """                if isVideo {
                    VideoPlayer(player: AVPlayer(url: url))
                        .ignoresSafeArea(edges: .bottom)
                } else {
                    AsyncImage(url: url) { phase in
                        if let image = phase.image {
                            image.resizable().scaledToFit()
                        } else {
                            ProgressView()
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                    .background(.black)
                }""",
    """                if isVideo, let url {
                    VideoPlayer(player: AVPlayer(url: url))
                        .ignoresSafeArea(edges: .bottom)
                } else {
                    CachedChatAttachmentImage(path: path, url: url,
                                              maxWidth: .infinity, maxHeight: .infinity)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(.black)
                }"""
)

# MessageBubble: cached photos can open immediately; only uncached photos/videos need a signed URL.
content = content.replace(
    """                Button {
                    Task {
                        do {
                            let url = try await store.signedAttachmentURL(path: path)
                            attachmentURL = url
                            isVideo = message.attachmentMimeType?.hasPrefix("video/") == true
                            showMedia = true
                        } catch { store.errorMessage = error.localizedDescription }
                    }
                } label: {
                    AttachmentThumbnail(url: attachmentURL, name: message.attachmentName,
                                        mimeType: message.attachmentMimeType)
                }""",
    """                Button {
                    isVideo = message.attachmentMimeType?.hasPrefix("video/") == true
                    if !isVideo, ChatAttachmentImageCache.shared.image(for: path) != nil {
                        showMedia = true
                    } else {
                        Task {
                            do {
                                let signedURL = try await store.signedAttachmentURL(path: path)
                                attachmentURL = signedURL
                                showMedia = true
                            } catch { store.errorMessage = error.localizedDescription }
                        }
                    }
                } label: {
                    AttachmentThumbnail(path: path, url: attachmentURL, name: message.attachmentName,
                                        mimeType: message.attachmentMimeType)
                }"""
)
# Also accept the exact multiline form currently used if spacing differs.
content = content.replace(
    """                Button {
                    Task {
                        do {
                            let url = try await store.signedAttachmentURL(path: path)
                            attachmentURL = url
                            isVideo = message.attachmentMimeType?.hasPrefix("video/") == true
                            showMedia = true
                        } catch { store.errorMessage = error.localizedDescription }
                    }
                } label: {""",
    """                Button {
                    isVideo = message.attachmentMimeType?.hasPrefix("video/") == true
                    if !isVideo, ChatAttachmentImageCache.shared.image(for: path) != nil {
                        showMedia = true
                    } else {
                        Task {
                            do {
                                let signedURL = try await store.signedAttachmentURL(path: path)
                                attachmentURL = signedURL
                                showMedia = true
                            } catch { store.errorMessage = error.localizedDescription }
                        }
                    }
                } label: {"""
)
content = content.replace(
    """                    AttachmentThumbnail(url: attachmentURL, name: message.attachmentName,
                                        mimeType: message.attachmentMimeType)""",
    """                    AttachmentThumbnail(path: path, url: attachmentURL, name: message.attachmentName,
                                        mimeType: message.attachmentMimeType)"""
)
content = content.replace(
    """        .sheet(isPresented: $showMedia) {
            if let attachmentURL {
                FullscreenChatMediaView(url: attachmentURL, isVideo: isVideo)
            }
        }""",
    """        .sheet(isPresented: $showMedia) {
            if let path = message.attachmentPath {
                FullscreenChatMediaView(path: path, url: attachmentURL, isVideo: isVideo)
            }
        }"""
)

# Avoid signing a fresh URL if the photo is already in the in-memory cache.
content = content.replace(
    """        .task(id: message.attachmentPath) {
            guard let path = message.attachmentPath,
                  message.messageType != "voice_note" else { return }
            do { attachmentURL = try await store.signedAttachmentURL(path: path) }
            catch { store.errorMessage = error.localizedDescription }
        }""",
    """        .task(id: message.attachmentPath) {
            guard let path = message.attachmentPath,
                  message.messageType != "voice_note" else { return }
            if message.attachmentMimeType?.hasPrefix("image/") == true,
               ChatAttachmentImageCache.shared.image(for: path) != nil {
                return
            }
            do { attachmentURL = try await store.signedAttachmentURL(path: path) }
            catch { store.errorMessage = error.localizedDescription }
        }"""
)

# Replace transcription with a bounded retry/fallback. Apple documents 1107 as an
# interrupted speech-process connection; retry once and fall back from on-device
# recognition to the standard service when the local recognizer is interrupted.
transcribe_start = content.index("    func transcribe(url: URL) async throws {")
waveform_start = content.index("    private static func makeWaveform(from data: Data)", transcribe_start)
new_transcribe = r"""    func transcribe(url: URL) async throws {
        guard SFSpeechRecognizer.authorizationStatus() == .authorized else {
            let status = await withCheckedContinuation { continuation in
                SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0) }
            }
            guard status == .authorized else {
                throw NSError(domain: "Carbyne", code: 403,
                              userInfo: [NSLocalizedDescriptionKey: "Speech recognition permission is required to transcribe voice notes."])
            }
            return try await transcribe(url: url)
        }
        guard let recognizer = SFSpeechRecognizer(), recognizer.isAvailable else {
            throw NSError(domain: "Carbyne", code: 503,
                          userInfo: [NSLocalizedDescriptionKey: "Apple speech recognition is currently unavailable. Please try again shortly."])
        }

        isTranscribing = true
        defer {
            isTranscribing = false
            recognitionTask?.cancel()
            recognitionTask = nil
        }

        let (data, _) = try await URLSession.shared.data(from: url)
        let localURL = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString + ".m4a")
        try data.write(to: localURL, options: .atomic)
        defer { try? FileManager.default.removeItem(at: localURL) }

        if #available(iOS 26.0, *) {
            transcript = try await transcribeWithSpeechAnalyzer(at: localURL)
            return
        }

        let useOnDeviceFirst = recognizer.supportsOnDeviceRecognition
        let recognizedText: String
        do {
            recognizedText = try await recognizeFile(at: localURL, with: recognizer,
                                                     onDevice: useOnDeviceFirst)
        } catch {
            guard Self.isSpeechServiceInterrupted(error) else { throw error }
            // A 1107 interruption on the local speech process can recover using
            // Apple's standard recognition service; if that is also interrupted,
            // wait briefly and make one final attempt.
            do {
                recognizedText = try await recognizeFile(at: localURL, with: recognizer,
                                                         onDevice: false)
            } catch {
                guard Self.isSpeechServiceInterrupted(error) else { throw error }
                try await Task.sleep(nanoseconds: 900_000_000)
                recognizedText = try await recognizeFile(at: localURL, with: recognizer,
                                                         onDevice: false)
            }
        }
        transcript = recognizedText
    }

    @available(iOS 26.0, *)
    private func transcribeWithSpeechAnalyzer(at url: URL) async throws -> String {
        guard let locale = await SpeechTranscriber.supportedLocale(equivalentTo: Locale.current) else {
            throw NSError(domain: "CarbyneSpeech", code: 4,
                          userInfo: [NSLocalizedDescriptionKey: "On-device transcription is not available for the device's current language."])
        }
        let transcriber = SpeechTranscriber(locale: locale, preset: .offlineTranscription)
        if let installation = try await AssetInventory.assetInstallationRequest(supporting: [transcriber]) {
            try await installation.downloadAndInstall()
        }

        let audioFile = try AVAudioFile(forReading: url)
        let analyzer = SpeechAnalyzer(modules: [transcriber])
        async let transcriptionFuture = try transcriber.results.reduce("") { text, result in
            text + String(result.text.characters)
        }

        if let lastSample = try await analyzer.analyzeSequence(from: audioFile) {
            try await analyzer.finalizeAndFinish(through: lastSample)
        } else {
            await analyzer.cancelAndFinishNow()
        }

        let recognized = try await transcriptionFuture.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !recognized.isEmpty else {
            throw NSError(domain: "CarbyneSpeech", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "No speech could be recognized in this voice note."])
        }
        return recognized
    }

    private func recognizeFile(at url: URL, with recognizer: SFSpeechRecognizer,
                               onDevice: Bool) async throws -> String {
        recognitionTask?.cancel()
        recognitionTask = nil
        let request = SFSpeechURLRecognitionRequest(url: url)
        request.taskHint = .dictation
        request.shouldReportPartialResults = false
        request.requiresOnDeviceRecognition = onDevice

        return try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String, Error>) in
            var didFinish = false
            let task = recognizer.recognitionTask(with: request) { result, error in
                if let error {
                    guard !didFinish else { return }
                    didFinish = true
                    continuation.resume(throwing: error)
                } else if let result, result.isFinal {
                    guard !didFinish else { return }
                    didFinish = true
                    let text = result.bestTranscription.formattedString
                        .trimmingCharacters(in: .whitespacesAndNewlines)
                    if text.isEmpty {
                        continuation.resume(throwing: NSError(
                            domain: "CarbyneSpeech", code: 2,
                            userInfo: [NSLocalizedDescriptionKey: "No speech could be recognized in this voice note."]
                        ))
                    } else {
                        continuation.resume(returning: text)
                    }
                }
            }
            self.recognitionTask = task
        }
    }

    private static func isSpeechServiceInterrupted(_ error: Error) -> Bool {
        let nsError = error as NSError
        return nsError.domain == "kAFAssistantErrorDomain" && nsError.code == 1107
    }

"""
content = content[:transcribe_start] + new_transcribe + content[waveform_start:]

content_path.write_text(content)
print("Added path-keyed chat photo caching, aspect-fit previews, a slightly smaller chat avatar, and retry/fallback for Speech error 1107.")
