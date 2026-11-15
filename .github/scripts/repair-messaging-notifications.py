from pathlib import Path

root = Path("ios/Carbyne/Sources")
content_path = root / "ContentView.swift"
store_path = root / "CarbyneStore.swift"
app_path = root / "CarbyneApp.swift"

def replace_once(source, old, new, label):
    if new in source:
        return source
    if old not in source:
        raise SystemExit(f"Could not find {label}; refusing to patch the wrong source.")
    return source.replace(old, new, 1)

# Chat screen: profile picture above the display name in the navigation header.
content = content_path.read_text()
content = replace_once(
    content,
    "import UniformTypeIdentifiers\n",
    "import UniformTypeIdentifiers\nimport UserNotifications\n",
    "notification import"
)

content = replace_once(
    content,
    """    @State private var showFilePicker = false
    @State private var recorder = CarbyneVoiceRecorder()""",
    """    @State private var selectedPhoto: PhotosPickerItem?
    @State private var recorder = CarbyneVoiceRecorder()""",
    "gallery picker state"
)

content = replace_once(
    content,
    """                Button { showFilePicker = true } label: {
                    Image(systemName: "paperclip").font(.system(size: 18))
                }
                .accessibilityLabel("Attach file")""",
    """                PhotosPicker(selection: $selectedPhoto, matching: .images, photoLibrary: .shared()) {
                    Image(systemName: "photo").font(.system(size: 20))
                }
                .accessibilityLabel("Choose photo from your library")""",
    "gallery-only attachment picker"
)

start = content.find("        .fileImporter(isPresented: $showFilePicker")
if start >= 0:
    end = content.find("        .task {", start)
    if end < 0:
        raise SystemExit("Could not find ChatThreadScreen task after the old file importer.")
    content = content[:start] + """        .onChange(of: selectedPhoto) { _, item in
            guard let item else { return }
            Task { await sendPhoto(item) }
        }
""" + content[end:]

content = replace_once(
    content,
    """        .navigationTitle(profile.title)
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: selectedPhoto)""",
    """        .navigationTitle("")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                VStack(spacing: 2) {
                    AvatarView(url: store.publicImageURL(path: profile.avatarPath), size: 30)
                    Text(profile.title)
                        .font(.system(size: 12, weight: .semibold))
                        .lineLimit(1)
                }
                .accessibilityElement(children: .combine)
            }
        }
        .onChange(of: selectedPhoto)""",
    "stacked profile photo chat header"
)

content = replace_once(
    content,
    """    private func toggleRecording() {
        if isRecording {""",
    """    private func sendPhoto(_ item: PhotosPickerItem) async {
        do {
            guard let data = try await item.loadTransferable(type: Data.self) else { return }
            let type = item.supportedContentTypes.first
            let mime = type?.preferredMIMEType ?? "image/jpeg"
            let ext = type?.preferredFilenameExtension ?? "jpg"
            await store.sendMessage(
                to: profile,
                body: "",
                attachmentData: data,
                fileName: "Photo.\\\\(ext)",
                mimeType: mime,
                messageType: "attachment"
            )
        } catch {
            store.errorMessage = error.localizedDescription
        }
        selectedPhoto = nil
    }

    private func toggleRecording() {
        if isRecording {""",
    "gallery photo upload method"
)

# Replace generic Play Audio action with a conventional voice-note player bubble.
bubble_start = content.find("struct MessageBubble: View {")
bubble_end = content.find("\\nfinal class CarbyneVoiceRecorder", bubble_start)
if bubble_start < 0 or bubble_end < 0:
    raise SystemExit("Could not locate MessageBubble and voice recorder boundaries.")
new_bubble = """struct MessageBubble: View {
    @EnvironmentObject private var store: CarbyneStore
    let message: CarbyneMessage
    let isOutgoing: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            if let body = message.body, !body.isEmpty {
                Text(body).font(.system(size: 15))
            }
            if let path = message.attachmentPath {
                if message.messageType == "voice_note" {
                    VoiceNotePlayer(path: path, isOutgoing: isOutgoing)
                } else {
                    Button {
                        Task {
                            do {
                                let url = try await store.signedAttachmentURL(path: path)
                                await UIApplication.shared.open(url)
                            } catch {
                                store.errorMessage = error.localizedDescription
                            }
                        }
                    } label: {
                        Label(message.attachmentName ?? "Photo", systemImage: "photo")
                            .font(.system(size: 13, weight: .medium))
                    }
                    .buttonStyle(.plain)
                }
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

struct VoiceNotePlayer: View {
    @EnvironmentObject private var store: CarbyneStore
    let path: String
    let isOutgoing: Bool
    @StateObject private var playback = VoiceNotePlaybackController()

    var body: some View {
        HStack(spacing: 10) {
            Button {
                Task {
                    do {
                        let url = try await store.signedAttachmentURL(path: path)
                        try await playback.toggle(url: url)
                    } catch {
                        store.errorMessage = error.localizedDescription
                    }
                }
            } label: {
                Image(systemName: playback.isPlaying ? "pause.fill" : "play.fill")
                    .font(.system(size: 15, weight: .bold))
                    .frame(width: 34, height: 34)
                    .background(isOutgoing ? Color.white.opacity(0.2) : Color.primary.opacity(0.08), in: Circle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel(playback.isPlaying ? "Pause voice note" : "Play voice note")

            VStack(alignment: .leading, spacing: 5) {
                HStack(alignment: .center, spacing: 2) {
                    ForEach(Array([5, 10, 7, 14, 9, 17, 11, 6, 15, 9, 18, 8, 13, 5, 11, 16, 7, 12].enumerated()), id: \\\\.offset) { item in
                        Capsule()
                            .frame(width: 3, height: CGFloat(item.element))
                    }
                }
                .frame(height: 20, alignment: .center)
                Text(playback.duration > 0 ? playback.formattedDuration : "Voice message")
                    .font(.system(size: 11, weight: .medium))
                    .opacity(0.8)
            }
            .frame(maxWidth: 155, alignment: .leading)
        }
        .padding(.vertical, 2)
        .frame(minWidth: 190, alignment: .leading)
    }
}

@MainActor
final class VoiceNotePlaybackController: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var isPlaying = false
    @Published private(set) var duration: TimeInterval = 0
    private var player: AVAudioPlayer?

    var formattedDuration: String {
        let seconds = Int(duration)
        return String(format: "%d:%02d", seconds / 60, seconds % 60)
    }

    func toggle(url: URL) async throws {
        if let player {
            if isPlaying {
                player.pause()
                isPlaying = false
            } else {
                player.play()
                isPlaying = true
            }
            return
        }

        let (data, _) = try await URLSession.shared.data(from: url)
        let newPlayer = try AVAudioPlayer(data: data)
        newPlayer.delegate = self
        newPlayer.prepareToPlay()
        duration = newPlayer.duration
        player = newPlayer
        newPlayer.play()
        isPlaying = true
    }

    func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        isPlaying = false
        player.currentTime = 0
    }
}
"""
content = content[:bubble_start] + new_bubble + content[bubble_end:]

