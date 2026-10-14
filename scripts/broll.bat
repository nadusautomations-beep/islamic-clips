@echo off
rem One-word shortcut for search_broll.py. Must sit in the same folder as
rem search_broll.py (keep both files together wherever you download them).
rem
rem Usage:
rem   broll forest
rem   broll "mountain sunrise drone" mountains
rem
rem First argument = what to search for (quote it if more than one word).
rem Second argument (optional) = topic label for the output filename.
rem If you skip the second argument, the first one is used for both.

if "%~1"=="" (
    echo Usage: broll "search terms" [topic_label]
    echo Example: broll "forest mist nature" forest
    exit /b 1
)

set QUERY=%~1
if "%~2"=="" (
    set TOPIC=%~1
) else (
    set TOPIC=%~2
)

python "%~dp0search_broll.py" "%QUERY%" --topic "%TOPIC%"
