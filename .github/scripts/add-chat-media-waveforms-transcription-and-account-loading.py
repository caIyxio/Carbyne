from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
store_path = root / "CarbyneStore.swift"
sheets_path = root / "AccountSheets.swift"
project_path = Path("ios/Carbyne/project.yml")

def replace_once(source, old, new, label):
    if new in source:
        return source
    if old not in source:
        raise SystemExit(f"Could not find {label}; refusing unsafe patch.")
    return source.replace(old, new, 1)

content = content_path.read_text()
store = store_path.read_text()
sheets = sheets_path.read_text()
project = project_path.read_text()

# Media support: video playback and on-device speech recognition.
if "import AVKit" not in content:
    content = "import AVKit\n" + content
if "import Speech" not in content:
    content = "import Speech\n" + content

# Each conversation view owns its displayed message snapshot; switching between
# threads cannot briefly show the previous person's messages.
content = replace_once(content,
    """    @State private var isRecording = false

    var body: some View {
        VStack(spacing: 0) {""",
    """    @State private var isRecording = false
    @State private var threadMessages: [CarbyneMessage] = []

    var body: some View {
        VStack(spacing: 0) {""", "per-thread message state")
content = replace_once(content,
    """                        ForEach(store.messages) { message in""",
    """                        ForEach(threadMessages) { message in""", "thread-local message rendering")
content = replace_once(content,
    """                .onChange(of: store.messages.count) { _, _ in
                    if let last = store.messages.last { withAnimation(.easeOut(duration: 0.2)) { proxy.scrollTo(last.id, anchor: .bottom) } }
                }""",
    """                .onChange(of: threadMessages.count) { _, _ in
                    if let last = threadMessages.last { withAnimation(.easeOut(duration: 0.2)) { proxy.scrollTo(last.id, anchor: .bottom) } }
                }""", "thread-local auto-scroll")
content = replace_once(content,
    """            ToolbarItem(placement: .principal) {
                VStack(spacing: 2) {
                    AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 30)
                    Text(profile.title)
                        .font(.system(size: 12, weight: .semibold))
                        .lineLimit(1)
                }
                .accessibilityElement(children: .combine)
            }""",
    """            ToolbarItem(placement: .principal) {
                NavigationLink {
                    PublicChannelScreen(profile: profile)
                } label: {
                    VStack(spacing: 3) {
                        AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 48)
                        Text(profile.title)
                            .font(.system(size: 13, weight: .semibold))
                            .lineLimit(1)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Open \(profile.title)'s profile")
            }""", "large tappable chat header avatar")
content = replace_once(content,
    """            await store.loadMessages(with: profile)
            await store.startMessagesRealtime()
        }
        .onDisappear {""",
    """            await store.loadMessages(with: profile)
            threadMessages = store.messages
            await store.startMessagesRealtime()
        }
        .onChange(of: store.messages) { _, updated in
            if store.activeChatProfile?.id == profile.id {
                threadMessages = updated
            }
        }
        .onDisappear {""", "thread-specific message refresh")
content = replace_once(content,
    """        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {""",
    """        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .id(profile.id)
        .toolbar {""", "unique conversation navigation identity")

# Select images and videos from Photos; the selected video is uploaded as an attachment.
content = replace_once(content,
    """PhotosPicker(selection: $selectedPhoto, matching: .images, photoLibrary: .shared())""",
    """PhotosPicker(selection: $selectedPhoto, matching: .any(of: [.images, .videos]), photoLibrary: .shared())""",
    "image and video picker")
content = replace_once(content,
    """            let type = item.supportedContentTypes.first
            let mime = type?.preferredMIMEType ?? "image/jpeg"
            let ext = type?.preferredFilenameExtension ?? "jpg"
            await store.sendMessage(
                to: profile,
                body: "",
                attachmentData: data,
                fileName: "Photo.\(ext)",
                mimeType: mime,
                messageType: "attachment"
            )""",
    """            let type = item.supportedContentTypes.first
            let mime = type?.preferredMIMEType ?? "image/jpeg"
            let ext = type?.preferredFilenameExtension ?? "jpg"
            let isVideo = type?.conforms(to: .movie) == true
            await store.sendMessage(
                to: profile,
                body: "",
                attachmentData: data,
                fileName: "\(isVideo ? "Video" : "Photo").\(ext)",
                mimeType: mime,
                messageType: "attachment"
            )""", "video attachment upload")