# Ask notification permission only when a signed-in user opens Chat.
content = replace_once(
    content,
    """            .task {
                await store.loadConversations()
                await store.startMessagesRealtime()
            }""",
    """            .task {
                await store.requestMessageNotificationPermission()
                await store.loadConversations()
                await store.startMessagesRealtime()
            }""",
    "chat notification permission request"
)

content_path.write_text(content)

# Deliver local message alerts with the system default sound for incoming messages
# while the app is connected to Supabase Realtime.
store = store_path.read_text()
store = replace_once(
    store,
    "import UIKit\\n",
    "import UIKit\\nimport UserNotifications\\n",
    "store notification import"
)
store = replace_once(
    store,
    """    private var messagesRealtimeChannel: RealtimeChannelV2?
    private var supabase: SupabaseClient""",
    """    private var messagesRealtimeChannel: RealtimeChannelV2?
    private var knownLatestMessageIDs = Set<UUID>()
    private var conversationSnapshotUserID: UUID?
    private var hasInitialConversationSnapshot = false
    private var supabase: SupabaseClient""",
    "notification snapshot state"
)
store = replace_once(
    store,
    """            conversations = loaded.sorted { $0.lastMessage.createdAt > $1.lastMessage.createdAt }
        } catch {""",
    """            let sorted = loaded.sorted { $0.lastMessage.createdAt > $1.lastMessage.createdAt }
            if conversationSnapshotUserID != userID {
                conversationSnapshotUserID = userID
                knownLatestMessageIDs.removeAll()
                hasInitialConversationSnapshot = false
            }
            if hasInitialConversationSnapshot {
                for conversation in sorted {
                    let message = conversation.lastMessage
                    if !knownLatestMessageIDs.contains(message.id),
                       message.recipientID == userID,
                       activeChatProfile?.id != message.senderID {
                        let senderName = conversation.profile.title
                        scheduleMessageNotification(from: senderName, preview: message.preview)
                    }
                }
            }
            knownLatestMessageIDs.formUnion(sorted.map { $0.lastMessage.id })
            hasInitialConversationSnapshot = true
            conversations = sorted
        } catch {""",
    "incoming message notification detection"
)
store = replace_once(
    store,
    """    func loadConversations() async {""",
    """    func requestMessageNotificationPermission() async {
        _ = try? await UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .sound, .badge])
    }

    private func scheduleMessageNotification(from sender: String, preview: String) {
        let content = UNMutableNotificationContent()
        content.title = sender
        content.body = preview
        content.sound = .default
        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil
        )
        Task { try? await UNUserNotificationCenter.current().add(request) }
    }

    func loadConversations() async {""",
    "notification methods"
)
store = replace_once(
    store,
    """                await self.loadConversations()
                if let peer = self.activeChatProfile { await self.loadMessages(with: peer) }""",
    """                await self.loadConversations()
                if let peer = self.activeChatProfile { await self.loadMessages(with: peer) }""",
    "realtime notification refresh"
)
store_path.write_text(store)

# Register a notification delegate so default-sound alerts can be presented in-app too.
app = app_path.read_text()
app = replace_once(
    app,
    "import UIKit\\n",
    "import UIKit\\nimport UserNotifications\\n",
    "app notification import"
)
app = replace_once(
    app,
    """@main
struct CarbyneApp: App {
    @StateObject private var store = CarbyneStore()""",
    """final class CarbyneAppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.banner, .sound, .list]
    }
}

@main
struct CarbyneApp: App {
    @UIApplicationDelegateAdaptor(CarbyneAppDelegate.self) private var appDelegate
    @StateObject private var store = CarbyneStore()""",
    "notification app delegate"
)
app_path.write_text(app)

print("Updated chat header, gallery-only photo attachments, voice-note playback UI, and default-sound local message alerts.")
