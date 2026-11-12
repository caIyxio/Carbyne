# Carbyne

Carbyne's repository now contains a GitHub Actions deployment pipeline and a native SwiftUI iOS client.

## Website deployment

The provided web export and SwiftUI source are preserved in the ordered base64 chunks under `.github/source-bundle/`. The website workflow extracts that source, validates it, copies the static production output into `dist/` on a GitHub-hosted Ubuntu runner, then sends the already-built `dist/` directory to the existing Netlify site with the Netlify CLI. That CLI invocation is a direct deploy; it does not ask Netlify to run the website build.

Add these GitHub repository or `production` environment secrets before the first production deploy:

- `NETLIFY_AUTH_TOKEN` — a Netlify personal access token.
- `NETLIFY_SITE_ID` — the existing Carbyne site ID.

The workflow intentionally fails before deployment if either secret is missing. It never prints their values. Pull requests build and validate the static site but do not publish production.

## Native iOS app

The native SwiftUI project is under `ios/Carbyne/` after extracting the source bundle. It uses the existing Carbyne Supabase project and the public publishable key already used by the website. Auth sessions use the iOS Keychain through Supabase's Swift SDK.

On GitHub Actions, the iOS workflow runs XcodeGen and Xcode on a macOS runner, compiles for a generic iOS device without code signing, packages the resulting app as `Carbyne-unsigned.ipa`, and uploads it as the `Carbyne-unsigned-IPA` workflow artifact. The IPA is deliberately unsigned; it must be signed with a sideloading tool and a device-compatible provisioning profile before it can be installed on an iPhone.

## Backend scope discovered during the port

The connected production schema currently exposes `profiles` and `subscriptions`. Its only storage bucket is public `avatars`, limited to JPEG/PNG/AVIF images up to 5 MB. The native app implements those real surfaces: sign-in/sign-up, TOTP MFA, account switching, public channel discovery, profile editing, subscriptions, and avatar/banner upload.

There is currently no conversations/messages table, posts/video table, or video storage bucket in this Supabase project, and the supplied website export does not implement direct messages or a populated feed. The DMs destination therefore states that messaging is not yet backed by the existing platform; the Home feed renders a genuine empty state rather than invented posts. Video publishing cannot be made functional without a backend data model and storage policy.

## Source bundle

The compressed source bundle is stored as ordered text chunks so it can be committed through GitHub's text-file API without altering the original bytes. To unpack it locally from the repository root:

```sh
cat .github/source-bundle/part-*.b64 | base64 --decode > /tmp/carbyne-project-source.tar.gz
tar -xzf /tmp/carbyne-project-source.tar.gz -C .
```

The `Carbyne.png` logo mentioned in the project brief was not present in the supplied ZIP or the repository's original `main` tree, so the app currently uses a native text wordmark rather than substituting an unrelated image.