# Render real photo/video thumbnails, tap to view in an in-app full-screen viewer.
bubble_start = content.index("struct MessageBubble: View {")
recorder_start = content.index("final class CarbyneVoiceRecorder", bubble_start)
bubble_end = content.rfind("\n", bubble_start, recorder_start)
new_bubble = """struct MessageBubble: View {
    @EnvironmentObject private var store: CarbyneStore
    let message: CarbyneMessage
    let isOutgoing: Bool
    @State private var attachmentURL: URL?
    @State private var showMedia = false
    @State private var isVideo = false

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if let body = message.body, !body.isEmpty {
                Text(body).font(.system(size: 15))
            }
            if message.messageType == "voice_note", let path = message.attachmentPath {
                VoiceNotePlayer(path: path, isOutgoing: isOutgoing)
            } else if let path = message.attachmentPath {
                Button {
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
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 13)
        .padding(.vertical, 10)
        .foregroundStyle(isOutgoing ? Color.white : Color.primary)
        .background(isOutgoing ? Color.accentColor : Color(uiColor: .secondarySystemBackground),
                    in: RoundedRectangle(cornerRadius: 17))
        .frame(maxWidth: 270, alignment: isOutgoing ? .trailing : .leading)
        .task(id: message.attachmentPath) {
            guard let path = message.attachmentPath,
                  message.messageType != "voice_note" else { return }
            do { attachmentURL = try await store.signedAttachmentURL(path: path) }
            catch { store.errorMessage = error.localizedDescription }
        }
        .sheet(isPresented: $showMedia) {
            if let attachmentURL {
                FullscreenChatMediaView(url: attachmentURL, isVideo: isVideo)
            }
        }
    }
}

struct AttachmentThumbnail: View {
    let url: URL?
    let name: String?
    let mimeType: String?

    var body: some View {
        Group {
            if mimeType?.hasPrefix("image/") == true, let url {
                AsyncImage(url: url) { phase in
                    if let image = phase.image {
                        image.resizable().scaledToFill()
                    } else if phase.error != nil {
                        attachmentFallback
                    } else {
                        ProgressView().frame(maxWidth: .infinity, minHeight: 130)
                    }
                }
                .frame(maxWidth: .infinity)
                .frame(height: 170)
                .clipped()
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
                attachmentFallback
            }
        }
        .frame(maxWidth: 230)
        .accessibilityLabel(mimeType?.hasPrefix("video/") == true ? "Video attachment preview" : "Photo attachment preview")
    }

    private var attachmentFallback: some View {
        Label(name ?? "Attachment", systemImage: mimeType?.hasPrefix("video/") == true ? "video" : "photo")
            .font(.system(size: 13, weight: .medium))
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color.primary.opacity(0.07), in: RoundedRectangle(cornerRadius: 12))
    }
}

struct FullscreenChatMediaView: View {
    @Environment(\.dismiss) private var dismiss
    let url: URL
    let isVideo: Bool

    var body: some View {
        NavigationStack {
            Group {
                if isVideo {
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
                }
            }
            .navigationTitle(isVideo ? "Video" : "Photo")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
        }
    }
}

struct VoiceNotePlayer: View {
    @EnvironmentObject private var store: CarbyneStore
    let path: String
    let isOutgoing: Bool
    @StateObject private var playback = VoiceNotePlaybackController()
    @State private var showExpanded = false
    @State private var showTranscript = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                Button {
                    Task {
                        do {
                            let url = try await store.signedAttachmentURL(path: path)
                            try await playback.toggle(url: url)
                        } catch { store.errorMessage = error.localizedDescription }
                    }
                } label: {
                    Image(systemName: playback.isPlaying ? "pause.fill" : "play.fill")
                        .font(.system(size: 15, weight: .bold))
                        .frame(width: 36, height: 36)
                        .background(isOutgoing ? Color.white.opacity(0.2) : Color.primary.opacity(0.08), in: Circle())
                }
                .buttonStyle(.plain)
                VStack(alignment: .leading, spacing: 5) {
                    WaveformBars(samples: playback.waveform.isEmpty ? Array(repeating: 0.2, count: 36) : playback.waveform)
                        .frame(height: 28)
                    Text(playback.duration > 0 ? playback.formattedDuration : "Voice message")
                        .font(.system(size: 11, weight: .medium)).opacity(0.8)
                }
                .frame(maxWidth: 160, alignment: .leading)
                Button { showExpanded = true } label: {
                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                        .font(.system(size: 11, weight: .semibold))
                }
                .buttonStyle(.plain)
            }
            Button {
                showTranscript.toggle()
                if showTranscript && playback.transcript == nil {
                    Task {
                        do {
                            let url = try await store.signedAttachmentURL(path: path)
                            try await playback.transcribe(url: url)
                        } catch { store.errorMessage = error.localizedDescription }
                    }
                }
            } label: {
                Text(showTranscript ? "Hide transcript" : "Transcribe")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundStyle(isOutgoing ? Color.white.opacity(0.9) : Color.accentColor)
            }
            .buttonStyle(.plain)
            if showTranscript {
                Text(playback.transcript ?? (playback.isTranscribing ? "Transcribing…" : "Transcript unavailable"))
                    .font(.system(size: 12)).textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .sheet(isPresented: $showExpanded) {
            NavigationStack {
                VStack(spacing: 24) {
                    Image(systemName: "waveform").font(.system(size: 42))
                    WaveformBars(samples: playback.waveform.isEmpty ? Array(repeating: 0.2, count: 64) : playback.waveform)
                        .frame(height: 80).padding(.horizontal, 20)
                    Text(playback.formattedDuration).font(.system(.title3, design: .rounded).monospacedDigit())
                    Button {
                        Task {
                            do {
                                let url = try await store.signedAttachmentURL(path: path)
                                try await playback.toggle(url: url)
                            } catch { store.errorMessage = error.localizedDescription }
                        }
                    } label: {
                        Image(systemName: playback.isPlaying ? "pause.fill" : "play.fill")
                            .font(.system(size: 24)).frame(width: 64, height: 64)
                            .background(Color.accentColor, in: Circle()).foregroundStyle(.white)
                    }
                    Button("Transcribe voice note") {
                        Task {
                            do {
                                let url = try await store.signedAttachmentURL(path: path)
                                try await playback.transcribe(url: url)
                            } catch { store.errorMessage = error.localizedDescription }
                        }
                    }
                    if let transcript = playback.transcript { Text(transcript).textSelection(.enabled) }
                    else if playback.isTranscribing { ProgressView("Transcribing…") }
                }
                .padding(24)
                .navigationTitle("Voice note")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { showExpanded = false } } }
            }
            .presentationDetents([.medium, .large])
        }
    }
}

struct WaveformBars: View {
    let samples: [CGFloat]
    var body: some View {
        GeometryReader { geometry in
            HStack(alignment: .center, spacing: 2) {
                ForEach(Array(samples.enumerated()), id: \.offset) { _, sample in
                    Capsule().fill(Color.primary.opacity(0.75))
                        .frame(maxWidth: .infinity)
                        .frame(height: max(3, geometry.size.height * min(max(sample, 0.04), 1)))
                }
            }
        }
    }
}

@MainActor
final class VoiceNotePlaybackController: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var isPlaying = false
    @Published private(set) var duration: TimeInterval = 0
    @Published private(set) var waveform: [CGFloat] = []
    @Published private(set) var transcript: String?
    @Published private(set) var isTranscribing = false
    private var player: AVAudioPlayer?

    var formattedDuration: String {
        let seconds = Int(duration)
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }

    func toggle(url: URL) async throws {
        if let player {
            if isPlaying { player.pause(); isPlaying = false }
            else { player.play(); isPlaying = true }
            return
        }
        let (data, _) = try await URLSession.shared.data(from: url)
        let newPlayer = try AVAudioPlayer(data: data)
        newPlayer.delegate = self
        newPlayer.prepareToPlay()
        duration = newPlayer.duration
        waveform = Self.makeWaveform(from: data)
        player = newPlayer
        newPlayer.play()
        isPlaying = true
    }

    func transcribe(url: URL) async throws {
        guard SFSpeechRecognizer.authorizationStatus() == .authorized else {
            let status = await withCheckedContinuation { continuation in
                SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0) }
            }
            guard status == .authorized else {
                throw NSError(domain: "Carbyne", code: 403, userInfo: [NSLocalizedDescriptionKey: "Speech recognition permission is required to transcribe voice notes."])
            }
            return try await transcribe(url: url)
        }
        guard let recognizer = SFSpeechRecognizer(), recognizer.isAvailable else {
            throw NSError(domain: "Carbyne", code: 503, userInfo: [NSLocalizedDescriptionKey: "Speech recognition is currently unavailable."])
        }
        isTranscribing = true
        defer { isTranscribing = false }
        let (data, _) = try await URLSession.shared.data(from: url)
        let localURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".m4a")
        try data.write(to: localURL)
        defer { try? FileManager.default.removeItem(at: localURL) }
        transcript = try await withCheckedThrowingContinuation { continuation in
            let request = SFSpeechURLRecognitionRequest(url: localURL)
            request.shouldReportPartialResults = false
            recognizer.recognitionTask(with: request) { result, error in
                if let error { continuation.resume(throwing: error) }
                else if let result, result.isFinal { continuation.resume(returning: result.bestTranscription.formattedString) }
            }
        }
    }

    private static func makeWaveform(from data: Data) -> [CGFloat] {
        let fileURL = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString + ".m4a")
        defer { try? FileManager.default.removeItem(at: fileURL) }
        do {
            try data.write(to: fileURL)
            let file = try AVAudioFile(forReading: fileURL)
            guard let format = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: file.processingFormat.sampleRate,
                                             channels: file.processingFormat.channelCount, interleaved: false),
                  let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(file.length)) else { return [] }
            try file.read(into: buffer)
            guard let channel = buffer.floatChannelData?[0], buffer.frameLength > 0 else { return [] }
            let count = Int(buffer.frameLength)
            let bars = 48
            let bucket = max(1, count / bars)
            return (0..<bars).map { index in
                let start = index * bucket
                let end = min(start + bucket, count)
                guard start < end else { return CGFloat(0.08) }
                var peak: Float = 0
                for sample in start..<end { peak = max(peak, abs(channel[sample])) }
                return CGFloat(min(max(peak * 3.5, 0.08), 1))
            }
        } catch { return [] }
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        isPlaying = false
        player.currentTime = 0
    }
}
"""
if bubble_start < 0 or recorder_start < 0:
    raise SystemExit("Could not locate message bubble replacement range.")
