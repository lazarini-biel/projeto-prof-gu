# Cria atalhos do SPARTA na Area de Trabalho, apontando para os .exe gerados.
# Uso:  powershell -File criar_atalhos.ps1 -Dist "C:\...\dist"
param(
  [Parameter(Mandatory=$true)][string]$Dist
)

$ErrorActionPreference = "Stop"
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell

$apps = @(
  @{ Nome = "SPARTA";              Exe = "SPARTA.exe"      },
  @{ Nome = "SPARTA - Cofre";      Exe = "Cofre.exe"       },
  @{ Nome = "SPARTA - Explorador"; Exe = "Explorador.exe"  },
  @{ Nome = "SPARTA - Mixer";      Exe = "Mixer.exe"       }
)

foreach ($a in $apps) {
  $alvo = Join-Path $Dist $a.Exe
  if (-not (Test-Path $alvo)) {
    Write-Host ("  (pulei " + $a.Nome + ": " + $a.Exe + " nao encontrado)")
    continue
  }
  $lnk = Join-Path $desktop ($a.Nome + ".lnk")
  $atalho = $shell.CreateShortcut($lnk)
  $atalho.TargetPath = $alvo
  $atalho.WorkingDirectory = $Dist
  $atalho.IconLocation = $alvo + ",0"
  $atalho.Description = $a.Nome
  $atalho.Save()
  Write-Host ("  OK: " + $a.Nome)
}

Write-Host "Atalhos criados na Area de Trabalho."
