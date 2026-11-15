from pathlib import Path

content_path = Path("ios/Carbyne/Sources/ContentView.swift")
store_path = Path("ios/Carbyne/Sources/CarbyneStore.swift")
content = content_path.read_text()
store = store_path.read_text()

# Give the Subscribe/Subscribed symbol a quick springy response when its
# server-confirmed state changes. The replace transition morphs plus/checkmark.
label = """                        Label(store.isSubscribed ? "Subscribed" : "Subscribe",
                              systemImage: store.isSubscribed ? "checkmark" : "plus")
                            .font(.system(size: 12, weight: .semibold))
"""
animated_label = """                        Label(store.isSubscribed ? "Subscribed" : "Subscribe",
                              systemImage: store.isSubscribed ? "checkmark" : "plus")
                            .font(.system(size: 12, weight: .semibold))
                            .contentTransition(.symbolEffect(.replace))
                            .symbolEffect(.bounce, value: store.isSubscribed)
                            .animation(.spring(response: 0.34, dampingFraction: 0.68), value: store.isSubscribed)
"""
if animated_label not in content:
    if label not in content:
        raise SystemExit("Could not find the public-profile Subscribe label to animate.")
    content = content.replace(label, animated_label, 1)

# Trigger a subtle UIKit haptic only after Supabase confirms the subscription
# change and the refreshed state actually differs from the previous state.
old = """        isLoading = true
        defer { isLoading = false }
        do {
            if isSubscribed {
"""
new = """        let wasSubscribed = isSubscribed
        let feedback = UIImpactFeedbackGenerator(style: wasSubscribed ? .soft : .medium)
        feedback.prepare()
        isLoading = true
        defer { isLoading = false }
        do {
            if isSubscribed {
"""
if new not in store:
    raise SystemExit("Could not find toggleSubscription's loading/action block.")
store = store.replace("        isLoading = true\n        defer { isLoading = false }\n        do {\n            if isSubscribed {", new, 1)

old_refresh = """            await refreshSubscription(for: channel)
        } catch { errorMessage = error.localizedDescription }
"""
new_refresh = """            await refreshSubscription(for: channel)
            if isSubscribed != wasSubscribed {
                feedback.impactOccurred()
            }
        } catch { errorMessage = error.localizedDescription }
"""
if new_refresh not in store:
    if old_refresh not in store:
        raise SystemExit("Could not find toggleSubscription's refresh completion.")
    store = store.replace(old_refresh, new_refresh, 1)

content_path.write_text(content)
store_path.write_text(store)
print("Added a spring symbol transition and success-only subscription haptics.")