content = content[:bubble_start] + new_bubble + content[bubble_end:]

# Edit Profile: tap either profile image to select a replacement, then use the existing crop editor.
content = replace_once(content,
    """    @State private var errorText: String?

    private var hasChanges""",
    """    @State private var errorText: String?
    @State private var avatarPickerItem: PhotosPickerItem?
    @State private var bannerPickerItem: PhotosPickerItem?
    @State private var cropImage: UIImage?
    @State private var cropKind: ProfileImageKind = .avatar

    private var hasChanges""", "edit profile image picker state")
content = replace_once(content,
    """                ProfileBannerView(url: store.publicImageURL(path: store.profile?.bannerPath))
                HStack(alignment: .bottom, spacing: 14) {
                    AvatarView(url: store.publicImageURL(path: store.profile?.avatarPath), size: 92)
                        .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 4))
                        .offset(y: -24)
                        .padding(.bottom, -24)""",
    """                PhotosPicker(selection: $bannerPickerItem, matching: .images) {
                    ZStack(alignment: .bottomTrailing) {
                        ProfileBannerView(url: store.publicImageURL(path: store.profile?.bannerPath))
                        Label("Change banner", systemImage: "pencil")
                            .font(.caption.weight(.semibold))
                            .padding(8)
                            .background(.ultraThinMaterial, in: Capsule())
                            .padding(10)
                    }
                }
                .buttonStyle(.plain)
                HStack(alignment: .bottom, spacing: 14) {
                    PhotosPicker(selection: $avatarPickerItem, matching: .images) {
                        AvatarView(url: store.publicImageURL(path: store.profile?.avatarPath), size: 92)
                            .overlay(Circle().stroke(Color(uiColor: .systemBackground), lineWidth: 4))
                            .overlay(alignment: .bottomTrailing) {
                                Image(systemName: "camera.fill").font(.system(size: 12, weight: .bold))
                                    .padding(7).background(.ultraThinMaterial, in: Circle())
                            }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Change profile picture")
                    .offset(y: -24)
                    .padding(.bottom, -24)""", "editable avatar and banner")
