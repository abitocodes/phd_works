$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# Tables under tables/ come from ..\scripts\toy_sybil_example.py --latex; do not edit them by hand.
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex

Write-Host "Built main.pdf"
