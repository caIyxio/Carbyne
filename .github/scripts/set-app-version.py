from pathlib import Path
import os
import re

project_yml = next(Path("ios/Carbyne").rglob("project.yml"), None)
if project_yml is None:
    raise SystemExit("XcodeGen project.yml was not found.")

version_file = Path("ios/Carbyne/VERSION")
version = version_file.read_text().strip() if version_file.exists() else "26.0.0"
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    raise SystemExit(f"Invalid app version: {version!r}")

# GitHub's workflow run number is monotonic across successful and failed builds.
# Local builds use 1 until a CI build number is supplied.
build_number = os.environ.get("GITHUB_RUN_NUMBER", "1")
if not re.fullmatch(r"\d+", build_number):
    raise SystemExit(f"Invalid build number: {build_number!r}")

text = project_yml.read_text()
settings_match = re.search(r"(?m)^settings:\s*$", text)
if settings_match is None:
    text = (
        'settings:\n'
        '  base:\n'
        f'    MARKETING_VERSION: "{version}"\n'
        f'    CURRENT_PROJECT_VERSION: "{build_number}"\n'
        '    VERSIONING_SYSTEM: apple-generic\n'
        f'    INFOPLIST_KEY_CFBundleShortVersionString: "{version}"\n'
        f'    INFOPLIST_KEY_CFBundleVersion: "{build_number}"\n\n'
        + text
    )
else:
    base_match = re.search(r"(?m)^  base:\s*$", text[settings_match.end():])
    if base_match is None:
        insert_at = settings_match.end()
        text = text[:insert_at] + (
            '\n  base:\n'
            f'    MARKETING_VERSION: "{version}"\n'
            f'    CURRENT_PROJECT_VERSION: "{build_number}"\n'
            '    VERSIONING_SYSTEM: apple-generic\n'
            f'    INFOPLIST_KEY_CFBundleShortVersionString: "{version}"\n'
            f'    INFOPLIST_KEY_CFBundleVersion: "{build_number}"\n'
        ) + text[insert_at:]
    else:
        base_start = settings_match.end() + base_match.start()
        base_end = settings_match.end() + base_match.end()
        insert_at = text.find("\n", base_end) + 1
        keys = {
            "MARKETING_VERSION": version,
            "CURRENT_PROJECT_VERSION": build_number,
            "VERSIONING_SYSTEM": "apple-generic",
            "INFOPLIST_KEY_CFBundleShortVersionString": version,
            "INFOPLIST_KEY_CFBundleVersion": build_number,
        }
        for key, value in keys.items():
            pattern = re.compile(rf"(?m)^(\\s*){re.escape(key)}:\\s*.*$")
            replacement = lambda match, value=value: f'{match.group(1)}{key}: "{value}"'
            if pattern.search(text):
                text = pattern.sub(replacement, text)
            else:
                text = text[:insert_at] + f'    {key}: "{value}"\n' + text[insert_at:]
                insert_at += len(f'    {key}: "{value}"\n')

# Ensure any existing target-level values cannot override the app version.
for key, value in {
    "MARKETING_VERSION": version,
    "CURRENT_PROJECT_VERSION": build_number,
    "VERSIONING_SYSTEM": "apple-generic",
    "INFOPLIST_KEY_CFBundleShortVersionString": version,
    "INFOPLIST_KEY_CFBundleVersion": build_number,
}.items():
    pattern = re.compile(rf"(?m)^(\\s*){re.escape(key)}:\\s*.*$")
    text = pattern.sub(lambda match, key=key, value=value: f'{match.group(1)}{key}: "{value}"', text)

project_yml.write_text(text)
print(f"Carbyne version set to {version} (build {build_number}).")
