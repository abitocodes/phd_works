$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Full dissertation (writes Chapter-0N/Chapter-0N.aux checkpoints and main.aux)
xelatex -interaction=nonstopmode main.tex
if ($LASTEXITCODE -ne 0) { throw "xelatex main.tex (pass 1) failed" }
xelatex -interaction=nonstopmode main.tex
if ($LASTEXITCODE -ne 0) { throw "xelatex main.tex (pass 2) failed" }

# Preserve chapter aux from the full build; per-chapter runs would otherwise overwrite page checkpoints
$auxBackup = Join-Path $PSScriptRoot "_chapter_aux_backup"
New-Item -ItemType Directory -Force -Path $auxBackup | Out-Null
foreach ($n in 1..8) {
  $nn = "{0:D2}" -f $n
  Copy-Item -Force "Chapter-$nn/Chapter-$nn.aux" "$auxBackup/Chapter-$nn.aux"
}

function Restore-ChapterAux {
  foreach ($n in 1..8) {
    $nn = "{0:D2}" -f $n
    Copy-Item -Force "$auxBackup/Chapter-$nn.aux" "Chapter-$nn/Chapter-$nn.aux"
  }
}

function Get-ChapterStartPage([int]$n) {
  $nn = "{0:D2}" -f $n
  $aux = Get-Content -Raw "Chapter-$nn/Chapter-$nn.aux"
  $m = [regex]::Match($aux, 'contentsline \{chapter\}.*\{(\d+)\}\{chapter\.' + $n + '\}')
  if (-not $m.Success) { throw "Could not parse start page for Chapter $n" }
  return [int]$m.Groups[1].Value
}

# Per-chapter PDFs: reuse main.aux + preserved chapter aux so page/chapter counters match main.pdf
foreach ($n in 1..8) {
  Restore-ChapterAux
  Copy-Item -Force main.aux "Chapter-$n.aux"
  if (Test-Path main.out) {
    Copy-Item -Force main.out "Chapter-$n.out"
  }
  $startPage = Get-ChapterStartPage $n
  xelatex -interaction=nonstopmode -jobname="Chapter-$n" `
    "\def\ChapterOnly{$n}\def\ChapterStartPage{$startPage}\input{main.tex}"
  if ($LASTEXITCODE -ne 0) { throw "xelatex Chapter-$n failed" }
}

Restore-ChapterAux
Write-Host "Built main.pdf and Chapter-1.pdf .. Chapter-8.pdf"
