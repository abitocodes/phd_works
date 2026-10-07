$ErrorActionPreference = "Stop"

$tex = "Proposal-Final_Taehong Kwon.direct.tex"

xelatex -interaction=nonstopmode $tex
xelatex -interaction=nonstopmode $tex

Write-Host "Built Proposal-Final_Taehong Kwon.direct.pdf"
