from pathlib import Path

root = Path("ios/Carbyne/Sources")
models_path = root / "CarbyneModels.swift"
store_path = root / "CarbyneStore.swift"
content_path = root / "ContentView.swift"
sheets_path = root / "AccountSheets.swift"
tabs_path = root / "CarbyneNativeTabController.swift"
project_path = Path("ios/Carbyne/project.yml")

def replace_once(source, old, new, label):
    if new in source:
        return source
    if old not in source:
        raise SystemExit(f"Could not find {label}; refusing to patch the wrong source.")
    return source.replace(old, new, 1)

# Profile bios and typed message records.
models = models_path.read_text()
models = replace_once(
    models,
    """    var bannerPath: String?

    enum CodingKeys""",
    """    var bannerPath: String?
    var bio: String?

    enum CodingKeys""",
    "profile bio property"
)
models = replace_once(
    models,
    """        case bannerPath = "banner_path"
    }

    var title""",
    """        case bannerPath = "banner_path"
        case bio
    }

    var title""",
    "profile bio coding key"
)
models = replace_once(
    models,
    """    let username: String
    let updatedAt: String

    enum CodingKeys""",
    """    let username: String
    let bio: String
    let updatedAt: String

    enum CodingKeys""",
    "profile update bio field"
)
models = replace_once(
    models,
    """        case displayName = "display_name"
        case updatedAt = "updated_at"
    }
}

struct SubscriptionRecord""",
    """        case displayName = "display_name"
        case bio
        case updatedAt = "updated_at"
    }
}

struct CarbyneMessage: Decodable, Identifiable, Hashable {
    let id: UUID
    let senderID: UUID
    let recipientID: UUID
    let body: String?
    let messageType: String
    let attachmentPath: String?
    let attachmentName: String?
    let attachmentMimeType: String?
    let attachmentSize: Int64?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, body
        case senderID = "sender_id"
        case recipientID = "recipient_id"
        case messageType = "message_type"
        case attachmentPath = "attachment_path"
        case attachmentName = "attachment_name"
        case attachmentMimeType = "attachment_mime_type"
        case attachmentSize = "attachment_size"
        case createdAt = "created_at"
    }

    var preview: String {
        if let body, !body.isEmpty { return body }
        if messageType == "voice_note" { return "Voice note" }
        return attachmentName ?? "Attachment"
    }
}

struct CarbyneMessageInsert: Encodable {
    let senderID: UUID
    let recipientID: UUID
    let body: String?
    let messageType: String
    let attachmentPath: String?
    let attachmentName: String?
    let attachmentMimeType: String?
    let attachmentSize: Int64?

    enum CodingKeys: String, CodingKey {
        case body
        case senderID = "sender_id"
        case recipientID = "recipient_id"
        case messageType = "message_type"
        case attachmentPath = "attachment_path"
        case attachmentName = "attachment_name"
        case attachmentMimeType = "attachment_mime_type"
        case attachmentSize = "attachment_size"
    }
}

struct CarbyneConversation: Identifiable {
    var id: UUID { profile.id }
    let profile: CarbyneProfile
    let lastMessage: CarbyneMessage
}

struct SubscriptionRecord""",
    "message models"
)
models_path.write_text(models)

