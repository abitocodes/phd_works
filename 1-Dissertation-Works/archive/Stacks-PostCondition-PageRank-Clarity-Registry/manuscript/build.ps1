$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

# tables/의 표는 ..\scripts\toy_sybil_example.py --latex가 만든다. 손으로 고치지 않는다.
xelatex -interaction=nonstopmode main.tex
xelatex -interaction=nonstopmode main.tex

Write-Host "main.pdf를 만들었습니다"
