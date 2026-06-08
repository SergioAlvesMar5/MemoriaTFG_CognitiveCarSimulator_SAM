
import argparse
import re
from pathlib import Path


OUTPUT_FILENAME = "clean_run_output.txt"


# If False, the script keeps relevant warnings, but removes noisy warnings from EOS/HTTP,
# missing editor icons, cache, telemetry, plugin loading, etc.
DEFAULT_KEEP_ALL_WARNINGS = True
CONTEXT_LINES_AFTER_CRITICAL = 25


TIMESTAMP_PREFIX_RE = re.compile(r"^(?:\[[^\]]*\]\s*)+")
SEVERITY_RE = re.compile(
    r"\b("
    r"Warning|Error|Fatal|Ensure|Exception|Assertion failed|Unhandled Exception|"
    r"Accessed None|Blueprint Runtime Error|Script Stack|Callstack|Crash|DXGI|DEVICE_HUNG"
    r")\b",
    re.IGNORECASE,
)

BLUEPRINT_MESSAGE_RE = re.compile(
    r"(LogBlueprintUserMessages|LogBlueprint|Blueprint Runtime Error|PrintString|Script Stack)",
    re.IGNORECASE,
)

PROJECT_RUNTIME_RE = re.compile(
    r"\b("
    r"FITNESS|fitness|Generaci[oó]n|Generation|Training|Train|Testing|Test|"
    r"SPAWNPOINT|SpawnPoint|VehicleAI|BP_VehicleAI|BP_EvolutionManager|"
    r"STOP|YIELD|TrafficLight|Semaforo|Semáforo|Ceda|StopTarget|"
    r"TIMEFINISHED|LAZY|REVERSE LAZY|Nuevo Record|HE MUERTO"
    r")\b",
    re.IGNORECASE,
)

# Categories that are almost always editor/engine noise.
# They are removed unless they contain a serious error/fatal/crash,
# or unless --keep-all-warnings is enabled and the line is a normal warning.
NOISY_CATEGORIES = {
    "LogEOSSDK",
    "LogHttp",
    "LogDerivedDataCache",
    "LogDerivatedDataCache",
    "LogDerivedDataBuild",
    "LogZenServiceInstance",
    "LogZenStore",
    "LogPluginManager",
    "LogConfig",
    "LogInit",
    "LogCsvProfiler",
    "LogDevObjectVersion",
    "LogAssetRegistry",
    "LogAudio",
    "LogAudioDebug",
    "LogAudioMixer",
    "LogSlate",
    "LogSlateStyle",
    "LogUObjectHash",
    "LogPackageName",
    "LogStudioTelemetry",
    "LogNFORDenoise",
    "LogMemory",
    "LogStats",
    "LogIris",
    "LogICUInternationalization",
    "LogTrace",
    "LogCore",
    "LogContentValidation",
    "LogSavePackage",
    "LogAssetEditorSubsystem",
    "LogPlayLevel",
    "AssetCheck",
    "SourceControl",
    "RenderDocPlugin",
    "PixWinPlugin",
    "OBJ",
}

# Warning lines that must be kept even when they belong to normally noisy categories.
# This keeps EOS/HTTP response headers such as:
# LogEOSSDK: Warning: LogHttp: ... Response Header Content-Type: text/plain
IMPORTANT_WARNING_PATTERNS = [
    r"LogEOSSDK:\s*Warning:\s*LogHttp:.*\bResponse Header\b",
    r"LogHttp:\s*Warning:.*\bResponse Header\b",
]

# Warning lines that are technically warnings but usually irrelevant for your analysis.
NOISY_WARNING_PATTERNS = [
    r"LogEOSSDK: Warning:",
    r"LogHttp: Warning:",
    r"libcurl",
    r"datarouter",
    r"api\.epicgames\.dev",
    r"telemetry",
    r"HTTP request timed out",
    r"Retry exhausted",
    r"TLS",
    r"SSL",
    r"certificate",
    r"Failed to read file .*(Icon|Selector|Slate|Platform_|alertSolid)",
    r"Map check complete:\s*0 Error\(s\),\s*0 Warning\(s\)",
]

# Other non-warning lines that are noise even if they contain project asset names.
BENIGN_SEVERITY_PATTERNS = [
    r"Custom abort handler registered for crash reporting",
    r"Map check complete:\s*0 Error\(s\),\s*0 Warning\(s\)",
]

NOISY_LINE_PATTERNS = [
    r"Mounting Engine plugin",
    r"Mounting Project plugin",
    r"Applying CVar settings",
    r"Set CVar",
    r"CVar \[\[",
    r"Metadata set",
    r"Loading .* ini files",
    r"Opening Asset editor",
    r"SavePackage",
    r"Generating thumbnails",
    r"Finished generating thumbnails",
    r"Rendered thumbnail",
    r"Validating asset",
    r"Revision control is disabled",
    r"DerivedDataCache",
    r"EOSSDK",
]


