$ErrorActionPreference = 'Stop'

$Root = 'C:\BLANCO_ASOCIADOS_AI'
$Repo = Join-Path $Root 'repo-control'
$Remote = 'https://github.com/roberal82/sic-ba-inteligencia-comercial.git'

New-Item -ItemType Directory -Force -Path $Root | Out-Null

if (-not (Test-Path $Repo)) {
    git clone $Remote $Repo
}

Set-Location $Repo
git fetch --all --prune

function Add-AgentWorktree {
    param(
        [string]$LocalBranch,
        [string]$RemoteBranch,
        [string]$Path
    )

    if (Test-Path $Path) {
        Write-Host "Worktree ya existe: $Path"
        return
    }

    $localExists = git branch --list $LocalBranch
    if ($localExists) {
        git worktree add $Path $LocalBranch
    } else {
        git worktree add --track -b $LocalBranch $Path "origin/$RemoteBranch"
    }
}

Add-AgentWorktree 'sprint/001-erp-drift' 'sprint/001-erp-drift' (Join-Path $Root 'sprint-control')
Add-AgentWorktree 'agent/claude-drift' 'agent/claude-drift' (Join-Path $Root 'claude-builder')
Add-AgentWorktree 'agent/codex-drift' 'agent/codex-drift' (Join-Path $Root 'codex-review')
Add-AgentWorktree 'agent/hermes-drift' 'agent/hermes-drift' (Join-Path $Root 'hermes-worker')
Add-AgentWorktree 'agent/gemini-drift' 'agent/gemini-drift' (Join-Path $Root 'gemini-validator')

$PrivateRoot = Join-Path $Root 'private-data'
@('input','staging','snapshots','outputs','logs') | ForEach-Object {
    New-Item -ItemType Directory -Force -Path (Join-Path $PrivateRoot $_) | Out-Null
}

Write-Host ''
Write-Host 'Sprint 001 preparado.'
Write-Host "Control:  $Root\sprint-control"
Write-Host "Claude:   $Root\claude-builder"
Write-Host "Codex:    $Root\codex-review"
Write-Host "Hermes:   $Root\hermes-worker"
Write-Host "Gemini:   $Root\gemini-validator"
Write-Host "Privado:  $Root\private-data"
Write-Host ''
Write-Host 'IMPORTANTE: private-data nunca debe subirse a GitHub.'
