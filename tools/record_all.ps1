# Enregistre automatiquement une série de runs étiquetés (PowerShell). À lancer depuis le dossier du projet :
#     .\tools\record_all.ps1                 # 3 runs de chaque profil, 800 s chacun (~3 h 15 au total)
#     .\tools\record_all.ps1 -Reps 1 -Duration 300   # essai rapide
# Prérequis : le nœud tourne (docker compose --profile node up -d), $env:EVA_PRIVATE_KEY est défini.
param(
  [int]$Reps = 3,
  [int]$Duration = 800,
  [string]$Rpc = "http://127.0.0.1:8545",
  [string]$Met = "http://127.0.0.1:6060/debug/metrics/prometheus",
  [string]$Container = "eva-guard-geth-1"
)
$ErrorActionPreference = "Stop"

# 1) contrôles avant de commencer
try {
  $r = Invoke-RestMethod -Uri $Rpc -Method Post -ContentType "application/json" -Body '{"jsonrpc":"2.0","id":1,"method":"net_peerCount","params":[]}'
  Write-Host "RPC ok (net_peerCount = $($r.result))"
} catch { Write-Host "RPC injoignable sur $Rpc : lancez d'abord le noeud."; exit 1 }
try {
  $null = Invoke-WebRequest -UseBasicParsing -Uri $Met -TimeoutSec 5
  Write-Host "Métriques ok"
} catch { Write-Host "ATTENTION : métriques injoignables ($Met). Les colonnes de trafic seront vides." }
if (-not $env:EVA_PRIVATE_KEY) { Write-Host "EVA_PRIVATE_KEY manquante : seuls les runs idle seront possibles."; exit 1 }

# 2) boucle : un profil après l'autre (jamais en parallèle : même noeud)
$profiles = @("idle", "moderate", "high", "restart", "burst")
$i = 0; $total = $profiles.Count * $Reps
for ($k = 1; $k -le $Reps; $k++) {
  foreach ($p in $profiles) {
    $i++
    Write-Host "=== Run $i / $total : $p (répétition $k) ==="
    py tools/run_session.py --profile $p --rpc $Rpc --metrics $Met --container $Container --duration $Duration
    if ($LASTEXITCODE -ne 0) { Write-Host "Echec du run $p : arrêt."; exit 1 }
    Start-Sleep -Seconds 60   # laisse le noeud se stabiliser entre deux runs
  }
}
Write-Host "Terminé. Contrôle : py -m eva_guard.real_check --manifest results/runs/manifest.csv"