def strip_unreal_prefix(line: str) -> str:
    """Remove Unreal timestamp/frame prefixes like [2026...][123]."""
    return TIMESTAMP_PREFIX_RE.sub("", line).strip()


def get_category(line: str) -> str:
    """Extract Unreal log category, for example LogBlueprintUserMessages."""
    clean = strip_unreal_prefix(line)
    if ":" not in clean:
        return ""
    return clean.split(":", 1)[0].strip()


def matches_any(line: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns)


def has_serious_severity(line: str) -> bool:
    return bool(
        re.search(
            r"\b(Error|Fatal|Ensure|Exception|Assertion failed|Unhandled Exception|Crash|DXGI|DEVICE_HUNG)\b",
            line,
            re.IGNORECASE,
        )
    )


def has_warning(line: str) -> bool:
    return bool(re.search(r"\bWarning\b", line, re.IGNORECASE))


def should_keep_line(line: str, keep_all_warnings: bool = DEFAULT_KEEP_ALL_WARNINGS) -> bool:
    raw = line.strip()

    if not raw:
        return False

    category = get_category(raw)

    # 0) Drop benign lines that contain words like Warning/Error/Crash but are not useful.
    if matches_any(raw, BENIGN_SEVERITY_PATTERNS):
        return False

    # 1) Always keep explicit Blueprint/user/runtime messages.
    if BLUEPRINT_MESSAGE_RE.search(raw):
        return True

    # 2) Keep selected warning lines that are useful even if they belong to noisy categories.
    if has_warning(raw) and matches_any(raw, IMPORTANT_WARNING_PATTERNS):
        return True

    # 3) Remove known irrelevant warning spam unless the user explicitly asks for every warning.
    if has_warning(raw) and not keep_all_warnings and matches_any(raw, NOISY_WARNING_PATTERNS):
        return False

    # 4) Keep serious failures even if they come from engine categories.
    if has_serious_severity(raw):
        return True

    # 5) Keep normal warnings if configured.
    if keep_all_warnings and has_warning(raw):
        return True

    # 6) Remove known noisy categories and generic editor/cache/package lines.
    if category in NOISY_CATEGORIES:
        return False

    if matches_any(raw, NOISY_LINE_PATTERNS):
        return False

    # 7) Keep relevant project/runtime lines, especially AI, fitness, generation and traffic events.
    if PROJECT_RUNTIME_RE.search(raw):
        return True

    # 8) Keep ordinary warnings that were not identified as noise.
    if has_warning(raw):
        return True

    # 9) Everything else is considered irrelevant.
    return False


def starts_critical_block(line: str) -> bool:
    return bool(
        re.search(
            r"\b(Fatal|Unhandled Exception|Assertion failed|Ensure condition failed|Callstack|DXGI_ERROR|DEVICE_HUNG|GPUCrash)\b",
            line,
            re.IGNORECASE,
        )
    )


def clean_log(input_path: Path, output_path: Path, keep_all_warnings: bool = DEFAULT_KEEP_ALL_WARNINGS) -> None:
    total_lines = 0
    kept_lines = 0
    removed_lines = 0
    context_lines_left = 0

    # Mode "w" overwrites clean_run_output.txt if it already exists.
    with input_path.open("r", encoding="utf-8", errors="ignore") as infile, \
         output_path.open("w", encoding="utf-8", errors="ignore") as outfile:

        for line in infile:
            total_lines += 1

            keep = should_keep_line(line, keep_all_warnings=keep_all_warnings)

            # After a real fatal/crash/ensure/callstack line, keep a small context block.
            if not keep and context_lines_left > 0 and line.strip():
                keep = True
                context_lines_left -= 1

            if keep:
                outfile.write(line)
                kept_lines += 1

                if starts_critical_block(line):
                    context_lines_left = CONTEXT_LINES_AFTER_CRITICAL
            else:
                removed_lines += 1

    print("Cleaning completed")
    print(f"Input file:     {input_path}")
    print(f"Output file:    {output_path}")
    print(f"Total lines:    {total_lines}")
    print(f"Kept lines:     {kept_lines}")
    print(f"Removed lines:  {removed_lines}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Clean Unreal Engine logs by keeping relevant warnings, errors, Blueprint messages, "
            "fitness/generation events and project runtime information."
        )
    )

    parser.add_argument(
        "input_file",
        help="Path to the original Unreal .log or .txt file",
    )

    parser.add_argument(
        "--keep-all-warnings",
        action="store_true",
        help="Keep every line containing 'Warning', including EOS/HTTP/editor warning spam.",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    script_folder = Path(__file__).resolve().parent
    output_path = script_folder / OUTPUT_FILENAME

    clean_log(
        input_path=input_path,
        output_path=output_path,
        keep_all_warnings=args.keep_all_warnings,
    )


if __name__ == "__main__":
    main()
