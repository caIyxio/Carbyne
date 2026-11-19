from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
store_path = Path("ios/Carbyne/Sources/CarbyneStore.swift")

content = content_path.read_text()
store = store_path.read_text()
account_sheets_path = Path("ios/Carbyne/Sources/AccountSheets.swift")
account_sheets = account_sheets_path.read_text()

# Ignore task cancellations instead of showing them as user-facing failures.
error_handler = '''    func displayableError(_ error: Error) -> String? {
        guard !Self.isCancellation(error) else { return nil }
        return error.localizedDescription
    }

    func handleError(_ error: Error, prefix: String? = nil) {
        guard let description = displayableError(error) else { return }
        errorMessage = prefix.map { "\\($0) \\(description)" } ?? description
    }

    private static func isCancellation(_ error: Error) -> Bool {
        if error is CancellationError { return true }
        let nsError = error as NSError
        if nsError.domain == NSURLErrorDomain && nsError.code == NSURLErrorCancelled { return true }
        if let underlying = nsError.userInfo[NSUnderlyingErrorKey] as? Error {
            return isCancellation(underlying)
        }
        return false
    }
'''

store_anchor = "    func restoreSession() async {"
if store_anchor not in store:
    raise SystemExit("CarbyneStore restoreSession insertion point not found.")
store = store.replace(store_anchor, error_handler + store_anchor, 1)
store = store.replace(
    "} catch {\n            session = nil",
    "} catch {\n            if Self.isCancellation(error) { return }\n            session = nil",
    1
)
store = store.replace(
    'errorMessage = "This account could not be loaded. Sign in again if its saved session has expired. \\(error.localizedDescription)"',
    'handleError(error, prefix: "This account could not be loaded. Sign in again if its saved session has expired.")'
)
store = store.replace("errorMessage = error.localizedDescription", "handleError(error)")
if "errorMessage = error.localizedDescription" in store:
    raise SystemExit("Unconverted CarbyneStore error assignment remains.")

# Apply the same cancellation filter to async actions launched by SwiftUI views.
content = content.replace("store.errorMessage = error.localizedDescription", "store.handleError(error)")
content = content.replace("transcriptionError = error.localizedDescription", "transcriptionError = store.displayableError(error)")

account_sheets = account_sheets_path.read_text()
account_sheets = account_sheets.replace("store.errorMessage = error.localizedDescription", "store.handleError(error)")
account_sheets = account_sheets.replace("message = error.localizedDescription", "message = store.displayableError(error)")

account_sheets_path.write_text(account_sheets)
content_path.write_text(content)
store_path.write_text(store)
print("Applied continuous appearance-matched Home fade and ignored Swift task cancellation errors.")

home_start = content.index("struct HomeScreen: View {")
home_end = content.index("\n\nstruct SearchScreen: View {", home_start)
home_source = content[home_start:home_end]
if "@Environment(\\.colorScheme) private var colorScheme" not in home_source:
    anchor = "struct HomeScreen: View {\n    @EnvironmentObject private var store: CarbyneStore\n    @Environment(\\.horizontalSizeClass) private var sizeClass\n"
    if anchor not in home_source:
        raise SystemExit("HomeScreen environment declaration not found.")
    home_source = home_source.replace(
        anchor,
        anchor + "    @Environment(\\.colorScheme) private var colorScheme\n",
        1
    )
    content = content[:home_start] + home_source + content[home_end:]

old_header = '''        .safeAreaInset(edge: .top, spacing: 0) {
            HStack {
                CarbyneWordmark(height: 34)
                Spacer()
                Button { openSearch() } label: {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 18, weight: .medium))
                        .frame(width: 42, height: 42)
                        .background {
                            if #available(iOS 26.0, *) {
                                Circle().fill(.clear)
                                    .glassEffect(.regular.interactive(), in: Circle())
                            } else {
                                Circle().fill(.ultraThinMaterial)
                                    .overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))
                            }
                        }
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Search")
            }
            .padding(.horizontal, isPad ? 34 : 20)
            .padding(.vertical, 7)
            .background(.ultraThinMaterial)
        }'''

new_header = '''        .safeAreaInset(edge: .top, spacing: 0) {
            ZStack(alignment: .top) {
                LinearGradient(
                    colors: [CarbynePalette.background, CarbynePalette.background.opacity(0)],
                    startPoint: .top,
                    endPoint: .bottom
                )
                .frame(height: 184)
                .frame(maxWidth: .infinity)
                .ignoresSafeArea(edges: .top)
                .allowsHitTesting(false)

                HStack {
                    Button {
                        Task {
                            await store.loadChannels(force: true)
                            if let ownProfile = store.profile {
                                await store.refreshSubscription(for: ownProfile)
                            }
                        }
                    } label: {
                        CarbyneWordmark(height: 34)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Refresh Home")

                    Spacer()
                    Button { openSearch() } label: {
                        Image(systemName: "magnifyingglass")
                            .font(.system(size: 18, weight: .medium))
                            .frame(width: 42, height: 42)
                            .background {
                                if #available(iOS 26.0, *) {
                                    Circle().fill(.clear)
                                        .glassEffect(.regular.interactive(), in: Circle())
                                } else {
                                    Circle().fill(.ultraThinMaterial)
                                        .overlay(Circle().strokeBorder(Color.primary.opacity(0.08)))
                                }
                            }
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Search")
                }
                .padding(.horizontal, isPad ? 34 : 20)
                .padding(.vertical, 7)
            }
            .frame(height: 56, alignment: .top)
        }'''

if old_header not in content:
    raise SystemExit("Expected original Home header block was not found.")
content = content.replace(old_header, new_header, 1)
content = content.replace(".background(CarbynePalette.background.ignoresSafeArea())\n        .safeAreaInset(edge: .top, spacing: 0) {", ".background(CarbynePalette.background)\n        .safeAreaInset(edge: .top, spacing: 0) {", 1)

old_method = '''    func loadChannels() async {
        guard let userID = session?.user.id else { return }
        if loadedChannelsForUserID == userID { return }'''
new_method = '''    func loadChannels(force: Bool = false) async {
        guard let userID = session?.user.id else { return }
        if loadedChannelsForUserID == userID && !force { return }'''
if old_method not in store:
    raise SystemExit("Expected loadChannels method was not found.")
store = store.replace(old_method, new_method, 1)

content_path.write_text(content)
store_path.write_text(store)
print("Applied adaptive light/dark Home gradient, tappable wordmark refresh, and forced channel reload.")