# Supabase-backed direct messages, private attachments, voice-note uploads and Realtime.
store = store_path.read_text()
store = replace_once(
    store,
    """    @Published private(set) var accountProfiles: [String: CarbyneProfile] = [:]
    @Published private(set) var subscriberCount = 0""",
    """    @Published private(set) var accountProfiles: [String: CarbyneProfile] = [:]
    @Published private(set) var conversations: [CarbyneConversation] = []
    @Published private(set) var messages: [CarbyneMessage] = []
    @Published var activeChatProfile: CarbyneProfile?
    @Published private(set) var subscriberCount = 0""",
    "messaging published state"
)
store = replace_once(
    store,
    """    private var clients: [String: SupabaseClient] = [:]
    private var supabase: SupabaseClient""",
    """    private var clients: [String: SupabaseClient] = [:]
    private var messagesRealtimeChannel: RealtimeChannelV2?
    private var supabase: SupabaseClient""",
    "messages realtime channel state"
)
store = replace_once(
    store,
    """    func saveProfile(displayName: String, username: String) async throws {""",
    """    func saveProfile(displayName: String, username: String, bio: String = "") async throws {""",
    "profile save signature"
)
store = replace_once(
    store,
    """            displayName: cleanName,
            username: cleanUsername,
            updatedAt: ISO8601DateFormatter().string(from: Date())""",
    """            displayName: cleanName,
            username: cleanUsername,
            bio: String(bio.trimmingCharacters(in: .whitespacesAndNewlines).prefix(160)),
            updatedAt: ISO8601DateFormatter().string(from: Date())""",
    "profile save bio value"
)
messaging_methods = """
    func loadConversations() async {
        guard let userID = session?.user.id else { conversations = []; return }
        do {
            let records: [CarbyneMessage] = try await supabase.from("messages")
                .select()
                .or("sender_id.eq.\\\\(userID.uuidString),recipient_id.eq.\\\\(userID.uuidString)")
                .order("created_at", ascending: false)
                .limit(300)
                .execute().value
            var latestByPeer: [UUID: CarbyneMessage] = [:]
            for message in records {
                let peerID = message.senderID == userID ? message.recipientID : message.senderID
                if latestByPeer[peerID] == nil { latestByPeer[peerID] = message }
            }
            var loaded: [CarbyneConversation] = []
            for (peerID, lastMessage) in latestByPeer {
                let peer: CarbyneProfile? = try await supabase.from("profiles")
                    .select()
                    .eq("id", value: peerID.uuidString)
                    .maybeSingle()
                    .execute().value
                if let peer { loaded.append(CarbyneConversation(profile: peer, lastMessage: lastMessage)) }
            }
            conversations = loaded.sorted { $0.lastMessage.createdAt > $1.lastMessage.createdAt }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadMessages(with peer: CarbyneProfile) async {
        guard let userID = session?.user.id else { messages = []; return }
        do {
            let outgoing: [CarbyneMessage] = try await supabase.from("messages")
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
            messages = (outgoing + incoming).sorted { $0.createdAt < $1.createdAt }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func sendMessage(
        to peer: CarbyneProfile,
        body: String,
        attachmentData: Data? = nil,
        fileName: String? = nil,
        mimeType: String? = nil,
        messageType: String = "text"
    ) async {
        guard let userID = session?.user.id else { errorMessage = "Sign in to send messages."; return }
        let cleanBody = body.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanBody.isEmpty || attachmentData != nil else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            var path: String?
            if let attachmentData {
                guard attachmentData.count <= 25 * 1024 * 1024 else {
                    throw NSError(domain: "Carbyne", code: 413, userInfo: [NSLocalizedDescriptionKey: "Attachments must be 25 MB or smaller."])
                }
                let name = (fileName ?? "attachment").replacingOccurrences(of: "/", with: "_")
                path = "\\\\(userID.uuidString)/\\\\(peer.id.uuidString)/\\\\(UUID().uuidString)-\\\\(name)"
                try await supabase.storage.from("message-attachments").upload(
                    path: path!,
                    data: attachmentData,
                    options: UploadOptions(contentType: mimeType ?? "application/octet-stream", cacheControl: .noCache, upsert: false)
                )
            }
            let record = CarbyneMessageInsert(
                senderID: userID,
                recipientID: peer.id,
                body: cleanBody.isEmpty ? nil : cleanBody,
                messageType: messageType,
                attachmentPath: path,
                attachmentName: path == nil ? nil : fileName ?? "Attachment",
                attachmentMimeType: path == nil ? nil : mimeType ?? "application/octet-stream",
                attachmentSize: attachmentData.map { Int64($0.count) }
            )
            try await supabase.from("messages").insert(record).execute()
            await loadMessages(with: peer)
            await loadConversations()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func signedAttachmentURL(path: String) async throws -> URL {
        try await supabase.storage.from("message-attachments").createSignedURL(path: path, expiresIn: 3600)
    }

    func startMessagesRealtime() async {
        guard let userID = session?.user.id, messagesRealtimeChannel == nil else { return }
        let channel = supabase.channel("carbyne-messages-\\\\(userID.uuidString)")
        let _ = channel.onPostgresChange(InsertAction.self, schema: "public", table: "messages") { [weak self] _ in
            Task { @MainActor [weak self] in
                guard let self else { return }
                await self.loadConversations()
                if let peer = self.activeChatProfile { await self.loadMessages(with: peer) }
            }
        }
        await channel.subscribe()
        messagesRealtimeChannel = channel
    }

    func stopMessagesRealtime() async {
        guard let channel = messagesRealtimeChannel else { return }
        messagesRealtimeChannel = nil
        await supabase.removeChannel(channel)
    }

"""
store = replace_once(
    store,
    """    func uploadProfileImage(_ image: UIImage, kind: ProfileImageKind) async {""",
    messaging_methods + """    func uploadProfileImage(_ image: UIImage, kind: ProfileImageKind) async {""",
    "messaging store methods"
)
store_path.write_text(store)

