param(
    [string]$BaseRef = "upstream/develop",
    [string]$HeadRef = "HEAD"
)

$ErrorActionPreference = "Stop"

git rev-parse --verify $BaseRef | Out-Null
git rev-parse --verify $HeadRef | Out-Null

"path`tupstream_blob`thead_blob`tadded`tdeleted`texact_zero_context_ranges"

$paths = git diff --name-only --diff-filter=M "$BaseRef...$HeadRef"
foreach ($path in $paths) {
    git cat-file -e "${BaseRef}:$path" 2>$null
    if ($LASTEXITCODE -ne 0) { continue }

    $upstreamBlob = (git rev-parse "${BaseRef}:$path").Trim()
    $headBlob = (git rev-parse "${HeadRef}:$path").Trim()
    $numstat = (git diff --numstat "$BaseRef...$HeadRef" -- $path) -split "`t"
    $ranges = git diff --unified=0 "$BaseRef...$HeadRef" -- $path |
        Select-String '^@@' |
        ForEach-Object {
            if ($_.Line -match '^@@\s+(-[^ ]+)\s+(\+[^ ]+)') {
                "$($Matches[1])/$($Matches[2])"
            }
        }

    "$path`t$upstreamBlob`t$headBlob`t$($numstat[0])`t$($numstat[1])`t$($ranges -join ',')"
}