content = replace_once(content,
    """        .task {
            displayName = store.profile?.displayName ?? ""
            username = store.profile?.username ?? ""
            bio = store.profile?.bio ?? ""
        }
    }
}

struct UploadScreen""",
    """        .task {
            displayName = store.profile?.displayName ?? ""
            username = store.profile?.username ?? ""
            bio = store.profile?.bio ?? ""
        }
        .onChange(of: avatarPickerItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    cropKind = .avatar
                    cropImage = image
                }
                avatarPickerItem = nil
            }
        }
        .onChange(of: bannerPickerItem) { _, item in
            guard let item else { return }
            Task {
                if let data = try? await item.loadTransferable(type: Data.self),
                   let image = UIImage(data: data) {
                    cropKind = .banner
                    cropImage = image
                }
                bannerPickerItem = nil
            }
        }
        .sheet(isPresented: Binding(get: { cropImage != nil }, set: { if !$0 { cropImage = nil } })) {
            if let cropImage {
                ProfileImageCropSheet(image: cropImage, kind: cropKind)
            }
        }
    }
}

struct UploadScreen""", "edit profile crop sheet presentation")

# Account switch: explicitly show a blocking loading state and only haptic on successful completion.
store = replace_once(store,
    """    @Published private(set) var isLoading = false
    @Published private(set) var requiresMFA""",
    """    @Published private(set) var isLoading = false
    @Published private(set) var isSwitchingAccount = false
    @Published private(set) var requiresMFA""", "account switching loading state")