# YouTube-like crop preview, drag-to-position, zoom, then explicit save.
sheets = sheets_path.read_text()
crop_sheet = """
struct ProfileImageCropSheet: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\\\\.dismiss) private var dismiss
    let image: UIImage
    let kind: ProfileImageKind
    @State private var zoom: CGFloat = 1
    @State private var offset: CGSize = .zero
    @State private var dragOrigin: CGSize = .zero
    @State private var isSaving = false

    private var aspect: CGFloat { kind == .avatar ? 1 : 3 }

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text(kind == .avatar ? "Position your profile picture" : "Position your banner")
                    .font(.system(size: 17, weight: .semibold))
                GeometryReader { geometry in
                    let baseScale = max(geometry.size.width / image.size.width, geometry.size.height / image.size.height)
                    ZStack {
                        Color.black
                        Image(uiImage: image)
                            .resizable()
                            .frame(width: image.size.width * baseScale * zoom,
                                   height: image.size.height * baseScale * zoom)
                            .offset(offset)
                        if kind == .avatar {
                            Circle().stroke(.white.opacity(0.9), lineWidth: 2)
                                .padding(1)
                        } else {
                            RoundedRectangle(cornerRadius: 2)
                                .stroke(.white.opacity(0.9), style: StrokeStyle(lineWidth: 1, dash: [6, 4]))
                                .padding(8)
                        }
                    }
                    .frame(width: geometry.size.width, height: geometry.size.height)
                    .clipShape(RoundedRectangle(cornerRadius: kind == .avatar ? geometry.size.width / 2 : 12))
                    .contentShape(Rectangle())
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                offset = CGSize(
                                    width: dragOrigin.width + value.translation.width,
                                    height: dragOrigin.height + value.translation.height
                                )
                            }
                            .onEnded { _ in
                                let drawWidth = image.size.width * baseScale * zoom
                                let drawHeight = image.size.height * baseScale * zoom
                                let maxX = max((drawWidth - geometry.size.width) / 2, 0)
                                let maxY = max((drawHeight - geometry.size.height) / 2, 0)
                                offset.width = min(max(offset.width, -maxX), maxX)
                                offset.height = min(max(offset.height, -maxY), maxY)
                                dragOrigin = offset
                            }
                    )
                }
                .aspectRatio(aspect, contentMode: .fit)
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text("Zoom")
                        Spacer()
                        Text("\\\\(zoom, specifier: "%.1f")×").foregroundStyle(.secondary)
                    }
                    Slider(value: $zoom, in: 1...4, step: 0.05)
                }
                Text(kind == .avatar
                     ? "Drag to reposition your image inside the circular crop."
                     : "Drag to reposition your banner. The preview shows the visible profile banner area.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Spacer(minLength: 0)
                Button {
                    Task {
                        isSaving = true
                        let cropped = renderCrop()
                        await store.uploadProfileImage(cropped, kind: kind)
                        isSaving = false
                        if store.errorMessage == nil { dismiss() }
                    }
                } label: {
                    if isSaving { ProgressView().frame(maxWidth: .infinity) }
                    else { Text("Save image").frame(maxWidth: .infinity) }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isSaving)
            }
            .padding(20)
            .navigationTitle("Adjust image")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) { Button("Cancel") { dismiss() } }
            }
        }
        .presentationDetents([.large])
    }

    private func renderCrop() -> UIImage {
        let normalized = image
        let target = kind == .avatar ? CGSize(width: 1080, height: 1080) : CGSize(width: 1500, height: 500)
        let outputScale = target.width / 320
        let renderer = UIGraphicsImageRenderer(size: target)
        return renderer.image { _ in
            let viewport = CGSize(width: 320, height: 320 / aspect)
            let baseScale = max(viewport.width / normalized.size.width, viewport.height / normalized.size.height)
            let drawWidth = normalized.size.width * baseScale * zoom
            let drawHeight = normalized.size.height * baseScale * zoom
            let rect = CGRect(
                x: ((viewport.width - drawWidth) / 2 + offset.width) * outputScale,
                y: ((viewport.height - drawHeight) / 2 + offset.height) * outputScale,
                width: drawWidth * outputScale,
                height: drawHeight * outputScale
            )
            normalized.draw(in: rect)
        }
    }
}

"""
sheets = replace_once(
    sheets,
    """struct ProfileEditorSheet: View {""",
    crop_sheet + """struct ProfileEditorSheet: View {""",
    "profile crop editor view"
)
sheets = replace_once(
    sheets,
    """    @State private var username = ""
    @State private var isSaving = false""",
    """    @State private var username = ""
    @State private var bio = ""
    @State private var isSaving = false""",
    "profile editor bio state"
)
sheets = replace_once(
    sheets,
    """                    Text("3–32 characters. Letters, numbers and underscores only.")
                        .font(.caption).foregroundStyle(.secondary)
                }
                if let message""",
    """                    Text("3–32 characters. Letters, numbers and underscores only.")
                        .font(.caption).foregroundStyle(.secondary)
                    Text("Bio")
                    TextEditor(text: $bio)
                        .frame(minHeight: 90)
                    Text("\\\\(bio.count)/160")
                        .font(.caption).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .trailing)
                }
                if let message""",
    "profile editor bio field"
)
sheets = replace_once(
    sheets,
    """try await store.saveProfile(displayName: displayName, username: username)""",
    """try await store.saveProfile(displayName: displayName, username: username, bio: bio)""",
    "profile editor save bio"
)
sheets = replace_once(
    sheets,
    """                username = store.profile?.username ?? ""
            } catch""",
    """                username = store.profile?.username ?? ""
                bio = store.profile?.bio ?? ""
            } catch""",
    "profile editor load bio"
)
sheets_path.write_text(sheets)

# Chat list, new conversation picker, message thread, file attachments and recorded voice notes.
content = content_path.read_text()
content = replace_once(
    content,
    """import PhotosUI

struct ProfileBannerView""",
    """import PhotosUI
import AVFoundation
import UniformTypeIdentifiers

struct ProfileBannerView""",
    "audio and file imports"
)
start = content.index("struct MessagesScreen: View {")
end = content.index("\\nstruct UploadScreen: View {", start)
chat_views = """
struct MessagesScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let openAuth: () -> Void
    @State private var showNewMessage = false

    var body: some View {
        NavigationStack {
            Group {
                if store.session == nil {
                    ContentUnavailableView {
                        Label("Your conversations", systemImage: "bubble.left.and.bubble.right")
                    } description: {
                        Text("Sign in to start messaging.")
                    } actions: {
                        Button("Log in", action: openAuth).buttonStyle(.borderedProminent)
                    }
                } else if store.conversations.isEmpty {
                    ContentUnavailableView {
                        Label("No conversations yet", systemImage: "bubble.left.and.bubble.right")
                    } description: {
                        Text("Start a conversation with someone on Carbyne.")
                    } actions: {
                        Button("New message") { Task { await store.loadChannels(); showNewMessage = true } }
                            .buttonStyle(.borderedProminent)
                    }
                } else {
                    List(store.conversations) { conversation in
                        NavigationLink {
                            ChatThreadScreen(profile: conversation.profile)
                        } label: {
                            HStack(spacing: 12) {
                                AvatarView(url: store.publicImageURL(path: conversation.profile.avatarPath), size: 52)
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(conversation.profile.title).font(.system(size: 15, weight: .semibold))
                                    Text(conversation.lastMessage.preview)
                                        .font(.system(size: 13))
                                        .foregroundStyle(.secondary)
                                        .lineLimit(1)
                                }
                                Spacer()
                                Text(conversation.lastMessage.createdAt, style: .time)
                                    .font(.system(size: 11))
                                    .foregroundStyle(.tertiary)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Chat")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if store.session != nil {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button {
                            Task { await store.loadChannels(); showNewMessage = true }
                        } label: {
                            Image(systemName: "square.and.pencil")
                        }
                        .accessibilityLabel("New message")
                    }
                }
            }
            .sheet(isPresented: $showNewMessage) { NewMessageSheet() }
            .task {
                await store.loadConversations()
                await store.startMessagesRealtime()
            }
            .onDisappear { Task { await store.stopMessagesRealtime() } }
        }
    }
}

struct NewMessageSheet: View {
    @EnvironmentObject private var store: CarbyneStore
    @Environment(\\\\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List(store.channels.filter { $0.id != store.session?.user.id }) { profile in
                NavigationLink {
                    ChatThreadScreen(profile: profile)
                } label: {
                    ChannelRow(profile: profile, imageURL: store.publicImageURL(path: profile.avatarPath))
                }
            }
            .navigationTitle("New message")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .topBarTrailing) { Button("Done") { dismiss() } } }
            .task { await store.loadChannels() }
        }
    }
}

struct ChatThreadScreen: View {
    @EnvironmentObject private var store: CarbyneStore
    let profile: CarbyneProfile
    @State private var draft = ""
    @State private var showFilePicker = false
    @State private var recorder = CarbyneVoiceRecorder()
    @State private var isRecording = false

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(store.messages) { message in
                            HStack {
                                if message.senderID == store.session?.user.id { Spacer(minLength: 42) }
                                MessageBubble(message: message, isOutgoing: message.senderID == store.session?.user.id)
                                if message.senderID != store.session?.user.id { Spacer(minLength: 42) }
                            }
                            .id(message.id)
                        }
                    }
                    .padding(14)
                }
                .onChange(of: store.messages.count) { _, _ in
                    if let last = store.messages.last { withAnimation(.easeOut(duration: 0.2)) { proxy.scrollTo(last.id, anchor: .bottom) } }
                }
            }
            HStack(spacing: 10) {
                Button { showFilePicker = true } label: {
                    Image(systemName: "paperclip").font(.system(size: 18))
                }
                .accessibilityLabel("Attach file")
                Button(action: toggleRecording) {
                    Image(systemName: isRecording ? "stop.circle.fill" : "waveform")
                        .font(.system(size: 20))
                        .foregroundStyle(isRecording ? .red : .primary)
                }
                .accessibilityLabel(isRecording ? "Stop and send voice note" : "Record voice note")
                TextField("Message", text: $draft, axis: .vertical)
                    .lineLimit(1...4)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 9)
                    .background(Color(uiColor: .secondarySystemBackground), in: Capsule())
                Button {
                    let text = draft
                    draft = ""
                    Task { await store.sendMessage(to: profile, body: text) }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 28))
                }
                .disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || store.isLoading)
                .accessibilityLabel("Send message")
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(.ultraThinMaterial)
        }
        .navigationTitle(profile.title)
        .navigationBarTitleDisplayMode(.inline)
        .fileImporter(isPresented: $showFilePicker, allowedContentTypes: [.item], allowsMultipleSelection: false) { result in
            Task {
                do {
                    guard let url = try result.get().first else { return }
                    let accessed = url.startAccessingSecurityScopedResource()
                    defer { if accessed { url.stopAccessingSecurityScopedResource() } }
                    let data = try Data(contentsOf: url)
                    let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
                    await store.sendMessage(
                        to: profile,
                        body: "",
                        attachmentData: data,
                        fileName: url.lastPathComponent,
                        mimeType: mime,
                        messageType: "attachment"
                    )
                } catch {
                    store.errorMessage = error.localizedDescription
                }
            }
        }
        .task {
            store.activeChatProfile = profile
            await store.loadMessages(with: profile)
            await store.startMessagesRealtime()
        }
        .onDisappear {
            if store.activeChatProfile?.id == profile.id { store.activeChatProfile = nil }
        }
    }

    private func toggleRecording() {
        if isRecording {
            isRecording = false
            guard let url = recorder.finish() else { return }
            Task {
                do {
                    let data = try Data(contentsOf: url)
                    await store.sendMessage(
                        to: profile,
                        body: "",
                        attachmentData: data,
                        fileName: "Voice note.m4a",
                        mimeType: "audio/mp4",
                        messageType: "voice_note"
                    )
                } catch {
                    store.errorMessage = error.localizedDescription
                }
            }
        } else {
            do {
                try recorder.start()
                isRecording = true
            } catch {
                store.errorMessage = error.localizedDescription
            }
        }
    }
}

struct MessageBubble: View {
    @EnvironmentObject private var store: CarbyneStore
    let message: CarbyneMessage
    let isOutgoing: Bool
    @State private var audioPlayer: AVPlayer?

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if let body = message.body, !body.isEmpty {
                Text(body).font(.system(size: 15))
            }
            if let path = message.attachmentPath {
                Button {
                    Task {
                        do {
                            let url = try await store.signedAttachmentURL(path: path)
                            if message.messageType == "voice_note" {
                                audioPlayer = AVPlayer(url: url)
                                audioPlayer?.play()
                            } else {
                                await UIApplication.shared.open(url)
                            }
                        } catch {
                            store.errorMessage = error.localizedDescription
                        }
                    }
                } label: {
                    Label(
                        message.messageType == "voice_note" ? "Play voice note" : (message.attachmentName ?? "Open attachment"),
                        systemImage: message.messageType == "voice_note" ? "waveform" : "paperclip"
                    )
                    .font(.system(size: 13, weight: .medium))
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
    }
}

final class CarbyneVoiceRecorder {
    private var recorder: AVAudioRecorder?
    private var outputURL: URL?

    func start() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .default, options: [.defaultToSpeaker, .allowBluetooth])
        try session.setActive(true)
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("carbyne-voice-\\\\(UUID().uuidString).m4a")
        let settings: [String: Any] = [
            AVFormatIDKey: Int(kAudioFormatMPEG4AAC),
            AVSampleRateKey: 44100,
            AVNumberOfChannelsKey: 1,
            AVEncoderAudioQualityKey: AVAudioQuality.high.rawValue
        ]
        let recorder = try AVAudioRecorder(url: url, settings: settings)
        recorder.record()
        self.recorder = recorder
        outputURL = url
    }

    func finish() -> URL? {
        recorder?.stop()
        recorder = nil
        return outputURL
    }
}

"""
content = content[:start] + chat_views + content[end:]