store = replace_once(store,
    """    func switchAccount(to email: String) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            supabase = client(for: email)
            let restored = try await supabase.auth.session
            session = restored
            rememberAccount(email)
            try await inspectMFA()
            if requiresMFA { try await beginLoginMFAChallenge() }
            else { try await refreshProfile() }
        } catch {
            session = nil
            profile = nil
            errorMessage = "This account needs you to sign in again. \(error.localizedDescription)"
        }
    }""",
    """    func switchAccount(to email: String) async {
        isLoading = true
        isSwitchingAccount = true
        errorMessage = nil
        var completed = false
        defer {
            isLoading = false
            isSwitchingAccount = false
            if completed {
                UINotificationFeedbackGenerator().notificationOccurred(.success)
            }
        }
        do {
            let nextClient = client(for: email)
            let restored = try await nextClient.auth.session
            let nextProfile: CarbyneProfile? = try await nextClient.from("profiles")
                .select()
                .eq("id", value: restored.user.id.uuidString)
                .maybeSingle()
                .execute().value
            supabase = nextClient
            session = restored
            profile = nextProfile
            rememberAccount(email)
            try await inspectMFA()
            if requiresMFA {
                try await beginLoginMFAChallenge()
            } else {
                viewedProfile = nextProfile
                completed = true
            }
        } catch {
            errorMessage = "This account needs you to sign in again. \(error.localizedDescription)"
        }
    }""", "safe account switch with success haptic")
store_path.write_text(store)

# A visible loading cover prevents the old account's content from appearing as the new account loads.
sheets = replace_once(sheets,
    """        .sheet(isPresented: $showAddAccount) { AuthenticationSheet() }
    }
}

struct AccountSwitcherSheet""",
    """        .sheet(isPresented: $showAddAccount) { AuthenticationSheet() }
        .overlay {
            if store.isSwitchingAccount {
                ZStack {
                    Color.black.opacity(0.22).ignoresSafeArea()
                    VStack(spacing: 12) {
                        ProgressView().controlSize(.large)
                        Text("Loading account…").font(.system(size: 14, weight: .semibold))
                    }
                    .padding(24)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18))
                }
                .transition(.opacity)
            }
        }
        .animation(.easeInOut(duration: 0.18), value: store.isSwitchingAccount)
    }
}

struct AccountSwitcherSheet""", "account switch loading overlay")
sheets_path.write_text(sheets)

# Add speech recognition privacy copy.
project = replace_once(project,
    """    INFOPLIST_KEY_NSMicrophoneUsageDescription: Carbyne uses the microphone to record voice notes you choose to send.""",
    """    INFOPLIST_KEY_NSMicrophoneUsageDescription: Carbyne uses the microphone to record voice notes you choose to send.
    INFOPLIST_KEY_NSSpeechRecognitionUsageDescription: Carbyne uses speech recognition to create transcriptions of voice notes when you request them.""",
    "speech recognition usage description")
project_path.write_text(project)

content_path.write_text(content)
print("Added photo/video previews and in-app viewer, per-thread message state, tappable larger chat avatars, real audio-derived waveforms, transcription, editable profile images, and account-switch loading/haptics.")