# Present the crop editor after picking an image instead of immediately center-cropping it.
content = replace_once(
    content,
    """    @State private var selectedKind: ProfileImageKind = .avatar
    @State private var isProcessing = false""",
    """    @State private var selectedKind: ProfileImageKind = .avatar
    @State private var isProcessing = false
    @State private var pendingImage: UIImage?
    @State private var showCropEditor = false""",
    "crop editor state"
)
content = replace_once(
    content,
    """        .onChange(of: bannerItem) { _, item in
            Task { await upload(item, kind: .banner) }
        }
    }

    private func upload""",
    """        .onChange(of: bannerItem) { _, item in
            Task { await upload(item, kind: .banner) }
        }
        .sheet(isPresented: $showCropEditor) {
            if let pendingImage {
                ProfileImageCropSheet(image: pendingImage, kind: selectedKind)
            }
        }
    }

    private func upload""",
    "crop editor sheet"
)
content = replace_once(
    content,
    """            await store.uploadProfileImage(image, kind: kind)
        } catch { store.errorMessage = error.localizedDescription }""",
    """            selectedKind = kind
            pendingImage = image
            showCropEditor = true
        } catch { store.errorMessage = error.localizedDescription }""",
    "image selection crop flow"
)
# Display bios on own/public profiles and their About sections.
content = replace_once(
    content,
    """                                Text("\\\\(store.subscriberCount) subscribers")
                                    .font(.system(size: 13))
                                    .foregroundStyle(.secondary)
                            }""",
    """                                Text("\\\\(store.subscriberCount) subscribers")
                                    .font(.system(size: 13))
                                    .foregroundStyle(.secondary)
                                if let bio = profile.bio, !bio.isEmpty {
                                    Text(bio).font(.system(size: 13)).foregroundStyle(.secondary).lineLimit(3)
                                }
                            }""",
    "own profile bio display"
)
content = replace_once(
    content,
    """                            case "About":
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                    Text("@\\\\(profile.username ?? "unknown")")
                                }""",
    """                            case "About":
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                    Text("@\\\\(profile.username ?? "unknown")")
                                    if let bio = profile.bio, !bio.isEmpty { Text(bio) }
                                    else { Text("No bio yet.").foregroundStyle(.secondary) }
                                }""",
    "own profile about bio"
)
content = replace_once(
    content,
    """                            Text("\\\\(store.subscriberCount) subscribers")
                                .font(.system(size: 16, weight: .medium)).foregroundStyle(.secondary)
                        }""",
    """                            Text("\\\\(store.subscriberCount) subscribers")
                                .font(.system(size: 16, weight: .medium)).foregroundStyle(.secondary)
                            if let bio = profile.bio, !bio.isEmpty {
                                Text(bio).font(.system(size: 13)).foregroundStyle(.secondary).lineLimit(3)
                            }
                        }""",
    "public profile bio display"
)
content = replace_once(
    content,
    """                            case "About":
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                    Text("@\\\\(profile.username ?? "unknown")")
                                }""",
    """                            case "About":
                                VStack(alignment: .leading, spacing: 8) {
                                    Text(profile.title)
                                    Text("@\\\\(profile.username ?? "unknown")")
                                    if let bio = profile.bio, !bio.isEmpty { Text(bio) }
                                    else { Text("No bio yet.").foregroundStyle(.secondary) }
                                }""",
    "public profile about bio"
)
content_path.write_text(content)

# Slightly enlarge the signed-in user's avatar in the fifth native tab item.
tabs = tabs_path.read_text()
tabs = replace_once(
    tabs,
    """            let size = CGSize(width: 24, height: 24)""",
    """            let size = CGSize(width: 28, height: 28)""",
    "tab bar avatar size"
)
tabs_path.write_text(tabs)

# Recording needs the standard iOS microphone permission explanation.
project = project_path.read_text()
project = replace_once(
    project,
    """    INFOPLIST_KEY_NSPhotoLibraryUsageDescription: Carbyne uses your photo library to update your profile picture and channel banner.""",
    """    INFOPLIST_KEY_NSPhotoLibraryUsageDescription: Carbyne uses your photo library to update your profile picture and channel banner.
    INFOPLIST_KEY_NSMicrophoneUsageDescription: Carbyne uses the microphone to record voice notes you choose to send.""",
    "microphone usage description"
)
project_path.write_text(project)

print("Added Supabase messaging, private attachments, voice notes, YouTube-style profile image positioning, profile bios, and a larger tab avatar.")
